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
from typing import Literal

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from sage_is_ai.pages.auth import require_admin_page, require_page_user
from sage_is_ai.pages.i18n import lang_query, supported
from sage_is_ai.pages.shell import render_page
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

router = APIRouter()


@router.get("/admin/sprigs", response_class=HTMLResponse)
async def sprigs_page(
    request: Request, user=Depends(require_admin_page)
) -> HTMLResponse:
    """The Sprigs™ admin panel, without a compiler.

    The panel arrives rendered, so there is no loading state and no second
    request for the catalog. The first paint is the data, which is what the
    island version could not manage.
    """
    return HTMLResponse(
        render_page(
            request=request,
            title="Sprigs — Sage.is AI",
            heading="Sprigs™",
            subheading=(
                "Capabilities grafted onto the Rootstock™ at runtime — "
                "no model download, no pip install."
            ),
            scripts=["vendor/htmx.min.js"],
            body=await render_panel(request, user),
        )
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
    return HTMLResponse(
        render_page(
            request=request,
            title="Theme & Branding — Sage.is AI",
            heading="Theme & Branding",
            subheading="The name, the marks and the colours this instance wears.",
            scripts=["vendor/htmx.min.js", "color-pair.js"],
            body=render_branding(request),
        )
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
    return HTMLResponse(
        render_page(
            request=request,
            title="Diagnostics — Sage.is AI",
            heading="Diagnostics",
            subheading="What this Rootstock™ can reach, and what it cannot.",
            scripts=["vendor/htmx.min.js"],
            body=await render_diagnostics(request, user),
        )
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
