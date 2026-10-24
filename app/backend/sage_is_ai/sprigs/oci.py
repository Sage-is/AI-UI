"""Pull a Sprig™ OCI artifact over HTTP(S). Replaced the ``oras`` CLI in 3.2.1.

A Sprig artifact is one per-arch OCI manifest whose layers are plain files,
each named by its ``org.opencontainers.image.title`` annotation (what
``oras push`` writes). Pulling it is the manifest plus one blob per titled
layer. Doing that here drops a Go binary and its CVE stream from the image.

Refused, each pinned in ``test_oci.py``: plain HTTP unless ``insecure=True``;
an image index; a layer title that is not a plain file name; a non-sha256
digest; a blob whose bytes or length differ from the manifest; a layer over
``SPRIG_MAX_ARTIFACT_BYTES`` (default 8 GiB). Pulls are anonymous: a Bearer
challenge gets an anonymous token, as ghcr.io serves public packages. httpx
drops Authorization when a blob redirects to another host. artifact.py still
checks the catalog's sha256 pin afterwards.
"""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

TITLE_ANNOTATION = "org.opencontainers.image.title"
MANIFEST_ACCEPT = ", ".join(
    (
        "application/vnd.oci.image.manifest.v1+json",
        "application/vnd.docker.distribution.manifest.v2+json",
        "application/vnd.oci.image.index.v1+json",
        "application/vnd.docker.distribution.manifest.list.v2+json",
    )
)
_INDEX_TYPES = frozenset(
    (
        "application/vnd.oci.image.index.v1+json",
        "application/vnd.docker.distribution.manifest.list.v2+json",
    )
)
_SAFE_TITLE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,254}")
_SHA256_DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
_MAX_MANIFEST_BYTES = 4 << 20
_CHUNK = 1 << 16


def max_layer_bytes() -> int:
    return int(os.environ.get("SPRIG_MAX_ARTIFACT_BYTES", str(8 << 30)))


class OCIError(Exception):
    """The pull failed: unreachable, refused, or not a Sprig-shaped artifact."""


class OCIDigestError(OCIError):
    """A blob's bytes do not match its manifest digest or size. Do not use it."""


def split_reference(repo: str) -> tuple[str, str]:
    """``host[:port]/name/space`` -> (host, name)."""
    host, sep, name = repo.strip().partition("/")
    if not sep or not host or not name:
        raise OCIError(f"registry reference must be host/name, got {repo!r}")
    return host, name


def safe_title(title: object) -> str:
    if not isinstance(title, str) or not _SAFE_TITLE.fullmatch(title) or ".." in title:
        raise OCIError(f"refusing layer title {title!r}: not a plain file name")
    return title


def parse_bearer_challenge(header: str) -> dict[str, str]:
    scheme, _, params = header.strip().partition(" ")
    if scheme.lower() != "bearer":
        raise OCIError(
            f"registry asked for {scheme or 'unknown'} auth; only anonymous Bearer is supported"
        )
    found = dict(re.findall(r'(\w+)="([^"]*)"', params))
    if "realm" not in found:
        raise OCIError("Bearer challenge without a realm")
    return found


def _checked_layer(layer: dict, title: str, limit: int) -> tuple[str, str, int]:
    """One titled layer's (title, digest, size), or the reason it is refused."""
    digest = layer.get("digest", "")
    if not isinstance(digest, str) or not _SHA256_DIGEST.fullmatch(digest):
        raise OCIError(f"layer {title!r}: unsupported digest {digest!r}")
    size = layer.get("size")
    if not isinstance(size, int) or isinstance(size, bool) or size < 0:
        raise OCIError(f"layer {title!r}: invalid size {size!r}")
    if size > limit:
        raise OCIError(
            f"layer {title!r}: {size} bytes is over SPRIG_MAX_ARTIFACT_BYTES={limit}"
        )
    return safe_title(title), digest, size


