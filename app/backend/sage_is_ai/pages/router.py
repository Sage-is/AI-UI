"""No-build pages. The frontend migration's server-rendered surface.

Every route here is explicit, so it resolves before the SPA catch-all and the
compiled bundle never sees it. The SPA keeps its own `/admin/sprigs`; this
serves an independent implementation of the same panel at
`/pages/admin/sprigs`. Both are live at once, which is the point: the guard-rail
Cypress spec runs against either one and must pass against both.

Pages authenticate from the auth cookie (see auth.py), which is what lets the
server render the panel instead of the browser assembling it. Phase 0 could not
do that, because the token lived in localStorage, and the island it built
instead came out bigger than the Svelte component it replaced. This rebuild is
meant to measure that difference.
"""

from html import escape
from uuid import uuid4
from typing import AsyncIterator, Literal

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    StreamingResponse,
)

from sage_is_ai.env import PAGES_RELOAD_DIRS
from sage_is_ai.pages import ASSETS_DIR
from sage_is_ai.pages.auth import (
    require_admin_page,
    require_agents_reader,
    require_page_user,
)
from sage_is_ai.pages.i18n import lang_query, supported, translator
from sage_is_ai.pages.shell import render_page
from sage_is_ai.pages.templates import TEMPLATES_DIR, render
from sage_is_ai.pages.branding_panel import render_branding, save_branding
from sage_is_ai.pages.changelog_panel import mark_changelog_read, render_changelog
from sage_is_ai.pages.features_panel import render_features, save_features
from sage_is_ai.pages.developer_panel import render_developer, save_developer
from sage_is_ai.pages.complete_panel import finish_setup, render_complete
from sage_is_ai.pages.welcome_panel import render_welcome, start_wizard
from sage_is_ai.pages.connection_panel import render_connection, verify_and_save
from sage_is_ai.pages.auth_panel import render_auth, save_auth
from sage_is_ai.pages.users_panel import (
    add_one_user,
    import_csv,
    render_users,
    set_working_alone,
)
from sage_is_ai.pages.search_audio_panel import (
    download_components,
    graft_components,
    render_search_audio,
)
from sage_is_ai.pages.diagnostics_panel import render_diagnostics
from sage_is_ai.pages.sprigs_panel import render_panel, run_action
from sage_is_ai.pages.agents_panel import (
    AVATAR_CACHE,
    AgentVerb,
    avatar_bytes,
    export_agents,
    import_agents,
    render_agents,
    # Aliased: `sprigs_panel` exports a `run_action` too, and two callables
    # with one name in one module is how the wrong one gets called.
    run_action as run_agent_action,
)
from sage_is_ai.pages.prompts_panel import (
    PromptVerb,
    export_prompts,
    import_prompts,
    render_prompts,
    # Aliased for the same reason the agents one is: three modules now export a
    # `run_action`, and three callables with one name is how the wrong one gets
    # called.
    run_action as run_prompt_action,
)

router = APIRouter()

# Identifies this process, and nothing else.
#
# The dev-reload client used to treat any RECONNECT as "the server restarted".
# That was only ever a proxy, and it broke the moment the stream started ending
# itself on a timer to stop it blocking shutdown: the browser reconnected every
# 60 seconds and dutifully reloaded the page. It was also wrong for a transient
# network blip.
#
# A token regenerated at import is the actual signal. Same token means the same
# process, whatever happened to the connection; a different one means the code
# was reloaded. Deliberately NOT `env.INSTANCE_ID`, which an operator can pin
# through the environment — pinning it would silently disable reloading.
_BOOT_TOKEN = uuid4().hex


