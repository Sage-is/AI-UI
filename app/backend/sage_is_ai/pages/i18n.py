"""Server-side translation for rendered pages.

The backend already talks in translation keys instead of English: a diagnostics
row carries `summary_key` and `summary_params`, never a sentence. So there was
nothing to write here except a reader. The words live in
`app/src/lib/i18n/locales/` and both sides read the same catalog.

Not done yet: anything but English. The image ships `en-US` and nothing else, so
a migrated page comes out in English no matter who is reading it. That is fine
while these pages are additive and the SPA still serves every route a user
reaches, but multi-locale support has to land before any of them takes over a
real route.

The other 55 catalogs are small. Copying them in is easy. The problem is that
the reader's language lives in `localStorage`, which the server never sees.
Fixing that means a locale cookie or `Accept-Language`, and that work belongs
with the rest of the Phase 3 shell.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

__all__ = ["t"]

_LOCALES = Path(__file__).resolve().parents[2] / "locales"
_INTERP = re.compile(r"{{\s*([A-Za-z0-9_]+)\s*}}")


@lru_cache(maxsize=4)
def _catalog(locale: str) -> dict:
    """Load a catalog once. A missing or malformed file is not fatal.

    Rendering raw keys looks bad, but a 500 on the diagnostics page is worse.
    That page is what an operator opens when something is already broken.
    """
    path = _LOCALES / locale / "translation.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def t(key: str, params: dict[str, Any] | None = None, *, locale: str = "en-US") -> str:
    """Resolve a dotted i18next key and fill in any `{{name}}` placeholders.

    Returns the key itself when it does not resolve, the same as i18next. An
    untranslated key on screen at least tells you which one to add.
    """
    node: Any = _catalog(locale)
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return key
        node = node[part]
    if not isinstance(node, str):
        return key
    if not params:
        return node
    return _INTERP.sub(lambda m: str(params.get(m.group(1), m.group(0))), node)
