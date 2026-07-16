"""embedding bootstrap — Sprig™-first wizard delivery.

Mirrors ``vector_bootstrap.ensure_chromadb``: ONE place that answers "make the
configured embedding model serve locally", tried BEFORE the legacy AI-Engine
install (torch + sentence-transformers + a live HuggingFace download). This was
the last live HF pull in the product: a catalog cultivar ships the same weights
pre-seeded, sha256-pinned, served by a supervised loopback child — no HF, no
torch, and the child process keeps the model load off the event loop.

Selection contract: an ``oci-artifact`` embedding entry whose ``model`` matches
``RAG_EMBEDDING_MODEL`` (exact, or exact on the repo-less basename so
"sentence-transformers/all-MiniLM-L6-v2" finds the "all-MiniLM-L6-v2" cultivar).
Python-served cultivars (``server: embedding`` — the onnx family) are preferred
over binary ones. Host-incompatible entries are refused by graft() itself (the
arch guard) and simply fall through — first to the next candidate, then to the
legacy path. Run AFTER ensure_chromadb: the onnx cultivars ride the onnxruntime
that overlay delivers.

Returns True when the dispatch is live (``point_embedding_at`` ran, status
flipped to ready). False means "nothing delivered — use the legacy path".
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def _matches(spec_model: str, model: str) -> bool:
    return spec_model == model or spec_model == model.split("/")[-1]


async def ensure_embedding(app) -> bool:
    """Sprig™-first embedding delivery. Idempotent; never raises."""
    from sage_is_ai.sprigs.embedding_dispatch import SPRIG_API_KEY, point_embedding_at

    cfg = app.state.config
    supervisor = getattr(app.state, "sprig_supervisor", None)
    model = cfg.RAG_EMBEDDING_MODEL

    # Already Sprig™-owned and live (re-triggered wizard after a graft).
    # EMBEDDING_FUNCTION, not ef: the sprig path serves through the openai
    # client wrapper and deliberately leaves app.state.ef as None.
    if (
        cfg.RAG_EMBEDDING_ENGINE == "openai"
        and cfg.RAG_OPENAI_API_KEY == SPRIG_API_KEY
        and getattr(app.state, "EMBEDDING_FUNCTION", None) is not None
    ):
        status = getattr(app.state, "MODEL_DOWNLOAD_STATUS", None)
        if status:
            status["embedding"] = "ready"
        return True

    # Only the local path is ours to deliver; external engines configure away.
    if cfg.RAG_EMBEDDING_ENGINE not in ("", None):
        return False
    if supervisor is None or not model:
        return False

    candidates = [
        (name, spec)
        for name, spec in supervisor.CATALOG.items()
        if spec.get("capability") == "embedding"
        and spec.get("delivery") == "oci-artifact"
        and _matches(spec.get("model", ""), model)
    ]
    # Prefer the python-served onnx family over binary servers.
    candidates.sort(key=lambda kv: kv[1].get("server") != "embedding")

    for name, _spec in candidates:
        try:
            handle = await supervisor.graft(name, "embedding")
            if handle.process is None:
                # A processless handle can't serve /v1/embeddings — treating
                # it as success would wedge the status machine on
                # "downloading" with the re-trigger guard locked.
                log.warning(
                    "embedding Sprig™ '%s' grafted without a server process; "
                    "trying next candidate or the legacy install.",
                    name,
                )
                continue
            # Inside the try: point_embedding_at persists config, and a
            # failure here must fall through (visibly) instead of escaping
            # into _download's handler and marking unrelated components error.
            point_embedding_at(app, handle)
        except Exception as e:  # noqa: BLE001 — arch refusal / registry down
            log.info(
                "embedding Sprig™ '%s' unavailable (%s); trying next candidate "
                "or the legacy install.",
                name,
                e,
            )
            continue
        log.info("embedding served by Sprig™ '%s' — no HF download.", name)
        return True

    return False
