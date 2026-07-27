"""No-build pages — the frontend migration's server-rendered surface.

Every route here is explicit, so it resolves before the SPA catch-all and the
compiled bundle never sees it. The SPA keeps its own `/admin/sprigs`; this
serves an independent implementation of the same panel at
`/pages/admin/sprigs`. Both are live at once, which is the point: the guard-rail
Cypress spec runs against either one and must pass against both.

Pages authenticate from the auth cookie (see auth.py), which is what lets the
panel be rendered by the SERVER rather than assembled in the browser. Phase 0
could not do that — the token lived in localStorage — and the island it built
instead came out bigger than the Svelte component it replaced. This is the
rebuild that measures the difference.
"""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse

from sage_is_ai.pages.auth import require_admin_page
from sage_is_ai.pages.shell import render_page
from sage_is_ai.pages.sprigs_panel import (
    graft_and_render,
    prune_and_render,
    render_panel,
)

router = APIRouter()


@router.get("/admin/sprigs", response_class=HTMLResponse)
async def sprigs_page(
    request: Request, user=Depends(require_admin_page)
) -> HTMLResponse:
    """The Sprigs™ admin panel, without a compiler.

    The panel arrives rendered. There is no loading state, no second request,
    and no client-side copy of the catalog — the first paint IS the data, which
    is the thing the island version could not do.
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
@router.get("/admin/sprigs/panel", response_class=HTMLResponse)
async def sprigs_panel(
    request: Request, user=Depends(require_admin_page)
) -> HTMLResponse:
    return HTMLResponse(await render_panel(request, user))


@router.post("/admin/sprigs/graft", response_class=HTMLResponse)
async def sprigs_graft(
    request: Request,
    name: str = Form(...),
    capability: str = Form(...),
    user=Depends(require_admin_page),
) -> HTMLResponse:
    return HTMLResponse(await graft_and_render(request, user, name, capability))


@router.post("/admin/sprigs/prune", response_class=HTMLResponse)
async def sprigs_prune(
    request: Request, name: str = Form(...), user=Depends(require_admin_page)
) -> HTMLResponse:
    return HTMLResponse(await prune_and_render(request, user, name))