# ── The development reloader's endpoint ──────────────────────────────────────
#
# Registered INSIDE an `if`, so when the flag is unset this route does not exist
# — a 404 rather than a route that exists and refuses. "It is not registered" is
# the kind of claim that rots into "it is registered but guarded", so the gate
# asserts the 404 rather than trusting this comment.
#
# What it streams, and why the two halves are different shapes:
#
#   Python changes  Nothing here reports them. Uvicorn's reloader restarts the
#                   process, this connection dies with it, and the browser's
#                   EventSource reconnects on its own. The DEATH of this stream
#                   is the signal, which is why there is no `.py` watcher — one
#                   would be a second source of truth for a fact the process
#                   already announces by ending.
#
#   Asset changes   Do need reporting. `pages/assets/*` is served from disk by a
#                   StaticFiles mount, so a stylesheet edit restarts nothing and
#                   there is no dropped connection to notice. `awatch` reports
#                   it and the island swaps the stylesheet without reloading.
#
#   Template edits  The same shape, and the reason `TEMPLATES_DIR` is watched
#                   alongside the assets. Jinja re-reads a changed template on
#                   the next request (0.48 s, measured) and restarts nothing, so
#                   without this the server would be serving new markup that no
#                   open tab had any reason to ask for.
#
# `watchfiles` is already in the image via `uvicorn[standard]`, so this costs no
# dependency. One watcher per connected tab, which is fine for the one or two a
# person has open and is not a shape to reuse for anything user-facing.
if PAGES_RELOAD_DIRS:

    @router.get("/_dev/reload")
    async def dev_reload(
        request: Request, user=Depends(require_page_user)
    ) -> StreamingResponse:
        async def stream() -> AsyncIterator[str]:
            from watchfiles import awatch

            # One second, not the three the spec defaults to. This is the delay
            # between saving a panel and seeing it, and there is no network
            # worth being polite to.
            yield "retry: 1000\n\n"
            # Who is answering. The client reloads when this CHANGES, not when
            # the connection reopens.
            yield f"event: hello\ndata: {_BOOT_TOKEN}\n\n"

            # `yield_on_timeout` gives the keep-alive for free: the watcher
            # hands back an empty change set every 15s instead of blocking, so
            # one loop covers both jobs. Racing a timeout against the watcher
            # with `wait_for` would cancel it mid-poll, which is a good way to
            # end up debugging the debugger.
            #
            # BOUNDED, and this is not tidiness. A stream that never ends blocks
            # uvicorn's graceful shutdown, and uvicorn shutting down is exactly
            # what a reload IS — so an open dev-reload connection wedged the very
            # reload it exists to announce. Found by leaving a tab open and
            # editing a panel: "WatchFiles detected changes… Reloading…" and then
            # nothing, forever, with the old worker still alive. Ending every
            # minute costs one reconnect the browser makes anyway (retry: 1000)
            # and caps how long a shutdown can wait on us.
            deadline = 0
            async for changes in awatch(
                ASSETS_DIR, TEMPLATES_DIR, rust_timeout=15_000, yield_on_timeout=True
            ):
                if not changes:
                    deadline += 1
                    if deadline >= 4:
                        return
                    yield ": keep-alive\n\n"
                    continue
                deadline = 0
                # A stylesheet can be swapped in place; markup cannot. Which
                # event the browser gets decides whether it keeps your scroll
                # position or starts the page over, so the distinction is worth
                # the two lines it costs.
                paths = {str(path) for _kind, path in changes}
                if any(str(TEMPLATES_DIR) in path for path in paths):
                    yield "event: markup\ndata: changed\n\n"
                else:
                    yield "event: assets\ndata: changed\n\n"

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-store",
                # Proxies that buffer would hold the events until the buffer
                # fills, which for a stream this quiet is forever.
                "X-Accel-Buffering": "no",
            },
        )


def _whole_page(
    request: Request, key: str, body: str, scripts: tuple[str, ...] = ()
) -> HTMLResponse:
    """Shell a surface that owns its whole page, from the `_PAGES` table.

    The counterpart to `_setup_page`. Same reason it exists: the heading, the
    subheading and the browser title were three literals per route, restated at
    every call, and the index needed them a fourth time.
    """
    heading, subheading = _PAGES[key]
    return HTMLResponse(
        render_page(
            request=request,
            title=f"{heading} — Sage.is AI",
            heading=heading,
            subheading=subheading,
            scripts=scripts,
            body=body,
        ),
        headers=_page_headers(request),
    )


_INDEX_GROUP_S = "--size:.7rem; --weight:600; --tt:uppercase; --ls:.04em; --op:.7; --m:1.5rem 0 .5rem"
_INDEX_LIST_S = "--m:0; --p:0; --d:flex; --fd:column; --g:.5rem; --lis:none"
_INDEX_ITEM_S = "--d:block; --p:.7rem; --br:.6rem; --b:1px solid var(--line)"
_INDEX_NAME_S = "--size:.9rem; --weight:500"
_INDEX_SUB_S = "--size:.72rem; --op:.7; --d:block; --m:.15rem 0 0"
_INDEX_PATH_S = "--size:.68rem; --op:.55; --d:block; --ff:ui-monospace, monospace"


def _index_item(path: str, title: str, subtitle: str, lang: str) -> str:
    return (
        f'<li><a data-cy="index-link" href="{escape(path + lang, quote=True)}"'
        f' style="{_INDEX_ITEM_S}">'
        f'<span style="{_INDEX_NAME_S}">{escape(title)}</span>'
        f'<small style="{_INDEX_SUB_S}">{escape(subtitle)}</small>'
        f'<small style="{_INDEX_PATH_S}">{escape(path)}</small>'
        f"</a></li>"
    )


