"""Save-time probe pre-check for admin config endpoints.

When an admin saves a list of URLs (OPENAI_API_BASE_URLS,
OLLAMA_BASE_URLS, etc.), this helper enforces the Phase 2d poka-yoke
contract: refuse to persist a newly-added URL that doesn't pass a
short HTTP probe.

Semantic (option C from the design pass):
- Probe every URL in the incoming list and record outcomes in the
  EndpointHealth registry (so the diagnostics page reflects current state).
- Refuse the save only when a NEWLY-ADDED URL is unreachable.
- Existing-but-now-broken URLs do NOT block the save. Operators editing
  an unrelated field shouldn't be trapped by a separate broken endpoint
  they aren't touching this minute.

Used by:
- routers/openai.py POST /config/update
- routers/ollama.py POST /config/update
- (future) routers/retrieval.py POST /config/update for embedding URL
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Iterable

from sage_is_ai.diagnostics.exceptions import EndpointUnreachable
from sage_is_ai.diagnostics.health_registry import endpoint_health
from sage_is_ai.diagnostics.probes import probe_http


def _normalize(urls: Iterable[str]) -> list[str]:
    """Strip whitespace, drop empties, return list (order preserved)."""
    return [u.strip() for u in urls if u and str(u).strip()]


def assert_newly_added_urls_reachable(
    submitted: Iterable[str],
    currently_persisted: Iterable[str],
    capability: str,
    timeout: float = 5.0,
) -> None:
    """Refuse the save if any URL in `submitted` that isn't in
    `currently_persisted` fails an HTTP probe.

    The currently-persisted set is taken VERBATIM from `app.state.config.*`
    BEFORE the assignment happens — the caller is responsible for snapshotting
    it before overwriting.

    Raises EndpointUnreachable on the first newly-added bad URL. The FastAPI
    exception handler in main.py converts this to a 503 (technically the
    error is "endpoint unreachable, save refused") — to surface as a 400
    instead, the caller can catch and re-raise as HTTPException(400).
    Phase 2d's docstring picks 400.
    """
    new_urls = _normalize(submitted)
    existing = set(_normalize(currently_persisted))

    if not new_urls:
        return

    # Probe ALL submitted URLs (so the registry reflects current state),
    # but only refuse on newly-added failures.
    with ThreadPoolExecutor(max_workers=min(8, len(new_urls))) as pool:
        results = list(
            pool.map(lambda u: (u, probe_http(u, timeout=timeout)), new_urls)
        )

    for url, result in results:
        endpoint_health.record_probe(result, capability=capability)
        if result.reachable:
            continue
        if url in existing:
            # Existing-but-now-broken — registry knows; save still proceeds.
            continue
        # Newly-added AND unreachable → refuse the save.
        raise EndpointUnreachable(
            url,
            underlying=Exception(
                result.error_message or result.error_class or "probe failed"
            ),
            capability=capability,
        )
