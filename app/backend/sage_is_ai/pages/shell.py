"""Server-rendered page shell — the seam the strangler grows through.

The plan's end state is that this backend renders the interface and small
islands of JavaScript own the parts that behave like an app. Today it renders
nothing; the SPA catch-all in main.py serves a compiled bundle for every path
that is not already a real route. `/themes/active.css` already proves an
explicit route wins against that catch-all, so no-build pages can live beside
the SPA for the whole migration without either one knowing about the other.

STILL AN F-STRING, AND DELIBERATELY SO. Every one of the twelve panels moved to
Jinja2 on 2026-08-01, for two reasons: a template is data read from disk, so a
markup edit costs a refresh instead of an app restart; and autoescape makes
escaping structural instead of remembered. Neither argument reaches this file.

The dev-loop half does not apply because the shell's markup does not change —
you restyle a panel, not the chrome around it — so `auto_reload` buys nothing
here.

The escaping half actually points the other way. Counted: this file interpolates
three ESCAPED values and four RAW ones (the body, the script tags, the subhead,
and the ui-Sprig slot). In an f-string, raw is the default and `escape()` marks
the exception; in a template, escaped is the default and `| safe` marks it. With
raw in the majority, moving here would mean four `| safe` markers — and `| safe`
is precisely the escape hatch that undoes what autoescape is for. The one rule
below stays easier to hold in an f-string than the inversion of it would be in a
template.

Revisit if that ratio flips, or if a second layout appears.

The one rule this file enforces: escape anything interpolated. A shell that
concatenates strings is a cross-site-scripting engine unless escaping is the
default path rather than the remembered one, so callers pass values and never
markup.

EGRESS
------
These pages load startr.style from its public URL, which is the one place this
product reaches off-machine on a normal page load. Everything else about the
Rootstock is built the other way: Sprigs are in-housed so no operator pulls from
HuggingFace, theme and ui-Sprig bundles are refused at graft if they reference
an external URL, and the pitch to a workshop is that nothing they type leaves
the room.

A stylesheet leaks far less than a script — no cookies are sent cross-origin for
a CSS link, and it cannot read the page — but it does tell startr.style that
someone opened an admin page, and an air-gapped deployment gets unstyled chrome.
Both are deliberate for now (Alexander, 2026-07-28), and both stop being true
when the versioned URL lands with SRI, or when a self-host flag serves a
vendored copy instead. Until then, keep layout that must not break in
pages.css: the local sheet is what survives the CDN being unreachable.
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
    # The development reloader's island, on every page or on none.
    #
    # Read at call time rather than at import, because a module-level read here
    # would bake the answer in at boot and the reloader's whole job is that boot
    # happens again. Appended in ONE place so a new page cannot be added that
    # forgets it — the failure would be the page that silently stops refreshing,
    # which is indistinguishable from the reloader being broken.
    from sage_is_ai.env import PAGES_RELOAD_DIRS

    scripts = (*scripts, "dev-reload.js") if PAGES_RELOAD_DIRS else scripts

    # Classic and deferred, not `type="module"`. A module is scoped, so a
    # library that publishes itself by declaring a top-level `var` — htmx does
    # exactly that — never reaches the global scope, and the failure is silent:
    # the page loads, the script runs, and nothing is wired up. `defer` gives
    # the same after-parse ordering without the scoping surprise.
    script_tags = "\n  ".join(
        f'<script defer src="{escape(asset_url(s), quote=True)}"></script>'
        for s in scripts
    )
    sub = (
        f'<p style="--size:.8rem; --op:.65; --m:.25rem 0 0">{escape(subheading)}</p>'
        if subheading
        else ""
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(title)}</title>
  <!-- First-party framework, loaded before our own sheet so page rules win.
       Unversioned by decision (Alexander, 2026-07-28) with /v1/ + SRI coming.
       Two things this costs, recorded rather than discovered:
         * an unversioned URL is a single point of failure — when it 5xxs these
           pages render with only the local sheet, which is why layout that must
           not break lives in pages.css and not in props;
         * it is a third-party request on every admin page load, which is a real
           exception to the zero-egress line the rest of the product holds. An
           air-gapped Rootstock gets unstyled chrome. See the EGRESS note in this module's docstring. -->
  <link rel="stylesheet" href="https://startr.style/style.css" />
  <link rel="stylesheet" href="{escape(asset_url('pages.css'), quote=True)}" />
</head>
<!-- Authored mobile-first: base values are the phone case, and a suffix appears
     only where the layout actually changes going up. -->
<body style="--maxw:52rem; --m:0 auto; --p:1rem; --p-md:1.5rem; --lh:1.55">
  <main>
    <header>
      <h1 style="--size:1.15rem; --m:0">{escape(heading)}</h1>
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