def titled_layers(manifest: dict) -> list[tuple[str, str, int]]:
    """(title, digest, size) for every titled layer; refuses anything unexpected."""
    if manifest.get("mediaType") in _INDEX_TYPES or "manifests" in manifest:
        raise OCIError(
            "got an image index, not a manifest: Sprig tags are one per arch "
            "(e.g. v2 and v2-amd64); check the catalog tag"
        )
    limit = max_layer_bytes()
    out = [
        _checked_layer(layer, title, limit)
        for layer in manifest.get("layers") or []
        # oras pull skipped untitled layers too
        if (title := (layer.get("annotations") or {}).get(TITLE_ANNOTATION)) is not None
    ]
    names = [t for t, _, _ in out]
    if not out:
        raise OCIError("manifest has no titled layers")
    if len(set(names)) != len(names):
        raise OCIError(f"manifest repeats a layer title: {names}")
    return out


async def pull(repo: str, tag: str, dest: Path, *, insecure: bool) -> list[Path]:
    """Download every titled layer of ``repo:tag`` into ``dest``; return the files."""
    import httpx

    host, name = split_reference(repo)
    base = f"{'http' if insecure else 'https'}://{host}/v2/{name}"
    dest.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(60.0, connect=15.0),
        follow_redirects=True,
        headers={"User-Agent": "sage-is-ai-ui-sprig-pull"},
    ) as client:
        auth: dict[str, str] = {}

        async def get(url: str, headers: dict[str, str]):
            nonlocal auth
            r = await client.get(url, headers={**headers, **auth})
            if r.status_code == 401 and not auth:
                challenge = parse_bearer_challenge(
                    r.headers.get("www-authenticate", "")
                )
                params = {
                    "service": challenge.get("service", host),
                    "scope": challenge.get("scope", f"repository:{name}:pull"),
                }
                t = await client.get(challenge["realm"], params=params)
                t.raise_for_status()
                body = t.json()
                token = body.get("token") or body.get("access_token")
                if not token:
                    raise OCIError(f"{challenge['realm']} returned no token")
                auth = {"Authorization": f"Bearer {token}"}
                r = await client.get(url, headers={**headers, **auth})
            return r

        try:
            r = await get(f"{base}/manifests/{tag}", {"Accept": MANIFEST_ACCEPT})
            if r.status_code == 404:
                raise OCIError(f"{repo}:{tag} not found")
            r.raise_for_status()
            if len(r.content) > _MAX_MANIFEST_BYTES:
                raise OCIError("manifest too large")
            files: list[Path] = []
            for title, digest, size in titled_layers(r.json()):
                url = f"{base}/blobs/{digest}"
                files.append(
                    await _fetch_blob(client, url, auth, dest, title, digest, size)
                )
            return files
        except httpx.HTTPError as exc:
            raise OCIError(f"{type(exc).__name__}: {exc}") from exc
        except ValueError as exc:  # a body that is not JSON
            raise OCIError(f"registry sent unreadable JSON: {exc}") from exc


async def _fetch_blob(client, url, auth, dest: Path, title, digest, size) -> Path:
    """Stream one blob to ``dest/title``, refusing a byte the manifest did not promise."""
    target = dest / title
    part = dest / f".{title}.part"
    h = hashlib.sha256()
    got = 0
    try:
        async with client.stream("GET", url, headers=auth) as r:
            r.raise_for_status()
            with part.open("wb") as fh:
                async for chunk in r.aiter_bytes(_CHUNK):
                    got += len(chunk)
                    if got > size:
                        raise OCIDigestError(
                            f"{title}: more bytes than the manifest's {size}"
                        )
                    h.update(chunk)
                    fh.write(chunk)
        if got != size:
            raise OCIDigestError(f"{title}: got {got} bytes, manifest says {size}")
        if f"sha256:{h.hexdigest()}" != digest:
            raise OCIDigestError(f"{title}: blob does not hash to {digest}")
        part.replace(target)
        return target
    finally:
        part.unlink(missing_ok=True)
