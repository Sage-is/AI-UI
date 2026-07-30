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

from typing import Literal

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse

from sage_is_ai.pages.auth import require_admin_page
from sage_is_ai.pages.shell import render_page
from sage_is_ai.pages.branding_panel import render_branding, save_branding
from sage_is_ai.pages.changelog_panel import mark_changelog_read, render_changelog
from sage_is_ai.pages.features_panel import render_features, save_features
from sage_is_ai.pages.developer_panel import render_developer, save_developer
from sage_is_ai.pages.complete_panel import finish_setup, render_complete
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
    "features": ("Features", "Enable or disable platform features for your users."),
    "developer": ("Developer Mode", "Run this thing from source, with hot reload."),
    "complete": ("You are all set", "What this instance has configured so far."),
    "search-audio": ("AI Engine", "Document search and speech-to-text, installed locally."),
}


def _setup_page(request: Request, panel: str, body: str) -> HTMLResponse:
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
            body=body,
        )
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
    return _setup_page(request, "changelog", render_changelog(request))


@router.post("/admin/setup/changelog/seen", response_class=HTMLResponse)
async def setup_changelog_seen(
    request: Request, user=Depends(require_admin_page)
) -> HTMLResponse:
    """Record the read, then re-render.

    Same shape as every other mutation here: the response IS the panel, so
    there is no client-side model that can fall out of step with the server's.
    """
    await mark_changelog_read(request, user)
    return _setup_page(request, "changelog", render_changelog(request))


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
) -> HTMLResponse:
    await finish_setup(request, user)
    return _setup_page(request, "complete", render_complete(request, user))


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
