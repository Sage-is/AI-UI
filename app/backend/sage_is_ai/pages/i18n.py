"""Server-side translation for rendered pages.

The backend already talks in translation keys instead of English: a diagnostics
row carries `summary_key` and `summary_params`, never a sentence. So there was
nothing to write here except a reader. The words live in
`app/src/lib/i18n/locales/` and both sides read the same catalog.

The image ships all 56 catalogs. `locale_for` picks one per request.

This was the blocker on any page taking over a real route. The wizard carries 210
translation keys and about a quarter are translated. Serving English to a Spanish
reader would have been a regression, not a gap.

The locale travels in the URL as `?lang=`, never a cookie. `locale_for` explains
why.

Two facts govern this file. The keys ARE the English text, so an untranslated key
renders as English rather than as a blank. And `_catalog` builds a filesystem path
from its argument, so every locale is checked against `supported()` first.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

__all__ = [
    "t",
    "locale_for",
    "lang_query",
    "translator",
    "supported",
    "DEFAULT_LOCALE",
]

_LOCALES = Path(__file__).resolve().parents[2] / "locales"
_INTERP = re.compile(r"{{\s*([A-Za-z0-9_]+)\s*}}")

DEFAULT_LOCALE = "en-US"


@lru_cache(maxsize=1)
def supported() -> frozenset[str]:
    """Every locale this image actually ships, read from disk once.

    Derived rather than listed. A hand-kept list would be a second place to
    update when the Dockerfile's COPY changes, and the failure mode of getting it
    wrong is a language that silently falls back to English.
    """
    try:
        return frozenset(
            p.name for p in _LOCALES.iterdir()
            if p.is_dir() and (p / "translation.json").is_file()
        )
    except OSError:
        return frozenset({DEFAULT_LOCALE})


@lru_cache(maxsize=64)
def _catalog(locale: str) -> dict:
    """Load a catalog once. A missing or malformed file is not fatal.

    Rendering raw keys looks bad, but a 500 on the diagnostics page is worse.
    That page is what an operator opens when something is already broken.

    The membership check is load-bearing, not defensive. This builds a filesystem
    path out of `locale`. Once that value comes from a query string, a name like
    `../locales/es-ES` resolves back onto a real catalog and gets loaded. The
    check means only a shipped directory can ever be opened.

    `locale_for` filters first, so nothing reaches here unvalidated over HTTP.
    This is the backstop. Both were removed independently and each one alone
    stopped the traversal.
    """
    if locale not in supported():
        return {}
    path = _LOCALES / locale / "translation.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def t(key: str, params: dict[str, Any] | None = None, *, locale: str = DEFAULT_LOCALE) -> str:
    """Resolve a dotted i18next key and fill in any `{{name}}` placeholders.

    Returns the key itself when it does not resolve, the same as i18next. An
    untranslated key on screen at least tells you which one to add.

    **An empty value counts as unresolved.** Two key styles share this catalog.
    Diagnostics uses nested dotted keys holding real English sentences. Everything
    the SPA renders uses the English sentence AS the key. 1,511 of the 1,538
    `en-US` entries are then stored as `""`, so the extractor can see them.

    The SPA guards that with `returnEmptyString: false`
    (`src/lib/i18n/index.ts:65`). Without the same guard here, wrapping a panel
    string blanks it for every English reader. That reads as a CSS bug, not a
    locale bug, which is why it is worth the line.
    """
    node: Any = _catalog(locale)
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            node = key
            break
        node = node[part]
    if not isinstance(node, str) or node == "":
        node = key
    if not params:
        return node
    # Interpolate the fallback too, not only a hit. The key is English text, so
    # an unresolved `{{count}} users configured` must still come out as
    # `3 users configured` rather than showing the reader a pair of braces.
    return _INTERP.sub(lambda m: str(params.get(m.group(1), m.group(0))), node)


def _from_accept_language(header: str) -> str | None:
    """Best shipped catalog for an `Accept-Language` header, or None.

    Two passes, because `es-MX` should reach the `es-ES` catalog rather than fall
    to English. An exact match wins outright; failing that the primary subtag is
    matched against every shipped locale, in the order the reader asked for.
    """
    ranked: list[tuple[float, str]] = []
    for part in header.split(","):
        tag, _, rest = part.strip().partition(";")
        tag = tag.strip()
        if not tag or tag == "*":
            continue
        quality = 1.0
        if rest.startswith("q="):
            try:
                quality = float(rest[2:])
            except ValueError:
                quality = 0.0
        if quality > 0:
            ranked.append((quality, tag))
    ranked.sort(key=lambda pair: pair[0], reverse=True)

    shipped = supported()
    for _, tag in ranked:
        if tag in shipped:
            return tag
    for _, tag in ranked:
        primary = tag.split("-")[0].lower()
        for locale in sorted(shipped):
            if locale.split("-")[0].lower() == primary:
                return locale
    return None


def locale_for(request: Any) -> str:
    """The locale this request should be rendered in.

    `?lang=` wins. One URL, one language, no `Vary` — the response is cacheable on
    its address. The SPA already agrees: i18next lists `querystring` ahead of
    `localStorage` with `lookupQuerystring: 'lang'`, so one parameter drives both
    sides.

    A cookie was rejected. A response varying by cookie owes `Vary: Cookie`. The
    auth cookie shares that header, so every session becomes its own cache entry.
    Get the `Vary` wrong and a shared cache hands one admin's page to another.

    `Accept-Language` is the cold-entry fallback. Those responses carry
    `Vary: Accept-Language`; see `router._page_headers`.
    """
    asked = (request.query_params.get("lang") or "").strip()
    if asked in supported():
        return asked
    header = request.headers.get("accept-language", "")
    return (_from_accept_language(header) if header else None) or DEFAULT_LOCALE


def lang_query(request: Any) -> str:
    """`?lang=<locale>` to hang off every internal link and form action.

    Public because the panels need it too. A `<form action>` that drops the
    parameter answers a Spanish reader in English the moment they press Save.
    Twelve action strings across nine files, one helper rather than twelve
    chances to forget.
    """
    return f"?lang={locale_for(request)}"


def translator(request: Any) -> Any:
    """`t` bound to this request's locale.

    Panels take one of these and call it, rather than threading a locale string
    through every helper that renders a fragment.
    """
    locale = locale_for(request)

    def _t(key: str, params: dict[str, Any] | None = None) -> str:
        return t(key, params, locale=locale)

    return _t
