"""Offline minisign verification for Sprig™ artifacts.

Verifies the standard minisign format (https://jedisct1.github.io/minisign/)
with no new dependencies and no network: blake2b from the stdlib, Ed25519 from
the ``cryptography`` package already in the base image. Anyone outside can
verify the same artifacts with the stock ``minisign -V`` CLI; this module is
the in-Rootstock™ half of that contract.

Why minisign and not sigstore keyless: verification here must work offline and
air-gapped (the registry pull is the only permitted network op, and boot
reconcile re-verifies with NO network at all). Keyless cosign needs the Fulcio/
Rekor trust roots and a transparency-log round-trip; a pinned Ed25519 public
key ships inside the image, next to the sha256 pins it complements.

Trust model: the sha256 pin in the catalog remains the allowlist (which exact
bytes may graft). The signature adds publisher provenance on top — it proves
the artifact was signed by the holder of the Sage.is signing key, which is
what makes mirrors and a future marketplace auditable.
"""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

_CHUNK = 1 << 16

# minisign algorithm tags (first 2 bytes of the base64 payloads)
_ALG_PUBKEY = b"Ed"      # public key files
_ALG_PREHASH = b"ED"     # signature over blake2b-512 of the file (minisign default)
_ALG_LEGACY = b"Ed"      # signature over the raw file (pre-0.7 legacy)


class MinisignError(Exception):
    """Any parse or verification failure. Callers treat this as tampering."""


def _b64_field(line: str, what: str) -> bytes:
    try:
        return base64.b64decode(line.strip(), validate=True)
    except Exception as exc:  # binascii.Error, ValueError
        raise MinisignError(f"{what}: invalid base64") from exc


def parse_public_key(pubkey_b64: str) -> tuple[bytes, Ed25519PublicKey]:
    """Parse the one-line base64 form of a minisign public key.

    (That is the second line of a ``.pub`` file: alg(2) || key_id(8) || key(32).)
    Returns (key_id, loaded key).
    """
    raw = _b64_field(pubkey_b64, "public key")
    if len(raw) != 42 or raw[:2] != _ALG_PUBKEY:
        raise MinisignError(
            f"public key: expected 42 bytes starting 'Ed', got {len(raw)} bytes"
        )
    key_id, key_bytes = raw[2:10], raw[10:42]
    try:
        return key_id, Ed25519PublicKey.from_public_bytes(key_bytes)
    except Exception as exc:
        raise MinisignError(f"public key: not a valid Ed25519 key: {exc}") from exc


def _parse_sig_file(sig_path: Path) -> tuple[bytes, bytes, bytes, bytes, str]:
    """Parse a ``.minisig`` file.

    Returns (alg, key_id, signature, global_sig, trusted_comment).
    """
    try:
        lines = sig_path.read_text("utf-8").splitlines()
    except OSError as exc:
        raise MinisignError(f"cannot read signature file {sig_path.name}: {exc}") from exc
    if len(lines) < 4:
        raise MinisignError(f"{sig_path.name}: expected 4 lines, got {len(lines)}")

    sig_doc = _b64_field(lines[1], f"{sig_path.name} signature")
    if len(sig_doc) != 74:
        raise MinisignError(f"{sig_path.name}: signature block is {len(sig_doc)} bytes, want 74")
    alg, key_id, signature = sig_doc[:2], sig_doc[2:10], sig_doc[10:74]

    trusted_prefix = "trusted comment: "
    if not lines[2].startswith(trusted_prefix):
        raise MinisignError(f"{sig_path.name}: line 3 is not a trusted comment")
    trusted_comment = lines[2][len(trusted_prefix):]

    global_sig = _b64_field(lines[3], f"{sig_path.name} global signature")
    if len(global_sig) != 64:
        raise MinisignError(f"{sig_path.name}: global signature is {len(global_sig)} bytes, want 64")

    return alg, key_id, signature, global_sig, trusted_comment


def verify_file(path: Path, sig_path: Path, pubkey_b64: str) -> str:
    """Verify ``path`` against its minisign signature. Returns the trusted comment.

    Raises MinisignError on ANY mismatch — wrong key, wrong algorithm, edited
    trusted comment, or content drift. Callers must not extract on failure.
    """
    key_id, pubkey = parse_public_key(pubkey_b64)
    alg, sig_key_id, signature, global_sig, trusted_comment = _parse_sig_file(sig_path)

    if sig_key_id != key_id:
        raise MinisignError(
            f"{sig_path.name}: signed by key {sig_key_id.hex()}, "
            f"but the pinned key is {key_id.hex()}"
        )

    if alg == _ALG_PREHASH:
        h = hashlib.blake2b(digest_size=64)
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(_CHUNK), b""):
                h.update(chunk)
        message = h.digest()
    elif alg == _ALG_LEGACY:
        message = path.read_bytes()
    else:
        raise MinisignError(f"{sig_path.name}: unknown algorithm {alg!r}")

    try:
        pubkey.verify(signature, message)
    except InvalidSignature as exc:
        raise MinisignError(
            f"signature verification FAILED for {path.name}: content does not "
            f"match what the key holder signed"
        ) from exc

    # The trusted comment is covered by a second signature; verify it so a
    # tampered comment (e.g. a swapped version string) is also fatal.
    try:
        pubkey.verify(global_sig, signature + trusted_comment.encode("utf-8"))
    except InvalidSignature as exc:
        raise MinisignError(
            f"trusted comment verification FAILED for {sig_path.name}"
        ) from exc

    return trusted_comment
