"""Boot-time probes for the EndpointHealth registry.

run_boot_probes(app) gathers every configured external URL and probes them
concurrently with a short timeout. Results populate the registry so the
diagnostics page (Phase 3) has data immediately at boot, before the first
real request triggers a discovery-via-failure event.

Probes never block boot. Failures land in the registry as `unreachable`
with the error class captured. Operators see the issue before a user does.
"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Iterable

from sage_is_ai.diagnostics.health_registry import endpoint_health
from sage_is_ai.diagnostics.probes import probe_http

log = logging.getLogger(__name__)


def _persistent_value(raw):
    """PersistentConfig wraps its value as `.value`; raw strings/lists pass
    through unchanged. Probe sites read both shapes; this normalizes."""
    return getattr(raw, "value", raw)


def _collect_urls(app) -> list[tuple[str, str]]:
    """Return [(url, capability)] for every configured external URL we want
    to probe at boot. Empty/None URLs are filtered out so the registry
    doesn't fill with placeholder rows."""
    cfg = app.state.config
    candidates: list[tuple[object, str]] = []

    candidates.extend(
        (u, "openai/list_models")
        for u in _persistent_value(getattr(cfg, "OPENAI_API_BASE_URLS", None)) or []
    )
    candidates.extend(
        (u, "ollama/list_models")
        for u in _persistent_value(getattr(cfg, "OLLAMA_BASE_URLS", None)) or []
    )

    for attr, capability in [
        ("TIKA_SERVER_URL", "rag/tika"),
        ("DOCLING_SERVER_URL", "rag/docling"),
        ("RAG_EXTERNAL_RERANKER_URL", "rag/reranker"),
    ]:
        url = _persistent_value(getattr(cfg, attr, None))
        if url:
            candidates.append((url, capability))

    rag_engine = _persistent_value(getattr(cfg, "RAG_EMBEDDING_ENGINE", None))
    if rag_engine == "openai":
        url = _persistent_value(getattr(cfg, "RAG_OPENAI_API_BASE_URL", None))
        if url:
            candidates.append((url, "embedding/openai"))

    out: list[tuple[str, str]] = []
    for raw, capability in candidates:
        if not raw:
            continue
        url = str(raw).strip()
        if not url or not url.startswith(("http://", "https://")):
            continue
        out.append((url, capability))
    return out


def _probe_one_blocking(url: str, capability: str, timeout: float) -> None:
    """probe_http is blocking (requests-based). Run a single probe and
    record the result. Called from a thread so the lifespan loop is free."""
    try:
        result = probe_http(url, timeout=timeout)
    except Exception as exc:  # defensive — probe_http itself shouldn't raise
        endpoint_health.record_failure(url, exc, capability)
        log.warning("boot probe failed for %s: %s", url, exc)
        return
    endpoint_health.record_probe(result, capability)


async def run_boot_probes(app, timeout: float = 5.0) -> None:
    """Probe every configured external URL concurrently; never block on a
    single slow URL. Call this from the FastAPI lifespan startup as a
    fire-and-forget task. Total wall time is bounded by `timeout` because
    probes run in parallel.

    Probes use the sync `probe_http` (requests-based) because (a) we
    already trust it for boundary-error context managers and (b) running
    it in a thread pool avoids adding aiohttp to the boot path's import
    graph just for the probe.

    Summary lines log at WARNING so they appear under uvicorn's default
    `--log-level warning` setting in production. Individual probe results
    are not logged (they're in the registry); only counts and any internal
    failure of the runner itself."""
    try:
        targets = _collect_urls(app)
        if not targets:
            log.warning("boot probes: no URLs configured; skipping")
            return

        log.warning("boot probes: probing %d endpoint(s)", len(targets))

        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor(max_workers=min(8, len(targets))) as pool:
            futures = [
                loop.run_in_executor(
                    pool, _probe_one_blocking, url, capability, timeout
                )
                for url, capability in targets
            ]
            await asyncio.gather(*futures, return_exceptions=True)

        snapshot = endpoint_health.snapshot()
        reachable = sum(
            1 for r in snapshot.values() if r.get("last_status") == "ok"
        )
        log.warning(
            "boot probes: complete (%d reachable, %d total)",
            reachable,
            len(snapshot),
        )
    except Exception as exc:
        # Defensive: a fire-and-forget asyncio task that raises is silent
        # under `--log-level warning`. Catch and log so we hear about it.
        log.exception("boot probes: internal failure: %s", exc)
