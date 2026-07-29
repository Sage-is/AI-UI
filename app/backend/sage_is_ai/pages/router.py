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
