"""No-build pages — Phase 0 of the frontend migration.

Every route here is explicit, so it resolves before the SPA catch-all and the
compiled bundle never sees it. The SPA keeps its own `/admin/sprigs`; this
serves a second, independent implementation of the same panel at
`/pages/admin/sprigs`. Both are live at once, which is the point: the guard-rail
Cypress spec runs against either one and must pass against both.

No authentication on the page itself, deliberately. The shell carries no
privileged data — it is chrome and an empty list. The island reads the token
the SPA already put in localStorage and calls the same authenticated JSON
endpoints the Svelte panel calls, so an unauthenticated visitor gets a page
that renders and then tells them to sign in. Serving fragments that DO carry
privileged data needs the token as a cookie, and that bridge is Phase 1 work.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from sage_is_ai.pages.shell import render_page

router = APIRouter()


@router.get("/admin/sprigs", response_class=HTMLResponse)
async def sprigs_page() -> HTMLResponse:
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
