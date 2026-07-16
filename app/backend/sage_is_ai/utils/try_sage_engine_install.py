"""Lifespan hook that installs the vector backend (chromadb) when missing.

Background: chromadb is intentionally absent from
``app/backend/requirements.txt`` because the marketed app expects an
operator to run the AI Engine wizard from the admin UI on first boot.
That works for general deployments but is wrong for the try.sage trial:
the trial ships with seeded knowledge bases that fail to ingest until
the wizard runs, and a workshop facilitator has no reason to know the
wizard exists.

This helper closes the gap. When ``ENABLE_TRY_SAGE`` is on and the
configured ``VECTOR_DB`` is ``chroma`` and the vector client is not live,
it delegates to the shared Sprig™-first bootstrap
(``sprigs/vector_bootstrap.ensure_chromadb``): the vector-chroma Sprig™
(volume-cached tar → registry) first, the pinned-pip ``ml_packages``
fallback second, then re-initializes ``factory.VECTOR_DB_CLIENT`` so the
seed pass that runs immediately after can ingest the seeded KB markdown.

Why not also handle torch / sentence-transformers / embedding-model
download here: the chromadb-only install covers the most common case
(default RAG_EMBEDDING_ENGINE is OpenAI for the trial — Groq's hidden
connection — so torch is not needed for chunking/embedding the seed
docs). Operators who want local embeddings can still run the full AI
Engine wizard from admin settings; that path is unchanged.

Idempotent: returns immediately when chromadb already imports. Failure
is non-fatal — the seed's existing graceful-skip path takes over and
logs a warning telling the operator to run the full wizard.
"""

import logging

from sage_is_ai.env import ENABLE_TRY_SAGE, SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


def _set_status(app, state: str, error: str | None = None) -> None:
    """Update the chromadb slot in the shared download-status dict.

    Reuses ``app.state.MODEL_DOWNLOAD_STATUS`` — the same dict the
    existing AI Engine wizard endpoint surfaces at
    ``/api/v1/retrieval/models/status``. The trial banner picks up the
    state via ``/api/v1/sage/runtime/status`` (which mirrors the field
    publicly) so both admins and trial users see install progress
    instead of staring at empty knowledge bases.
    """
    status = getattr(app.state, "MODEL_DOWNLOAD_STATUS", None)
    if not isinstance(status, dict):
        return
    status["chromadb"] = state
    if state == "error" and error:
        # Reuse the existing single "error" slot rather than introducing
        # a chromadb-specific error field — keeps the JSON shape stable
        # for any admin tooling already polling the status dict.
        status["error"] = f"chromadb: {error}"


async def ensure_try_sage_vector_backend(app=None) -> bool:
    """Install chromadb on demand for try-mode trials, then re-seed.

    Designed to be fired as ``asyncio.create_task(...)`` from lifespan
    startup so the container becomes responsive immediately. On first
    boot the seed pass already runs once (graceful skip when chromadb
    is missing — see ``_ensure_kb``); when this background task
    finishes the install, it calls ``seed_try_sage(app)`` again so the
    KBs actually ingest without operator action.

    Idempotent on every axis: short-circuits when chromadb already
    imports, the seed itself is find-or-create, and a re-seed without
    new vector backend is a no-op.

    Returns True when the vector backend is available after this call,
    False otherwise. The boolean is mostly for callers that want to
    block on the result (e.g. tests); production callers fire-and-forget.
    """
    if not ENABLE_TRY_SAGE:
        return False

    # Deferred import — config has side effects we'd rather not run
    # until lifespan startup is actually doing work.
    from sage_is_ai.config import VECTOR_DB

    if VECTOR_DB != "chroma":
        # We only know how to auto-install chroma. Other backends
        # (qdrant, milvus, opensearch) ship as wire clients and do
        # not gate the seed in the same way.
        return False

    # Detect "already-good" state by checking the factory singleton, not
    # just `import chromadb`. Subtle but important: a previous broken
    # boot may have left the wrong chromadb version on disk that imports
    # fine on its own but is missing transitive deps (e.g. chromadb 1.5.x
    # without posthog), so config.py's `import posthog; import chromadb`
    # block fails and `factory.VECTOR_DB_CLIENT` stays None. If we
    # short-circuit here on `import chromadb` success alone, we declare
    # the trial "ready" while the seed still can't ingest. Checking the
    # factory client directly captures the real load-bearing condition.
    from sage_is_ai.retrieval.vector import factory as _factory

    if _factory.VECTOR_DB_CLIENT is not None:
        if app is not None:
            _set_status(app, "ready")
        return True

    # Delegate to the shared Sprig™-first bootstrap (sprigs/vector_bootstrap.py):
    # volume-cached vector-chroma tar → registry → pinned-pip fallback. It owns
    # the MODEL_DOWNLOAD_STATUS["chromadb"] transitions the trial banner reads,
    # the ml_packages cleanup, and the factory re-init.
    from sage_is_ai.sprigs.vector_bootstrap import ensure_chromadb

    if not await ensure_chromadb(app):
        log.warning(
            "try.sage: chromadb bootstrap failed on every path (sprig + pip). "
            "Seed will skip KBs; run the AI Engine wizard from admin settings."
        )
        return False

    log.info("try.sage: vector client ready.")

    # Re-run the seed so KB markdown gets ingested *now* without waiting
    # for the next reset cycle or container restart. The seed is
    # idempotent — agents/personas already exist from the first pass at
    # lifespan startup, so this is effectively a "_ensure_kb retry"
    # with the vector client populated. Skipped when no app handle was
    # provided (e.g. test contexts that just want the install).
    if app is not None:
        try:
            from sage_is_ai.utils.try_sage_seed import seed_try_sage

            await seed_try_sage(app)
            log.info("try.sage: post-install seed pass complete; KBs ingested.")
        except Exception as e:
            log.warning(
                "try.sage: post-install seed pass failed (%s). Run "
                "`Reset now` from the trial banner to retry.",
                e,
            )

    return True
