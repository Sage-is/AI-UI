"""Hidden OpenAI-compatible connection registry for try.sage trial mode.

Why this module exists
----------------------

The trial deployment ships with a real LLM provider that *inference must
use* (chat completions, model listing, embeddings) but that *admins must
not see, edit, or delete* through the Connections UI. A curious workshop
admin in the trial environment must not be able to rotate the upstream
key, swap the URL, or even know what they are.

To honor that contract we keep hidden connections **memory-only** in a
**separate** ``app.state`` attribute (``app.state.try_sage_hidden_connections``).
They never touch ``app.state.config.OPENAI_API_BASE_URLS`` /
``OPENAI_API_KEYS`` / ``OPENAI_API_CONFIGS`` — those are the public,
admin-managed, DB-persisted lists. Because the public lists are the
**only** source admin endpoints read, hidden connections cannot leak
through any existing admin GET / POST: the leak surface is structurally
zero, not "filtered to zero".

The inference resolver in ``routers/openai.py`` is the one place that
unions the two lists. It walks the public list, then walks
``get_hidden_connections(app)``. Models served by hidden connections are
tagged so the dispatch path (chat/embeddings/proxy) can route them back
to their hidden URL/key without ever indexing into the public list.

Why memory-only
---------------

``TRY_SAGE_LLM_API_URL`` and ``TRY_SAGE_LLM_API_KEY`` are env-only in
``env.py`` precisely so they never round-trip through the config DB.
Persisting them — even as a "hidden" row — would mean a DB dump leaks
the trial's keys-to-the-kingdom. Keeping them in process memory means
a restart re-reads the env, and a DB compromise reveals nothing.

Why the model allowlist is opt-in narrowing
-------------------------------------------

``TRY_SAGE_LLM_MODELS`` is an *opt-in narrowing filter*, not a gate.

- **Empty (default)**: pass through every model the upstream provider
  serves. The upstream key is the real authority on what the trial can
  call — its IAM/permissions are the gate, not our allowlist.
- **Populated**: constrain the trial to that subset. Useful when the
  upstream key can call expensive models (GPT-4 class) and the trial
  should only expose cheap ones (GPT-4o-mini class).

Earlier revisions defaulted "empty" to "expose nothing" as defense in
depth. In practice that doubled the friction during workshop bring-up:
operators set URL+key, hit `/api/models`, saw an empty list, thought
the trial was broken, opened the docs to find out about a third env
var. The upstream key already constrains what the trial can call —
making the allowlist required just hid that signal behind a confusing
empty response.
"""

import hashlib
import logging
from typing import Any

from sage_is_ai.env import (
    ENABLE_TRY_SAGE,
    SRC_LOG_LEVELS,
    TRY_SAGE_LLM_API_KEY,
    TRY_SAGE_LLM_API_URL,
    TRY_SAGE_LLM_MODELS,
)

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


# Stable marker on every hidden-connection dict. Used by:
#   - is_hidden_connection() — predicate for filter helpers.
#   - filter_admin_visible() — strips entries where source matches.
#   - inference resolver in routers/openai.py — recognizes the entry as
#     "route through hidden registry, not OPENAI_API_BASE_URLS[idx]".
HIDDEN_CONNECTION_SOURCE = "try_sage_hidden"


def _stable_id(url: str) -> str:
    """Deterministic ID derived from the URL.

    Survives restarts (same URL → same ID) so the inference resolver can
    reference a hidden connection by ID across requests without a DB
    round-trip. Truncated SHA-256 is plenty — collisions in this tiny
    namespace (1-2 hidden connections per deployment) are not a concern.
    """
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return f"hidden-{digest[:16]}"


def _build_hidden_entry(url: str, key: str) -> dict:
    """Build the in-memory dict that represents one hidden connection.

    Shape mirrors a single entry from the public list zipped with its
    config — ``url`` + ``key`` + ``config`` — plus the ``source`` and
    ``id`` fields needed to identify it as hidden during inference
    resolution.
    """
    return {
        "id": _stable_id(url),
        "url": url.rstrip("/"),
        "key": key,
        # The OpenAI router treats api_config.get("enable", True) as the
        # gate for whether to fetch this provider at all; we always want
        # the hidden connection enabled when registered.
        "config": {"enable": True},
        "source": HIDDEN_CONNECTION_SOURCE,
    }


