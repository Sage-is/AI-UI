"""Diagnostics as server-rendered fragments. Phase 2's first surface.

Replaces 895 lines of Svelte across four components. Second fragment call site,
which is what the template-engine decision was waiting on.

Diagnostics is the page an operator opens when something is already wrong. The
Svelte version has to download a bundle and boot a framework before it can ask
the server what broke. This one has the answer in the first response. That gap
matters most when the frontend is the broken thing.

One behaviour deliberately not changed. The plan says diagnostics' "polling
becomes a declarative refresh", which in htmx is one attribute,
`hx-trigger="every 30s"`. It is not here. Today's page does not poll: the
30-second timer only re-renders a relative-time label ("2 minutes ago"), and the
data refreshes when a human asks for it. A real 30-second re-probe would change
what the product does, on an endpoint that hits every configured service. Per
the plan, a UX change gets its own commit and its own argument instead of riding
in on a migration.

What did change: the timestamp is absolute and rendered by the server, not a
relative label kept alive by a timer.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from functools import lru_cache
from html import escape as e
from pathlib import Path

from fastapi import Request

from sage_is_ai.pages.i18n import t

__all__ = ["render_diagnostics"]

# The same fixRegistry.json the Svelte component imports, shipped into the image
# by the Dockerfile. Read rather than re-typed: 9 issue types and 40 remediation
# steps transcribed into Python would be a second copy to keep in step, which is
# the drift this migration exists to remove.
_DATA_DIR = Path(__file__).resolve().parents[2] / "data-registry"
_REGISTRY_PATH = _DATA_DIR / "fixRegistry.json"
_LIBRARY_PATH = _DATA_DIR / "commandLibrary.json"


@lru_cache(maxsize=1)
def _fix_registry() -> dict:
    try:
        return json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        # A diagnostics page that renders without remedies is degraded. One that
        # 500s because a data file moved is useless exactly when it is needed.
        return {}


@lru_cache(maxsize=1)
def _command_library() -> list:
    try:
        data = json.loads(_LIBRARY_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def _library_block() -> str:
    """Six recovery snippets, copy-only.

    The library never runs anything on the operator's behalf, by design — an
    earlier generation of this page had an arbitrary-shell surface and it was
    rejected as anti-Poka-Yoke. These get pasted into the operator's own
    terminal, under their own audit trail. Server rendering does not change
    that: there is no execution path here to add.
    """
    entries = _command_library()
    if not entries:
        return ""
    items = ""
    for entry in entries:
        warning = (
            f'<p class="fix-warning">{e(t(entry["warning_key"], {}))}</p>'
            if entry.get("warning_key")
            else ""
        )
        items += (
            f'<details class="fix" data-cy="diag-command" '
            f'data-command-id="{e(str(entry.get("id", "")), quote=True)}">'
            f'<summary>{e(t(entry.get("title_key", ""), {}))}</summary>'
            f'<p class="fix-plain">{e(t(entry.get("description_key", ""), {}))}</p>'
            f"{warning}"
            f'<pre class="fix-command">{e(str(entry.get("command", "")))}</pre>'
            f"</details>"
        )
    return (
        '<section class="diag-section" data-cy="diag-command-library">'
        "<h2>Recovery commands</h2>"
        '<p class="page-muted">Copy these into your own terminal. Nothing here runs itself.</p>'
        f"{items}</section>"
    )


def _fix_steps(issue_type: str, shape: str) -> str:
    """The remedy for one issue, for THIS deployment.

    The server knows the deployment shape, so it renders the steps that apply
    instead of offering a chooser — one of the few places where moving the
    render server-side removes an interaction rather than reproducing it.

    A <details> element, not a modal. The plan calls for native HTML over custom
    widgets, and a disclosure needs no JavaScript, no focus trap, no escape-key
    handler, and no second round-trip. It differs from the Svelte version, which
    opens a dialog; the guard-rail asserts the operator is OFFERED a fix, not
    the shape of the container it arrives in.
    """
    entry = _fix_registry().get(issue_type)
    if not entry:
        return ""

    steps = entry.get(f"{shape}_steps") or entry.get("universal_steps") or []
    if not steps:
        # Shape unknown or unlisted: show every shape's steps rather than
        # nothing, labelled, so an operator can find their own case.
        steps = [
            {**st, "_shape": key[: -len("_steps")]}
            for key, value in entry.items()
            if key.endswith("_steps") and isinstance(value, list)
            for st in value
        ]
    if not steps:
        return ""

    items = ""
    for step in steps:
        text = t(step.get("description_key", ""), {})
        prefix = f'<em>{e(step["_shape"])}</em> — ' if step.get("_shape") else ""
        extra = ""
        if step.get("ui_path"):
            extra += f'<div class="fix-path">{e(str(step["ui_path"]))}</div>'
        if step.get("command"):
            # Copy-only, never executed — same contract the Svelte modal holds.
            extra += f'<pre class="fix-command">{e(str(step["command"]))}</pre>'
        items += f"<li>{prefix}{e(text)}{extra}</li>"

    plain = t(entry.get("plain_english_key", ""), {})
    return (
        f'<details class="fix" data-cy="diag-fix" data-issue-type="{e(issue_type, quote=True)}">'
        f"<summary>Show me how to fix this</summary>"
        f'<p class="fix-plain">{e(plain)}</p>'
        f"<ol class=\"fix-steps\">{items}</ol>"
        f"</details>"
    )

# Worst first. An operator scanning this page wants to know what is broken, so
# the broken things go at the top.
_RANK = {"unreachable": 0, "degraded": 1, "unknown": 2, "ok": 3}
_STATUS_LABEL = {
    "ok": "OK",
    "degraded": "Degraded",
    "unreachable": "Unreachable",
    "unknown": "Unknown",
}
_SECTIONS = [
    ("endpoints", "Endpoints"),
    ("boot_status", "Boot status"),
    ("static_assets", "Static assets"),
    ("browser_headers", "Browser headers"),
]


def _row(label: str, record: dict, shape: str = "unknown") -> str:
    """One diagnostic row.

    `data-status` and `data-label` are the guard-rail contract. They are
    attributes rather than rendered words on purpose: the spec reads the
    attributes, so it judges this page and the Svelte one by the same rule, and
    rewording or translating a label does not break it.
    """
    status = record.get("status") or "unknown"
    summary = (
        t(record["summary_key"], record.get("summary_params") or {})
        if record.get("summary_key")
        else ""
    )
    fix = _fix_steps(str(record["issue_type"]), shape) if record.get("issue_type") else ""

    technical = ""
    if record.get("technical"):
        # <details> instead of the Svelte Collapsible: the plan's "native HTML
        # over custom widgets", and it is the whole component here.
        technical = (
            f'<details class="fix" data-cy="diag-technical">'
            f"<summary>Technical detail</summary>"
            f'<pre class="fix-command">'
            f'{e(json.dumps(record["technical"], indent=2, default=str))}</pre>'
            f"</details>"
        )

    # Re-probe only where the Svelte page offers it: an endpoints row, whose
    # label IS the URL and whose capability sits inside `technical`. Sourced the
    # same way rather than from invented fields, so the two pages cannot offer
    # the button in different places.
    capability = str((record.get("technical") or {}).get("capability") or "")
    reprobe = ""
    if capability and label.startswith(("http://", "https://")):
        reprobe = (
            f'<button type="button" class="btn" data-cy="diag-reprobe"'
            f' hx-post="/pages/admin/diagnostics/probe"'
            f' hx-vals=\'{{"url": "{e(label, quote=True)}",'
            f' "capability": "{e(capability, quote=True)}"}}\''
            f' hx-target="#diagnostics-panel" hx-swap="outerHTML">Re-probe</button>'
        )
    return f"""<div class="diag-row" data-cy="diag-row" data-label="{e(label, quote=True)}"
     data-status="{e(status, quote=True)}">
  <span class="badge badge-{e(status, quote=True)}">{e(_STATUS_LABEL.get(status, "Unknown"))}</span>
  <div class="diag-main">
    <div class="diag-label">{e(label)}</div>
    <div class="diag-summary">{e(summary)}</div>
  </div>
  <div class="diag-actions">{reprobe}</div>
