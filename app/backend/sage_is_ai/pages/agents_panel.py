"""The Agents surface, server-rendered. The first migration driven by a number.

Every surface before this one was chosen for being ripe. This one was chosen for
being the worst page in the product: measured on production, `/workshop/models`
is **144 requests, 20,520 kB, 6,181 kB transferred, 32 seconds** — a list of
agents that loads slower than a conversation, against a budget of ~2 MB and two
seconds.

PLAIN HTML ON PURPOSE. Not one style attribute, not one class. Alexander,
2026-08-01: "before adding any style or start.style get things working as pure
html and then I'll review... Don't go reinventing things." Structure is the thing
a review can judge; paint on top of a wrong structure hides the wrongness. The
styling pass comes after that review, and either lifts what the Svelte page
already has or uses the framework — it does not invent a third look.

## The payload, measured on a production snapshot rather than reasoned about

The first version of this docstring blamed agent avatars, with arithmetic. The
snapshot in `tools/db_snapshots/` refuted it in one query: of **324 agents**, only
**16** carry a data URI, all agent `meta` totals **868 kB**, and the whole `model`
table is **1,114 kB**. That is the third inference in this migration that read
perfectly and measured false, after the 22 MB WASM and the markdown libraries.

**What is actually large is the owner, repeated.** `GET /api/v1/models/` returns
`list[ModelUserResponse]`, which nests the owner's entire `UserResponse` in every
row. Twenty-one of that instance's thirty-two users carry a base64 avatar; those
users hold **120 kB** between them, and serialized once per agent they own they
become **2,511 kB** in a single response — the same handful of images, twenty-one
times over. The legacy page then renders none of them: the row shows "By {name}"
as text, so every one of those bytes is downloaded, parsed, and dropped.

This page carries what it renders. The row context holds a name string, and the
owner's picture is never serialized, so that cost is not reduced here — it is
absent. That is the fragment path's structural advantage over an island, and it
is the first place in this migration where it shows up as bytes rather than lines.

Agent avatars are still served by URL rather than inlined, for the sixteen that
have one: the template points at `/pages/workshop/agents/avatar/{id}` with the
content hash in the query and a year of `immutable`, so each downloads once per
version instead of once per page load. Worth doing and cheap — but it is a minor
win, and calling it the fix would repeat the mistake at the top of this comment.

The stored format is separately wrong — PNG at 250x250 for a 44px slot — and that
is the editor's problem, with its own before-and-after and a migration.

## Everything else follows the convention

It calls `routers/models.py` directly rather than round-tripping our own API,
which matters more here than usual: `get_models` returns a DIFFERENT list per
role — every model for an admin, writable ones for a facilitator, own ones for
everyone else. Reimplementing that filter is exactly the authorization
restatement this migration exists to delete, and getting it wrong leaks other
people's agents.

Search and the tag filter live in the URL, so the state is shareable, the back
button works, and there is no client-side array to fall out of step with the
server's. That is also why neither needs a script.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
from urllib.parse import quote

from fastapi import HTTPException, Request, status

from sage_is_ai.pages.i18n import lang_query, translator
from sage_is_ai.pages.templates import render

__all__ = [
    "render_agents",
    "run_action",
    "export_agents",
    "import_agents",
    "avatar_bytes",
    "AVATAR_CACHE",
]

# A year, and immutable, because the version token in the URL changes whenever
# the stored image does. Same trick `shell.asset_url()` uses, and the same reason
# SvelteKit can do it to `_app/immutable`: a URL that changes with its content
# never needs revalidating.
AVATAR_CACHE = "public, max-age=31536000, immutable"

_DATA_PREFIX = "data:"


def _can_edit(user, model) -> bool:
    """Whether this reader may edit this agent.

    Uses the backend's own `has_access` rather than restating the rule the
    Svelte row restates. That component reads
    `model.access_control.write.group_ids.some(...)` directly, which is both a
    second copy of the policy and a crash waiting for the first agent whose
    `access_control` is null — the audit behind this migration counted 142 such
    restatements in the frontend and this is one of them.
    """
    from sage_is_ai.utils.access_control import has_access

    if user.role == "admin" or model.user_id == user.id:
        return True
    return has_access(user.id, "write", model.access_control)


def _avatar(model, base: str, lang: str) -> str:
    """Where the browser should fetch this agent's picture.

    A stored value that is already a URL is left alone — that is the default
    `/static/icons/favicon.png` and any operator who typed a real address. Only a
    data URI is redirected through our own route, because only a data URI is the
    problem.

    The version token is the first eight hex of the content hash, so editing an
    avatar changes the URL and the year-long cache cannot serve the old one.
    """
    raw = (getattr(model, "meta", None) and model.meta.profile_image_url) or ""
    if not raw.startswith(_DATA_PREFIX):
        return raw
    token = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]
    # No locale on this URL. An image has no language, and adding one would give
    # the same bytes 56 addresses and 56 cache entries.
    return f"{base}/avatar/{quote(model.id, safe='')}?v={token}"


def _decode(raw: str) -> tuple[bytes, str]:
    """A `data:` URI as bytes and a content type.

    Refuses anything that is not base64 image data rather than guessing. The
    stored value is written by our own editor today, but it is a database column
    an operator can reach, so it is treated as input.
    """
    try:
        header, payload = raw.split(",", 1)
    except ValueError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No image")

    if not header.startswith(_DATA_PREFIX) or ";base64" not in header:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No image")

    media = header[len(_DATA_PREFIX) : header.index(";")] or "application/octet-stream"
    # An image content type only. Serving whatever a data URI claims would turn a
    # database column into a way to serve HTML from our own origin.
    if not media.startswith("image/"):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No image")

    try:
        return base64.b64decode(payload, validate=True), media
    except (binascii.Error, ValueError):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No image")


def _visible(user, agent_id: str = ""):
    """The agents this reader may see, straight from the API handler.

    `get_models` accepts an `id` argument and ignores it, so filtering happens
    here rather than being passed down. That is deliberate: the handler is the
    one place that knows an admin sees everything, a facilitator sees what they
    can write, and everyone else sees their own. Asking a second question of the
    table would be a second copy of that rule.
    """
    from sage_is_ai.routers.models import get_models

    return get_models(user=user)


# Rows per page. Twenty-four divides evenly by 1, 2 and 3, so a page never ends
# with a half-empty row at any of the column counts the list uses.
PAGE_SIZE = 24


def _url(base: str, locale: str, *, q: str = "", tag: str = "", page: int = 1) -> str:
    """Every internal link on this page, built in one place.

    The template used to concatenate query strings itself, which meant escaping
    `&` by hand in five places and getting the order right each time. One helper
    is one thing to be wrong, and it is also what guarantees a reader keeps their
    locale, their search AND their tag when they press Next — losing any of the
    three is the bug this page is otherwise wide open to.
    """
    from urllib.parse import urlencode

    params = {"lang": locale}
    if q:
        params["q"] = q
    if tag:
        params["tag"] = tag
    if page > 1:
        params["page"] = str(page)
    return f"{base}?{urlencode(params)}"


async def render_agents(
    request: Request,
    user,
    *,
    base: str = "/pages/workshop/agents",
    query: str = "",
    tag: str = "",
    page: int = 1,
    message: str = "",
) -> str:
    """Build the context; `templates/agents.html` decides how it looks."""
    _ = translator(request)
    lang = lang_query(request)
    locale = lang.split("=", 1)[1]

    models = await _visible(user)
    all_tags = sorted(
        {
            str(t.get("name"))
            for m in models
            if not (getattr(m.meta, "hidden", False) or False)
            for t in (getattr(m.meta, "tags", None) or [])
            if isinstance(t, dict) and t.get("name")
        }
    )

    needle = query.strip().lower()
    rows = []
    for m in models:
        meta = m.meta
        description = (getattr(meta, "description", None) or "").strip()
        if needle and needle not in f"{m.name} {m.id} {description}".lower():
            continue
        if tag and tag not in {
            str(t.get("name")) for t in (getattr(meta, "tags", None) or []) if isinstance(t, dict)
        }:
            continue
        author = (m.user and (m.user.name or m.user.email)) or _("Deleted User")
        rows.append(
            {
                "id": m.id,
                "name": m.name,
                "description": description or m.id,
                # `By {{name}}` is an existing catalog key; interpolating here
                # rather than in the template keeps every sentence in one place.
                "author": _("By {{name}}", {"name": author}),
                "avatar": _avatar(m, base, lang),
                "is_active": bool(m.is_active),
                "hidden": bool(getattr(meta, "hidden", False) or False),
                "can_edit": _can_edit(user, m),
                "edit_url": f"/workshop/models/edit?id={quote(m.id, safe='')}",
                "open_url": f"/?models={quote(m.id, safe='')}",
                "toggle_label": _("Disable") if m.is_active else _("Enable"),
                "hide_label": _("Show Model") if getattr(meta, "hidden", False) else _("Hide Model"),
            }
        )

    # Page AFTER filtering, so the count and the pager describe what the reader
    # is actually looking at. Paging before filtering would show "page 2 of 3"
    # over a search that matched two things.
    total = len(rows)
    pages = max(1, -(-total // PAGE_SIZE))  # ceiling division
    # Clamp rather than 404. A stale bookmark to page 9 of a list that shrank
    # should show the last page, not an error — the reader did nothing wrong.
    page = min(max(1, page), pages)
    visible = rows[(page - 1) * PAGE_SIZE : page * PAGE_SIZE]

    def url(**kw):
        return _url(base, locale, q=query, tag=tag, **kw)

    return render(
        "agents.html",
        base=base,
        lang=lang,
        message=message,
        query=query,
        tag=tag,
        tags=all_tags,
        tag_urls={t: _url(base, locale, q=query, tag=t) for t in all_tags},
        all_tags_url=_url(base, locale, q=query),
        clear_url=_url(base, locale, tag=tag),
        agents=visible,
        count=total,
        # The pager. Rendered only when there is more than one page, so a small
        # instance never sees paging machinery it does not need.
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
        # The community links render only when the instance has the feature on,
        # matching the legacy page. Read from app config rather than assumed,
        # because a zero-egress Rootstock turns it off and a dead outbound link
        # on an air-gapped deployment is worse than no link.
        community=bool(
            getattr(request.app.state.config, "ENABLE_COMMUNITY_SHARING", False)
        ),
        community_url="https://sage.is/community",
        community_heading=_("Sage.is AI Community"),
        community_label=_("Discover your next agent"),
        share_label=_("Share"),
        heading_count=_("{{count}} agents", {"count": len(rows)}),
        search_label=_("Search Models"),
        search_action=_("Search"),
        clear_label=_("Clear"),
        all_label=_("All"),
        create_label=_("New Agent"),
        edit_label=_("Edit"),
        actions_label=_("Actions"),
        copy_link_label=_("Copy Link"),
        clone_label=_("Clone"),
        export_label=_("Export"),
        delete_label=_("Delete"),
        import_label=_("Import Agents"),
        export_all_label=_("Export Agents"),
        empty_label=_("No agents yet."),
    )


async def run_action(request: Request, user, agent_id: str, verb: str) -> str:
    """Run one row action through the API handler, then re-render the page.

    Every action has the same shape — call, catch, report, re-render — so they
    share it, the way `sprigs_panel.run_action` does. The handlers own the
    permission checks (owner, group writer, or admin) and raise the same refusal
    they raise for the JSON API; turning that into a sentence on the page instead
    of an error document is the only difference a page is entitled to make.

    `verb` is a `Literal` at the route, so FastAPI refuses anything off-list
    before this runs and there is no unknown-verb branch to write.
    """
    from sage_is_ai.models.models import ModelForm
    from sage_is_ai.routers.models import (
        create_new_model,
        delete_model_by_id,
        toggle_model_by_id,
        update_model_by_id,
    )

    _ = translator(request)
    message = ""
    try:
        if verb == "toggle":
            await toggle_model_by_id(id=agent_id, user=user)
        elif verb == "delete":
            await delete_model_by_id(id=agent_id, user=user)
            message = _("Deleted {{name}}", {"name": agent_id})
        else:
            model = await _find(user, agent_id)
            form = ModelForm(**model.model_dump(exclude={"user", "updated_at", "created_at"}))
            if verb == "hide":
                meta = form.meta.model_dump()
                meta["hidden"] = not bool(meta.get("hidden"))
                form.meta = type(form.meta)(**meta)
                await update_model_by_id(request=request, id=agent_id, form_data=form, user=user)
            else:  # clone
                # A copy needs a free id, and the suffix is the simplest thing
                # that cannot collide with the original. `create_new_model`
                # refuses a taken id, so a second clone of the same agent is
                # refused rather than silently overwriting the first.
                form.id = f"{form.id}-copy"
                form.name = f"{form.name} (copy)"
                await create_new_model(request=request, form_data=form, user=user)
                message = _("Cloned {{name}}", {"name": agent_id})
    except HTTPException as exc:
        message = str(exc.detail)
    return await render_agents(request, user, message=message)


async def _find(user, agent_id: str):
    """One agent, through the same visibility filter as the list."""
    for model in await _visible(user):
        if model.id == agent_id:
            return model
    raise HTTPException(status.HTTP_404_NOT_FOUND, "No such agent")


async def export_agents(user, agent_id: str = "") -> list[dict]:
    """One agent, or all of them, as the JSON the import side reads.

    The browser used to assemble this with `file-saver` from a list it already
    held. The server has the data, so the download is a link — which is the only
    reason `file-saver` was a dependency of this surface.

    NOTE, and this is load-bearing for the avatar work: the export carries
    `meta.profile_image_url` verbatim, so today it is self-contained and imports
    into any instance. If avatars ever move out of the row and into storage, this
    is the function that has to re-inline them, or every export silently becomes
    non-portable and nobody finds out until someone imports one elsewhere.
    """
    models = [await _find(user, agent_id)] if agent_id else await _visible(user)
    return [m.model_dump(exclude={"user"}) for m in models]


async def import_agents(request: Request, user, payload: bytes) -> str:
    """Create or update agents from an exported file, then re-render.

    Mirrors what the Svelte reader did in the browser, minus the part where it
    swallowed every error: its `.catch(() => null)` per row meant a file of
    twenty agents could import none of them and report nothing. This counts, and
    says how many landed and how many did not.
    """
    import json

    from sage_is_ai.models.models import ModelForm
    from sage_is_ai.routers.models import create_new_model, update_model_by_id

    _ = translator(request)
    try:
        rows = json.loads(payload or b"[]")
    except ValueError:
        return await render_agents(request, user, message=_("That file is not valid JSON."))
    if not isinstance(rows, list):
        return await render_agents(request, user, message=_("That file is not valid JSON."))

    done, failed = 0, 0
    existing = {m.id for m in await _visible(user)}
    for row in rows:
        # An export from the model editor nests the agent under `info`; one from
        # this page does not. Both shapes are accepted, because a person with a
        # file does not know which tool made it.
        data = row.get("info") if isinstance(row, dict) and isinstance(row.get("info"), dict) else row
        try:
            form = ModelForm(**data)
            if form.id in existing:
                await update_model_by_id(request=request, id=form.id, form_data=form, user=user)
            else:
                await create_new_model(request=request, form_data=form, user=user)
            done += 1
        except (HTTPException, TypeError, ValueError):
            failed += 1

    message = _("Imported {{count}} agents.", {"count": done})
    if failed:
        message += " " + _("{{count}} could not be read.", {"count": failed})
    return await render_agents(request, user, message=message)


async def avatar_bytes(user, agent_id: str) -> tuple[bytes, str]:
    """One agent's stored picture, decoded.

    Reached through the same visibility filter as the list rather than by a
    direct table lookup, so a reader cannot fetch the avatar of an agent they
    cannot see by guessing an id. A 404 for both "no such agent" and "not yours",
    because telling them apart tells an outsider which ids exist.
    """
    for model in await _visible(user):
        if model.id == agent_id:
            return _decode((getattr(model, "meta", None) and model.meta.profile_image_url) or "")
    raise HTTPException(status.HTTP_404_NOT_FOUND, "No image")