def _index_group(label: str, items: str) -> str:
    return f'<h2 style="{_INDEX_GROUP_S}">{escape(label)}</h2><ul style="{_INDEX_LIST_S}">{items}</ul>'


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def pages_index(
    request: Request, user=Depends(require_admin_page)
) -> HTMLResponse:
    """The front door. Every server-rendered page, in one list.

    Both `""` and `"/"` are registered rather than leaning on FastAPI's
    redirect-on-missing-slash, because the SPA is mounted at `/` with an
    index.html fallback — so a path this router does not claim is answered by
    the app rather than redirected, and the difference between `/pages` and
    `/pages/` would have been "a list" versus "the chat window".

    Admin-only, like every page it links to bar one. Nothing is disclosed by it:
    an admin can already reach all of these, and until now had to know the URLs.

    Not gated to development. An index that exists only in a review container is
    an index you cannot use on the instance you are actually debugging.
    """
    _ = translator(request)
    lang = lang_query(request)

    admin_pages = "".join(
        _index_item(f"/pages/{key}", _(title), _(subtitle), lang)
        for key, (title, subtitle) in _PAGES.items()
    )
    # In wizard order, not dict order — the sequence is the meaning here, and
    # `_SETUP_ORDER` is the one place that knows it.
    setup_pages = "".join(
        _index_item(
            f"/pages/admin/setup/{panel}",
            _(_SETUP_PAGES[panel][0]),
            _(_SETUP_PAGES[panel][1]),
            lang,
        )
        for panel in _SETUP_ORDER
    )
    everyone = _index_item(
        "/pages/changelog",
        _("What's New"),
        _("The release notes, open to every signed-in reader."),
        lang,
    )

    # Fragment endpoints (`…/panel`) and the reloader's event stream are left
    # out deliberately: one returns markup with no shell and the other never
    # finishes, so both are traps in a list you click through.
    body = (
        '<section data-cy="pages-index">'
        + _dev_banner(_)
        + _index_group(_("Admin pages"), admin_pages)
        + _index_group(_("Setup wizard"), setup_pages)
        + _index_group(_("Open to everyone"), everyone)
        + "</section>"
    )
    return HTMLResponse(
        render_page(
            request=request,
            title="Pages — Sage.is AI",
            heading=_("Server-rendered pages"),
            subheading=_("Every page this instance renders without a build step."),
            body=body,
        ),
        headers=_page_headers(request),
    )


def _dev_banner(_) -> str:
    """Say so, loudly, when this instance is running the development reloader.

    The same fact `/admin/diagnostics` reports as degraded, said where somebody
    working on these pages will actually be looking. Absent in production, which
    is every instance that does not set the variable.
    """
    if not PAGES_RELOAD_DIRS:
        return ""
    return (
        '<p data-cy="index-dev-banner" style="--p:.7rem; --br:.6rem; '
        '--b:1px solid var(--line); --size:.78rem; --m:0 0 .5rem">'
        f'<strong>{escape(_("Development reloader is on."))}</strong> '
        + escape(
            _(
                "Saving a panel restarts the app and reloads this tab; saving a "
                "stylesheet swaps it in place. Watching: {{paths}}",
                {"paths": PAGES_RELOAD_DIRS},
            )
        )
        + "</p>"
    )


@router.get("/admin/sprigs", response_class=HTMLResponse)
async def sprigs_page(
    request: Request, user=Depends(require_admin_page)
) -> HTMLResponse:
    """The Sprigs™ admin panel, without a compiler.

    The panel arrives rendered, so there is no loading state and no second
    request for the catalog. The first paint is the data, which is what the
    island version could not manage.
    """
    return _whole_page(
        request, "admin/sprigs", await render_panel(request, user), ("vendor/htmx.min.js",)
    )


# The three fragment endpoints. Each returns the panel, which is also the swap
# target, so a mutation and a refresh are the same shape of response.
#
# The name travels in the path and nothing else does. `graft_sprig` checks it
# against the catalog, which doubles as the allowlist, so an unknown name is
# refused before anything runs. The capability is looked up there rather than
# sent by the browser, so the browser has no chance to get it wrong.
@router.get("/admin/sprigs/panel", response_class=HTMLResponse)
async def sprigs_panel(request: Request, user=Depends(require_admin_page)) -> HTMLResponse:
    return HTMLResponse(await render_panel(request, user))


@router.post("/admin/sprigs/{verb}/{name}", response_class=HTMLResponse)
async def sprigs_action(
    verb: Literal["graft", "prune"],
    name: str,
    request: Request,
    user=Depends(require_admin_page),
) -> HTMLResponse:
    return HTMLResponse(await run_action(request, user, name, verb))


@router.get("/admin/branding", response_class=HTMLResponse)
async def branding_page(
    request: Request, user=Depends(require_admin_page)
) -> HTMLResponse:
    """Theme & branding — the first form-only surface.

    The form arrives filled in. The Svelte version renders an empty form, boots,
    fetches the config and then populates it, which is visible as a flash on a
    slow connection and is the reason its spec has to wait for a value rather
    than for the field.
    """
    return _whole_page(
        request,
        "admin/branding",
        render_branding(request),
        ("vendor/htmx.min.js", "color-pair.js"),
    )


