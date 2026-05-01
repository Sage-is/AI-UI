"""Lifespan hook that installs the vector backend (chromadb) when missing.

Background: chromadb is intentionally absent from
``app/backend/requirements.txt`` because the marketed app expects an
operator to run the AI Engine wizard from the admin UI on first boot.
That works for general deployments but is wrong for the try.sage trial:
the trial ships with seeded knowledge bases that fail to ingest until
the wizard runs, and a workshop facilitator has no reason to know the
wizard exists.

This helper closes the gap. When ``ENABLE_TRY_SAGE`` is on and the
configured ``VECTOR_DB`` is ``chroma`` and chromadb is not importable,
it pip-installs chromadb into the data volume's ``ml_packages``
directory (the same target the route handler at
``routers/retrieval.py:trigger_model_download`` uses) and re-initializes
``factory.VECTOR_DB_CLIENT`` so the seed pass that runs immediately
after can ingest the seeded KB markdown.

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
import os
import subprocess
import sys

from fastapi.concurrency import run_in_threadpool

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

    try:
        import chromadb  # noqa: F401

        log.info(
            "try.sage: chromadb imports but factory client is None — "
            "likely missing transitive deps from a previous wrong-version "
            "install. Re-installing the pyproject-pinned version."
        )
    except ImportError:
        pass

    # Surface install state to the trial banner. The banner reads
    # `app.state.MODEL_DOWNLOAD_STATUS` via the public
    # `/api/v1/sage/runtime/status` endpoint and renders a small
    # "Setting up knowledge bases…" line while we work, so admins
    # (and users) see why KBs aren't bound yet during the first-boot
    # window. Skipped when no app handle was provided.
    if app is not None:
        _set_status(app, "downloading")

    ml_target = os.path.join(
        os.environ.get("DATA_DIR", "/app/backend/data"), "ml_packages"
    )
    os.makedirs(ml_target, exist_ok=True)

    # Defensive cleanup: remove any pre-existing chromadb* directories
    # in the target. A previous boot that ran `pip install chromadb`
    # (no version pin) installed chromadb 1.5.x whose dist-info would
    # confuse pip's resolver and whose .so files might still get picked
    # up by Python's import cache. Wiping just the chromadb-shaped dirs
    # keeps any other wizard-installed packages (torch, sentence-
    # transformers) intact.
    import shutil

    for entry in os.listdir(ml_target):
        if entry.startswith("chromadb"):
            full = os.path.join(ml_target, entry)
            try:
                if os.path.isdir(full):
                    shutil.rmtree(full)
                else:
                    os.remove(full)
            except OSError as e:
                log.warning(
                    "try.sage: could not clean %s before install (%s); "
                    "pip may complain.",
                    full,
                    e,
                )

    log.info(
        "try.sage: chromadb missing — pip-installing into %s before seed runs. "
        "First-boot delay: ~30s–2 min depending on network.",
        ml_target,
    )

    # Pin to the version declared in pyproject.toml. Without a pin, pip
    # grabs the latest (chromadb 1.5.x) whose opentelemetry deps don't
    # match the base image and `import chromadb` then fails with
    # `cannot import name 'OTEL_SPAN_PARENT_ORIGIN'`. The pyproject pin
    # is the canonical version this app's tested against; track it
    # there if a bump is needed.
    chromadb_pin = "chromadb==0.6.3"

    try:
        await run_in_threadpool(
            subprocess.run,
            [
                "pip",
                "install",
                chromadb_pin,
                # `--force-reinstall` replaces a previously-installed wrong
                # version (e.g. unpinned latest from an earlier boot) with
                # the pinned 0.6.3. Without this, an earlier boot's
                # chromadb 1.5.x lingers in --target and `import chromadb`
                # keeps hitting its opentelemetry incompatibility. Costs
                # nothing on a clean first install (~30s either way).
                "--force-reinstall",
                "--target",
                ml_target,
                "--break-system-packages",
                "--root-user-action=ignore",
            ],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        log.warning(
            "try.sage: chromadb auto-install failed (%s). Seed will skip KBs; "
            "run the AI Engine wizard from admin settings to retry.",
            e,
        )
        if app is not None:
            _set_status(app, "error", str(e))
        return False
    except FileNotFoundError as e:
        # `pip` not on PATH — unusual but possible in stripped containers.
        log.warning(
            "try.sage: chromadb auto-install skipped — pip not found on PATH (%s). "
            "Run the AI Engine wizard from admin settings instead.",
            e,
        )
        if app is not None:
            _set_status(app, "error", "pip not on PATH")
        return False

    if ml_target not in sys.path:
        sys.path.insert(0, ml_target)

    # Verify the install is actually importable from this process.
    try:
        import chromadb  # noqa: F401
    except ImportError as e:
        log.warning(
            "try.sage: chromadb pip-install reported success but import still "
            "fails (%s). Seed will skip KBs.",
            e,
        )
        if app is not None:
            _set_status(app, "error", "import after install failed")
        return False

    # Re-initialize the factory singleton — without this the existing
    # `factory.VECTOR_DB_CLIENT` reference (set to None at module-load
    # time when the original chromadb import raised) stays None, and
    # the seed's vector-DB precheck would still skip KB creation.
    from sage_is_ai.retrieval.vector import factory

    try:
        factory.VECTOR_DB_CLIENT = factory.Vector.get_vector(VECTOR_DB)
    except Exception as e:
        log.warning(
            "try.sage: chromadb installed but vector client init failed (%s). "
            "Seed will skip KBs.",
            e,
        )
        if app is not None:
            _set_status(app, "error", "client init failed")
        return False

    log.info("try.sage: chromadb installed and vector client ready.")
    if app is not None:
        _set_status(app, "ready")

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