</div>
{fix}{technical}"""


def _rows_of(health: dict, section: str) -> list[tuple[str, dict]]:
    """Normalise a section into (label, record) pairs.

    browser_headers nests its record under `configured`; the others do not. The
    Svelte page writes that special case out again at each use site. Collapsing
    it into one function is most of why this file is shorter.
    """
    out = []
    for label, entry in (health.get(section) or {}).items():
        record = entry.get("configured") if isinstance(entry, dict) and "configured" in entry else entry
        if isinstance(record, dict):
            out.append((label, record))
    return out


def _ghost_block(health: dict, shape: str) -> str:
    """Endpoints the config no longer names, kept because they still have state.

    A <details>, closed by default, matching the Svelte page's collapsible —
    these are history, and history should not push the live rows down the page.
    """
    ghosts = [
        (label, rec)
        for label, rec in _rows_of(health, "endpoints")
        if rec.get("in_config") is False
    ]
    if not ghosts:
        return ""
    rows = "".join(_row(label, rec, shape) for label, rec in ghosts)
    return (
        '<details class="fix" data-cy="diag-ghost-endpoints">'
        f"<summary>Previously configured ({len(ghosts)})</summary>{rows}</details>"
    )


def _issues(health: dict) -> list[tuple[str, dict]]:
    found = [
        (label, rec)
        for section, _ in _SECTIONS
        for label, rec in _rows_of(health, section)
        if (rec.get("status") or "ok") != "ok"
    ]
    found.sort(key=lambda pair: _RANK.get(pair[1].get("status"), 99))
    return found


async def render_diagnostics(request: Request, user) -> str:
    """Render the whole panel, which is also the htmx swap target."""
    from sage_is_ai.routers.diagnostics import get_diagnostics_health

    health = await get_diagnostics_health(request, user)
    if not isinstance(health, dict):
        health = dict(health)

    boot = health.get("boot_probes") or {}
    banner = ""
    if (boot.get("in_flight") or 0) > 0:
        banner = (
            f'<p class="toast" data-cy="diag-boot-probes">Boot probes still running — '
            f'{boot.get("completed", 0)} of {boot.get("total", 0)} complete.</p>'
        )

    shape = str((health.get("deployment_shape") or {}).get("shape") or "unknown")
    issues = _issues(health)
    issues_block = (
        '<section class="diag-section" data-cy="diag-issues"><h2>Issues</h2>'
        + "".join(_row(label, rec, shape) for label, rec in issues)
        + "</section>"
        if issues and not banner
        else ""
    )

    sections = "".join(
        f'<section class="diag-section" data-cy="diag-section" data-section="{key}">'
        f"<h2>{e(title)}</h2>"
        + ("".join(
               _row(label, rec, shape)
               for label, rec in rows
               if not (key == "endpoints" and rec.get("in_config") is False)
           ) or '<p class="page-muted">Nothing reported.</p>')
        + (_ghost_block(health, shape) if key == "endpoints" else "")
        + "</section>"
        for key, title in _SECTIONS
        for rows in [_rows_of(health, key)]
    )

    # Absolute and server-rendered, so nothing has to keep it accurate. The
    # Svelte page holds a relative label open with a 30-second timer.
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return f"""<div id="diagnostics-panel">
  <div class="panel-bar">
    <span class="page-count">Last refreshed {e(stamp)}</span>
    <button type="button" class="btn" data-cy="diagnostics-refresh"
            hx-get="/pages/admin/diagnostics/panel" hx-target="#diagnostics-panel"
            hx-swap="outerHTML">Re-probe all</button>
  </div>{banner}{issues_block}{sections}{_library_block()}
</div>"""
