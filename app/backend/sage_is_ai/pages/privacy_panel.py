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
from sage_is_ai.privacy.rules import DEFAULT_DETECTORS, DETECTORS, FORM_KINDS, STRATEGIES, rules_from_config

TRISTATE = (("default", "instance default"), ("on", "on"), ("off", "off"))


def _connections(request: Request, cfg: dict) -> list[dict]:
    urls = list(request.app.state.config.OPENAI_API_BASE_URLS or [])
    configs = request.app.state.config.OPENAI_API_CONFIGS or {}
    flags = cfg.get("connections") or {}
    rows = []
    for idx, url in enumerate(urls):
        api_config = configs.get(str(idx), {}) or {}
        flag = flags.get(str(idx))
        rows.append({
            "key": str(idx),
            "name": api_config.get("name") or url,
            "url": url,
            "enabled": api_config.get("enable", True),
            "state": "default" if flag is None else ("on" if flag else "off"),
            "effective": bool(cfg.get("default_external") if flag is None else flag),
        })
    return rows


def render_privacy(request: Request, *, message: str = "", kind: str = "info", bench: dict | None = None,
                   revealed: dict | None = None) -> str:
    cfg = hooks.config(request)
    detectors = {**DEFAULT_DETECTORS, **(cfg.get("detectors") or {})}
    return render(
        "privacy.html",
        message=message,
        kind=kind,
        enabled=bool(cfg.get("enabled", True)),
        default_external=bool(cfg.get("default_external")),
        connections=_connections(request, cfg),
        detectors=[{"name": name, "category": category, "on": bool(detectors.get(name))} for name, (category, _) in DETECTORS.items()],
        rules=list(cfg.get("rules") or []) + [{"name": "", "kind": "literal", "pattern": "", "category": "", "strategy": "pseudonym", "replacement": "", "enabled": True}],
        kinds=FORM_KINDS,
        strategies=STRATEGIES,
        tristate=TRISTATE,
        bench=bench,
        map_count=PrivacyMaps.count(),
        map_recent=PrivacyMaps.recent(20),
        revealed=revealed or {},
        audits=PrivacyAudits.recent(10),
    )


def _rules_from_form(form) -> tuple[list[dict], str]:
    names, kinds, patterns = form.getlist("rule_name"), form.getlist("rule_kind"), form.getlist("rule_pattern")
    categories, strategies = form.getlist("rule_category"), form.getlist("rule_strategy")
    replacements, enabled = form.getlist("rule_replacement"), form.getlist("rule_enabled")
    rules = []
    for i, pattern in enumerate(patterns):
        pattern = (pattern or "").strip()
        if not pattern:
            continue
        kind = kinds[i] if i < len(kinds) and kinds[i] in FORM_KINDS else "literal"
        if kind == "regex":
            try:
                re.compile(pattern)
            except re.error as error:
                return [], f"Rule {i + 1}: bad regex ({error})"
        rules.append({
            "name": (names[i] if i < len(names) else "").strip() or f"rule {len(rules) + 1}",
            "kind": kind,
            "pattern": pattern,
            "category": (categories[i] if i < len(categories) else "").strip() or ("name" if kind == "literal" else "value"),
            "strategy": strategies[i] if i < len(strategies) and strategies[i] in STRATEGIES else "pseudonym",
            "replacement": (replacements[i] if i < len(replacements) else "").strip(),
            "enabled": (enabled[i] if i < len(enabled) else "on") == "on",
        })
    return rules, ""


async def save_privacy(request: Request, user, form) -> str:
    cfg = hooks.config(request)
    rules, error = _rules_from_form(form)
    if error:
        return render_privacy(request, message=error, kind="error")
    connections = {}
    for key, value in form.multi_items():
        if key.startswith("connection_") and value in ("on", "off"):
            connections[key[len("connection_"):]] = value == "on"
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
        "hits": [{"rule": h.rule, "category": h.category, "count": h.count} for h in hits],
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
    return render_privacy(request, message="Forgotten. Old replies holding that pseudonym stay as they are.", kind="success")


async def purge_privacy(request: Request, user, form) -> str:
    if form.get("confirm") != "yes":
        return render_privacy(request, message="Tick the confirmation to purge.", kind="error")
    count = PrivacyMaps.purge()
    invalidate()
    PrivacyAudits.write(user.id, "purge", f"{count} pairs")
    return render_privacy(request, message=f"Purged {count} pairs.", kind="success")
