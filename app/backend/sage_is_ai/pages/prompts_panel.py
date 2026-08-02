"""The Prompts surface, server-rendered.

PLAIN HTML ON PURPOSE. Not one style attribute, not one class. Standing rule from
Alexander, 2026-08-01: get it working as pure HTML, review, *then* style. Paint on
a wrong structure hides the wrongness, and a plain page that behaves and a styled
page that does not are different bugs worth telling apart for free.

## Why this surface, and what it is for

It was chosen for being SMALL rather than heavy — 636 component lines, 8 rows,
and only **+121 kB above the floor** on the production snapshot. That is the
point: it is the rehearsal for the measure-build-measure loop now that the loop
is machinery, and it is too small for the result to be what anyone is watching.

## What the numbers said before a line was written

Two measurements, and they agreed, which is worth recording because last time
they did not. The snapshot holds **8 prompts whose content totals 7 kB** — and
all 8 rows carry a base64 owner avatar, **115 kB across 3 owners**, because
`/api/v1/prompts/list` returns `PromptUserResponse` and that nests the owner's
entire `UserResponse` (`models/prompts.py:61`). The browser measurement put the
surface at +121 kB above the floor. 115 + 7 ≈ 121.

**So roughly 95% of this surface's own payload is owner avatars it renders as a
text name.** The row shows `By {{name}}` and nothing else. This page carries what
it renders: the row context holds a name string, and the picture is never
serialized. Not reduced — absent. Prune, don't port.

The legacy page also fetches BOTH `/prompts/list` and `/prompts/` on every load,
for one list. This page asks once.

## The defect this surface must not inherit

`Prompts.insert_new_prompt` stores `command` verbatim, while `get`, `update` and
`delete` all look it up as `f"/{command}"` (`routers/prompts.py:99,126,161`). An
invariant assumed in three places and enforced in none — so a prompt stored
without the slash can never be fetched, edited or deleted, and the UI's import
path strips the slash before creating. Every imported prompt is undeletable, and
the interface reports nothing.

That is filed as a backend fix at the write point. Until it lands, everything
here goes through `_canonical()`, which finds a prompt by either spelling. A
server-rendered page that reproduced the bug faithfully would be a worse page,
not a more faithful one.
"""

from __future__ import annotations

from typing import Literal, get_args
from urllib.parse import quote, urlencode

from fastapi import HTTPException, Request, status

from sage_is_ai.pages.i18n import lang_query, translator
from sage_is_ai.pages.templates import render

__all__ = [
    "PromptVerb",
    "render_prompts",
    "run_action",
    "export_prompts",
    "import_prompts",
]

# Rows per page. Same as the Agents surface for the same reason: 24 divides
# evenly by 1, 2 and 3, so a page never ends with a half-empty row.
PAGE_SIZE = 24

# The row actions that CHANGE something, declared once. Export is a download and
# Share is an outbound link, so neither is a verb — they are links in the markup
# and cannot mutate anything.
PromptVerb = Literal["clone", "delete"]


def _check_verbs(handlers: dict) -> None:
    """Refuse to serve a verb table that disagrees with `PromptVerb`.

    The Agents panel shipped an if/elif chain ending `else: # clone`, so adding a
    verb would have silently cloned rather than failing. Two lists that must
    agree is a defect waiting for whoever adds the third verb; this makes the
    disagreement impossible to ship, naming both sides in the failure.
    """
    declared, implemented = set(get_args(PromptVerb)), set(handlers)
    if declared != implemented:
        raise RuntimeError(
            "prompts verb table disagrees with PromptVerb: "
            f"declared-not-implemented={sorted(declared - implemented)}, "
            f"implemented-not-declared={sorted(implemented - declared)}"
        )


class _NeedsConfirmation(Exception):
    """Raised to re-render with one row asking, instead of acting.

    An exception rather than a return value because it has to travel out of a
    handler in the verb table, and every handler in that table returns a
    message string. Widening that contract to "a string, or a request to ask
    first" would put a branch in the caller for a case only one verb has.
    """

    def __init__(self, slug: str) -> None:
        super().__init__(slug)
        self.slug = slug


def _slug(command: str) -> str:
    """The bare command, without the leading slash, for use in a URL."""
    return command[1:] if command.startswith("/") else command


async def _visible(user):
    """The prompts this reader may act on, straight from the API handler.

    `get_prompt_list` is the one place that knows an admin sees everything, a
    facilitator sees what they can write, and everyone else sees their own.
    Asking the table directly would be a second copy of that rule — the exact
    restatement this migration exists to delete.
    """
    from sage_is_ai.routers.prompts import get_prompt_list

    return await get_prompt_list(user=user)


async def _find(user, command: str):
    """One prompt, through the same visibility filter as the list.

    Matches on the SLUG rather than the stored string, so it finds a row whether
    it was stored as `/thing` or `thing`. See the module docstring: the storage
    format is not guaranteed, and a page that assumes it would inherit a bug
    that already makes every imported prompt unreachable.
    """
    want = _slug(command)
    for prompt in await _visible(user):
        if _slug(prompt.command) == want:
            return prompt
    raise HTTPException(status.HTTP_404_NOT_FOUND, "No such prompt")


