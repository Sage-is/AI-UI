"""Server-rendered page shell — the seam the strangler grows through.

The plan's end state is that this backend renders the interface and small
islands of JavaScript own the parts that behave like an app. Today it renders
nothing; the SPA catch-all in main.py serves a compiled bundle for every path
that is not already a real route. `/themes/active.css` already proves an
explicit route wins against that catch-all, so no-build pages can live beside
the SPA for the whole migration without either one knowing about the other.

There is no template engine here on purpose. Adding one is a dependency
decision that deserves its own argument, and the pilot needs exactly one
layout. When the second and third pages arrive and this starts to strain,
that is the signal to bring a real engine in — not before.

The one rule this file enforces: escape anything interpolated. A shell that
concatenates strings is a cross-site-scripting engine unless escaping is the
default path rather than the remembered one, so callers pass values and never
markup.
"""

from html import escape
from typing import Iterable

from fastapi import Request

from sage_is_ai.env import VERSION

__all__ = ["render_page", "asset_url"]


def asset_url(filename: str) -> str:
    """Cache-bust by release.

    The assets are served with a week-long Cache-Control, which is only safe if
    an upgrade changes the URL. They are not content-hashed — there is no build
    step to hash them, which is the whole point — so the release version stands
    in. It changes exactly when the file could have changed.
    """
    return f"/pages/_assets/{filename}?v={escape(VERSION, quote=True)}"


def _ui_sprig_slot(request: Request) -> str:
    """The marketplace slot: where a grafted ui-Sprig's fragment appears.

    Server-side, not a client fetch. The fragment is already on this machine and
    already validated, so rendering it here means it arrives with the page —
    no second request, no flash of a slot-shaped hole, and no path where
    unvalidated markup could be injected by something other than a graft.

    Empty when no ui-Sprig is grafted, which is the common case and costs one
    config read.
    """
    from sage_is_ai.sprigs.ui_dispatch import (
        UiValidationError,
        ui_fragment_path,
        validate_ui_bundle,
    )

    # Read through app.state.config, never the module-level PersistentConfig
    # objects. They are the same objects today, but AppConfig.__getattr__ checks
    # Redis for a newer value when Redis is configured — so a direct module read
    # would be correct on one worker and stale on the next, which is the kind of
    # divergence that only shows up after multi-worker ships.
    cfg = request.app.state.config
    name = str(cfg.SPRIG_ACTIVE_UI or "").strip()
    if not name:
        return ""

    granted = str(cfg.SPRIG_UI_SCRIPTING_GRANT or "").strip()
    try:
        # Revalidated at render, not trusted from graft time. The bytes have not
        # changed, but the scripting grant is a separate value an admin can
        # revoke without regrafting — and a fragment that only passed because of
        # a grant must stop rendering when the grant is gone.
        validate_ui_bundle(name, scripting_granted=granted == name)
        markup = ui_fragment_path(name).read_text(encoding="utf-8")
    except (UiValidationError, OSError):
        return ""

    # Not escaped, deliberately, and this is the one place in the shell that is
    # true: a ui-Sprig IS markup, and it passed the fail-closed contract in
    # sprigs/ui_dispatch.py to get here. That contract is what makes this safe,
    # so it is the thing to protect — never widen this to content that has not
    # been through it.
    return f'<section id="sprig-ui-slot" data-sprig-ui="{escape(name, quote=True)}">{markup}</section>'


def render_page(
    *,
    request: Request,
    title: str,
    heading: str,
    subheading: str = "",
    scripts: Iterable[str] = (),
    body: str = "",
) -> str:
    """Render the chrome around a page's island.

    `body` is the one parameter that carries markup, and it is written here in
    the codebase rather than derived from user input. Everything else is
    escaped. Keep it that way.
    """
    script_tags = "\n  ".join(
        f'<script type="module" src="{escape(asset_url(s), quote=True)}"></script>'
        for s in scripts
    )
    sub = (
        f'<p class="page-sub">{escape(subheading)}</p>' if subheading else ""
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(title)}</title>
  <link rel="stylesheet" href="{escape(asset_url('pages.css'), quote=True)}" />
</head>
<body>
  <main class="page">
    <header class="page-head">
      <h1>{escape(heading)}</h1>
      {sub}
    </header>
    {body}
    {_ui_sprig_slot(request)}
  </main>
  <!-- Islands report failures here rather than into the console, so an
       operator sees what went wrong without opening devtools. -->
  <div id="toasts" role="status" aria-live="polite"></div>
  {script_tags}
</body>
</html>
"""
