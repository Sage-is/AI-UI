"""The privacy panel: switches, detectors, rules, a test bench, and the map.

Every form answers with the whole panel, so a save, a bench run, a reveal and
a purge all come back the same shape. The bench runs the real engine against
an in-memory mapper, so trying a rule never writes to the map.
"""

from __future__ import annotations

import re

from fastapi import Request

from sage_is_ai.models.privacy import PrivacyAudits, PrivacyMaps
from sage_is_ai.pages.templates import render
from sage_is_ai.privacy import hooks
from sage_is_ai.privacy.engine import MemoryMapper, pseudonymize, reverse
from sage_is_ai.privacy.mapper import invalidate
from sage_is_ai.privacy.rules import (
    DEFAULT_DETECTORS,
    DETECTORS,
    FORM_KINDS,
    STRATEGIES,
    rules_from_config,
)

TRISTATE = (("default", "instance default"), ("on", "on"), ("off", "off"))


def _connections(request: Request, cfg: dict) -> list[dict]:
    """Every connection the filter can cover, keyed as hooks.connection_key keys
    a model: OpenAI-style by index, Ollama as `ollama:<index>`, and one row for
    people's own direct connections (2026-11-03)."""
    state = request.app.state.config
    flags = cfg.get("connections") or {}

    def row(key, name, url, enabled, external):
        flag = flags.get(key)
        return {
            "key": key,
            "name": name,
            "url": url,
            "enabled": enabled,
            "state": "default" if flag is None else ("on" if flag else "off"),
            "effective": hooks.connection_filtered(cfg, flag, external),
        }

    rows = []
    openai_configs = state.OPENAI_API_CONFIGS or {}
    for idx, url in enumerate(state.OPENAI_API_BASE_URLS or []):
        c = openai_configs.get(str(idx), {}) or {}
        external = c.get("connection_type", "external") != "local"
        rows.append(row(str(idx), c.get("name") or url, url, c.get("enable", True), external))
    ollama_configs = getattr(state, "OLLAMA_API_CONFIGS", None) or {}
    for idx, url in enumerate(getattr(state, "OLLAMA_BASE_URLS", None) or []):
        c = ollama_configs.get(str(idx), ollama_configs.get(url, {})) or {}  # url: legacy key
        external = c.get("connection_type", "local") != "local"
        name = f"Ollama: {c.get('name') or url}"
        rows.append(row(f"ollama:{idx}", name, url, c.get("enable", True), external))
    if getattr(state, "ENABLE_DIRECT_CONNECTIONS", False):
        rows.append(row("direct", "People's own direct connections", "", True, True))
    return rows


def render_privacy(
    request: Request,
    *,
    message: str = "",
    kind: str = "info",
    bench: dict | None = None,
    revealed: dict | None = None,
) -> str:
    cfg = hooks.config(request)
    detectors = {**DEFAULT_DETECTORS, **(cfg.get("detectors") or {})}
    return render(
        "privacy.html",
        message=message,
        kind=kind,
        enabled=bool(cfg.get("enabled", True)),
        default_external=bool(cfg.get("default_external")),
        connections=_connections(request, cfg),
        detectors=[
            {"name": name, "category": category, "on": bool(detectors.get(name))}
            for name, (category, _) in DETECTORS.items()
        ],
        rules=list(cfg.get("rules") or [])
        + [
            {
                "name": "",
                "kind": "literal",
                "pattern": "",
                "category": "",
                "strategy": "pseudonym",
                "replacement": "",
                "enabled": True,
            }
        ],
        kinds=FORM_KINDS,
        strategies=STRATEGIES,
        tristate=TRISTATE,
        bench=bench,
        map_count=PrivacyMaps.count(),
        map_recent=PrivacyMaps.recent(20),
        revealed=revealed or {},
        audits=PrivacyAudits.recent(10),
    )


_RULE_FIELDS = (
    "name",
    "kind",
    "pattern",
    "category",
    "strategy",
    "replacement",
    "enabled",
)


def _at(values: list, i: int, default: str = "") -> str:
    """The i-th posted value of a repeated field, or the default when absent."""
    return values[i] if i < len(values) else default


