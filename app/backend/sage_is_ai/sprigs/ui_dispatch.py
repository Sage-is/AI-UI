"""ui-Sprig™ dispatch — activate a grafted interface fragment.

A ui-Sprig is hypermedia: one self-contained ``fragment.html`` and an optional
``fragment.css``, extracted onto the DATA volume like a theme's stylesheet.
Activation is one persisted pointer (``SPRIG_ACTIVE_UI``); ``/ui/active.html``
serves the active fragment, or nothing when none is grafted.

It exists because the marketplace cannot launch without it. A teacher theming
their instance should not need a JavaScript toolchain, and the ``ui-``
capability is how a fragment of interface ships the way ``theme.css`` already
does.

Validation is fail-closed at graft, and this module is deliberate about what it
can and cannot promise.

WHAT IT ENFORCES

* Zero egress. External references are refused, the same rule themes follow,
  using the same validator — one implementation, so the two cannot drift.
* No scripting by default. A fragment carries markup. Script arrives only when
  an admin grants it, per Sprig, off by default, revoked at prune.
* Nothing that executes without looking like script: inline ``on*`` handlers,
  ``javascript:`` URLs, and hyperscript's three attribute forms (``_``,
  ``script``, ``data-script``), which are interpreted and therefore invisible to
  a Content-Security-Policy.
* No framing. ``<iframe>``, ``<object>`` and ``<embed>`` pull in a document we
  did not validate.

WHAT IT CANNOT ENFORCE, AND WHAT WE DO INSTEAD

The plan's rule is "no framework sprigs": a fragment may use the host's runtime
and may not bring its own. No static check decides in general whether a blob of
JavaScript is a framework. So the rule is carried three ways rather than
pretended into one regex — scripting is off unless an admin turns it on; when
on, script must be same-origin, so a CDN cannot supply one; and the total
script a fragment may carry is capped well below what any framework weighs.
That last one is the load-bearing part, and the runtime probe in
``tools/spikes/biomes`` is why: an independently-built Svelte biome inlines
~18 kB of runtime minimum, so a 16 kB ceiling makes bundling one structurally
impossible while leaving an island room to work.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from sage_is_ai.env import DATA_DIR
from sage_is_ai.sprigs.theme_dispatch import (
    ThemeValidationError,
    validate_theme_css,
)

log = logging.getLogger("sprig.ui")

_MAX_HTML_BYTES = 256 * 1024
# Sized from measurement, not taste: a Svelte runtime is ~18 kB even after
# tree-shaking (tools/spikes/biomes). Anything under that cannot be a framework.
_MAX_SCRIPT_BYTES = 16 * 1024

_HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)
_SCRIPT_BLOCK = re.compile(r"<script\b[^>]*>(.*?)</\s*script\s*>", re.I | re.S)
_SCRIPT_OPEN = re.compile(r"<\s*script\b", re.I)
_SCRIPT_SRC = re.compile(r"<\s*script\b[^>]*\bsrc\s*=\s*[\"']?([^\"'\s>]+)", re.I)

# Executable or framing content that is refused whatever the grant says.
_ALWAYS_FORBIDDEN = re.compile(
    r"<\s*(?:iframe|object|embed|base)\b"
    r"|javascript:|vbscript:"
    r"|\bsrcdoc\s*=",
    re.I,
)

# Anything reaching off this origin. Matches the theme rule so a fragment
# cannot beacon out where a stylesheet may not.
_EXTERNAL_REF = re.compile(
    r"(?:src|href|action|data|poster|formaction)\s*=\s*[\"']?\s*(?:https?:|//)",
    re.I,
)

# Inline event handlers: script that never appears inside a <script> tag.
_INLINE_HANDLER = re.compile(r"\son[a-z]+\s*=", re.I)

# hyperscript's three attribute forms. Interpreted, so a CSP cannot see them —
# the same three the user-content sanitizer strips in utils/sanitize.ts. Kept
# in step with that list on purpose: one rule, enforced on both sides.
_HYPERSCRIPT_ATTR = re.compile(r"(?:^|\s)(?:_|script|data-script)\s*=", re.I)


class UiValidationError(ValueError):
    """The ui bundle failed the fragment contract. Do NOT activate."""


def ui_bundle_dir(name: str) -> Path:
    """Volume path of a grafted ui-Sprig's bundle (seed=model-dir layout)."""
    return DATA_DIR / "sage-is" / "sprigs" / name / "extracted"