async def _canonical(user, command: str) -> str:
    """The command spelled as the API's own lookups expect it.

    The three by-command routes prepend a slash before querying, so they must be
    handed the bare form of a command that is STORED with one. Handing them the
    bare form of a command stored without one still fails — that is the backend
    defect, not something a caller can paper over, which is why the fix belongs
    at the write point and this only handles the reachable case.
    """
    return _slug((await _find(user, command)).command)


def _url(base: str, locale: str, *, q: str = "", page: int = 1) -> str:
    """Every internal link on this page, built in one place.

    One helper is one thing to be wrong, and it is what guarantees a reader keeps
    their locale AND their search when they press Next — losing either is the bug
    a hand-concatenated query string invites.
    """
    params = {"lang": locale}
    if q:
        params["q"] = q
    if page > 1:
        params["page"] = str(page)
    return f"{base}?{urlencode(params)}"


async def render_prompts(
    request: Request,
    user,
    *,
    base: str = "/pages/workshop/prompts",
    query: str = "",
    page: int = 1,
    message: str = "",
    pending_delete: str = "",
) -> str:
    """Build the context; `templates/prompts.html` decides how it looks."""
    _ = translator(request)
    lang = lang_query(request)
    locale = lang.split("=", 1)[1]

    prompts = await _visible(user)

    needle = query.strip().lower()
    rows = []
    for p in prompts:
        author_name = (p.user and (p.user.name or p.user.email)) or _("Deleted User")
        # Search over exactly what the Svelte page searches: title, command, and
        # the owner's name or email. Same fields, so a reader who learns the
        # search on one page has not learned a different one.
        if needle and needle not in f"{p.title} {p.command} {author_name}".lower():
            continue
        slug = _slug(p.command)
        rows.append(
            {
                "command": p.command,
                "slug": slug,
                "title": p.title,
                # `By {{name}}` is an existing catalog key. The owner is a STRING
                # here and never a picture — see the module docstring.
                "author": _("By {{name}}", {"name": author_name}),
                "edit_url": f"/workshop/prompts/edit?command={quote(slug, safe='')}",
                "export_url": f"{base}/export/{quote(slug, safe='')}{lang}",
                # Two-step delete, resolved on the SERVER. The row that is
                # awaiting confirmation renders a confirm/cancel pair instead of
                # its menu; every other row is untouched.
                "confirming": slug == pending_delete,
            }
        )

    # Page AFTER filtering, so the count and the pager describe what the reader
    # is actually looking at.
    total = len(rows)
    pages = max(1, -(-total // PAGE_SIZE))
    # Clamp rather than 404: a stale bookmark to a page that no longer exists
    # should show the last page. The reader did nothing wrong.
    page = min(max(1, page), pages)
    visible = rows[(page - 1) * PAGE_SIZE : page * PAGE_SIZE]

    def url(**kw):
        return _url(base, locale, q=query, **kw)

    return render(
        "prompts.html",
        base=base,
        lang=lang,
        message=message,
        query=query,
        clear_url=_url(base, locale),
        prompts=visible,
        count=total,
        page=page,
        pages=pages,
        pager=[{"n": n, "href": url(page=n), "current": n == page} for n in range(1, pages + 1)]
        if pages > 1
        else [],
        prev_url=url(page=page - 1) if page > 1 else "",
        next_url=url(page=page + 1) if page < pages else "",
        prev_label=_("Previous"),
        next_label=_("Next"),
        showing_label=_(
            "Showing {{from}}-{{to}} of {{count}}",
            {
                "from": (page - 1) * PAGE_SIZE + 1 if total else 0,
                "to": (page - 1) * PAGE_SIZE + len(visible),
                "count": total,
            },
        ),
        is_admin=user.role == "admin",
        cancel_url=_url(base, locale, q=query, page=page),
        create_url="/workshop/prompts/create",
        export_all_url=f"{base}/export{lang}",
        # The community links render only when the instance has the feature on,
        # matching the legacy page. A zero-egress Rootstock turns it off, and a
        # dead outbound link on an air-gapped deployment is worse than no link.
        community=bool(getattr(request.app.state.config, "ENABLE_COMMUNITY_SHARING", False)),
        community_url="https://sage.is/community",
        share_url="https://sage.is/prompts/create",
        community_heading=_("Sage.is AI Community"),
        community_title=_("Discover your next prompt"),
        community_sub=_("Discover, download, and explore custom prompts"),
        search_label=_("Search Prompts"),
        search_submit_label=_("Search"),
        clear_label=_("Clear"),
        create_label=_("New Prompt"),
        edit_label=_("Edit"),
        actions_label=_("Actions"),
        share_label=_("Share"),
        clone_label=_("Clone"),
        export_label=_("Export"),
        delete_label=_("Delete"),
        import_label=_("Import Prompts"),
        export_all_label=_("Export Prompts"),
        empty_label=_("No prompts yet."),
        confirm_delete_label=_("Delete prompt?"),
        confirm_label=_("Confirm"),
        cancel_label=_("Cancel"),
    )


async def run_action(
    request: Request, user, command: str, verb: str, *, confirmed: bool = False
) -> str:
    """Run one row action through the API handler, then re-render the page.

    The handlers own the permission checks and raise the same refusal they raise
    for the JSON API; turning that into a sentence on the page instead of an
    error document is the only difference a page is entitled to make.

    `verb` is a `Literal` at the route, so FastAPI refuses anything off-list with
    a 422 before this runs and there is no unknown-verb branch to write.
    """
    from sage_is_ai.models.prompts import PromptForm
    from sage_is_ai.routers.prompts import create_new_prompt, delete_prompt_by_command

    _ = translator(request)

    async def _delete():
        # ASKS FIRST, and asks on the server. The Svelte page opens a modal
        # dialog; this re-renders with one row expanded into a confirm/cancel
        # pair. That is not a workaround for lacking a dialog — for a page with
        # no script it is better than one: no focus trap to get wrong, no escape
        # key to handle, and it still works with JavaScript disabled, which a
        # modal does not.
        if not confirmed:
            raise _NeedsConfirmation(_slug(command))
        await delete_prompt_by_command(command=await _canonical(user, command), user=user)
        return _("Deleted {{name}}", {"name": command})

    async def _clone():
        original = await _find(user, command)
        # A copy needs a free command, and the suffix is the simplest thing that
        # cannot collide. `create_new_prompt` refuses a taken command, so a
        # second clone is refused rather than overwriting the first.
        #
        # Stored WITH the leading slash on purpose — that is the spelling the
        # by-command routes can find. Writing the bare form here would create a
        # prompt nobody could ever delete.
        form = PromptForm(
            command=f"/{_slug(original.command)}-clone",
            title=f"{original.title} (Clone)",
            content=original.content,
            access_control=original.access_control,
        )
        await create_new_prompt(request=request, form_data=form, user=user)
        return _("Cloned {{name}}", {"name": command})

    # A table, not a chain — an unhandled verb raises rather than doing the wrong
    # thing quietly, and `_check_verbs` turns even that into a boot failure.
    handlers = {"clone": _clone, "delete": _delete}
    _check_verbs(handlers)

    try:
        message = await handlers[verb]()
    except _NeedsConfirmation as ask:
        return await render_prompts(request, user, pending_delete=ask.slug)
    except HTTPException as exc:
        message = str(exc.detail)
    return await render_prompts(request, user, message=message)


async def export_prompts(user, command: str = "") -> list[dict]:
    """One prompt, or all of them, as the JSON the import side reads.

    The browser used to assemble this with `file-saver` from a list it already
    held. The server has the data, so the download is a link — which is the only
    reason `file-saver` was a dependency of this surface.
    """
    prompts = [await _find(user, command)] if command else await _visible(user)
    return [p.model_dump(exclude={"user"}) for p in prompts]


async def import_prompts(request: Request, user, payload: bytes) -> str:
    """Create or update prompts from an exported file, then re-render.

    Mirrors what the Svelte reader did in the browser with two differences, both
    deliberate. It COUNTS: the original's `.catch(() => null)` per row meant a
    file of twenty prompts could import none of them and report nothing. And it
    keeps the leading slash instead of stripping it — the original stripped it
    before calling create, which is precisely what makes every imported prompt
    permanently undeletable.
    """
    import json

    from sage_is_ai.models.prompts import PromptForm
    from sage_is_ai.routers.prompts import create_new_prompt, update_prompt_by_command

    _ = translator(request)
    try:
        rows = json.loads(payload or b"[]")
    except ValueError:
        return await render_prompts(request, user, message=_("That file is not valid JSON."))
    if not isinstance(rows, list):
        return await render_prompts(request, user, message=_("That file is not valid JSON."))

    done, failed = 0, 0
    existing = {_slug(p.command) for p in await _visible(user)}
    for row in rows:
        if not isinstance(row, dict):
            failed += 1
            continue
        try:
            slug = _slug(str(row.get("command", "")))
            if not slug:
                raise ValueError("no command")
            form = PromptForm(
                command=f"/{slug}",
                title=str(row.get("title", slug)),
                content=str(row.get("content", "")),
                access_control=row.get("access_control"),
            )
            if slug in existing:
                await update_prompt_by_command(command=slug, form_data=form, user=user)
            else:
                await create_new_prompt(request=request, form_data=form, user=user)
            done += 1
        except (HTTPException, TypeError, ValueError):
            failed += 1

    message = _("Imported {{count}} prompts.", {"count": done})
    if failed:
        message += " " + _("{{count}} could not be read.", {"count": failed})
    return await render_prompts(request, user, message=message)