def register_hidden_connections(app) -> None:
    """Lifespan-startup hook: install the trial's hidden LLM connection.

    No-op when ``ENABLE_TRY_SAGE`` is False or when the URL/key are
    empty (logs a warning in the latter case so a misconfigured trial
    is visible in the boot logs without crashing the process).

    Idempotent: safe to call from both ``lifespan`` and the auto-reset
    routine. The resulting list always reflects current env values.
    """
    if not ENABLE_TRY_SAGE:
        # Clear any previous registration so toggling try mode off and
        # restarting actually unregisters the hidden connection (it
        # should not survive a flag flip across restarts).
        app.state.try_sage_hidden_connections = []
        return

    # Trial mode never wants the open-webui Arena Model surfaced — it's
    # a meta "compare two models side-by-side" feature that confuses
    # workshop attendees and clutters the model selector. Force it off
    # at every boot and reset; if an admin flips it on via the UI mid-
    # session it'll re-disable on the next reset cycle.
    app.state.config.ENABLE_EVALUATION_ARENA_MODELS = False

    url = (TRY_SAGE_LLM_API_URL or "").strip()
    key = (TRY_SAGE_LLM_API_KEY or "").strip()

    if not url or not key:
        log.warning(
            "try.sage hidden LLM connection not registered: "
            "TRY_SAGE_LLM_API_URL or TRY_SAGE_LLM_API_KEY is empty. "
            "Inference will fall back to public admin-managed connections."
        )
        app.state.try_sage_hidden_connections = []
        return

    entry = _build_hidden_entry(url, key)
    app.state.try_sage_hidden_connections = [entry]

    allowlist_size = len(TRY_SAGE_LLM_MODELS)
    log.info(
        "try.sage registered hidden LLM connection (id=%s, allowlist=%d %s).",
        entry["id"],
        allowlist_size,
        "models" if allowlist_size > 0 else "models — empty means 'pass through full upstream list'",
    )


def get_hidden_connections(app) -> list[dict]:
    """Return the in-memory hidden connection list.

    Empty when try mode is off or unconfigured. Callers in the inference
    resolver union this with the public list. Never called by admin
    endpoints (admin endpoints read ``app.state.config.OPENAI_API_BASE_URLS``
    instead, by design).
    """
    return list(getattr(app.state, "try_sage_hidden_connections", []) or [])


def is_hidden_connection(conn: Any) -> bool:
    """True when ``conn`` is a hidden-connection dict.

    Single source of truth — every "is this hidden?" check across the
    codebase routes through this predicate so the marker rule lives in
    exactly one place.
    """
    if not isinstance(conn, dict):
        return False
    return conn.get("source") == HIDDEN_CONNECTION_SOURCE


def filter_admin_visible(connections: list[dict]) -> list[dict]:
    """Strip hidden connections from any list bound for an admin response.

    Used as a final defense-in-depth wrap on any endpoint that *could*
    surface inference-resolver output to an admin. Today no such endpoint
    exists (configs.py / openai.py admin endpoints read the public list
    directly, never the unioned list), but the helper is here so future
    code that mistakenly routes through the unioned list still filters.
    """
    if not connections:
        return []
    return [conn for conn in connections if not is_hidden_connection(conn)]


