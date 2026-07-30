"""The changelog panel — first wizard surface, and the first with no legacy URL.

Every surface before this one replaced a page. This one replaces a branch of a
modal that `(app)/+layout.svelte` mounts and a store decides to show, so there
was no address to point a spec at. The registry grew an open step for that
(`cypress/support/surfaces.ts`), which is what lets the parity gate compare a
panel you cannot visit.

Two things this panel does differently from the Svelte one, both deliberate.

**The changelog is a module constant, not a fetch.** `env.CHANGELOG` is parsed
from CHANGELOG.md once at import. The Svelte panel boots, then calls
`/api/changelog`, then renders — three steps to display something that has not
changed since the process started. Reading the constant is the same rule the
other panels follow (call the handler, never round-trip your own API), taken to
its end: there is no handler to call, only data.

**Continue is a form post, not a modal close.** In the modal, Continue closes it
and, when the changelog is the only panel, records the version as read. At a
route there is nothing to close, so what survives is the half that outlives the
click — the server records the read. That is the property that stops the
changelog reappearing on every page load, and it is what the guard-rail spec
asserts on both implementations.

No confetti. The Svelte panel fires `svelte-confetti` on the title, and it is
not reproduced here — a component whose entire job is an animation is not worth
a script tag on a server-rendered page. Recorded rather than dropped silently,
because an unremarked disappearance is indistinguishable from a bug.
"""

from __future__ import annotations

from html import escape as e

from fastapi import Request

__all__ = ["render_changelog", "mark_changelog_read"]

# Written once, repeated by the loops below. A prop string that appears on every
# generated row costs one source line here, which is the whole argument for
# props over a parallel stylesheet.
_VERSION_S = "--size:1.05rem; --weight:600; --m:1.25rem 0 .35rem"
_SECTION_S = "--size:.7rem; --weight:600; --tt:uppercase; --ls:.04em; --op:.7; --m:.75rem 0 .25rem"
_TITLE_S = "--weight:600; --tt:uppercase; --size:.72rem; --ls:.02em"
_BODY_S = "--m:.15rem 0 .6rem; --size:.85rem"


def _entries(items: object) -> str:
    """One section's entries as a description list.

    `<dl>` is the element that already means "terms and what they mean", which
    is exactly a changelog entry: a short title and the sentence explaining it.
    It replaces the nested div-in-div the Svelte panel uses and needs no class
    to say what it is.
    """
    if not isinstance(items, (list, tuple)):
        return ""
    rows = "".join(
        f'<dt style="{_TITLE_S}">{e(str(row.get("title", "")))}</dt>'
        f'<dd style="{_BODY_S}">{e(str(row.get("content", "")))}</dd>'
        for row in items
        if isinstance(row, dict)
    )
    return f'<dl style="--m:0">{rows}</dl>' if rows else ""


def _version(version: str, data: dict) -> str:
    sections = "".join(
        f'<h3 data-section="{e(str(name), quote=True)}" style="{_SECTION_S}">{e(str(name))}</h3>'
        + _entries(items)
        for name, items in data.items()
        if name != "date"
    )
    date = e(str(data.get("date", "")))
    return (
        f'<article data-version="{e(version, quote=True)}">'
        f'<h2 style="{_VERSION_S}">v{e(version)} - {date}</h2>'
        f"<hr />{sections}</article>"
    )


def render_changelog(request: Request) -> str:
    """The panel. Arrives rendered, because the data was never remote."""
    from sage_is_ai.env import CHANGELOG, VERSION

    versions = "".join(
        _version(str(v), d) for v, d in CHANGELOG.items() if isinstance(d, dict)
    )
    # An empty changelog is a real state — a build whose CHANGELOG.md failed to
    # parse — and rendering nothing at all would look like a broken page rather
    # than an empty one.
    body = versions or '<p style="--op:.7">No release notes are available.</p>'
    return f"""
<section data-cy="changelog-panel">
  <p style="--size:.8rem; --op:.7; --m:0 0 .5rem">
    Release Notes
    <span data-app-version="{e(VERSION, quote=True)}"> &middot; v{e(VERSION)}</span>
  </p>
  <div data-cy="changelog-body" style="--maxh:24rem; --ofy:auto">{body}</div>
  <form method="post" action="/pages/admin/setup/changelog/seen" style="--m:1rem 0 0">
    <button data-cy="changelog-continue" type="submit"
            style="--p:.45rem 1rem; --br:999px; --b:1px solid var(--line); --cur:pointer">
      Continue
    </button>
  </form>
</section>
"""


async def mark_changelog_read(request: Request, user) -> None:
    """Record that this version's changelog has been read.

    Calls the API handler rather than writing the row, so the one place that
    knows what a settings update is allowed to do stays the one place. The read
    is a merge, not a replace: the handler takes the whole `ui` blob and stores
    it, so dropping the rest of the reader's preferences on the floor is exactly
    what a naive write here would do.
    """
    from sage_is_ai.env import VERSION
    from sage_is_ai.models.users import Users, UserSettings
    from sage_is_ai.routers.users import update_user_settings_by_session_user

    current = Users.get_user_by_id(user.id)
    settings = (current.settings if current else None) or {}
    if hasattr(settings, "model_dump"):
        settings = settings.model_dump()
    ui = dict((settings or {}).get("ui") or {})
    ui["version"] = VERSION

    await update_user_settings_by_session_user(
        request, UserSettings(**{**settings, "ui": ui}), user
    )
