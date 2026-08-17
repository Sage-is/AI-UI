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

import re
from functools import lru_cache
from hashlib import sha256
from html import escape
from typing import Iterable

from fastapi import Request

from sage_is_ai.env import PAGES_RELOAD_DIRS, VERSION

__all__ = ["render_page", "asset_url"]


def asset_url(filename: str) -> str:
    """Cache-bust by CONTENT, not by release.

    The assets are served with a week-long Cache-Control, which is only safe if
    the URL changes whenever the bytes do. The release version used to stand in
    for that, on the reasoning that it "changes exactly when the file could have
    changed". That was wrong, and it cost a debugging session: a file edited
    twice inside one release keeps one URL, so a browser that loaded the first
    version runs it for a week while the server serves the second. The operator
    ships a fix and watches the old behaviour — the failure-indistinguishable-
    from-success shape this repo keeps finding.

    Hashing needs no build step: read the file, take eight hex characters, cache
    the answer. Sixteen small files, once per process. A missing file falls back
    to the version rather than raising, because a stale URL is a nuisance and a
    500 on the diagnostics page is an outage.

    NOT cached when the dev reloader is on. There the whole point is that the
    file changes under a running process, so the cost of a stat-and-hash per
    render buys the thing you started the reloader for.
    """
    token = (
        _asset_token(filename) if PAGES_RELOAD_DIRS else _asset_token_cached(filename)
    )
    return f"/pages/_assets/{filename}?v={escape(token, quote=True)}"


def _asset_token(filename: str) -> str:
    from sage_is_ai.pages import ASSETS_DIR

    try:
        data = (ASSETS_DIR / filename).read_bytes()
    except OSError:
        return VERSION
    return sha256(data).hexdigest()[:8]


@lru_cache(maxsize=64)
def _asset_token_cached(filename: str) -> str:
    return _asset_token(filename)


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


_CSS_COLOR = re.compile(
    r"^(#[0-9a-fA-F]{3,8}|[a-zA-Z]{1,30}|(rgb|rgba|hsl|hsla)\([0-9.,%\s/deg]{1,60}\))$"
)


def _css_color(value) -> str:
    """A color literal safe to interpolate into the shell's <style> block.

    Branding is admin-set, but these bytes land inside a style element the
    whole admin surface shares — the allowlist keeps a stored value from ever
    closing the tag or smuggling a url(). Anything unrecognized renders as
    nothing, which is the framework default, not an error.
    """
    v = str(value or "").strip()
    return v if v and _CSS_COLOR.match(v) else ""


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

    # Startr Swap, on every page, appended here for the same reason as the
    # reloader below: no route opts in, so no route can forget. A page that
    # quietly stopped swapping would still work — it would just navigate — and
    # that is the failure nobody reports.
    #
    # It knows nothing about this application. The `data-swap` value on <main>
    # is what confines it to `/pages/`; everything else it needs arrives as an
    # attribute or an event. Upstream home and the publishing rules are in the
    # file's own header.
    scripts = ("startr-swap.js", *scripts)

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

    # Admin branding colors, mirrored from the SPA's $lib/utils/branding.ts —
    # same props, same rule, change one, change both. An active theme Sprig™
    # wins: while SPRIG_ACTIVE_THEME names one, branding colors step back and
    # the branding panel offers the prune. The var() re-declarations restore
    # Startr.Style's own cascade in case a sheet severed it with literals; the
    # framework's color-mix recipes re-resolve — no color math here.
    brand_style = ""
    cfg = request.app.state.config
    if not str(cfg.SPRIG_ACTIVE_THEME or "").strip():
        b = cfg.BRANDING if isinstance(cfg.BRANDING, dict) else {}
        primary = _css_color(b.get("primary_color"))
        accent = _css_color(b.get("accent_color"))
        decls = []
        if primary:
            decls += [
                f"--primary:{primary}",
                "--links:var(--primary)",
                "--button-hover:var(--primary)",
            ]
        if accent:
            decls.append(f"--secondary:{accent}")
        if decls:
            brand_style = f"\n  <style>:root{{{';'.join(decls)}}}</style>"
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
  <link rel="stylesheet" href="{escape(asset_url("pages.css"), quote=True)}" />{brand_style}
</head>
<!-- Authored mobile-first: base values are the phone case, and a suffix appears
     only where the layout actually changes going up. -->
<body style="--m:0 auto; --p:1rem">
  <!-- `data-swap` marks this the swap region AND confines Startr Swap to
       `/pages/`. Without the value it would take over every same-origin link in
       here, including the ones that deliberately leave for the SPA. -->
  <main data-swap="/pages/">
    <header>
      <!-- `page-heading` is the one marker that proves a SERVER-RENDERED page
           answered. It matters because nothing under /pages/ can 404: the SPA is
           mounted at / with html=True, so an unmatched path returns the app
           shell with a 200 and the wrong page is indistinguishable from the
           right one by status. Every gate that needs to know "did a real page
           come back?" reads this instead of the status code. -->
      <h1 data-cy="page-heading" style="--size:1.15rem; --m:0">{escape(heading)}</h1>
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
