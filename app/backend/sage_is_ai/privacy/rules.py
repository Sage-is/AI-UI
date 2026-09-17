"""What to look for. Built-in detectors, admin regexes, and literal words.

A rule names a category (what the value is) and a strategy (what to do with
it): a shape-preserving pseudonym that reverses, a fixed literal that
reverses when unique, or a one-way redaction.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# name -> (category, pattern). Categories drive the fake's shape.
DETECTORS: dict[str, tuple[str, str]] = {
    "email": ("email", r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"),
    # NANP: optional +1, area code, exchange, line; spaces, dots, dashes, parens.
    "phone": ("phone", r"(?<![\d\w])(?:\+?1[ .\-]?)?\(?[2-9]\d{2}\)?[ .\-]?\d{3}[ .\-]?\d{4}(?![\d\w])"),
    # International with a leading +, not +1.
    "phone_intl": ("phone", r"(?<![\d\w])\+(?!1(?:\D|$))\d{1,3}[ .\-]?(?:\d[ .\-]?){6,12}\d(?![\d\w])"),
    "postal_ca": ("postal", r"\b[ABCEGHJ-NPRSTVXY]\d[ABCEGHJ-NPRSTV-Z][ \-]?\d[ABCEGHJ-NPRSTV-Z]\d\b"),
    "postal_us": ("postal", r"\b\d{5}(?:-\d{4})?\b"),
    "card": ("card", r"\b(?:\d[ \-]?){13,18}\d\b"),
    "ip": ("ip", r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
}

DEFAULT_DETECTORS = {"email": True, "phone": True, "phone_intl": True, "postal_ca": True, "card": True, "postal_us": False, "ip": False}
DETECTOR_STRATEGY = {"card": "redact"}
STRATEGIES = ("pseudonym", "literal", "redact")
KINDS = ("detector", "regex", "literal")


@dataclass(frozen=True)
class Rule:
    name: str
    kind: str  # detector | regex | literal
    pattern: str
    category: str = "value"
    strategy: str = "pseudonym"
    replacement: str = ""
    enabled: bool = True
    order: int = 0

    def compiled(self) -> re.Pattern:
        if self.kind == "literal":
            return re.compile(r"(?<!\w)" + re.escape(self.pattern) + r"(?!\w)", re.IGNORECASE)
        if self.kind == "detector":
            return re.compile(DETECTORS[self.pattern][1])
        return re.compile(self.pattern, re.IGNORECASE)


@dataclass
class Hit:
    rule: str
    category: str
    count: int = 0


def rules_from_config(config: dict) -> list[Rule]:
    """Detectors the admin left on, then the admin's own rules, in their order."""
    rules: list[Rule] = []
    detectors = {**DEFAULT_DETECTORS, **(config.get("detectors") or {})}
    for name, (category, _) in DETECTORS.items():
        if detectors.get(name):
            rules.append(Rule(name=name, kind="detector", pattern=name, category=category,
                              strategy=DETECTOR_STRATEGY.get(name, "pseudonym"), order=100))
    for index, raw in enumerate(config.get("rules") or []):
        if not raw.get("enabled", True) or not raw.get("pattern"):
            continue
        kind = raw.get("kind") if raw.get("kind") in KINDS else "literal"
        strategy = raw.get("strategy") if raw.get("strategy") in STRATEGIES else "pseudonym"
        rules.append(Rule(
            name=raw.get("name") or f"rule {index + 1}", kind=kind, pattern=raw["pattern"],
            category=raw.get("category") or ("name" if kind == "literal" else "value"),
            strategy=strategy, replacement=raw.get("replacement") or "", order=int(raw.get("order") or index),
        ))
    return rules


def hint_rules(hints) -> list[Rule]:
    """Known values a caller names per request: ``[{"kind": "surname", "value": "Silva"}]``."""
    rules = []
    for index, hint in enumerate(hints or []):
        value = str((hint or {}).get("value") or "").strip()
        if len(value) < 2:
            continue
        rules.append(Rule(name=f"hint:{index}", kind="literal", pattern=value,
                          category=str(hint.get("kind") or "name"), order=-1))
    return rules
