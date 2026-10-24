"""Password hashing: bcrypt, called directly (no passlib since 3.2.1).

passlib 1.7.4 is the last release (2020) and can no longer read the bcrypt
module's version; ``utils/auth.py`` used to mute its logger to hide that error.
These two functions reproduce exactly what passlib did for this app, so every
hash already stored keeps verifying:

- ``$2b$`` hashes at 12 rounds, the passlib default.
- ``$2a$`` and ``$2y$`` hashes verify too; both are the same algorithm.
- Input is cut to 72 bytes of UTF-8. bcrypt reads no further, passlib cut
  silently, and bcrypt 5 raises instead of cutting.

Pinned by ``test_passwords.py`` against hashes passlib itself produced.
"""

from __future__ import annotations

import bcrypt

BCRYPT_MAX_BYTES = 72
BCRYPT_ROUNDS = 12


def _bcrypt_input(password: str) -> bytes:
    return password.encode("utf-8")[:BCRYPT_MAX_BYTES]


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(
        _bcrypt_input(password), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    ).decode("ascii")


def verify_password(plain_password: str, hashed_password: str | None) -> bool | None:
    """True or False for a bcrypt hash; None when there is no hash to check.

    A stored value that is not a bcrypt hash is a failed check, never an
    exception. passlib raised UnknownHashError or ValueError there.
    """
    if not hashed_password:
        return None
    stored = hashed_password.encode("ascii", "replace")
    if stored.startswith(b"$2y$"):
        # PHP's name for the corrected algorithm; identical to $2b$.
        stored = b"$2b$" + stored[4:]
    try:
        return bcrypt.checkpw(_bcrypt_input(plain_password), stored)
    except ValueError:
        return False
