"""Jinja2 for the no-build pages. SPIKE — one panel, measured before twelve.

Templating was rejected once on line count and is being retried on two arguments
that line count does not measure.

THE DEV LOOP. A template is data read from disk, not code imported at boot. With
`auto_reload` a changed template is re-read on the next request, so a markup edit
costs a REFRESH rather than the ~2.8 s app restart an f-string edit costs.
Uvicorn's reloader watches `*.py` only, so a `.html` save does not restart
anything — the two mechanisms compose rather than fight.

ESCAPING BECOMES STRUCTURAL. `shell.py` says it in its own docstring: "A shell
that concatenates strings is a cross-site-scripting engine unless escaping is the
default path rather than the remembered one." Today it is remembered — `e(...)`
at every interpolation across twelve panels, and the one somebody forgets is the
hole. `select_autoescape` makes forgetting impossible in a `.html` template.

`auto_reload` is GATED on the same flag as everything else in the dev loop. It
costs a stat per template per render, which is nothing next to a request but is
also nothing to pay for on an instance where the files cannot change.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from sage_is_ai.env import PAGES_RELOAD_DIRS

__all__ = ["render", "TEMPLATES_DIR"]

TEMPLATES_DIR = Path(__file__).parent / "templates"

_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html"]),
    auto_reload=bool(PAGES_RELOAD_DIRS),
    # Generated markup should not carry the template's own indentation into the
    # response. Both are about whitespace around block tags, not inside text.
    trim_blocks=True,
    lstrip_blocks=True,
)


def render(name: str, /, **context: Any) -> str:
    """Render a template to a string.

    A plain function rather than passing the environment around: the panels do
    not need to know Jinja exists beyond the template name, which is what keeps
    this reversible if the spike does not pay.
    """
    return _env.get_template(name).render(**context)
