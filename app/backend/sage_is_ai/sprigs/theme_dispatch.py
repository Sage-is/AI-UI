"""Theme Sprig™ dispatch — activate a grafted interface theme.

A theme Sprig is design tokens only: one self-contained ``theme.css``
extracted onto the DATA volume (seed=model-dir, so it survives restarts and
image upgrades like any weight cultivar). Activation is one persisted config
pointer (``SPRIG_ACTIVE_THEME``); every page loads ``/themes/active.css``,
and that route serves the active theme's file, or empty css when none.

Validation is fail-closed at graft time. CSS cannot execute script, but it
CAN beacon out through external ``url()`` references, which would break the
zero-egress story — so external references are refused, along with imports
and anything script-shaped. Comments are stripped before scanning so a
theme's documentation may name the forbidden syntax without tripping it.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from sage_is_ai.env import DATA_DIR

log = logging.getLogger("sprig.theme")

_MAX_CSS_BYTES = 512 * 1024
_COMMENT = re.compile(r"/\*.*?\*/", re.S)
# CSS escape sequences (\XX hex, \char) let `url(\68ttps://…)` or `\@import`
# smuggle a forbidden token past a naive text scan. Decode them before the
# scan so the check sees what the browser's CSS parser will see.
_CSS_HEX_ESCAPE = re.compile(r"\\([0-9a-fA-F]{1,6})\s?")
_CSS_CHAR_ESCAPE = re.compile(r"\\(.)")


def _decode_css_escapes(text: str) -> str:
    text = _CSS_HEX_ESCAPE.sub(
        lambda m: chr(int(m.group(1), 16)) if int(m.group(1), 16) <= 0x10FFFF else "",
        text,
    )
    return _CSS_CHAR_ESCAPE.sub(r"\1", text)


_FORBIDDEN = re.compile(
    # External or executable references. Inline data: URIs stay allowed per the
    # spec (they beacon nowhere); http(s)/protocol-relative url() do not. The
    # url() arm tolerates the internal whitespace CSS permits; the standalone
    # javascript:/vbscript:/<script>/expression() arms catch executable payloads
    # wherever they sit.
    r"@import"
    r"|url\(\s*[\"']?\s*(?:https?:|//)"
    r"|javascript:|vbscript:|<\s*script|expression\s*\(",
    re.I,
)


class ThemeValidationError(ValueError):
    """theme.css failed the self-containment rules. Do NOT activate."""


def theme_css_path(name: str) -> Path:
    """Volume path of a grafted theme's stylesheet (seed=model-dir layout)."""
    return DATA_DIR / "sage-is" / "sprigs" / name / "extracted" / "theme.css"


def validate_theme_css(css_path: Path) -> None:
    """Enforce the theme contract: present, size-capped, self-contained."""
    if not css_path.is_file():
        raise ThemeValidationError(f"{css_path.name} missing after delivery")
    raw = css_path.read_bytes()
    if len(raw) > _MAX_CSS_BYTES:
        raise ThemeValidationError(
            f"theme.css is {len(raw)} bytes; the contract caps themes at "
            f"{_MAX_CSS_BYTES} bytes"
        )
    # Strip comments, then decode CSS escapes, then collapse the whitespace
    # the CSS grammar allows inside tokens — all three are ways to hide a
    # forbidden reference from a plain substring scan.
    text = _COMMENT.sub("", raw.decode("utf-8", "replace"))
    text = _decode_css_escapes(text)
    hit = _FORBIDDEN.search(text)
    if hit:
        raise ThemeValidationError(
            f"theme.css is not self-contained (found {hit.group(0)!r}): themes "
            f"may not import, reference external URLs, or carry executable "
            f"content"
        )


def point_theme_at(app, handle) -> None:
    """Validate the delivered css, then flip the one persisted pointer.

    Shared shape with the other *_dispatch modules, though themes have no
    process and no loopback port — the 'dispatch' is the config pointer the
    /themes/active.css route reads.
    """
    css = theme_css_path(handle.name)
    validate_theme_css(css)
    app.state.config.SPRIG_ACTIVE_THEME = handle.name
    log.info("theme sprig '%s' active (%s)", handle.name, css)