def _rules_from_form(form) -> tuple[list[dict], str]:
    columns = {field: form.getlist(f"rule_{field}") for field in _RULE_FIELDS}
    rules = []
    for i, pattern in enumerate(columns["pattern"]):
        pattern = (pattern or "").strip()
        if not pattern:
            continue
        rule = _rule_from_row(columns, i, pattern, len(rules))
        error = _regex_error(pattern) if rule["kind"] == "regex" else ""
        if error:
            return [], f"Rule {i + 1}: bad regex ({error})"
        rules.append(rule)
    return rules, ""


def _rule_from_row(columns: dict, i: int, pattern: str, count: int) -> dict:
    kind = _at(columns["kind"], i)
    kind = kind if kind in FORM_KINDS else "literal"
    strategy = _at(columns["strategy"], i)
    return {
        "name": _at(columns["name"], i).strip() or f"rule {count + 1}",
        "kind": kind,
        "pattern": pattern,
        "category": _at(columns["category"], i).strip()
        or ("name" if kind == "literal" else "value"),
        "strategy": strategy if strategy in STRATEGIES else "pseudonym",
        "replacement": _at(columns["replacement"], i).strip(),
        "enabled": _at(columns["enabled"], i, "on") == "on",
    }


def _regex_error(pattern: str) -> str:
    try:
        re.compile(pattern)
    except re.error as error:
        return str(error)
    return ""


async def save_privacy(request: Request, user, form) -> str:
    cfg = hooks.config(request)
    rules, error = _rules_from_form(form)
    if error:
        return render_privacy(request, message=error, kind="error")
    connections = {}
    for key, value in form.multi_items():
        if key.startswith("connection_") and value in ("on", "off"):
            connections[key[len("connection_") :]] = value == "on"
    chosen = set(form.getlist("detector"))
    new_cfg = {
        **cfg,
        "enabled": form.get("enabled") == "on",
        "default_external": form.get("default_external") == "on",
        "connections": connections,
        "detectors": {name: (name in chosen) for name in DETECTORS},
        "rules": rules,
    }
    request.app.state.config.PRIVACY_CONFIG = new_cfg
    return render_privacy(request, message="Saved.", kind="success")


async def bench_privacy(request: Request, form) -> str:
    text = str(form.get("text") or "")
    cfg = hooks.config(request)
    mapper = MemoryMapper(hooks.key())
    out, hits = pseudonymize(text, rules_from_config(cfg), mapper)
    back = reverse(out, mapper.reverse_table())
    bench = {
        "text": text,
        "out": out,
        "back": back,
        "round_trip": back == text,
        "hits": [
            {"rule": h.rule, "category": h.category, "count": h.count} for h in hits
        ],
    }
    return render_privacy(request, bench=bench)


async def reveal_privacy(request: Request, user, form) -> str:
    row = PrivacyMaps.reveal(str(form.get("id") or ""))
    if row is None:
        return render_privacy(request, message="No such pair.", kind="error")
    PrivacyAudits.write(user.id, "reveal", f"{row['category']} {row['fake']}")
    return render_privacy(request, revealed={row["id"]: row["real"]})


async def forget_privacy(request: Request, user, form) -> str:
    row = PrivacyMaps.reveal(str(form.get("id") or ""))
    if row is None:
        return render_privacy(request, message="No such pair.", kind="error")
    PrivacyMaps.forget(row["id"])
    invalidate()
    PrivacyAudits.write(user.id, "forget", f"{row['category']} {row['fake']}")
    return render_privacy(
        request,
        message="Forgotten. Old replies holding that pseudonym stay as they are.",
        kind="success",
    )


async def purge_privacy(request: Request, user, form) -> str:
    if form.get("confirm") != "yes":
        return render_privacy(
            request, message="Tick the confirmation to purge.", kind="error"
        )
    count = PrivacyMaps.purge()
    invalidate()
    PrivacyAudits.write(user.id, "purge", f"{count} pairs")
    return render_privacy(request, message=f"Purged {count} pairs.", kind="success")
