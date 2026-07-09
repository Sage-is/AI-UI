"""chromadb bootstrap — Sprig™-first, pinned-pip fallback.

ONE implementation of "make chromadb + the vector client available", shared by
the two former pip sites (the AI Engine wizard step in ``routers/retrieval.py``
and the try.sage boot installer in ``utils/try_sage_engine_install.py``), which
had already drifted apart (uv-pip + append vs pip --force-reinstall + insert).

Order of attempts:
  1. Already good — ``factory.VECTOR_DB_CLIENT`` is live.
  2. Overlay already on disk — the vector-chroma Sprig™ was delivered earlier
     (this boot's reconcile, or a prior graft on this container); an
     ``importlib.invalidate_caches()`` + import + factory re-init is all that's
     missing. This also closes a real gap: after container recreation the boot
     reconcile re-extracts the overlay, but nothing re-initialized the factory.
  3. Graft the vector-chroma Sprig™ — sha256-pinned closure, volume-cached tar
     first (offline: no registry, no PyPI needed after the first acquisition),
     oras pull second. This is the north-star path.
  4. Pinned pip fallback (``chromadb==0.6.3`` into DATA_DIR/ml_packages) — kept
     because production (try.sage.is) has no artifact registry until the
     prod-registry cutover lands. On a registry-less box the sprig attempt
     fails DNS in milliseconds, so the fallback costs nothing. When the cutover
     ships, this path goes cold with zero code change here.

Returns True when the vector client is live after the call.
"""

from __future__ import annotations

import importlib
import logging
import os
import shutil
import subprocess
import sys

from fastapi.concurrency import run_in_threadpool

log = logging.getLogger(__name__)

# The canonical pin — tracks pyproject/the vector-chroma Sprig™ closure.
# Unpinned pip resolves chromadb 1.5.x whose opentelemetry deps don't match the
# base image ("cannot import name 'OTEL_SPAN_PARENT_ORIGIN'").
CHROMADB_PIN = "chromadb==0.6.3"


def _set_status(app, state: str, error: str | None = None) -> None:
    """Best-effort MODEL_DOWNLOAD_STATUS['chromadb'] update (trial banner reads it)."""
    status = getattr(app.state, "MODEL_DOWNLOAD_STATUS", None) if app else None
    if not status:
        return
    status["chromadb"] = state
    if error:
        status["error"] = f"chromadb: {error}"


def _factory_ready() -> bool:
    from sage_is_ai.retrieval.vector import factory

    return factory.VECTOR_DB_CLIENT is not None


def _try_activate(vector_db: str) -> bool:
    """invalidate caches → import chromadb → re-init the factory singleton."""
    importlib.invalidate_caches()
    try:
        import chromadb  # noqa: F401
    except ImportError:
        return False
    from sage_is_ai.retrieval.vector import factory

    try:
        factory.VECTOR_DB_CLIENT = factory.Vector.get_vector(vector_db)
    except Exception as e:  # noqa: BLE001 — wrong-version installs raise oddly
        log.warning("chromadb imports but vector client init failed: %s", e)
        return False
    return factory.VECTOR_DB_CLIENT is not None


async def _pip_fallback(vector_db: str) -> bool:
    """The hardened pinned-pip path (relocated from try_sage_engine_install)."""
    ml_target = os.path.join(
        os.environ.get("DATA_DIR", "/app/backend/data"), "ml_packages"
    )
    os.makedirs(ml_target, exist_ok=True)

    # Defensive cleanup: wipe chromadb-shaped entries only, so a prior
    # wrong-version install can't confuse the resolver or the import cache,
    # while wizard-installed torch/sentence-transformers stay intact.
    for entry in os.listdir(ml_target):
        if entry.startswith("chromadb"):
            full = os.path.join(ml_target, entry)
            try:
                shutil.rmtree(full) if os.path.isdir(full) else os.remove(full)
            except OSError as e:
                log.warning("could not clean %s before install (%s)", full, e)

    log.info(
        "chromadb: sprig delivery unavailable — pip-installing %s into %s "
        "(~30s-2min depending on network).",
        CHROMADB_PIN,
        ml_target,
    )
    try:
        await run_in_threadpool(
            subprocess.run,
            [
                "pip",
                "install",
                CHROMADB_PIN,
                # Replace any wrong-version leftovers; no-op on clean installs.
                "--force-reinstall",
                "--target",
                ml_target,
                "--break-system-packages",
                "--root-user-action=ignore",
            ],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        log.warning("chromadb pip fallback failed: %s", e)
        return False
    except FileNotFoundError as e:
        log.warning("chromadb pip fallback skipped — pip not on PATH: %s", e)
        return False

    if ml_target not in sys.path:
        sys.path.insert(0, ml_target)
    return _try_activate(vector_db)


async def ensure_chromadb(app) -> bool:
    """Sprig™-first, pip-fallback chromadb bootstrap. Idempotent on every axis."""
    from sage_is_ai.config import VECTOR_DB

    if VECTOR_DB != "chroma":
        return False

    # 1. Already live? (Factory check, NOT bare import — a wrong-version
    #    chromadb can import while the client stays None.)
    if _factory_ready():
        _set_status(app, "ready")
        return True

    _set_status(app, "downloading")

    # 2. Overlay already on disk (boot reconcile / earlier graft)?
    if _try_activate(VECTOR_DB):
        log.info("chromadb: activated from the already-delivered overlay.")
        _set_status(app, "ready")
        return True

    # 3. Sprig™ delivery — volume-cached tar first, registry second.
    supervisor = getattr(app.state, "sprig_supervisor", None) if app else None
    if supervisor is not None:
        try:
            await supervisor.graft("vector-chroma", "vector")
            if _try_activate(VECTOR_DB):
                log.info("chromadb: delivered via the vector-chroma Sprig™.")
                _set_status(app, "ready")
                return True
            log.warning(
                "vector-chroma delivered but chromadb not importable in this "
                "process; falling back to pip."
            )
        except Exception as e:  # noqa: BLE001 — registry-less prod fails fast here
            log.info("vector-chroma Sprig™ unavailable (%s); falling back to pip.", e)

    # 4. Pinned pip fallback.
    if await _pip_fallback(VECTOR_DB):
        _set_status(app, "ready")
        return True

    _set_status(app, "error", "all delivery paths failed")
    return False
