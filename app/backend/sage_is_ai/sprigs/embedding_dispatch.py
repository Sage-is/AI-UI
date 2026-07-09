"""Point the Rootstock™ embedding dispatch at a grafted embedding Sprig™.

Shared by the graft route (``routers/sprigs.py``) and the supervisor's boot
reconcile (``supervisor.py``) so the "make the app embed through this loopback
Sprig™" logic lives in exactly one place — no drift between the request-time graft
and the restart-time re-graft.
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)

# Sentinel API key a grafted embedding Sprig™ writes into RAG_OPENAI_API_KEY. The
# mock/onnx/llama children ignore the key; its real job is to mark the persisted
# embedding config as "owned by a Sprig™" so the boot path can detect a graft that
# did not survive a restart (see main.py restart-safety guard).
SPRIG_API_KEY = "sprig-local"


def point_embedding_at(app, handle) -> None:
    """Repoint RAG embedding config + rebuild EMBEDDING_FUNCTION at ``handle``.

    Mutates ``app.state.config.RAG_*`` (auto-persists via PersistentConfig),
    rebuilds ``app.state.ef`` / ``app.state.EMBEDDING_FUNCTION``, flips the
    embedding download-status to ready, and records the endpoint as healthy so the
    diagnostics row appears immediately. Engine is always ``openai`` here (the
    Sprig™ serves an OpenAI-compatible ``/v1/embeddings``).
    """
    cfg = app.state.config

    previous_url = cfg.RAG_OPENAI_API_BASE_URL
    if previous_url and previous_url != handle.base_url:
        log.info("embedding dispatch replacing previous base url %s", previous_url)

    cfg.RAG_EMBEDDING_ENGINE = "openai"
    cfg.RAG_EMBEDDING_MODEL = handle.model
    cfg.RAG_OPENAI_API_BASE_URL = handle.base_url
    cfg.RAG_OPENAI_API_KEY = SPRIG_API_KEY

    # Lazy imports: routers.retrieval pulls a large dependency graph, and importing
    # it at module load would be fragile during the supervisor's boot reconcile.
    from sage_is_ai.retrieval.utils import get_embedding_function
    from sage_is_ai.routers.retrieval import get_ef

    app.state.ef = get_ef(cfg.RAG_EMBEDDING_ENGINE, cfg.RAG_EMBEDDING_MODEL)
    app.state.EMBEDDING_FUNCTION = get_embedding_function(
        cfg.RAG_EMBEDDING_ENGINE,
        cfg.RAG_EMBEDDING_MODEL,
        app.state.ef,
        cfg.RAG_OPENAI_API_BASE_URL,
        cfg.RAG_OPENAI_API_KEY,
        cfg.RAG_EMBEDDING_BATCH_SIZE,
        azure_api_version=None,
    )

    if getattr(app.state, "MODEL_DOWNLOAD_STATUS", None):
        app.state.MODEL_DOWNLOAD_STATUS["embedding"] = "ready"

    from sage_is_ai.diagnostics import endpoint_health

    endpoint_health.record_success(handle.base_url, capability="sprig:embedding")
