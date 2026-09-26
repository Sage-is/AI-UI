"""Wired Sprigs™ — the settings an operator supplies after a graft.

You graft a Sprig, then you WIRE it. The settings are wires; a Sprig with an
unsupplied required wire is **unwired** and does not run; pruning discards the
wires with the thing they configured. Named for the bonsai practice of wiring a
branch into shape after the graft takes — deliberate, and it comes off again.

The vocabulary is published in `sprig-spec/v1.md` and `rootstock-spec/v1.md`.
This module is the reference implementation of it.

WHY IT LIVES HERE RATHER THAN IN THE ROUTER. Three readers need the same
answers — the router that saves a wire, the panel that renders the form, and
whatever consumes a wired capability. Three copies of "is this wire known" is
how one of them ends up permissive.

THE ONE RULE THAT MATTERS: A SECRET WIRE NEVER TRAVELS BACK. `public_values`
is what any surface may render; it reports a secret as set-or-not and never as
its value. The Telegram BotFather token is the case this was built for, and a
value that has reached a page once has reached a browser cache, a screenshot and
a bug report.

Storage is one `PersistentConfig`, `SPRIG_WIRES`, holding
``{sprig_name: {wire_name: value}}``. That matches how `SPRIG_ACTIVE_UI` and
`SPRIG_UI_SCRIPTING_GRANT` already work and adds no table.
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)

__all__ = [
    "WireError",
    "declared_wires",
    "validate",
    "read_wires",
    "write_wires",
    "clear_wires",
    "public_values",
    "missing_required",
    "is_unwired",
]

# What a wire may be. `secret` is not a fifth kind of text — it is the marker
# that decides whether a value may ever be rendered.
WIRE_TYPES = ("text", "url", "bool", "secret")

# A stored secret is reported as this. Never a partial value, never a length:
# both leak, and a masked string invites somebody to "just show the last four".
SECRET_SET = "•••"


class WireError(ValueError):
    """A wire was refused. The message names the wire, so the fix is obvious."""


def declared_wires(spec: dict) -> list[dict[str, Any]]:
    """The wires a catalog entry declares, or none.

    The CATALOG is the authority, exactly as it is for capabilities. A wire that
    is not declared cannot be set, which is what makes this fail-closed rather
    than a free-form settings bag.
    """
    return list(spec.get("wires") or [])


def validate(spec: dict, submitted: dict[str, Any]) -> dict[str, Any]:
    """Check `submitted` against the declaration and return what to store.

    Refuses unknown names rather than dropping them. Silently ignoring a wire
    somebody typed is how an operator ends up certain they configured something
    they did not.
    """
    declared = {w["name"]: w for w in declared_wires(spec)}

    unknown = sorted(set(submitted) - set(declared))
    if unknown:
        raise WireError(
            f"unknown wire(s) {unknown}; this Sprig declares {sorted(declared) or 'none'}"
        )

    out: dict[str, Any] = {}
    for name, value in submitted.items():
        wire = declared[name]
        kind = wire.get("type", "text")

        if kind == "bool":
            out[name] = (
                bool(value)
                if isinstance(value, bool)
                else str(value).lower()
                in (
                    "1",
                    "true",
                    "on",
                    "yes",
                )
            )
            continue

        text = "" if value is None else str(value).strip()

        # An empty secret means "leave what is stored alone", not "erase it".
        # A form that renders a secret as blank would otherwise wipe it on every
        # save of an unrelated field.
        if kind == "secret" and not text:
            continue

        if kind == "url" and text:
            for candidate in [
                u.strip() for u in text.replace(",", "\n").splitlines() if u.strip()
            ]:
                if not candidate.lower().startswith(("http://", "https://")):
                    raise WireError(f"wire {name!r} must be http(s); got {candidate!r}")

        out[name] = text

    return out


def read_wires(config: Any, name: str) -> dict[str, Any]:
    """Every wire stored for one Sprig. Never raises."""
    try:
        return dict((config.SPRIG_WIRES or {}).get(name) or {})
    except (AttributeError, TypeError):
        return {}


def write_wires(config: Any, name: str, values: dict[str, Any]) -> dict[str, Any]:
    """Merge `values` over what is stored, and persist.

    A MERGE rather than a replace, because a form may legitimately submit one
    field — and because an empty secret means "keep what is there", which a
    replace would defeat.
    """
    store = dict(config.SPRIG_WIRES or {})
    merged = {**(store.get(name) or {}), **values}
    store[name] = merged
    # Reassign rather than mutate: PersistentConfig persists on assignment, and
    # mutating the dict in place would keep the value in memory and lose it on
    # the next boot — the kind of bug that only shows up after a restart.
    config.SPRIG_WIRES = store
    return merged


def clear_wires(config: Any, name: str) -> bool:
    """Drop a Sprig's wires. Called on prune, so revoking is not a second step."""
    store = dict(config.SPRIG_WIRES or {})
    if name not in store:
        return False
    store.pop(name)
    config.SPRIG_WIRES = store
    return True


def public_values(spec: dict, stored: dict[str, Any]) -> dict[str, Any]:
    """What a surface may render.

    Secrets come back as `SECRET_SET` or an empty string — never the value. This
    is the function every panel must go through, and the reason it is not
    optional is that the alternative is remembering, at each of them.
    """
    out: dict[str, Any] = {}
    for wire in declared_wires(spec):
        name = wire["name"]
        value = stored.get(name, wire.get("default", ""))
        if wire.get("type") == "secret":
            out[name] = SECRET_SET if stored.get(name) else ""
        else:
            out[name] = value
    return out


def missing_required(spec: dict, stored: dict[str, Any]) -> list[str]:
    """Required wires with nothing in them."""
    return [
        wire["name"]
        for wire in declared_wires(spec)
        if wire.get("required") and not stored.get(wire["name"])
    ]


def is_unwired(spec: dict, stored: dict[str, Any]) -> bool:
    """True when a required wire is unsupplied — the Sprig must not run."""
    return bool(missing_required(spec, stored))
