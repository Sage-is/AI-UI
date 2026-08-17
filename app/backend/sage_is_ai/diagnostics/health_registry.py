"""EndpointHealth — single source of truth for "is this URL alive."

Every HTTP-backed capability (embeddings, reranker, audio, tika, docling,
playwright, etc.) reports the outcome of each call into this registry. Boot
probes seed it; live request paths refresh it via `record_*` calls or the
`with_endpoint_health` context manager.

The diagnostics page (Phase 3) reads from here. The FastAPI exception handler
that maps EndpointUnreachable -> 503 reads from here for the "fix" hint.

Persistence: a snapshot to data/diagnostics.json survives container restarts
so the page is useful immediately after a fresh boot, before the next request
populates fresh state. Snapshots are best-effort — a write failure is logged
but does not raise.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Optional

from sage_is_ai.diagnostics.exceptions import EndpointUnreachable
from sage_is_ai.diagnostics.probes import ProbeResult

log = logging.getLogger(__name__)


@dataclass
class EndpointRecord:
    url: str
    capability: Optional[str] = None
    last_probed_at: Optional[float] = None
    last_status: Optional[str] = None  # "ok" | "unreachable" | "degraded"
    last_error_class: Optional[str] = None
    last_error_message: Optional[str] = None
    last_status_code: Optional[int] = None
    last_latency_ms: Optional[float] = None
    last_ok_at: Optional[float] = None
    consecutive_failures: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


class EndpointHealth:
    """Thread-safe in-memory registry with best-effort disk snapshot.

    Construct once at app startup; access via the module-level `endpoint_health`
    singleton elsewhere. Tests can instantiate fresh copies.
    """

    # Rate-limit window (seconds) between record_success-triggered snapshot
    # writes. record_success fires on every healthy request — snapshotting
    # on each one would burn disk for no gain. Failures still flush
    # immediately so a 2.3.3 outage isn't lost across a restart.
    _SUCCESS_SNAPSHOT_INTERVAL_S = 30.0

    def __init__(self, snapshot_path: Optional[Path] = None):
        self._lock = threading.RLock()
        self._records: Dict[str, EndpointRecord] = {}
        self._snapshot_path = snapshot_path
        # Tracks when record_success last persisted to disk. Single
        # class-level timestamp; the RLock already serializes access so
        # we don't need per-URL bookkeeping. 0.0 means "never written".
        self._last_persisted_at: float = 0.0
        self._load_snapshot()

    # ---- mutators ----------------------------------------------------------

    def record_probe(
        self, result: ProbeResult, capability: Optional[str] = None
    ) -> None:
        with self._lock:
            rec = self._records.setdefault(result.url, EndpointRecord(url=result.url))
            rec.capability = capability or rec.capability
            rec.last_probed_at = time.time()
            rec.last_status_code = result.status_code
            rec.last_latency_ms = result.latency_ms
            if result.reachable:
                rec.last_status = (
                    "ok" if (result.status_code or 0) < 500 else "degraded"
                )
                rec.last_error_class = None
                rec.last_error_message = None
                if rec.last_status == "ok":
                    rec.last_ok_at = rec.last_probed_at
                    rec.consecutive_failures = 0
                else:
                    rec.consecutive_failures += 1
            else:
                rec.last_status = "unreachable"
                rec.last_error_class = result.error_class
                rec.last_error_message = result.error_message
                rec.consecutive_failures += 1
        # NOTE: do NOT touch self._last_persisted_at here. That timestamp
        # is owned solely by record_success() for its rate-limit decision.
        # If a failure burst kept resetting it, record_success could see a
        # fresh value and skip its periodic flush, losing recovered-endpoint
        # state across a container restart. Failures always flush
        # synchronously below.
        self._save_snapshot()

    def record_failure(
        self,
        url: str,
        exc: BaseException,
        capability: Optional[str] = None,
    ) -> None:
        with self._lock:
            rec = self._records.setdefault(url, EndpointRecord(url=url))
            rec.capability = capability or rec.capability
            rec.last_probed_at = time.time()
            rec.last_status = "unreachable"
            rec.last_error_class = type(exc).__name__
            rec.last_error_message = str(exc)
            rec.consecutive_failures += 1
        # See record_probe for why we don't update _last_persisted_at here.
        self._save_snapshot()

    def record_success(self, url: str, capability: Optional[str] = None) -> None:
        # Phase 3a fix for the Phase 2 oversight: record_success previously
        # never persisted, so a container restart resurrected the last failure
        # state for endpoints that had since healed. We now snapshot, but
        # rate-limit to one write per _SUCCESS_SNAPSHOT_INTERVAL_S because
        # this fires on every healthy request. Failures still flush
        # synchronously via record_probe/record_failure.
        should_persist = False
        with self._lock:
            rec = self._records.setdefault(url, EndpointRecord(url=url))
            rec.capability = capability or rec.capability
            now = time.time()
            rec.last_probed_at = now
            rec.last_ok_at = now
            rec.last_status = "ok"
            rec.last_error_class = None
            rec.last_error_message = None
            rec.consecutive_failures = 0
            if now - self._last_persisted_at >= self._SUCCESS_SNAPSHOT_INTERVAL_S:
                self._last_persisted_at = now
                should_persist = True
        if should_persist:
            self._save_snapshot()

    # ---- readers -----------------------------------------------------------

    def get(self, url: str) -> Optional[EndpointRecord]:
        with self._lock:
            return self._records.get(url)

    def snapshot(self) -> Dict[str, dict]:
        with self._lock:
            return {url: rec.to_dict() for url, rec in self._records.items()}

    # ---- persistence -------------------------------------------------------

    def _save_snapshot(self) -> None:
        if self._snapshot_path is None:
            return
        # Snapshot writes can race when many record_* calls fire concurrently
        # (boot probes run in a thread pool). Hold the lock across the ENTIRE
        # sequence — snapshot() through tmp.replace() — so the bytes on disk
        # always reflect a single coherent moment in _records. RLock allows
        # re-entry from snapshot() inside the same call. mkdir() also goes
        # inside the lock so two concurrent writers can't both lose the
        # directory race; cost is negligible.
        try:
            with self._lock:
                self._snapshot_path.parent.mkdir(parents=True, exist_ok=True)
                payload = self.snapshot()
                tmp = self._snapshot_path.with_suffix(
                    self._snapshot_path.suffix + ".tmp"
                )
                tmp.write_text(json.dumps(payload, indent=2))
                tmp.replace(self._snapshot_path)
        except OSError as e:
            log.warning("EndpointHealth snapshot write failed: %s", e)

    def _load_snapshot(self) -> None:
        if self._snapshot_path is None or not self._snapshot_path.exists():
            return
        try:
            payload = json.loads(self._snapshot_path.read_text())
            with self._lock:
                for url, raw in payload.items():
                    self._records[url] = EndpointRecord(**raw)
        except (OSError, json.JSONDecodeError, TypeError) as e:
            log.warning("EndpointHealth snapshot load failed: %s", e)


def _default_snapshot_path() -> Optional[Path]:
    """Resolve data/diagnostics.json lazily so tests and tools can import
    this module without env.py side effects, while production gets a real
    on-disk snapshot path."""
    try:
        from sage_is_ai.env import DATA_DIR
    except Exception:  # pragma: no cover — env not importable in some tools
        return None
    return Path(DATA_DIR) / "diagnostics.json"


# Module-level singleton. Snapshot path resolves lazily on first import.
endpoint_health = EndpointHealth(snapshot_path=_default_snapshot_path())


# ---- request-path context managers ----------------------------------------


@contextmanager
def with_endpoint_health_sync(url: str, capability: Optional[str] = None):
    """Synchronous wrap for `requests`-based call sites (embeddings, etc.).

    Translates `requests.RequestException` and friends into a structured
    `EndpointUnreachable` while updating the registry. Other exceptions
    pass through unchanged.
    """
    import requests as _requests

    try:
        yield
    except _requests.RequestException as exc:
        endpoint_health.record_failure(url, exc, capability)
        raise EndpointUnreachable(url, underlying=exc, capability=capability) from exc
    else:
        endpoint_health.record_success(url, capability)


@asynccontextmanager
async def with_endpoint_health(url: str, capability: Optional[str] = None):
    """Async wrap for aiohttp-based call sites (routers/openai.py, etc.).

    Translates `aiohttp.ClientConnectorError`, `asyncio.TimeoutError`, and
    `aiohttp.ClientError` into `EndpointUnreachable`. Other exceptions
    pass through unchanged.
    """
    import asyncio

    try:
        import aiohttp
    except ImportError:
        aiohttp = None  # type: ignore[assignment]

    try:
        yield
    except (asyncio.TimeoutError,) as exc:
        endpoint_health.record_failure(url, exc, capability)
        raise EndpointUnreachable(url, underlying=exc, capability=capability) from exc
    except Exception as exc:
        if aiohttp is not None and isinstance(exc, aiohttp.ClientError):
            endpoint_health.record_failure(url, exc, capability)
            raise EndpointUnreachable(
                url, underlying=exc, capability=capability
            ) from exc
        raise
    else:
        endpoint_health.record_success(url, capability)
