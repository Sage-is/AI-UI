"""SprigSupervisor — minimal runtime grafting for the first-graft walking skeleton.

Mirrors the BridgeManager lifecycle shape (``start`` / ``shutdown`` + a registry
dict) but manages OS child processes. It grafts exactly one capability — a local
embedding mock — by spawning it as a loopback subprocess and polling ``/health``
until ready.

Intentionally minimal (Phase 8.0 / Decision #19). DEFERRED until graft #2:
``oras`` pull / sigstore verify, restart-with-backoff + health-watch loop,
``state.json`` crash-recovery, prune / topgraft / revive, multi-entry catalog,
multi-worker support, prior-config snapshot/restore, structured log capture.
"""

from __future__ import annotations

import asyncio
import logging
import socket
import sys
import time

import requests

from sage_is_ai.sprigs.models import SprigHandle

log = logging.getLogger(__name__)

# Default-model dimensionality (all-MiniLM-L6-v2 -> 384). See mock_embedding_server.
_MOCK_EMBEDDING_DIM = 384

_HEALTH_TIMEOUT_S = 15.0
_SHUTDOWN_GRACE_S = 5.0


def _reserve_loopback_port() -> int:
    """Ask the kernel for a free ephemeral loopback port, then release it.

    Bind-to-0 then close. There is a tiny TOCTOU window between release and the
    child re-binding the same port; acceptable for a dev-box skeleton.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
    finally:
        s.close()


class SprigSupervisor:
    """Spawns and supervises grafted Sprig™ child processes."""

    # The catalog IS the allowlist. Only these (name -> spec) may be grafted.
    CATALOG: dict[str, dict] = {
        "mock-embedding": {
            "capability": "embedding",
            "model": "mock-embedding",
            "dim": _MOCK_EMBEDDING_DIM,
        },
    }

    def __init__(self, app):
        self.app = app
        self._sprigs: dict[str, SprigHandle] = {}

    async def start(self) -> None:
        # No autostart in the skeleton; the supervisor acts only on explicit graft.
        log.info("SprigSupervisor ready (no sprigs auto-grafted)")

    async def shutdown(self) -> None:
        for name in list(self._sprigs):
            await self._terminate(name)

    def handles(self) -> dict[str, dict]:
        """Serializable view of currently-grafted Sprigs™ for the catalog API."""
        out: dict[str, dict] = {}
        for name, h in self._sprigs.items():
            alive = h.process is not None and h.process.returncode is None
            out[name] = {
                "name": h.name,
                "capability": h.capability,
                "port": h.port,
                "base_url": h.base_url,
                "model": h.model,
                "pid": h.process.pid if h.process else None,
                "state": "rooted" if alive else "wilted",
            }
        return out

    async def graft(self, name: str, capability: str) -> SprigHandle:
        spec = self.CATALOG.get(name)
        if spec is None or spec["capability"] != capability:
            raise ValueError(
                f"unknown sprig '{name}' or unsupported capability '{capability}'"
            )

        # Idempotency: a live graft of the same name returns the existing handle.
        existing = self._sprigs.get(name)
        if existing and existing.process and existing.process.returncode is None:
            log.info("sprig '%s' already grafted on port %s", name, existing.port)
            return existing

        port = _reserve_loopback_port()
        handle = SprigHandle(
            name=name,
            capability=capability,
            port=port,
            base_url=f"http://127.0.0.1:{port}/v1",
            health_url=f"http://127.0.0.1:{port}/health",
            model=spec["model"],
            process=await asyncio.create_subprocess_exec(
                sys.executable,
                "-m",
                "sage_is_ai.sprigs.mock_embedding_server",
                "--port",
                str(port),
                "--dim",
                str(spec["dim"]),
                # DEVNULL (not PIPE): we don't capture logs yet, and an unread PIPE
                # would deadlock the child once its stdout buffer fills.
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
                # Own session so a foreground SIGINT to the Rootstock™ process
                # group doesn't double-signal the child; lifespan owns teardown.
                start_new_session=True,
            ),
        )
        self._sprigs[name] = handle

        try:
            await self._wait_until_healthy(handle)
        except Exception:
            await self._terminate(name)
            raise

        log.info(
            "grafted sprig '%s' (pid %s) on %s", name, handle.process.pid, handle.base_url
        )
        return handle

    async def _wait_until_healthy(
        self, handle: SprigHandle, timeout: float = _HEALTH_TIMEOUT_S
    ) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            proc = handle.process
            if proc is not None and proc.returncode is not None:
                raise RuntimeError(
                    f"sprig '{handle.name}' exited on boot (rc={proc.returncode})"
                )
            try:
                resp = await asyncio.to_thread(
                    requests.get, handle.health_url, timeout=1.0
                )
                if resp.status_code == 200:
                    return
            except requests.RequestException:
                pass
            await asyncio.sleep(0.25)
        raise TimeoutError(
            f"sprig '{handle.name}' not healthy within {timeout:.0f}s"
        )

    async def _terminate(self, name: str) -> None:
        handle = self._sprigs.pop(name, None)
        if handle is None or handle.process is None:
            return
        proc = handle.process
        if proc.returncode is not None:
            return
        try:
            proc.terminate()  # SIGTERM
            try:
                await asyncio.wait_for(proc.wait(), timeout=_SHUTDOWN_GRACE_S)
            except asyncio.TimeoutError:
                proc.kill()  # SIGKILL fallback
                await proc.wait()
        except ProcessLookupError:
            pass
        log.info("pruned sprig '%s'", name)
