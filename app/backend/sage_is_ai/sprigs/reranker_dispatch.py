"""Point the Rootstock™ reranking dispatch at a grafted reranker Sprig™.

Shared by the graft route (``routers/sprigs.py``) and the supervisor's boot
reconcile (``supervisor.py``) — same single-source rationale as
``embedding_dispatch.py``. The grafted child is llama-server in ``--rerank``
mode, whose ``/v1/rerank`` speaks the Jina/Cohere contract that the existing
``ExternalReranker`` client (retrieval/models/external.py) already parses — so
this only points config; no client code changes.
"""

from __future__ import annotations

import logging

from sage_is_ai.sprigs.embedding_dispatch import SPRIG_API_KEY

log = logging.getLogger(__name__)


def point_reranker_at(app, handle) -> None:
    """Repoint RAG reranking config + rebuild RERANKING_FUNCTION at ``handle``.

    ExternalReranker treats its url as the FULL endpoint (it POSTs to it
    verbatim), so we persist ``base_url + "/rerank"`` — base_url already ends in
    ``/v1``. The ``sprig-local`` key marks the config as graft-owned for the
    main.py restart backstop, mirroring the embedding sentinel.
    """
    cfg = app.state.config

    cfg.RAG_RERANKING_ENGINE = "external"
    cfg.RAG_RERANKING_MODEL = handle.model
    cfg.RAG_EXTERNAL_RERANKER_URL = handle.base_url + "/rerank"
    cfg.RAG_EXTERNAL_RERANKER_API_KEY = SPRIG_API_KEY

    # Lazy imports — same import-order rationale as embedding_dispatch.
    from sage_is_ai.retrieval.utils import get_reranking_function
    from sage_is_ai.routers.retrieval import get_rf

    app.state.rf = get_rf(
        cfg.RAG_RERANKING_ENGINE,
        cfg.RAG_RERANKING_MODEL,
        cfg.RAG_EXTERNAL_RERANKER_URL,
        cfg.RAG_EXTERNAL_RERANKER_API_KEY,
        False,
    )
    app.state.RERANKING_FUNCTION = get_reranking_function(
        cfg.RAG_RERANKING_ENGINE,
        cfg.RAG_RERANKING_MODEL,
        app.state.rf,
    )

    from sage_is_ai.diagnostics import endpoint_health

    endpoint_health.record_success(handle.base_url, capability="sprig:reranker")