def ui_fragment_path(name: str) -> Path:
    return ui_bundle_dir(name) / "fragment.html"


def ui_css_path(name: str) -> Path:
    return ui_bundle_dir(name) / "fragment.css"


def validate_ui_bundle(name: str, *, scripting_granted: bool = False) -> None:
    """Enforce the ui-Sprig contract. Raises UiValidationError, or returns.

    `scripting_granted` is the admin's per-Sprig decision, and it widens exactly
    one rule: whether script may be present at all. It never permits an external
    reference, never lifts the size cap, and never allows the interpreted
    attribute forms, because those are the parts an admin cannot meaningfully
    consent to — they are invisible in the bundle they were shown.
    """
    fragment = ui_fragment_path(name)
    if not fragment.is_file():
        raise UiValidationError("fragment.html missing after delivery")

    raw = fragment.read_bytes()
    if len(raw) > _MAX_HTML_BYTES:
        raise UiValidationError(
            f"fragment.html is {len(raw)} bytes; the contract caps fragments at "
            f"{_MAX_HTML_BYTES} bytes"
        )

    # Comments come out first so a fragment may document the forbidden syntax
    # without tripping on its own documentation — the same courtesy themes get.
    text = _HTML_COMMENT.sub("", raw.decode("utf-8", "replace"))

    hit = _ALWAYS_FORBIDDEN.search(text)
    if hit:
        raise UiValidationError(
            f"fragment.html carries {hit.group(0)!r}: a ui-Sprig may not frame "
            f"or execute content the Rootstock has not validated"
        )

    hit = _EXTERNAL_REF.search(text)
    if hit:
        raise UiValidationError(
            f"fragment.html is not self-contained (found {hit.group(0)!r}): a "
            f"ui-Sprig may not reference anything off this origin"
        )

    hit = _HYPERSCRIPT_ATTR.search(text)
    if hit:
        raise UiValidationError(
            f"fragment.html carries an interpreted script attribute "
            f"({hit.group(0).strip()!r}): these run without a <script> tag and "
            f"a Content-Security-Policy cannot see them"
        )

    if _INLINE_HANDLER.search(text) and not scripting_granted:
        raise UiValidationError(
            "fragment.html carries an inline event handler; grant this Sprig™ "
            "scripting permission first, or ship markup only"
        )

    if _SCRIPT_OPEN.search(text):
        if not scripting_granted:
            raise UiValidationError(
                "fragment.html carries <script>; a ui-Sprig ships hypermedia by "
                "default. Grant this Sprig™ scripting permission if you trust it."
            )
        if _SCRIPT_SRC.search(text):
            # Same-origin is already guaranteed by the external-reference check
            # above; this refuses script sourced from a FILE as well, so the
            # only script an admin can grant is the script they can read in the
            # bundle they approved.
            raise UiValidationError(
                "fragment.html sources script from a file; a granted ui-Sprig "
                "may only carry inline script, so what runs is what was reviewed"
            )
        script_bytes = sum(len(m.encode("utf-8")) for m in _SCRIPT_BLOCK.findall(text))
        if script_bytes > _MAX_SCRIPT_BYTES:
            raise UiValidationError(
                f"fragment.html carries {script_bytes} bytes of script; the "
                f"contract caps a ui-Sprig at {_MAX_SCRIPT_BYTES} bytes so that "
                f"no fragment can bring its own framework"
            )

    css = ui_css_path(name)
    if css.is_file():
        # Reuse the theme validator rather than restating its rules. Self-
        # containment is one policy; two implementations of it would be one
        # policy and one bug waiting.
        try:
            validate_theme_css(css)
        except ThemeValidationError as e:
            raise UiValidationError(f"fragment.css rejected: {e}") from e


def point_ui_at(app, handle) -> None:
    """Validate the delivered bundle, then flip the one persisted pointer.

    The grant is read by NAME. A grant made for one ui-Sprig must not transfer
    to whatever is grafted next, or an admin's decision about a fragment they
    read becomes a standing permission for one they never saw.
    """
    granted = str(getattr(app.state.config, "SPRIG_UI_SCRIPTING_GRANT", "") or "")
    validate_ui_bundle(handle.name, scripting_granted=granted == handle.name)
    app.state.config.SPRIG_ACTIVE_UI = handle.name
    log.info("ui sprig '%s' active (%s)", handle.name, ui_fragment_path(handle.name))
