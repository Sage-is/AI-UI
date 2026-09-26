"""OCI-artifact Sprig™ delivery — graft #3 (in-house the weights, offline serve).

The Rootstock™ PULLS a tar.zst (ONNX weights + sprig.yaml manifest) from an OCI
registry via the ``oras`` CLI, verifies its sha256 against the catalog pin,
extracts it, and seeds chromadb's offline ONNX model cache. The existing
``embedding_server.py --backend onnx`` then loads from that seeded cache with NO
chroma-S3 / HuggingFace egress (chromadb's DefaultEmbeddingFunction reads
``$HOME/.cache/chroma``, which the image symlinks into ``DATA_DIR/cache/chroma``).

Proven against a LOCAL registry (localhost:5000, --plain-http). Production swap to
``ghcr.io/sage-is`` is a one-line catalog change (set ``insecure: False`` and
``oras login`` at deploy). See scripts/build-sprig-minilm.sh for the packaging side.

The verified tar is cached on the DATA volume (keyed on tag), so a re-graft after a
restart extracts offline with no network — the supervisor's boot reconcile relies on
this to restore "deliver" overlays that live in the ephemeral container layer.

Signing (graft #3.1, shipped): artifacts carry a minisign signature as a second
file in the OCI artifact (``<tar>.minisig``), verified OFFLINE after the sha256
gate and before extraction — see ``sprigs/minisign.py`` for the trust model and
the sigstore-vs-minisign rationale. Policy: a present signature is always
verified (fail-closed); a signature becomes REQUIRED per-entry via the catalog
field ``signed: True`` or globally via ``SPRIG_REQUIRE_SIGNED=1``. The pinned
public key ships in ``_DEFAULT_PUBKEY`` below (env ``SPRIG_MINISIGN_PUBKEY``
overrides, and a catalog entry may pin its own ``pubkey`` — the hook a future
marketplace needs for third-party publishers).

DEFERRED: multi-blob manifests, torch-cultivar bundling.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import shutil
from pathlib import Path

from sage_is_ai.sprigs.minisign import MinisignError, verify_file

log = logging.getLogger("sprig.artifact")

# The Sage.is artifact-signing public key (the one-line base64 form of a
# minisign .pub). Ships with the image — same trust root as the sha256 pins.
# Empty until the production keypair is generated ([MANUALLY], key custody is
# the operator's); until then only entries/envs that opt in enforce signing.
_DEFAULT_PUBKEY = ""

# chromadb DefaultEmbeddingFunction reads Path.home()/.cache/chroma/onnx_models;
# in-container $HOME/.cache/chroma is symlinked to DATA_DIR/cache/chroma (Dockerfile).
# The artifact tar is packed with that subtree at its root, so the extraction is
# copied into the chroma cache root.
_CHROMA_CACHE_SUBPATH = ("cache", "chroma")
# Sentinel proving a complete extract — the heavy model file, last we trust.
_ONNX_SENTINEL = ("onnx_models", "all-MiniLM-L6-v2", "onnx", "model.onnx")

_PULL_TIMEOUT_S = 300.0
_CHUNK = 1 << 16  # 64 KiB streaming hash


class ArtifactError(Exception):
    """Base — any failure here is surfaced by graft() as a clear graft failure."""


class ArtifactPullError(ArtifactError):
    """oras pull failed (registry unreachable, auth, missing artifact)."""


class ArtifactVerificationError(ArtifactError):
    """sha256 mismatch — corrupted or tampered artifact. Do NOT extract."""


class ArtifactExtractionError(ArtifactError):
    """tar.zst decompress/extract failed."""


class ArtifactCacheSeedError(ArtifactError):
    """Seeding the offline chroma ONNX cache failed."""


def _artifact_root(data_dir: Path, catalog_name: str) -> Path:
    """Per-cultivar working tree: DATA_DIR/sage-is/sprigs/<name>."""
    root = data_dir / "sage-is" / "sprigs" / catalog_name
    root.mkdir(parents=True, exist_ok=True)
    return root


def _chroma_cache_dir(data_dir: Path) -> Path:
    """The chroma cache root the ONNX backend reads at load time."""
    return data_dir.joinpath(*_CHROMA_CACHE_SUBPATH)


async def _run(cmd: list[str], *, timeout: float, err: type[ArtifactError]) -> None:
    """Run a subprocess, capturing stderr so the failure reason reaches the graft
    error (the supervisor DEVNULLs the *server* child, but we own these tools)."""
    log.warning("artifact exec: %s", " ".join(cmd))
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except FileNotFoundError as exc:
        raise err(f"{cmd[0]} not found on this Rootstock™ image: {exc}") from exc
    except asyncio.TimeoutError as exc:
        raise err(f"{cmd[0]} timed out after {timeout:.0f}s") from exc
    if proc.returncode != 0:
        tail = (stderr or b"").decode("utf-8", "replace").strip()[-800:]
        raise err(f"{cmd[0]} exited {proc.returncode}: {tail}")


async def _pull(repo: str, tag: str, dest: Path, *, insecure: bool) -> Path:
    """oras pull <repo>:<tag> into dest; return the produced tar.zst path."""
    uri = f"{repo}:{tag}"
    cmd = ["oras", "pull", uri, "--output", str(dest)]
    if insecure:
        cmd.append("--plain-http")  # localhost dev registry over HTTP
    await _run(cmd, timeout=_PULL_TIMEOUT_S, err=ArtifactPullError)

    tars = sorted(dest.glob("*.tar.zst"))
    if not tars:
        raise ArtifactPullError(
            f"oras pull of {uri} produced no *.tar.zst in {dest} "
            f"(got: {[p.name for p in dest.iterdir()]})"
        )
    if len(tars) > 1:
        log.warning("multiple tar.zst pulled, using %s", tars[0].name)
    return tars[0]


async def _verify_sha256(path: Path, expected: str) -> None:
    """Stream-hash the artifact and compare to the catalog pin (case-insensitive)."""

    def _hash() -> str:
        h = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(_CHUNK), b""):
                h.update(chunk)
        return h.hexdigest()

    actual = await asyncio.to_thread(_hash)
    if actual.lower() != expected.lower():
        raise ArtifactVerificationError(
            f"sha256 mismatch for {path.name}: expected {expected}, got {actual}. "
            f"Refusing to extract (corrupt or tampered artifact)."
        )
    log.warning("sha256 OK for %s (%s)", path.name, actual)


def _signing_policy(spec: dict) -> tuple[str, bool]:
    """Resolve (pubkey, required) for one cultivar.

    Precedence: catalog entry ``pubkey`` > ``SPRIG_MINISIGN_PUBKEY`` env >
    the baked ``_DEFAULT_PUBKEY``. Required when the entry says ``signed: True``
    or ``SPRIG_REQUIRE_SIGNED`` is set (a global ratchet for hardened deploys).
    """
    pubkey = (
        spec.get("pubkey")
        or os.environ.get("SPRIG_MINISIGN_PUBKEY", "").strip()
        or _DEFAULT_PUBKEY
    )
    required = bool(spec.get("signed")) or os.environ.get(
        "SPRIG_REQUIRE_SIGNED", ""
    ).lower() in ("1", "true", "yes")
    return pubkey, required


async def _verify_signature(tar_zst: Path, spec: dict, catalog_name: str) -> None:
    """Enforce the signing policy on a sha256-verified tar. Fail-closed.

    - Signature present + key pinned  -> verify (any failure refuses the graft).
    - Signature present, no key       -> refuse if required, else loud warning.
    - Signature missing               -> refuse if required, else no-op.
    """
    pubkey, required = _signing_policy(spec)
    sig = tar_zst.parent / (tar_zst.name + ".minisig")

    if not sig.exists():
        if required:
            raise ArtifactVerificationError(
                f"cultivar '{catalog_name}' requires a signed artifact, but "
                f"{tar_zst.name} has no .minisig. Refusing to extract. "
                f"(Re-publish with scripts/sign-sprigs.sh.)"
            )
        return

    if not pubkey:
        if required:
            raise ArtifactVerificationError(
                f"cultivar '{catalog_name}' requires signature verification but "
                f"no public key is pinned (catalog 'pubkey', "
                f"SPRIG_MINISIGN_PUBKEY, or _DEFAULT_PUBKEY). Refusing."
            )
        log.warning(
            "artifact for '%s' carries a signature but no public key is "
            "pinned; signature NOT verified",
            catalog_name,
        )
        return

    try:
        comment = await asyncio.to_thread(verify_file, tar_zst, sig, pubkey)
    except MinisignError as exc:
        raise ArtifactVerificationError(
            f"minisign verification failed for '{catalog_name}': {exc}. "
            f"Refusing to extract (tampered artifact or wrong signing key)."
        ) from exc
    log.warning("minisign OK for %s (%s)", tar_zst.name, comment)


async def _extract(tar_zst: Path, dest: Path) -> None:
    """Decompress + untar into dest (zstd via tar's compress-program shim)."""
    dest.mkdir(parents=True, exist_ok=True)
    await _run(
        ["tar", "--use-compress-program=zstd", "-xf", str(tar_zst), "-C", str(dest)],
        timeout=_PULL_TIMEOUT_S,
        err=ArtifactExtractionError,
    )


async def _seed_chroma_cache(extracted: Path, cache_dir: Path) -> None:
    """Copy the extracted ONNX tree into the chroma cache root the server reads.

    The tar is packed with ``onnx_models/...`` (and ``telemetry_user_id``) at its
    root, so we copy those entries into cache_dir. Copy (not symlink) for
    cross-filesystem + container-restart durability; the tree is ~80MB, one-time.
    """

    def _copy() -> None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        for entry in extracted.iterdir():
            target = cache_dir / entry.name
            if entry.is_dir():
                shutil.copytree(entry, target, dirs_exist_ok=True)
            else:
                shutil.copy2(entry, target)

    try:
        await asyncio.to_thread(_copy)
    except OSError as exc:
        raise ArtifactCacheSeedError(f"failed seeding chroma cache: {exc}") from exc

    sentinel = cache_dir.joinpath(*_ONNX_SENTINEL)
    if not sentinel.exists():
        raise ArtifactCacheSeedError(
            f"seed incomplete: {sentinel} missing after extract+copy. "
            f"Artifact layout must contain {'/'.join(_ONNX_SENTINEL)}."
        )


async def _obtain_tar(spec: dict, root: Path, catalog_name: str) -> Path:
    """Return a sha256-verified ``tar.zst`` for this cultivar, preferring the copy
    already cached on the data volume over a network pull.

    The cache path is keyed on the catalog ``tag`` (``<name>-<tag>.tar.zst`` under
    the cultivar's volume-resident root). Consequences:

    - **Restart durability / air-gap:** a re-graft after a container restart finds
      the verified tar on the volume and extracts offline — no ``oras``, no network,
      which is what makes "deliver" overlays (extracted into the ephemeral container
      layer) survive a restart.
    - **Tag-bump correctness:** bumping a cultivar's tag changes the cache key, so a
      stale-tag tar is a cache miss and forces a fresh pull (fixes the old "sentinel
      present ⇒ never re-pull" footgun for the tar side).

    On a cache miss it pulls via ``oras``, verifies against the pin BEFORE the tar
    enters the cache, promotes it to the stable path, and drops stale-tag caches.
    """
    repo = spec.get("repo")
    tag = spec.get("tag", "latest")
    expected_sha = spec.get("binary_sha256")
    insecure = bool(spec.get("insecure", False))
    if not repo or not expected_sha:
        raise ArtifactError(
            f"cultivar '{catalog_name}' delivery=oci-artifact requires "
            f"'repo' and 'binary_sha256' in the catalog."
        )

    cached = root / f"{catalog_name}-{tag}.tar.zst"
    cached_sig = root / f"{catalog_name}-{tag}.tar.zst.minisig"
    _, sig_required = _signing_policy(spec)
    if cached.exists():
        if sig_required and not cached_sig.exists():
            # The cache predates the signing requirement; the registry copy may
            # be signed by now — fall through to a fresh pull instead of failing.
            log.warning(
                "cached artifact for '%s' has no signature but one is now "
                "required; re-pulling",
                catalog_name,
            )
        else:
            try:
                await _verify_sha256(cached, expected_sha)
                await _verify_signature(cached, spec, catalog_name)
                log.warning(
                    "using volume-cached artifact for '%s' (%s); no network pull",
                    catalog_name,
                    cached.name,
                )
                return cached
            except ArtifactVerificationError:
                log.warning(
                    "cached artifact for '%s' failed verification; discarding "
                    "and re-pulling",
                    catalog_name,
                )
                cached.unlink(missing_ok=True)
                cached_sig.unlink(missing_ok=True)

    staging = root / ".staging"
    if staging.exists():
        shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True, exist_ok=True)
    tar_zst = await _pull(repo, tag, staging, insecure=insecure)
    await _verify_sha256(tar_zst, expected_sha)  # gate BEFORE it enters the cache
    await _verify_signature(tar_zst, spec, catalog_name)  # same gate discipline

    # Promote to the stable cache path; drop stale-tag caches for this cultivar.
    for old in root.glob(f"{catalog_name}-*.tar.zst"):
        if old != cached:
            old.unlink(missing_ok=True)
    for old in root.glob(f"{catalog_name}-*.tar.zst.minisig"):
        if old != cached_sig:
            old.unlink(missing_ok=True)
    pulled_sig = staging / (tar_zst.name + ".minisig")
    if pulled_sig.exists():
        pulled_sig.replace(cached_sig)
    else:
        # No signature in this publish: drop any stale one so it can't be
        # paired with the new tar (a mismatched pair must not look signed).
        cached_sig.unlink(missing_ok=True)
    tar_zst.replace(cached)
    shutil.rmtree(staging, ignore_errors=True)
    return cached


