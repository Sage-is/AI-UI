"""Make every `/pages/` route reachable with or without a trailing slash.

## The failure this removes, and why nothing caught it

`/pages/workshop/agents` renders the page. `/pages/workshop/agents/` returned the
single-page-app shell with a **200**, and so did every other page under `/pages/`.
Not an error, not a 404 — the wrong page, silently, at a URL a person could
plausibly type or a link could plausibly carry.

Two mechanisms combine to produce it, and both are load-bearing elsewhere:

1. `SPAStaticFiles` is mounted at `/` with `html=True`, so **nothing under
   `/pages/` can 404** — the shell answers anything unmatched. That is
   deliberate: the SPA owns client-side routing. It also means a wrong URL is
   indistinguishable from a right one by status code, which is why the reload
   gate and the index gate both assert on page CONTENT rather than on 200.
2. Starlette's own `redirect_slashes` never gets a turn. It runs only when no
   route matched, and the catch-all mount always matches first.

The two forms were also inconsistent in opposite directions. The index is
declared `@router.get("/")` under a `/pages` prefix, so `/pages/` was the real
page and `/pages` fell through to the shell. Every other route is declared
without a trailing slash, so the slash form fell through instead. One surface,
two opposite rules, neither written down.

## What this does

A redirect rather than a silent rewrite: the address bar ends up showing the
canonical URL, so a reader who bookmarks what they see bookmarks the right thing,
and the correction is visible in the log instead of being invisible everywhere.

**307, not 308.** It preserves the method — a POSTed row action that arrives with
a trailing slash must stay a POST, or the redirect would turn a delete into a
GET and silently do nothing. 308 preserves the method too, but it is permanent
and therefore cached by browsers and proxies; a canonical-URL decision is not
worth poisoning caches over while the migration is still moving.

The query string is carried across. Losing it would drop a reader's search, tag
and page — the exact bug `_url()` exists to prevent on the way out, reappearing
on the way in.
"""

from __future__ import annotations

from starlette.datastructures import URL
from starlette.responses import RedirectResponse
from starlette.types import ASGIApp, Receive, Scope, Send

__all__ = ["PagesSlashMiddleware"]

_PREFIX = "/pages"
_INDEX = "/pages/"


class PagesSlashMiddleware:
    """Canonicalise trailing slashes for `/pages/` before the SPA mount sees them.

    Written as raw ASGI rather than `BaseHTTPMiddleware` on purpose: this has to
    decide before anything reads the body, it never touches the response, and
    `BaseHTTPMiddleware` wraps every request in a task group to stream one
    through. For a redirect that is all cost and no benefit.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        target = _canonical(scope.get("path", ""))
        if target is None:
            await self.app(scope, receive, send)
            return

        url = URL(scope=scope).replace(path=target)
        response = RedirectResponse(str(url), status_code=307)
        await response(scope, receive, send)


def _canonical(path: str) -> str | None:
    """The path this one should be redirected to, or None to leave it alone.

    Pure and separately testable, because the interesting part is which paths it
    declines to touch. `/pages/_assets/...` is a mount for files: a trailing
    slash there is not a page address, and redirecting it would break a
    stylesheet in a way that looks like a CSS bug.
    """
    if path == _PREFIX:
        # The index is declared with the slash, so this is the one path that
        # gains one instead of losing it.
        return _INDEX
    if not path.startswith(_INDEX) or path == _INDEX:
        return None
    if path.startswith("/pages/_assets"):
        return None
    if not path.endswith("/"):
        return None
    stripped = path.rstrip("/")
    # `/pages///` collapses to `/pages`, which is not a page. Send it to the
    # index rather than to a path that would fall through to the shell again.
    return stripped if stripped != _PREFIX else _INDEX
