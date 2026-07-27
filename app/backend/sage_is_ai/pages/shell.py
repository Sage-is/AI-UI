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


def render_page(
    *,
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
  </main>
  <!-- Islands report failures here rather than into the console, so an
       operator sees what went wrong without opening devtools. -->
  <div id="toasts" role="status" aria-live="polite"></div>
  {script_tags}
</body>
</html>
"""
