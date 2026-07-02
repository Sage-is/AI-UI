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
import os
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
        "minilm-onnx-inhoused": {
            "capability": "embedding",
            "server": "embedding",
            "backend": "onnx",
            "model": "all-MiniLM-L6-v2",
            "dim": 384,  # same width as mock + graft-2 ONNX -> no reindex
            "ready_timeout_s": 60.0,  # weights pre-seeded by oras pull, no S3 download
            # --- graft #3: OCI-artifact offline delivery (in-housed weights) ---
            "delivery": "oci-artifact",
            "repo": "local-registry:5000/sprig-embedding-minilm-onnx",
            "tag": "v1",
            "insecure": True,  # localhost dev registry over HTTP. PROD: ghcr.io/sage-is + drop.
            "binary_sha256": "14374a654078dea0b624b6cee6cadcefbcd714ef5964ffee1989fec578e6121d",
        },
        "multilingual-e5-large": {
            "capability": "embedding",
            "server": "embedding",
            # onnx-transformer: onnxruntime + tokenizers, NO torch. Slim rootstock.
            "backend": "onnx-transformer",
            "pooling": "mean",  # e5 uses mean pooling
            "model": "intfloat/multilingual-e5-large",
            "dim": 1024,
            "ready_timeout_s": 120.0,  # weights pre-seeded by oras pull, no HF download
            "delivery": "oci-artifact",
            "seed": "model-dir",
            "repo": "local-registry:5000/sprig-embedding-e5-large-onnx",
            "tag": "v1",
            "insecure": True,
            "binary_sha256": "8fbe2a95fd729deb50a6fa9df7e7d49c78199ca3fa506c08b4f97161fca08a17",
        },
        "bge-large-en-v1.5": {
            "capability": "embedding",
            "server": "embedding",
            "backend": "onnx-transformer",
            "pooling": "cls",  # bge uses CLS pooling
            "model": "BAAI/bge-large-en-v1.5",
            "dim": 1024,
            "ready_timeout_s": 120.0,
            "delivery": "oci-artifact",
            "seed": "model-dir",
            "repo": "local-registry:5000/sprig-embedding-bge-onnx",
            "tag": "v1",
            "insecure": True,
            "binary_sha256": "df16cc5d077c5f9756b130e435e26629beea7bf07ea00c7551e2fc96f7f9a410",
        },
        # "deliver" sprig — NOT a running server. Pulls the Svelte dev/build
        # toolchain (node_modules, ~1.1GB) from OUR registry and extracts it into
        # /app on demand, so it lives OUTSIDE the base rootstock image (dev mode
        # grafts it; production never carries it). Decision #14 dev-svelte.
        "dev-svelte": {
            "capability": "dev",
            "server": "deliver",
            "model": "svelte dev/build toolchain (node_modules + bun)",
            "dim": 0,
            "delivery": "oci-artifact",
            "seed": "app-dir",
            "target": "/app",
            "sentinel": "node_modules",
            "ready_timeout_s": 120.0,
            "repo": "local-registry:5000/sprig-dev-svelte",
            "tag": "v2",
            "insecure": True,
            "binary_sha256": "c801539acd1373c2498c8f170eb4cba2643a0d48a15497d3446aafdbb418cb38",
        },
        # Vector DB substrate — the chromadb closure (~170MB: chromadb, onnxruntime,
        # kubernetes, grpc, hnswlib, posthog) extracted straight into site-packages.
        # factory.py boots with VECTOR_DB_CLIENT=None when absent; restart after
        # delivery to activate (import bindings are frozen at boot).
        "vector-chroma": {
            "capability": "vector",
            "server": "deliver",
            "model": "chromadb vector DB + closure (site-packages overlay)",
            "dim": 0,
            "delivery": "oci-artifact",
            "seed": "app-dir",
            "target": "/usr/local/lib/python3.11/site-packages",
            "sentinel": "chromadb",
            "post_graft_note": "Vector DB delivered. Restart the Rootstock™ to activate document search.",
            "ready_timeout_s": 180.0,
            "repo": "local-registry:5000/sprig-vector-chroma",
            "tag": "v1",
            "insecure": True,
            "binary_sha256": "4613edba24d576055b0ccfbe40955d3de90c2718e9fce2f20561fc9e7da53d6f",
        },
        # Static ffmpeg + ffprobe (johnvansickle 7.0.2) — audio transcode for
        # pydub/whisper paths. Replaces the ~110MB apt ffmpeg codec stack.
        "media-ffmpeg": {
            "capability": "media",
            "server": "deliver",
            "model": "static ffmpeg + ffprobe 7.0.2",
            "dim": 0,
            "delivery": "oci-artifact",
            "seed": "app-dir",
            "target": "/usr/local/bin",
            "sentinel": "ffmpeg",
            "ready_timeout_s": 120.0,
            "repo": "local-registry:5000/sprig-media-ffmpeg",
            "tag": "v1",
            "insecure": True,
            "binary_sha256": "cfe4304c74ebcc04a8ee221968fdc783f46addbf5646c14971885bbb0e613bb2",
        },
        # rclone (static Go binary) — cloud backup/restore. restore_backup_start.sh
        # skips backups gracefully when absent.
        "backup-rclone": {
            "capability": "backup",
            "server": "deliver",
            "model": "rclone (cloud backup)",
            "dim": 0,
            "delivery": "oci-artifact",
            "seed": "app-dir",
            "target": "/usr/local/bin",
            "sentinel": "rclone",
            "ready_timeout_s": 120.0,
            "repo": "local-registry:5000/sprig-backup-rclone",
            "tag": "v1",
            "insecure": True,
            "binary_sha256": "df0f3c87f32c5ae4e9c71cb976bc25db870c53c8b5c5491d8cba8844a216a61f",
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
                "state": h.state or ("rooted" if alive else "wilted"),
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
            args = [
                "sage_is_ai.sprigs.embedding_server",
                "--port", "{port}",
                "--backend", backend,
                "--model", spec.get("model", ""),
                "--dim", dim,
            ]
            if backend == "onnx-transformer":
                # onnxruntime + tokenizers, no torch; model.onnx comes from the
                # oci-artifact (SPRIG_MODEL_DIR, set in graft()). Pooling per model.
                args += ["--pooling", spec.get("pooling", "mean")]
            return (args, ready_timeout)

        raise ValueError(f"unknown sprig server '{server}' for '{name}'")

    async def _deliver(self, name: str, spec: dict) -> SprigHandle:
        """A 'deliver' sprig has no server: pull + verify + extract the artifact
        into its target (e.g. the dev/build toolchain into /app). Idempotent via
        the artifact sentinel. Returns a handle in state 'delivered'."""
        from sage_is_ai.env import DATA_DIR
        from sage_is_ai.sprigs import artifact

        try:
            target = await artifact.ensure(
                spec=spec, data_dir=DATA_DIR, catalog_name=name
            )
        except artifact.ArtifactError as exc:
            raise ValueError(f"delivery failed for '{name}': {exc}") from exc

        handle = SprigHandle(
            name=name,
            capability=spec["capability"],
            port=0,
            base_url="",
            health_url="",
            model=spec.get("model", ""),
            process=None,
            state="delivered",
        )
        self._sprigs[name] = handle
        log.info("delivered sprig '%s' -> %s", name, target)
        return handle

    async def graft(self, name: str, capability: str) -> SprigHandle:
        spec = self.CATALOG.get(name)
        if spec is None or spec["capability"] != capability:
            raise ValueError(
                f"unknown sprig '{name}' or unsupported capability '{capability}'"
            )

        # "deliver" sprigs (dev/build toolchain, assets) have no server — just
        # pull + extract the artifact into its target.
        if spec.get("server") == "deliver":
            return await self._deliver(name, spec)

        # Idempotency: a live graft of the same name returns the existing handle.
        existing = self._sprigs.get(name)
        if existing and existing.process and existing.process.returncode is None:
            log.info("sprig '%s' already grafted on port %s", name, existing.port)
            return existing

        # Pick the Sprig™ module + argv from the catalog 'server' selector.
        argv, ready_timeout = self._build_argv(name, spec)

        # GRAFT #3: OCI-artifact cultivars pull + sha256-verify + extract + seed the
        # offline weight cache BEFORE we disturb anything, so a failed pull leaves the
        # current cultivar intact. The seeded cache makes the ONNX server load with
        # zero chroma-S3 / HuggingFace egress.
        child_env = None
        if spec.get("delivery") == "oci-artifact":
            from sage_is_ai.env import DATA_DIR
            from sage_is_ai.sprigs import artifact

            try:
                served = await artifact.ensure(
                    spec=spec, data_dir=DATA_DIR, catalog_name=name
                )
            except artifact.ArtifactError as exc:
                raise ValueError(f"artifact delivery failed for '{name}': {exc}") from exc

            child_env = {
                **os.environ,
                "OFFLINE_MODE": "true",
                "HF_HUB_OFFLINE": "1",
                "TRANSFORMERS_OFFLINE": "1",
            }
            if spec.get("backend") == "onnx-transformer":
                # served == the extracted model dir (model.onnx + tokenizer.json)
                child_env["SPRIG_MODEL_DIR"] = served
            else:
                # served == the seeded chroma cache dir (MiniLM DefaultEmbeddingFunction)
                child_env["SPRIG_EMBEDDING_CACHE_DIR"] = served

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
                # env=None for non-oci cultivars => inherit parent env (unchanged);
                # oci-artifact cultivars get the offline-forcing env built above.
                env=child_env,
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

    async def prune(self, name: str) -> bool:
        """Terminate + remove a grafted Sprig™. Returns True if it was present.

        Idempotent. Revive is not a separate supervisor op — re-grafting the same
        name (graft()) re-roots a wilted/pruned cultivar through the normal path.
        """
        present = name in self._sprigs
        await self._terminate(name)
        return present

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
