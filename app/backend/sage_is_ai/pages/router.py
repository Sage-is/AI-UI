"""No-build pages — Phase 0 of the frontend migration.

Every route here is explicit, so it resolves before the SPA catch-all and the
compiled bundle never sees it. The SPA keeps its own `/admin/sprigs`; this
serves a second, independent implementation of the same panel at
`/pages/admin/sprigs`. Both are live at once, which is the point: the guard-rail
Cypress spec runs against either one and must pass against both.

Pages authenticate from the auth cookie (see auth.py). The island still reads
the localStorage token for its own JSON calls, because the SPA put it there and
both surfaces are live at once — but the page itself is now gated, so a
signed-out visitor lands on the sign-in screen instead of on chrome wrapped
around an empty list.
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from sage_is_ai.pages.auth import require_admin_page
from sage_is_ai.pages.shell import render_page

router = APIRouter()


@router.get("/admin/sprigs", response_class=HTMLResponse)
async def sprigs_page(
    request: Request, user=Depends(require_admin_page)
) -> HTMLResponse:
    """The Sprigs™ admin panel, without a compiler.

    The Svelte version of this panel is 238 lines and reaches the backend
    through the generated API wrapper layer. This one talks to the same
    endpoints directly. The list markup is built by the island rather than the
    server because the catalog call needs the operator's token, which lives in
    localStorage — so this page proves the no-build path and deletes wrapper
    code, and it does NOT yet prove a first-paint win. Fragments that render
    server-side arrive with the cookie bridge in Phase 1.
    """
    body = """
    <div class="panel-bar">
      <span class="page-count" data-cy="sprigs-grafted-count"></span>
      <button type="button" data-cy="sprigs-refresh" class="btn">Refresh</button>
    </div>
    <div id="sprigs" class="sprig-list" aria-busy="true">
      <p class="page-muted" data-cy="sprigs-loading">Loading the catalog…</p>
    </div>
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
            scripts=["sprigs.js"],
            body=body,
        )
    )
