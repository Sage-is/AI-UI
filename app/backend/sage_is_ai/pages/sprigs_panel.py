"""The Sprigs™ panel as server-rendered fragments — the measurement.

Phase 0 built this panel as a vanilla island and it came out slightly BIGGER
than the Svelte component it replaced, against a plan predicting a ~40% cut. The
diagnosis was that the panel is fragment-shaped — a list with buttons that POST
and re-fetch — and that the fragment path was unavailable because a server
render needs the operator's identity, which lived in localStorage. The cookie
bridge removed that, so this is the third implementation.

Three things keep it small, and none of them is htmx being clever.

It does not restate the backend. `routers/sprigs.py` is called directly, so this
is a VIEW over those handlers — no second copy of the allowlist, the dispatch,
or the reset semantics. Round-tripping our own API would have meant a second
serialization, a second auth pass, and a copy of every error contract.

It does not hold state. A mutation returns the whole panel and htmx swaps it, so
there is no client-side model to keep in step with the server's, and the class
of bug where the two disagree cannot occur.

It does not tell the server what the server already knows. The client posts a
name to a path and nothing else — not the capability, not the current state. The
catalog is the authority on both, so asking the browser to carry them would be
inventing a way for them to be wrong.
"""

from __future__ import annotations


from fastapi import HTTPException, Request

from sage_is_ai.pages.templates import render

from sage_is_ai.sprigs.models import GraftRequest, PruneRequest, WireRequest

__all__ = ["render_panel", "run_action", "save_wires"]

# Supervisor lifecycle state -> operator label. The guard-rail spec reads the
# data-state attribute rather than the word, so these stay free to be reworded.
# "enabled" is a Sprig™ that runs NOTHING and pulls nothing — its code already
# ships in the image, so grafting only makes the capability available to be
# wired (calendar is the first). Distinct from "delivered", which promises an
# extracted artifact: a state whose name stops being true is worse than one
# more state.
_LABEL = {
    "rooted": "Grafted",
    "wilted": "Wilted",
    "delivered": "Delivered",
    "enabled": "Enabled",
}
_GRAFTED = {"rooted", "delivered", "enabled"}


def _card(name: str, spec: dict, g: dict | None, host_arch: str, error: dict | None = None) -> dict:
    """One catalog row as data. `templates/sprigs.html` decides how it looks."""
    state = (g or {}).get("state") or "sprouted"
    if state in _GRAFTED:
        verb, label, cls, blocked = "prune", "Prune", "btn-danger", False
    else:
        verb = "graft"
        label = "Revive" if state == "wilted" else "Graft"
        cls, blocked = "btn-primary", spec.get("compatible") is False

    base_url = (g or {}).get("base_url") or ""
    pid = f" · pid {g['pid']}" if g and g.get("pid") else ""
    return {
        "name": name,
        "state": state,
        "state_label": _LABEL.get(state, "Sprouted"),
        "meta": " · ".join(
            str(p)
            for p in (
                spec.get("capability"),
                spec.get("model"),
                spec.get("dim") and f"{spec['dim']}d",
            )
            if p
        ),
        "blocked": blocked,
        "host_arch": host_arch or "unknown",
        "where": (base_url + pid) if base_url else "",
        "error": str(error.get("message", "")) if error else "",
        "health": bool(state in _GRAFTED and base_url),
        "verb": verb,
        "button_label": label,
        "button_class": cls,
        # WIRES. Rendered only for a grafted Sprig that declares them —
        # configuring something not attached is an errand with no result.
        #
        # `wire_values` comes from the catalog endpoint, which already ran it
        # through `public_values`, so a SECRET arrives as a set-or-not marker
        # and never as its value. This panel does not re-derive that, because a
        # second implementation of "may this be rendered" is how one of them
        # ends up permissive.
        "wires": [
            {**w, "value": (spec.get("wire_values") or {}).get(w["name"], "")}
            for w in (spec.get("wires") or [])
        ] if state in _GRAFTED else [],
        "unwired": bool(spec.get("unwired")) and state in _GRAFTED,
        "missing_wires": ", ".join(spec.get("missing_wires") or []),
    }


async def render_panel(request: Request, user, *, message: str = "", kind: str = "info") -> str:
    """Build the context; `templates/sprigs.html` decides how it looks.

    The whole panel is also the whole swap target. Returning everything rather
    than patching is what removes the client-side model.
    """
    from sage_is_ai.routers.sprigs import get_sprig_catalog

    data = await get_sprig_catalog(request, user)
    catalog, grafted = data.get("catalog") or {}, data.get("grafted") or {}
    errors = data.get("errors") or {}
    count = sum(1 for g in grafted.values() if (g or {}).get("state") in _GRAFTED)
    return render(
        "sprigs.html",
        message=message,
        kind=kind,
        count_text=f"{count} of {len(catalog)} grafted" if catalog else "",
        cards=[
            _card(n, spec, grafted.get(n), data.get("host_arch") or "", errors.get(n))
            for n, spec in catalog.items()
        ],
    )

async def run_action(request: Request, user, name: str, verb: str) -> str:
    """Run a lifecycle action through the API handler, then re-render.

    Both actions have the same shape — call, catch, report, re-render — so they
    share it. The backend's `detail` is what reaches the operator on failure,
    because it names the actual fix ("cultivar needs numpy — graft vector-chroma
    first") and "Failed to graft" does not.

    The success sentence comes from the backend too. `post_graft_note` already
    worked that way; the prune resets used to be a table of hardcoded strings
    restated in every panel, which is the drift this migration exists to delete.
    """
    from sage_is_ai.routers.sprigs import graft_sprig, prune_sprig

    supervisor = request.app.state.sprig_supervisor
    try:
        if verb == "graft":
            # Capability comes from the catalog, not the browser. The client has
            # no business knowing it, and a value it cannot send is a value it
            # cannot get wrong.
            capability = (supervisor.CATALOG.get(name) or {}).get("capability", "")
            res = await graft_sprig(request, GraftRequest(name=name, capability=capability), user)
            extra = getattr(res, "warning", None) or ""
        else:
            res = await prune_sprig(request, PruneRequest(name=name), user)
            extra = " ".join(res.get("messages") or [])
    except HTTPException as exc:
        return await render_panel(
            request, user, message=f"Failed to {verb} {name}: {exc.detail}", kind="error"
        )

    done = "Grafted" if verb == "graft" else "Pruned"
    return await render_panel(
        request, user, message=f"{done} {name}." + (f" {extra}" if extra else ""), kind="success"
    )


async def save_wires(request: Request, user, name: str, form: dict) -> str:
    """Store an admin's wires for one Sprig™, then re-render the whole panel.

    A partial submission is a merge and an empty `secret` keeps what is stored —
    both decided in `sprigs/wiring`, so this only has to hand the form over.
    Re-rendering everything rather than patching one row is the same choice the
    graft and prune actions make: no client-side model, nothing to fall out of
    step.
    """
    from sage_is_ai.routers.sprigs import wire_sprig

    try:
        await wire_sprig(request, WireRequest(name=name, values=form), user)
    except HTTPException as exc:
        return await render_panel(
            request, user, message=f"Could not wire {name}: {exc.detail}", kind="error"
        )
    return await render_panel(request, user, message=f"Wired {name}.")