async def ensure(spec: dict, data_dir: Path, catalog_name: str) -> str:
    """Obtain (cached-or-pull) → verify → extract → seed. Returns the path to serve.

    Idempotent and offline-safe on restart/re-graft:
    - weight cultivars (model-dir / chroma-onnx) extract onto the DATA volume, so
      their sentinel survives a restart and we short-circuit with no work;
    - "deliver" overlays (app-dir) extract into the ephemeral container layer, so on
      restart the target is gone — we re-extract from the volume-cached tar
      (``_obtain_tar``, no network) and re-stamp the delivered-tag marker.

    Raises ArtifactError subclasses; graft() maps these to a clear graft failure
    and prunes the half-grafted sprig.
    """
    # Two weight seed modes:
    #   "chroma-onnx" -> extract MiniLM weights into chromadb's cache; serve via the
    #                    onnx backend (DefaultEmbeddingFunction). Returns the cache dir.
    #   "model-dir"   -> extract model.onnx + tokenizer.json; serve via the
    #                    onnx-transformer backend. Returns the extracted model dir.
    seed_mode = spec.get("seed", "chroma-onnx")
    root = _artifact_root(data_dir, catalog_name)
    extract_dir = root / "extracted"

    # "app-dir": deliver toolchain/assets into a container-layer target (e.g. the
    # tar carries node_modules/ and we extract it into /app). The target is NOT on
    # the data volume, so it vanishes on container recreation. The delivered-tag
    # marker (on the volume) + the volume-cached tar let boot re-deliver offline; we
    # re-deliver whenever the delivered tag != the catalog tag (restart or tag bump).
    if seed_mode == "app-dir":
        target = Path(spec.get("target", "/app"))
        sentinel_name = spec.get("sentinel", "")
        sentinel = target / sentinel_name
        tag = spec.get("tag", "latest")
        tag_marker = root / ".delivered-tag"
        already = (
            bool(sentinel_name)
            and sentinel.exists()
            and tag_marker.exists()
            and tag_marker.read_text().strip() == tag
        )
        if already:
            log.warning(
                "delivery '%s' tag %s already present at %s; skipping",
                catalog_name,
                tag,
                sentinel,
            )
            return str(target)
        tar_zst = await _obtain_tar(spec, root, catalog_name)
        await _extract(tar_zst, target)  # extract the packed tree into target
        if sentinel_name and not sentinel.exists():
            raise ArtifactExtractionError(
                f"delivery '{catalog_name}' missing {sentinel} after extract"
            )
        tag_marker.write_text(tag)
        log.warning("delivered '%s' tag %s -> %s", catalog_name, tag, target)
        return str(target)

    if seed_mode == "model-dir":
        # Spec-driven sentinel: onnx cultivars ship model.onnx (default),
        # llama-binary cultivars ship model.gguf.
        sentinel = extract_dir / spec.get("sentinel", "model.onnx")
        serve_path = extract_dir
    else:
        serve_path = _chroma_cache_dir(data_dir)
        sentinel = serve_path.joinpath(*_ONNX_SENTINEL)

    # Weights live on the DATA volume: this sentinel survives a restart, so a
    # re-graft short-circuits with no pull and no extract — but ONLY while the
    # delivered tag matches the catalog. An image upgrade that bumps a weight
    # cultivar's tag must re-pull, or the deployment silently serves the OLD
    # weights forever (the upgrade-path gap: sentinel-only checks can't see a
    # version change). Same `.delivered-tag` marker pattern as app-dir mode.
    tag = spec.get("tag", "latest")
    tag_marker = root / ".delivered-tag"
    if (
        sentinel.exists()
        and tag_marker.exists()
        and tag_marker.read_text().strip() == tag
    ):
        log.warning(
            "artifact already present for '%s' tag %s (%s); skipping pull",
            catalog_name,
            tag,
            sentinel,
        )
        return str(serve_path)
    if sentinel.exists():
        log.warning(
            "artifact for '%s' is a different tag (want %s); re-pulling",
            catalog_name,
            tag,
        )

    tar_zst = await _obtain_tar(spec, root, catalog_name)
    # Wipe the old extract tree first so a tag upgrade can't leave stale files
    # (e.g. an old tokenizer) mixed under the new weights.
    if extract_dir.exists():
        shutil.rmtree(extract_dir, ignore_errors=True)
    await _extract(tar_zst, extract_dir)

    if seed_mode == "model-dir":
        expected = spec.get("sentinel", "model.onnx")
        if not (extract_dir / expected).exists():
            raise ArtifactExtractionError(
                f"artifact for '{catalog_name}' is missing {expected} (seed=model-dir)"
            )
        tag_marker.write_text(tag)
        log.warning(
            "artifact extracted for '%s' tag %s -> %s", catalog_name, tag, extract_dir
        )
        return str(extract_dir)

    cache_dir = _chroma_cache_dir(data_dir)
    await _seed_chroma_cache(extract_dir, cache_dir)
    tag_marker.write_text(tag)
    log.warning("artifact seeded for '%s' tag %s -> %s", catalog_name, tag, cache_dir)
    return str(cache_dir)