@router.post("/admin/branding/save", response_class=HTMLResponse)
async def branding_save(
    request: Request, user=Depends(require_admin_page)
) -> HTMLResponse:
    """Save, then return the whole panel.

    The form is read straight off the request rather than declared as `Form(...)`
    parameters, because the field list already exists in one place
    (`branding_panel.FIELDS`) and restating it here as seven arguments would be a
    second copy to keep in step. `save_branding` takes only the names it knows,
    so an extra posted value cannot reach the config.
    """
    form = await request.form()
    return HTMLResponse(await save_branding(request, user, dict(form)))


# ── The Agents surface ────────────────────────────────────────────────────────
#
@router.get("/workshop/agents", response_class=HTMLResponse)
async def agents_page(
    request: Request,
    q: str = "",
    tag: str = "",
    # `int` so FastAPI rejects `?page=abc` with a 422 before the handler runs;
    # `ge=1` so a negative page cannot index backwards into the list. The panel
    # clamps the upper end, because a stale bookmark past the last page should
    # land on the last page rather than an error.
    page: int = Query(1, ge=1),
    user=Depends(require_agents_reader),
) -> HTMLResponse:
    """The agent list, rendered. No script on the page at all.

    Search and the tag filter are a GET form and links, so their state is in the
    URL: shareable, back-button-correct, and cacheable per query. The Svelte
    page holds them in component state and ships `marked`, `sortablejs` and
    `file-saver` to draw the same list.
    """
    return _whole_page(
        request,
        "workshop/agents",
        await render_agents(request, user, query=q, tag=tag, page=page),
    )


@router.post("/workshop/agents/{verb}/{agent_id:path}", response_class=HTMLResponse)
async def agents_action(
    verb: AgentVerb,
    agent_id: str,
    request: Request,
    user=Depends(require_agents_reader),
) -> HTMLResponse:
    """One row action, then the whole page back.

    `Literal` so FastAPI refuses an unknown verb with a 422 before the handler
    runs, the same shape the Sprigs routes use. `agent_id:path` because a model
    id may contain a slash (`ollama/llama3`), and the default converter would
    split it into a 404.
    """
    # The WHOLE page, not the fragment. A fragment is right for a surface whose
    # response is swapped into a live document — that is why `/admin/sprigs`
    # returns one, and htmx puts it where it belongs. This surface has no
    # swapper: the form does an ordinary POST, so the browser NAVIGATES to
    # whatever comes back. Returning a bare panel meant navigating to a document
    # with no <head> and no stylesheet, and every action — toggle, hide, clone,
    # delete — dropped the reader onto an unstyled page. Shipped that way, and
    # invisible to every gate, because they all assert server state and hook
    # presence and none of them asks whether a document is still a document.
    return _whole_page(request, "workshop/agents", await run_agent_action(request, user, agent_id, verb))


