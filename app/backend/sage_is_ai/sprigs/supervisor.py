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
    #   server: "mock"      -> mock_embedding_server (deterministic, no model)
    #           "embedding" -> embedding_server (real model; pick backend below)
    #   backend (embedding only): "onnx" (chromadb ONNX MiniLM, no torch) |
    #           "sentence-transformers" (needs torch — AI Engine install or graft #3)
    #   model:  mock tag, or the model id passed to the real server
    #   dim:    declared embedding width (the vector store binds this per collection)
    #   ready_timeout_s: per-cultivar health deadline (real models download weights)
    CATALOG: dict[str, dict] = {
        "mock-embedding": {
            "capability": "embedding",
            "server": "mock",
            "model": "mock-embedding",
            "dim": _MOCK_EMBEDDING_DIM,
            "ready_timeout_s": 15.0,
        },
        "all-MiniLM-onnx": {
            "capability": "embedding",
            "server": "embedding",
            "backend": "onnx",
            "model": "all-MiniLM-L6-v2",
            "dim": 384,  # same width as the mock -> no collection migration
            "ready_timeout_s": 120.0,  # first graft pulls ~80MB ONNX weights
        },
        "multilingual-e5-large": {
            "capability": "embedding",
            "server": "embedding",
            "backend": "sentence-transformers",
            "model": "intfloat/multilingual-e5-large",
            "dim": 1024,  # needs torch (AI Engine install / graft #3); ~2.2GB cold pull
            "ready_timeout_s": 300.0,
        },
        "bge-large-en-v1.5": {
            "capability": "embedding",
            "server": "embedding",
            "backend": "sentence-transformers",
            "model": "BAAI/bge-large-en-v1.5",
            "dim": 1024,  # needs torch; ~1.3GB cold pull
            "ready_timeout_s": 300.0,
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

    def _build_argv(self, name: str, spec: dict) -> tuple[list[str], float]:
        """Resolve the child module + args from the catalog 'server' selector.

        Returns (argv_after_`python -m`, ready_timeout_s). argv may contain the
        literal token "{port}", which graft() substitutes once a port is reserved.
        Raises ValueError (surfaced as a clear graft failure) when a cultivar's
        runtime deps are missing on this Rootstock™.
        """
        server = spec.get("server", "mock")
        dim = str(spec["dim"])
        ready_timeout = float(spec.get("ready_timeout_s", _HEALTH_TIMEOUT_S))

        if server == "mock":
            return (
                ["sage_is_ai.sprigs.mock_embedding_server", "--port", "{port}", "--dim", dim],
                ready_timeout,
            )

        if server == "embedding":
            backend = spec.get("backend", "onnx")
            if backend == "sentence-transformers":
                # Fail fast + clearly on a slim Rootstock™ rather than spawning a
                # child that dies on `import torch` (whose reason is in DEVNULL'd stderr).
                import importlib.util

                missing = [
                    m
                    for m in ("torch", "sentence_transformers")
                    if importlib.util.find_spec(m) is None
                ]
                if missing:
                    raise ValueError(
                        f"cultivar '{name}' needs {', '.join(missing)}, not installed in "
                        f"this Rootstock™. Install the AI Engine, or graft a bundled "
                        f"Sprig™ (graft #3)."
                    )
            return (
                [
                    "sage_is_ai.sprigs.embedding_server",
                    "--port", "{port}",
                    "--backend", backend,
                    "--model", spec.get("model", ""),
                    "--dim", dim,
                ],
                ready_timeout,
            )

        raise ValueError(f"unknown sprig server '{server}' for '{name}'")

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

        # Pick the Sprig™ module + argv from the catalog 'server' selector.
        argv, ready_timeout = self._build_argv(name, spec)

        # TOP-GRAFT: the Rootstock™ has a single RAG_EMBEDDING_* config + one
        # EMBEDDING_FUNCTION, so only one embedding cultivar may be rooted at a
        # time. Terminate any OTHER rooted embedding sprig BEFORE spawning the new
        # one — frees its port deterministically, no process/port leak. If the new
        # graft then fails its health check, the except below prunes the new one,
        # leaving zero embedding sprigs rooted (the honest state).
        if capability == "embedding":
            for other in [
                n
                for n, h in list(self._sprigs.items())
                if n != name and h.capability == "embedding"
            ]:
                log.info("top-grafting: pruning prior embedding sprig '%s'", other)
                await self._terminate(other)

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
                *[a.format(port=port) for a in argv],
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
            await self._wait_until_healthy(handle, timeout=ready_timeout)
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
