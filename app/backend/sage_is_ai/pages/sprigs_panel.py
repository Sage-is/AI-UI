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

from html import escape as e

from fastapi import HTTPException, Request

from sage_is_ai.sprigs.models import GraftRequest, PruneRequest

__all__ = ["render_panel", "run_action"]

# Supervisor lifecycle state -> operator label. The guard-rail spec reads the
# data-state attribute rather than the word, so these stay free to be reworded.
_LABEL = {"rooted": "Grafted", "wilted": "Wilted", "delivered": "Delivered"}
_GRAFTED = {"rooted", "delivered"}


def _card(name: str, spec: dict, g: dict | None, host_arch: str, error: dict | None = None) -> str:
    state = (g or {}).get("state") or "sprouted"
    # One button, described rather than branched into. The two-branch version of
    # this was two near-identical blocks of markup that had to be kept in step.
    if state in _GRAFTED:
        verb, label, cls, blocked = "prune", "Prune", "btn-danger", False
    else:
        verb = "graft"
        label = "Revive" if state == "wilted" else "Graft"
        cls, blocked = "btn-primary", spec.get("compatible") is False

    n = e(name, quote=True)
    meta = " · ".join(
        str(p) for p in (spec.get("capability"), spec.get("model"),
                         spec.get("dim") and f"{spec['dim']}d") if p
    )
    notes = ""
    if blocked:
        notes += (f'<div class="sprig-warn" data-cy="sprig-incompatible">Not available on '
                  f"this server ({e(host_arch or 'unknown')})</div>")
    if g and g.get("base_url"):
        pid = f" · pid {g['pid']}" if g.get("pid") else ""
        notes += f'<div class="sprig-where">{e(g["base_url"] + pid)}</div>'
    if error:
        # Stays on the card until a graft or a prune resolves it. The toast is
        # the notification; this is the record, and it survives the reload that
        # loses the toast — along with the restart, since it lives on the volume.
        notes += (
            f'<div class="sprig-error" data-cy="sprig-error" role="status">'
            f'{e(str(error.get("message", "")))}</div>'
        )
    health = ('<a class="btn" href="/admin/diagnostics">Health</a>'
              if state in _GRAFTED and (g or {}).get("base_url") else "")

    return f"""<div class="sprig-card" data-cy="sprig-card" data-sprig="{n}">
  <span class="badge badge-{e(state, quote=True)}" data-cy="sprig-state"
        data-state="{e(state, quote=True)}">{e(_LABEL.get(state, "Sprouted"))}</span>
  <div class="sprig-main">
    <div class="sprig-name">{e(name)}</div>
    <div class="sprig-meta">{e(meta)}</div>{notes}
  </div>
  <div class="sprig-actions">{health}
    <button type="button" class="btn {cls}" data-cy="sprig-{verb}"{" disabled" if blocked else ""}
            hx-post="/pages/admin/sprigs/{verb}/{n}"
            hx-target="#sprigs-panel" hx-swap="outerHTML">{label}</button>
  </div>
</div>"""


async def render_panel(request: Request, user, *, message: str = "", kind: str = "info") -> str:
    """The whole panel, which is also the whole swap target.

    Returning everything rather than patching is what removes the client-side
    model. It costs a few hundred bytes on a mutation and buys the absence of an
    entire bug class.
    """
    from sage_is_ai.routers.sprigs import get_sprig_catalog

    data = await get_sprig_catalog(request, user)
    catalog, grafted = data.get("catalog") or {}, data.get("grafted") or {}
    errors = data.get("errors") or {}
    count = sum(1 for g in grafted.values() if (g or {}).get("state") in _GRAFTED)
    cards = "".join(
        _card(n, s, grafted.get(n), data.get("host_arch") or "", errors.get(n)) for n, s in catalog.items()
    )
    # role=status so a screen reader announces it: the message is the only
    # feedback a mutation gives, and it fades.
    note = (f'<p class="toast toast-float toast-{e(kind, quote=True)}" role="status" '
            f'data-cy="panel-message">{e(message)}</p>'
            if message else "")

    return f"""<div id="sprigs-panel">
  <div class="panel-bar">
    <span class="page-count" data-cy="sprigs-grafted-count">{
        f"{count} of {len(catalog)} grafted" if catalog else ""}</span>
    <button type="button" class="btn" data-cy="sprigs-refresh"
            hx-get="/pages/admin/sprigs/panel" hx-target="#sprigs-panel"
            hx-swap="outerHTML">Refresh</button>
  </div>{note}
  <div class="sprig-list">{cards or '<p class="page-muted">No Sprigs in the catalog.</p>'}</div>
</div>"""


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
