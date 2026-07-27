"""The Sprigs™ panel as server-rendered fragments — the measurement.

Phase 0 built this panel as a vanilla island and it came out slightly BIGGER
than the Svelte component it replaced, against a plan that predicted a ~40% cut.
The diagnosis at the time was that the panel is fragment-shaped, not
island-shaped — a list with buttons that POST and re-fetch — and that the
fragment path was structurally unavailable because a server-rendered view needs
the operator's token, which lived in localStorage. The cookie bridge removed
that blocker, so this is the third implementation, written to settle the
question with a number instead of an argument.

Two things make it small, and neither is htmx being clever.

The first is that it does not restate the backend. The graft and prune handlers
in routers/sprigs.py are called directly, so this module is a VIEW over them —
no second copy of the allowlist check, the dispatch, or the reset semantics. An
HTTP round-trip to our own API would have been the other option and it would
have been worse: a second serialization, a second auth pass, and a copy of every
error contract.

The second is that state lives in one place. The island had to hold the catalog
in memory, decide what changed, and rebuild DOM. Here a mutation returns the
whole panel and htmx swaps it, so there is no client-side model to keep in step
with the server's — and the class of bug where those two disagree cannot occur.
"""

from __future__ import annotations

from html import escape

from fastapi import Request

from sage_is_ai.sprigs.models import GraftRequest, PruneRequest

__all__ = ["render_panel", "graft_and_render", "prune_and_render"]

# Supervisor lifecycle state -> operator-facing label. Same table the Svelte
# panel and the island carry, and the guard-rail spec reads the data-state
# attribute rather than the word, so this stays free to be reworded.
_LABEL = {"rooted": "Grafted", "wilted": "Wilted", "delivered": "Delivered"}
_GRAFTED = {"rooted", "delivered"}


def _msg(text: str, kind: str) -> str:
    if not text:
        return ""
    return f'<p class="toast toast-{escape(kind)}" data-cy="panel-message">{escape(text)}</p>'


def _card(name: str, spec: dict, grafted: dict, host_arch: str) -> str:
    g = grafted.get(name)
    state = (g or {}).get("state") or "sprouted"
    is_grafted = state in _GRAFTED
    incompatible = spec.get("compatible") is False

    meta = " · ".join(
        str(p)
        for p in (spec.get("capability"), spec.get("model"), spec.get("dim") and f"{spec['dim']}d")
        if p
    )

    # One button, chosen by state. The island needed the same branch plus the
    # bookkeeping to re-render it; here the branch IS the render.
    if is_grafted:
        health = (
            '<a class="btn" href="/admin/diagnostics" title="View health in Diagnostics">Health</a>'
            if (g or {}).get("base_url")
            else ""
        )
        action = (
            f'{health}<button type="button" class="btn btn-danger" data-cy="sprig-prune"'
            f' title="Terminate and remove this Sprig&#8482;"'
            f' hx-post="/pages/admin/sprigs/prune" hx-vals=\'{{"name": "{escape(name, quote=True)}"}}\''
            f' hx-target="#sprigs-panel" hx-swap="outerHTML">Prune</button>'
        )
    else:
        label = "Revive" if state == "wilted" else "Graft"
        disabled = " disabled" if incompatible else ""
        title = (
            ' title="This Sprig&#8482; requires a different server architecture"'
            if incompatible
            else ""
        )
        action = (
            f'<button type="button" class="btn btn-primary" data-cy="sprig-graft"{disabled}{title}'
            f' hx-post="/pages/admin/sprigs/graft"'
            f' hx-vals=\'{{"name": "{escape(name, quote=True)}",'
            f' "capability": "{escape(str(spec.get("capability", "")), quote=True)}"}}\''
            f' hx-target="#sprigs-panel" hx-swap="outerHTML">{label}</button>'
        )

    warn = (
        f'<div class="sprig-warn" data-cy="sprig-incompatible">Not available on this '
        f"server ({escape(host_arch or 'unknown')})</div>"
        if incompatible and not is_grafted
        else ""
    )
    where = (
        f'<div class="sprig-where">{escape(g["base_url"])}'
        f'{escape(" · pid " + str(g["pid"])) if g.get("pid") else ""}</div>'
        if g and g.get("base_url")
        else ""
    )

    return (
        f'<div class="sprig-card" data-cy="sprig-card" data-sprig="{escape(name, quote=True)}">'
        f'<span class="badge badge-{escape(state, quote=True)}" data-cy="sprig-state"'
        f' data-state="{escape(state, quote=True)}">{escape(_LABEL.get(state, "Sprouted"))}</span>'
        f'<div class="sprig-main">'
        f'<div class="sprig-name">{escape(name)}</div>'
        f'<div class="sprig-meta">{escape(meta)}</div>{warn}{where}</div>'
        f'<div class="sprig-actions">{action}</div>'
        f"</div>"
    )