def _matches_allowlist(model_id: str, allowlist: set[str]) -> bool:
    """Vendor-prefix-tolerant allowlist match.

    Upstream providers (Groq, OpenRouter, etc.) often namespace model
    IDs by vendor — ``openai/gpt-oss-120b``, ``qwen/qwen3-32b``,
    ``meta-llama/llama-4-scout-17b-16e-instruct``. Operators tend to
    write the bare name in ``TRY_SAGE_LLM_MODELS``. Exact match would
    drop every model and the trial would silently expose nothing.

    Match rules:

    1. **Exact**: ``"openai/gpt-oss-120b" == "openai/gpt-oss-120b"``.
    2. **Bare entry → namespaced model**: an allowlist entry without
       ``/`` matches a model ID whose final path segment equals it.
       ``gpt-oss-120b`` matches ``openai/gpt-oss-120b`` but not
       ``openai/gpt-oss-20b``. Tail-segment compare, not substring —
       avoids `gpt-4` matching `gpt-4-turbo`.

    Trade-off: a bare allowlist entry matches every vendor that serves
    the same tail name. Acceptable for trial mode — the operator can
    always write the full prefixed ID for surgical control.
    """
    if model_id in allowlist:
        return True
    tail = model_id.rsplit("/", 1)[-1]
    for entry in allowlist:
        if "/" in entry:
            continue  # Namespaced entries only match exactly (handled above).
        if tail == entry:
            return True
    return False


def filter_models_to_allowlist(
    models: list[dict], hidden_conn_id: str
) -> list[dict]:
    """Optionally narrow a model list to ``TRY_SAGE_LLM_MODELS``.

    Models served by *other* connections (positive ``urlIdx``, or
    different ``hidden_conn_id``) are passed through unchanged — this
    helper is only authoritative for one hidden connection at a time.

    Allowlist semantics (see module docstring):

    - **Empty** (default): pass every hidden-conn model through. The
      upstream provider's key is the real gate — if the trial deployer
      doesn't want users hitting the upstream's full catalog they can
      either narrow the upstream key's permissions or set this list.
    - **Populated**: keep only the named model IDs from the hidden
      connection. Match is vendor-prefix tolerant (see
      ``_matches_allowlist``) so an operator can write `qwen3-32b` and
      have it match Groq's `qwen/qwen3-32b`.
    """
    allowlist = set(TRY_SAGE_LLM_MODELS or [])

    # No allowlist → no filtering. Hidden-conn models pass through with
    # the same handling as any other connection.
    if not allowlist:
        return list(models)

    filtered: list[dict] = []
    for model in models:
        if model.get("_try_sage_hidden_id") != hidden_conn_id:
            # Not from this hidden connection — leave alone.
            filtered.append(model)
            continue

        model_id = model.get("id") or model.get("name") or ""
        if _matches_allowlist(model_id, allowlist):
            filtered.append(model)
        # else: drop it. The upstream provider may technically serve
        # this model, but the trial deployer chose to narrow.
    return filtered


def resolve_hidden_connection(
    app, hidden_conn_id: str
) -> dict | None:
    """Look up a hidden connection by its stable ID.

    Used at inference-dispatch sites (chat/completions, embeddings,
    proxy) to recover the URL + key for a model whose ``urlIdx`` was
    flagged as hidden during model-list resolution.

    Returns ``None`` if no match — caller should treat that as
    "fall back to the public list" or 404, depending on context.
    """
    for conn in get_hidden_connections(app):
        if conn.get("id") == hidden_conn_id:
            return conn
    return None


def get_hidden_status(app) -> dict:
    """Diagnostic dict for ``GET /api/v1/sage/runtime/llm-status`` (admin).

    Returns ``{"configured": bool, "model_count": int}`` only — never
    the URL or key.

    ``configured`` is True iff at least one hidden connection is
    registered. The allowlist is no longer required for "configured" —
    an empty allowlist now means "pass through the upstream provider's
    full model list" (see ``filter_models_to_allowlist`` and the module
    docstring).

    ``model_count`` reports the *allowlist* length:
    - ``0`` means "no narrowing — every model the upstream serves is
      exposed"
    - ``N`` means "exactly these N model IDs are exposed"

    Admins reading this endpoint should treat ``configured: true,
    model_count: 0`` as "fully open to the upstream catalog" rather
    than "broken".
    """
    connections = get_hidden_connections(app)
    model_count = len(TRY_SAGE_LLM_MODELS or [])
    return {
        "configured": bool(connections),
        "model_count": model_count,
    }