@router.get("/workshop/agents/export")
@router.get("/workshop/agents/export/{agent_id:path}")
async def agents_export(
    agent_id: str = "", user=Depends(require_agents_reader)
) -> JSONResponse:
    """Download one agent or all of them as JSON.

    A link with `download`, not a Blob assembled in the browser — the server
    already holds the data, and building it client-side was the only thing
    `file-saver` did on this surface.
    """
    name = f"{agent_id or 'agents'}-export.json"
    return JSONResponse(
        await export_agents(user, agent_id),
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@router.post("/workshop/agents/import", response_class=HTMLResponse)
async def agents_import(
    request: Request, file: UploadFile = File(...), user=Depends(require_agents_reader)
) -> HTMLResponse:
    return _whole_page(request, "workshop/agents", await import_agents(request, user, await file.read()))


@router.get("/workshop/agents/avatar/{agent_id:path}")
async def agents_avatar(
    agent_id: str, user=Depends(require_agents_reader)
) -> Response:
    """An agent's picture as bytes, cached hard.

    The version token in the query is the content hash, so this URL changes when
    the image does and `immutable` is safe. That is the difference between an
    avatar costing its bytes once per browser and once per page load — which is
    what it costs today, inlined as base64 in every list response.
    """
    data, media = await avatar_bytes(user, agent_id)
    return Response(content=data, media_type=media, headers={"Cache-Control": AVATAR_CACHE})


# ── The Prompts surface ───────────────────────────────────────────────────────
#
@router.get("/workshop/prompts", response_class=HTMLResponse)
async def prompts_page(
    request: Request,
    q: str = "",
    page: int = Query(1, ge=1),
    user=Depends(require_agents_reader),
) -> HTMLResponse:
    """The prompt list, rendered. No script on the page at all.

    Guarded by `require_agents_reader` on purpose: the workshop is one
    permission (`workshop.models`) in `USER_PERMISSIONS`, and inventing a second
    one for prompts would let the two drift and would be a policy this page
    made up rather than one the operator set.
    """
    return _whole_page(
        request,
        "workshop/prompts",
        await render_prompts(request, user, query=q, page=page),
    )


@router.post("/workshop/prompts/{verb}/{command:path}", response_class=HTMLResponse)
async def prompts_action(
    verb: PromptVerb,
    command: str,
    request: Request,
    confirm: int = 0,
    user=Depends(require_agents_reader),
) -> HTMLResponse:
    """One row action, then the panel back.

    `command:path` because a prompt command is user-chosen text that may contain
    a slash; the default converter would split it into a 404.

    `confirm` is the second step of a destructive action, and it is a QUERY
    parameter rather than a hidden field so the difference between "asked" and
    "did it" is visible in the log and in the browser's own history. A delete
    without it re-renders the row asking; with it, the row goes.
    """
    # The whole page — see the note on `agents_action`. Same reason, same trap.
    return _whole_page(
        request,
        "workshop/prompts",
        await run_prompt_action(request, user, command, verb, confirmed=bool(confirm)),
    )


@router.get("/workshop/prompts/export")
@router.get("/workshop/prompts/export/{command:path}")
async def prompts_export(
    command: str = "", user=Depends(require_agents_reader)
) -> JSONResponse:
    """Download one prompt or all of them as JSON."""
    name = f"{command or 'prompts'}-export.json"
    return JSONResponse(
        await export_prompts(user, command),
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@router.post("/workshop/prompts/import", response_class=HTMLResponse)
async def prompts_import(
    request: Request, file: UploadFile = File(...), user=Depends(require_agents_reader)
) -> HTMLResponse:
    return _whole_page(request, "workshop/prompts", await import_prompts(request, user, await file.read()))


# The whole-page surfaces, the way `_SETUP_PAGES` does it for the wizard.
#
# These headings used to be literals inside each route body, which was fine
# while nothing else needed them. The index below needs them too, and a second
# copy of a heading is a heading that drifts — so they live here once and both
# the route and the index read them.
_PAGES: dict[str, tuple[str, str]] = {
    "admin/sprigs": (
        "Sprigs™",
        "Capabilities grafted onto the Rootstock™ at runtime — "
        "no model download, no pip install.",
    ),
    "admin/diagnostics": (
        "Diagnostics",
        "What this Rootstock™ can reach, and what it cannot.",
    ),
    "admin/branding": (
        "Theme & Branding",
        "The name, the marks and the colours this instance wears.",
    ),
    # Not under `admin/`, and that is the point: this surface is permission-gated
    # rather than admin-only, so putting it in the admin tree would be a trap for
    # whoever audits by path next. Same reasoning as `/pages/changelog`.
    "workshop/agents": (
        "Agents",
        "A model, a system prompt, the knowledge and tools it may reach.",
    ),
    "workshop/prompts": (
        "Prompts",
        "Reusable snippets your team can call by name in any conversation.",
    ),
}


_SETUP_PAGES = {
    "changelog": ("What's New", "Everything that changed, newest first."),
    "welcome": ("Setup Wizard", "Pick what to configure. Nothing here is permanent."),
    "auth": ("Authentication", "Let people sign in with Google, GitHub, or an emailed link."),
    "connection": ("Model Connections", "Point this instance at a model provider."),
    "users": ("Users", "Invite your team, or say you are working alone."),
    "features": ("Features", "Enable or disable platform features for your users."),
    "developer": ("Developer Mode", "Run this thing from source, with hot reload."),
    "complete": ("You are all set", "What this instance has configured so far."),
    "search-audio": ("AI Engine", "Document search and speech-to-text, installed locally."),
}


# The order a reader walks the panels in: authentication first, then
# connections, users, features, the AI engine, developer, and the summary last.
#
# The only copy. It began as a mirror of `allSteps` in the Svelte orchestrator,
# which is deleted; the sequence is not restated in the dialog host, which asks
# the server where to go next, nor in `setup-navigation.cy.ts`, which discovers
# it by walking `setup-next`.
_SETUP_ORDER = (
    "changelog",
    "welcome",
    "auth",
    "connection",
    "users",
    "features",
    "search-audio",
    "developer",
    "complete",
)

_NAV_S = "--d:flex; --jc:space-between; --ai:center; --g:1rem; --m:1.5rem 0 0"
_STEP_S = "--size:.75rem; --op:.6"


def _page_headers(request: Request) -> dict[str, str]:
    """Cache-correctness headers for a rendered page.

    `Vary: Accept-Language` only when the header decided the locale, which is a
    cold entry with no `?lang=`. Once the reader is inside, every link carries the
    parameter and the URL alone identifies the representation.

    Never `Vary: Cookie`. See `i18n.locale_for`.

    The approved plan called for redirecting cold entries to the canonical URL
    instead. This costs one fewer round trip and behaves better when a link is
    passed between people: a redirect bakes the SHARER's language into the address
    they copy, and the recipient's own `Accept-Language` is then ignored.
    """
    if request.query_params.get("lang") in supported():
        return {}
    return {"Vary": "Accept-Language"}


def _setup_nav(panel: str, lang: str = "") -> str:
    """Previous and next links between the setup routes.

    A panel at its own address has no wizard around it, so without this each
    route is a cul-de-sac — you land, you act, and there is nowhere to go. The
    modal's sequence is Svelte state that nothing here can read, so the order
    lives in `_SETUP_ORDER` and the links are plain anchors.

    Not a replacement for the wizard's skip logic, which is the orchestrator's
    job and still belongs to the modal. This is navigation, not a flow.
    """
    if panel not in _SETUP_ORDER:
        return ""
    i = _SETUP_ORDER.index(panel)
    back = (
        f'<a data-cy="setup-prev" href="/pages/admin/setup/{_SETUP_ORDER[i - 1]}{lang}">'
        f"&larr; {escape(_SETUP_PAGES[_SETUP_ORDER[i - 1]][0])}</a>"
        if i
        else "<span></span>"
    )
    forward = (
        f'<a data-cy="setup-next" href="/pages/admin/setup/{_SETUP_ORDER[i + 1]}{lang}">'
        f"{escape(_SETUP_PAGES[_SETUP_ORDER[i + 1]][0])} &rarr;</a>"
        if i + 1 < len(_SETUP_ORDER)
        else "<span></span>"
    )
    return (
        f'<nav style="{_NAV_S}">{back}'
        f'<small data-cy="setup-step" data-step="{i + 1}" data-of="{len(_SETUP_ORDER)}"'
        f' style="{_STEP_S}">{i + 1} of {len(_SETUP_ORDER)}</small>'
        f"{forward}</nav>"
    )


def _next_setup_url(panel: str, lang: str = "") -> str:
    """Where "continue" goes from here; the last panel continues to itself."""
    i = _SETUP_ORDER.index(panel)
    nxt = _SETUP_ORDER[i + 1] if i + 1 < len(_SETUP_ORDER) else panel
    return f"/pages/admin/setup/{nxt}{lang}"


def _setup_page(
    request: Request, panel: str, body: str, scripts: tuple[str, ...] = ()
) -> HTMLResponse:
    """One shell call for every setup panel.

    The changelog route needed the same six arguments twice — once for the GET
    and once for the response to its post — and nine panels would have made that
    thirty-six. The titles live in one table instead.
    """
    heading, subheading = _SETUP_PAGES[panel]
    return HTMLResponse(
        render_page(
            request=request,
            title=f"{heading} — Sage.is AI",
            heading=heading,
            subheading=subheading,
            scripts=scripts,
            body=body + _setup_nav(panel, lang_query(request)),
        ),
        headers=_page_headers(request),
    )


@router.get("/admin/setup/changelog", response_class=HTMLResponse)
async def setup_changelog_page(
    request: Request, user=Depends(require_admin_page)
) -> HTMLResponse:
    """What's new — the setup wizard's changelog branch, at an address.

    The Svelte original has no URL at all: it is a branch of a modal, reached by
    a button that sets a store. Giving it a route is what lets the guard-rail
    spec and the parity gate judge it the same way they judge every other
    surface, instead of the wizard migrating on weaker evidence than the pages
    that came before it.

    No scripts. The panel is text and one form post, so there is nothing for
    htmx to swap.
    """
    return _setup_page(
        request, "changelog", render_changelog(request), scripts=("changelog-pager.js",)
    )


@router.post("/admin/setup/changelog/seen", response_class=HTMLResponse)
async def setup_changelog_seen(
    request: Request, user=Depends(require_admin_page)
) -> HTMLResponse:
    """Record the read, then move on.

    The one mutation here that does NOT re-render its own panel. Everywhere else
    the response is the panel, so no client-side model can drift from the
    server's — but "Continue" means continue, and handing back the notes you
    just finished reading would be a dead end. 303 rather than 302, so the
    browser follows with GET and a reload does not re-post.
    """
    await mark_changelog_read(request, user)
    return RedirectResponse(
        _next_setup_url("changelog", lang_query(request)), status_code=303
    )


# The one route here that is not admin-only, and the reason it exists is the
# cut-over: Settings, About, "See what's new" is a control every reader has, and
# before the wizard moved to the server it opened a Svelte panel with no role
# check. Serving those notes only from `/admin/` would have turned a working
# button into a 403 for everyone who is not an admin.
#
# Same renderer as the wizard panel, different post target and no wizard
# navigation — a reader who is not configuring the instance has no next step.
@router.get("/changelog", response_class=HTMLResponse)
async def changelog_page(
    request: Request, user=Depends(require_page_user)
) -> HTMLResponse:
    heading, subheading = _SETUP_PAGES["changelog"]
    return HTMLResponse(
        render_page(
            request=request,
            title=f"{heading} — Sage.is AI",
            heading=heading,
            subheading=subheading,
            scripts=("changelog-pager.js",),
            body=render_changelog(request, base="/pages/changelog"),
        ),
        headers=_page_headers(request),
    )


@router.post("/changelog/seen", response_class=HTMLResponse)
async def changelog_seen(
    request: Request, user=Depends(require_page_user)
) -> RedirectResponse:
    """Record the read, then leave the pages surface.

    Back to the app rather than to another panel, because for this reader the
    notes were the whole errand. That is also what closes the dialog: the host
    in `SetupDialog.svelte` closes when a response lands outside `/pages/`, so
    the same redirect serves the reader with JavaScript and the one without.
    """
    await mark_changelog_read(request, user)
    return RedirectResponse("/", status_code=303)


@router.get("/admin/setup/welcome", response_class=HTMLResponse)
async def setup_welcome_page(
    request: Request, user=Depends(require_admin_page)
) -> HTMLResponse:
    return _setup_page(request, "welcome", render_welcome(request, user))


@router.post("/admin/setup/welcome/start", response_class=HTMLResponse)
async def setup_welcome_start(
    request: Request, user=Depends(require_admin_page)
) -> RedirectResponse:
    """Store the chosen steps, then go to the first one that has an address.

    303 rather than a re-render: "Get Started" means start, and handing back the
    same list of choices would be the dead end the changelog post already
    avoids.
    """
    form = await request.form()
    return RedirectResponse(
        await start_wizard(request, user, dict(form)), status_code=303
    )


@router.get("/admin/setup/connection", response_class=HTMLResponse)
async def setup_connection_page(
    request: Request, user=Depends(require_admin_page)
) -> HTMLResponse:
    return _setup_page(request, "connection", render_connection(request))


@router.post("/admin/setup/connection/{provider}", response_class=HTMLResponse)
async def setup_connection_save(
    provider: Literal["openai", "ollama"],
    request: Request,
    user=Depends(require_admin_page),
) -> HTMLResponse:
    """Verify one provider, then save it.

    The provider travels in the path and is constrained to the two this panel
    knows, so an unknown value is refused by FastAPI before any handler runs.
    """
    form = await request.form()
    return _setup_page(
        request, "connection", await verify_and_save(request, user, provider, dict(form))
    )


@router.get("/admin/setup/users", response_class=HTMLResponse)
async def setup_users_page(
    request: Request, user=Depends(require_admin_page)
) -> HTMLResponse:
    return _setup_page(request, "users", render_users(request, user))


@router.post("/admin/setup/users/add", response_class=HTMLResponse)
async def setup_users_add(
    request: Request, user=Depends(require_admin_page)
) -> HTMLResponse:
    form = await request.form()
    return _setup_page(request, "users", await add_one_user(request, user, dict(form)))


@router.post("/admin/setup/users/import", response_class=HTMLResponse)
async def setup_users_import(
    request: Request, user=Depends(require_admin_page)
) -> HTMLResponse:
    """Import a CSV in one request.

    The whole file is read here rather than streamed, because it is a list of
    people an admin typed and the row loop has to hold the parse anyway. A file
    large enough for that to matter is not a wizard step.
    """
    form = await request.form()
    upload = form.get("csv")
    raw = await upload.read() if hasattr(upload, "read") else b""
    if not raw:
        return _setup_page(
            request, "users", render_users(request, user, "Choose a CSV file first.")
        )
    return _setup_page(request, "users", await import_csv(request, user, raw))


@router.post("/admin/setup/users/alone", response_class=HTMLResponse)
async def setup_users_alone(
    request: Request, user=Depends(require_admin_page)
) -> HTMLResponse:
    await set_working_alone(request, user)
    return _setup_page(
        request, "users", render_users(request, user, "Recorded: working alone.")
    )


@router.get("/admin/setup/auth", response_class=HTMLResponse)
async def setup_auth_page(
    request: Request, user=Depends(require_admin_page)
) -> HTMLResponse:
    return _setup_page(request, "auth", await render_auth(request, user))


@router.post("/admin/setup/auth/save", response_class=HTMLResponse)
async def setup_auth_save(
    request: Request, user=Depends(require_admin_page)
) -> HTMLResponse:
    form = await request.form()
    return _setup_page(request, "auth", await save_auth(request, user, dict(form)))


@router.get("/admin/setup/features", response_class=HTMLResponse)
async def setup_features_page(
    request: Request, user=Depends(require_admin_page)
) -> HTMLResponse:
    return _setup_page(request, "features", render_features(request))


@router.post("/admin/setup/features/save", response_class=HTMLResponse)
async def setup_features_save(
    request: Request, user=Depends(require_admin_page)
) -> HTMLResponse:
    """Save, then return the whole panel.

    The form is read off the request rather than declared as `Form(...)`
    parameters, because the field list already exists in `features_panel.FIELDS`
    and restating it here would be a second copy to keep in step. `save_features`
    reads only the names it knows, so an extra posted value cannot reach the
    config.
    """
    form = await request.form()
    return _setup_page(request, "features", await save_features(request, user, dict(form)))


@router.get("/admin/setup/developer", response_class=HTMLResponse)
async def setup_developer_page(
    request: Request, user=Depends(require_admin_page)
) -> HTMLResponse:
    return _setup_page(request, "developer", render_developer(request, user))


@router.post("/admin/setup/developer/save", response_class=HTMLResponse)
async def setup_developer_save(
    request: Request, user=Depends(require_admin_page)
) -> HTMLResponse:
    form = await request.form()
    return _setup_page(
        request, "developer", await save_developer(request, user, dict(form))
    )


@router.get("/admin/setup/complete", response_class=HTMLResponse)
async def setup_complete_page(
    request: Request, user=Depends(require_admin_page)
) -> HTMLResponse:
    return _setup_page(request, "complete", render_complete(request, user))


@router.post("/admin/setup/complete/finish", response_class=HTMLResponse)
async def setup_complete_finish(
    request: Request, user=Depends(require_admin_page)
) -> RedirectResponse:
    """Record that setup is done, then hand the reader back to the app.

    This used to re-render the summary, which was a dead end: you press "Let's
    Go" and get the same page you were already looking at. The modal closed
    instead, and closing is what the button means. Leaving `/pages/` is now how
    that is said — the dialog host closes on it, and a reader without JavaScript
    lands in the app rather than back on the summary.
    """
    await finish_setup(request, user)
    return RedirectResponse("/", status_code=303)


@router.get("/admin/setup/search-audio", response_class=HTMLResponse)
async def setup_search_audio_page(
    request: Request, user=Depends(require_admin_page)
) -> HTMLResponse:
    return _setup_page(request, "search-audio", render_search_audio(request))


@router.post("/admin/setup/search-audio/graft", response_class=HTMLResponse)
async def setup_search_audio_graft(
    request: Request, user=Depends(require_admin_page)
) -> HTMLResponse:
    """Graft the selected cultivars, then return the whole panel.

    The component names travel in the form; the cultivar and its capability are
    looked up from `COMPONENTS` and the catalog. The browser never names a
    cultivar, so it cannot ask for one that is not on this panel.
    """
    form = await request.form()
    return _setup_page(
        request, "search-audio", await graft_components(request, user, dict(form))
    )


@router.post("/admin/setup/search-audio/download", response_class=HTMLResponse)
async def setup_search_audio_download(
    request: Request, user=Depends(require_admin_page)
) -> HTMLResponse:
    form = await request.form()
    return _setup_page(
        request, "search-audio", await download_components(request, user, dict(form))
    )


@router.get("/admin/diagnostics", response_class=HTMLResponse)
async def diagnostics_page(
    request: Request, user=Depends(require_admin_page)
) -> HTMLResponse:
    """Diagnostics, answered in the first response.

    The Svelte version downloads a bundle and boots a framework before it can
    ask what is broken. When the thing that is broken is the frontend, that
    ordering matters more than it usually does.
    """
    return _whole_page(
        request,
        "admin/diagnostics",
        await render_diagnostics(request, user),
        ("vendor/htmx.min.js",),
    )


@router.post("/admin/diagnostics/probe", response_class=HTMLResponse)
async def diagnostics_probe(
    request: Request,
    url: str = Form(...),
    capability: str = Form(""),
    user=Depends(require_admin_page),
) -> HTMLResponse:
    """Re-probe one endpoint, then re-render.

    Calls the API handler rather than reimplementing it, which matters more here
    than elsewhere: that handler refuses any URL not currently configured
    (rule R6 — re-probe must never become an arbitrary-URL primitive, even under
    admin auth). Routing around it to save a few lines would route around the
    SSRF defence too.
    """
    from sage_is_ai.routers.diagnostics import ProbeForm, probe_endpoint

    try:
        await probe_endpoint(ProbeForm(url=url, capability=capability or None), request, user)
    except HTTPException:
        # The refusal is the interesting case and it is already visible in the
        # re-rendered row's status; a probe that fails is data, not an error.
        pass
    return HTMLResponse(await render_diagnostics(request, user))


@router.get("/admin/diagnostics/panel", response_class=HTMLResponse)
async def diagnostics_panel(
    request: Request, user=Depends(require_admin_page)
) -> HTMLResponse:
    return HTMLResponse(await render_diagnostics(request, user))