async def render_panel(request: Request, user, *, message: str = "", kind: str = "info") -> str:
    """The whole panel, which is also the whole swap target.

    Returning everything rather than patching is what removes the client-side
    model. It costs a few hundred bytes over the wire on a mutation and buys the
    absence of an entire bug class.
    """
    from sage_is_ai.routers.sprigs import get_sprig_catalog

    data = await get_sprig_catalog(request, user)
    catalog = data.get("catalog") or {}
    grafted = data.get("grafted") or {}
    host_arch = data.get("host_arch") or ""

    count = sum(1 for g in grafted.values() if (g or {}).get("state") in _GRAFTED)
    cards = "".join(_card(n, s, grafted, host_arch) for n, s in catalog.items())
    body = cards or '<p class="page-muted">No Sprigs in the catalog.</p>'
    counter = (
        f'<span class="page-count" data-cy="sprigs-grafted-count">'
        f"{count} of {len(catalog)} grafted</span>"
        if catalog
        else '<span class="page-count" data-cy="sprigs-grafted-count"></span>'
    )

    return (
        '<div id="sprigs-panel">'
        f'<div class="panel-bar">{counter}'
        '<button type="button" class="btn" data-cy="sprigs-refresh"'
        ' hx-get="/pages/admin/sprigs/panel" hx-target="#sprigs-panel"'
        ' hx-swap="outerHTML">Refresh</button></div>'
        f'{_msg(message, kind)}'
        f'<div class="sprig-list">{body}</div>'
        "</div>"
    )


async def graft_and_render(request: Request, user, name: str, capability: str) -> str:
    """Graft, then re-render. The API handler does the work; this reports it."""
    from fastapi import HTTPException

    from sage_is_ai.routers.sprigs import graft_sprig

    try:
        res = await graft_sprig(request, GraftRequest(name=name, capability=capability), user)
    except HTTPException as e:
        # The backend detail names the actual cause and the fix ("cultivar needs
        # numpy — graft vector-chroma first"). Showing "Failed to graft" instead
        # is the Poka-Yoke regression the guard-rail spec exists to catch.
        return await render_panel(
            request, user, message=f"Failed to graft {name}: {e.detail}", kind="error"
        )

    # The post-graft note is the contract: the operator is TOLD what happens
    # next. It rides in the same swap rather than a separate toast, so it cannot
    # be lost to a race between the response and a re-render.
    note = getattr(res, "warning", None)
    message = f"Grafted {name}." + (f" {note}" if note else "")
    return await render_panel(request, user, message=message, kind="success")


async def prune_and_render(request: Request, user, name: str) -> str:
    from fastapi import HTTPException

    from sage_is_ai.routers.sprigs import prune_sprig

    try:
        res = await prune_sprig(request, PruneRequest(name=name), user)
    except HTTPException as e:
        return await render_panel(
            request, user, message=f"Failed to prune {name}: {e.detail}", kind="error"
        )

    # Pruning a delivered capability silently changes what the rest of the
    # product can do. Say which, in the same words the other two panels use.
    resets = [
        ("embedding_reset", "Embedding dispatch reset — graft a cultivar to restore document search."),
        ("reranking_reset", "Reranking reset — hybrid search runs without rerank until a reranker is grafted."),
        ("stt_reset", "Speech-to-text reset — graft an STT Sprig™ to restore local voice input."),
        ("theme_reset", "Theme reset — the interface returns to the default look on reload."),
        ("ui_reset", "Fragment removed — the page returns to its default layout on reload."),
        ("scripting_grant_revoked", "Scripting permission revoked with the Sprig™ it was granted to."),
    ]
    extra = " ".join(text for key, text in resets if res.get(key))
    return await render_panel(
        request, user, message=f"Pruned {name}." + (f" {extra}" if extra else ""), kind="success"
    )
