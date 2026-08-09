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
from pathlib import Path

from fastapi import Request

from sage_is_ai.pages.i18n import t
from sage_is_ai.pages.templates import render

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


def _library_entries() -> list[dict]:
    """The recovery snippets as data. Copy-only, and there is no execution path
    here to add — an earlier generation of this page had an arbitrary-shell
    surface and it was rejected as anti-Poka-Yoke."""
    return [
        {
            "id": str(entry.get("id", "")),
            "title": t(entry.get("title_key", ""), {}),
            "description": t(entry.get("description_key", ""), {}),
            "warning": t(entry["warning_key"], {}) if entry.get("warning_key") else "",
            "command": str(entry.get("command", "")),
        }
        for entry in _command_library()
    ]


def _fix_steps(issue_type: str, shape: str) -> dict | None:
    """The remedy for one issue, for THIS deployment, as data.

    The server knows the deployment shape, so it renders the steps that apply
    instead of offering a chooser — one of the few places where moving the
    render server-side removes an interaction rather than reproducing it.

    A `<details>` in the template, not a modal: the plan calls for native HTML
    over custom widgets, and a disclosure needs no JavaScript, no focus trap, no
    escape-key handler and no second round-trip. The guard-rail asserts the
    operator is OFFERED a fix, not the shape of the container it arrives in.
    """
    entry = _fix_registry().get(issue_type)
    if not entry:
        return None

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
        return None

    return {
        "issue_type": issue_type,
        "plain": t(entry.get("plain_english_key", ""), {}),
        "steps": [
            {
                "shape": step.get("_shape", ""),
                "text": t(step.get("description_key", ""), {}),
                "ui_path": str(step["ui_path"]) if step.get("ui_path") else "",
                "command": str(step["command"]) if step.get("command") else "",
            }
            for step in steps
        ],
    }


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


def _row(label: str, record: dict, shape: str = "unknown") -> dict:
    """One diagnostic row as data. `templates/diagnostics.html` renders it.

    `data-status` and `data-label` are the guard-rail contract — attributes
    rather than rendered words, so the spec judges this page and the Svelte one
    by the same rule and a reworded label cannot break it.
    """
    status = record.get("status") or "unknown"
    capability = str((record.get("technical") or {}).get("capability") or "")
    return {
        "label": label,
        "status": status,
        "status_label": _STATUS_LABEL.get(status, "Unknown"),
        "summary": (
            t(record["summary_key"], record.get("summary_params") or {})
            if record.get("summary_key")
            else ""
        ),
        "fix": _fix_steps(str(record["issue_type"]), shape) if record.get("issue_type") else None,
        "technical": (
            json.dumps(record["technical"], indent=2, default=str)
            if record.get("technical")
            else ""
        ),
        # Re-probe only where the Svelte page offers it: an endpoints row, whose
        # label IS the URL and whose capability sits inside `technical`.
        "capability": capability,
        "reprobe": bool(capability and label.startswith(("http://", "https://"))),
    }

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
    """Build the context; `templates/diagnostics.html` decides how it looks.

    No try/except wrapper, deliberately. Rule R8 says this page must never 500,
    and every helper it calls already fails soft on its own — a blanket catch
    here would hide a real fault behind an empty page, which is worse than the
    error for the one person who opens this page when things are broken.
    """
    from sage_is_ai.routers.diagnostics import get_diagnostics_health

    health = await get_diagnostics_health(request, user)
    if not isinstance(health, dict):
        health = dict(health)

    boot = health.get("boot_probes") or {}
    banner = (
        {"completed": boot.get("completed", 0), "total": boot.get("total", 0)}
        if (boot.get("in_flight") or 0) > 0
        else None
    )
    shape = str((health.get("deployment_shape") or {}).get("shape") or "unknown")

    sections = []
    for key, title in _SECTIONS:
        rows = _rows_of(health, key)
        live = [
            _row(label, rec, shape)
            for label, rec in rows
            if not (key == "endpoints" and rec.get("in_config") is False)
        ]
        # History, and history should not push the live rows down the page.
        ghosts = (
            [_row(label, rec, shape) for label, rec in rows if rec.get("in_config") is False]
            if key == "endpoints"
            else []
        )
        sections.append({"key": key, "title": title, "rows": live, "ghosts": ghosts})

    return render(
        "diagnostics.html",
        # Absolute and server-rendered, so nothing has to keep it accurate. The
        # Svelte page holds a relative label open with a 30-second timer.
        stamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        banner=banner,
        issues=[_row(label, rec, shape) for label, rec in _issues(health)],
        sections=sections,
        library=_library_entries(),
    )
