"""The database mapper: the memory mapper's arithmetic, persisted.

The reverse table is cached for a few seconds per process and dropped on
every insert, so a reply can be reversed without a query per token.
"""

from __future__ import annotations

import time

from sage_is_ai.models.privacy import PrivacyMaps
from sage_is_ai.privacy.engine import MemoryMapper

_CACHE: dict = {"pairs": None, "at": 0.0}
_TTL_S = 5.0


class DbMapper(MemoryMapper):
    def lookup(self, category: str, real: str) -> str | None:
        return PrivacyMaps.get_fake(category, real.strip())

    def owner(self, fake: str) -> tuple[str, str] | None:
        return PrivacyMaps.get_owner(fake)

    def store(self, category: str, real: str, fake: str) -> None:
        PrivacyMaps.insert(category, real.strip(), fake)
        invalidate()

    def reverse_table(self) -> dict[str, str]:
        now = time.monotonic()
        if _CACHE["pairs"] is None or now - _CACHE["at"] > _TTL_S:
            _CACHE["pairs"] = dict(PrivacyMaps.pairs())
            _CACHE["at"] = now
        return _CACHE["pairs"]


def invalidate() -> None:
    _CACHE["pairs"] = None
