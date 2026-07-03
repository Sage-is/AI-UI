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

DEFERRED to graft #3.1: cosign/sigstore keyless verify, multi-blob manifests,
torch-cultivar bundling, restart/backoff/state.json. The sha256 pin + the image
build audit trail is the trust anchor for this cut.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import shutil
from pathlib import Path

log = logging.getLogger("sprig.artifact")

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


async def ensure(spec: dict, data_dir: Path, catalog_name: str) -> str:
    """Pull → verify → extract → seed. Returns the chroma cache dir to serve from.

    Idempotent: if the ONNX sentinel already exists in the cache, returns
    immediately without touching the network (offline-safe restart / re-graft).

    Raises ArtifactError subclasses; graft() maps these to a clear graft failure
    and prunes the half-grafted sprig.
    """
    # Two seed modes:
    #   "chroma-onnx" -> extract MiniLM weights into chromadb's cache; serve via the
    #                    onnx backend (DefaultEmbeddingFunction). Returns the cache dir.
    #   "model-dir"   -> extract model.onnx + tokenizer.json; serve via the
    #                    onnx-transformer backend. Returns the extracted model dir.
    seed_mode = spec.get("seed", "chroma-onnx")
    root = _artifact_root(data_dir, catalog_name)
    extract_dir = root / "extracted"

    # "app-dir": deliver toolchain/assets straight into a target path (e.g. the
    # tar carries node_modules/ and we extract it into /app). No server, no cache.
    if seed_mode == "app-dir":
        target = Path(spec.get("target", "/app"))
        sentinel = target / spec.get("sentinel", "")
        if spec.get("sentinel") and sentinel.exists():
            log.warning("delivery '%s' already present at %s; skipping pull",
                        catalog_name, sentinel)
            return str(target)
        repo = spec.get("repo")
        tag = spec.get("tag", "latest")
        expected_sha = spec.get("binary_sha256")
        insecure = bool(spec.get("insecure", False))
        if not repo or not expected_sha:
            raise ArtifactError(
                f"cultivar '{catalog_name}' delivery=oci-artifact requires "
                f"'repo' and 'binary_sha256'."
            )
        staging = root / ".staging"
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        staging.mkdir(parents=True, exist_ok=True)
        tar_zst = await _pull(repo, tag, staging, insecure=insecure)
        await _verify_sha256(tar_zst, expected_sha)
        await _extract(tar_zst, target)  # extract the packed tree into target
        if spec.get("sentinel") and not sentinel.exists():
            raise ArtifactExtractionError(
                f"delivery '{catalog_name}' missing {sentinel} after extract"
            )
        log.warning("delivered '%s' from %s:%s -> %s", catalog_name, repo, tag, target)
        return str(target)

    if seed_mode == "model-dir":
        # Spec-driven sentinel: onnx cultivars ship model.onnx (default),
        # llama-binary cultivars ship model.gguf.
        sentinel = extract_dir / spec.get("sentinel", "model.onnx")
        serve_path = extract_dir
    else:
        serve_path = _chroma_cache_dir(data_dir)
        sentinel = serve_path.joinpath(*_ONNX_SENTINEL)

    if sentinel.exists():
        log.warning(
            "artifact already present for '%s' (%s); skipping pull", catalog_name, sentinel
        )
        return str(serve_path)

    repo = spec.get("repo")
    tag = spec.get("tag", "latest")
    expected_sha = spec.get("binary_sha256")
    insecure = bool(spec.get("insecure", False))
    if not repo or not expected_sha:
        raise ArtifactError(
            f"cultivar '{catalog_name}' delivery=oci-artifact requires "
            f"'repo' and 'binary_sha256' in the catalog."
        )

    staging = root / ".staging"
    if staging.exists():
        shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True, exist_ok=True)

    tar_zst = await _pull(repo, tag, staging, insecure=insecure)
    await _verify_sha256(tar_zst, expected_sha)  # gate extraction on integrity
    await _extract(tar_zst, extract_dir)

    if seed_mode == "model-dir":
        expected = spec.get("sentinel", "model.onnx")
        if not (extract_dir / expected).exists():
            raise ArtifactExtractionError(
                f"artifact for '{catalog_name}' is missing {expected} (seed=model-dir)"
            )
        log.warning(
            "artifact extracted for '%s' from %s:%s -> %s",
            catalog_name, repo, tag, extract_dir,
        )
        return str(extract_dir)

    cache_dir = _chroma_cache_dir(data_dir)
    await _seed_chroma_cache(extract_dir, cache_dir)
    log.warning(
        "artifact seeded for '%s' from %s:%s -> %s", catalog_name, repo, tag, cache_dir
    )
    return str(cache_dir)
