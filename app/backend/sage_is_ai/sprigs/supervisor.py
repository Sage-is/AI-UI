"""SprigSupervisor — runtime grafting of Rootstock™ capabilities.

Mirrors the BridgeManager lifecycle shape (``start`` / ``shutdown`` + a registry
dict) but manages OS child processes and on-disk overlays. Grafts a capability by
either (a) spawning a loopback subprocess (embedding cultivars: mock, ONNX,
onnx-transformer, or a static llama-server binary) and polling ``/health`` until
ready, or (b) pulling + sha256-verifying + extracting an OCI artifact into a target
("deliver" sprigs: vector-chroma, rag-loaders, export-document, code-pyodide,
browser-ml, media-ffmpeg, backup-rclone, dev-svelte).

SHIPPED: the 15-entry CATALOG (11 capabilities, ALL zero-egress at graft time —
the last live-pull entry, all-MiniLM-onnx, was retired 2026-07-05), ``oras``
OCI-artifact delivery (see artifact.py), prune, top-graft (one cultivar rooted
per server capability: embedding/reranker/stt), and durable grafts —
start() reconciles from a volume-resident ``state.json`` so a graft survives a
Rootstock™ restart, re-extracting deliver overlays from the volume-cached tar and
re-spawning embedding cultivars offline. One worker owns the reconcile (flock).
Revive is not a separate op — re-grafting a wilted name re-roots it through graft().

DEFERRED: sigstore/cosign signing (sha256 pin is the current trust anchor),
restart-with-backoff health-watch, full multi-worker support (one worker spawns
children; the per-worker catalog view can still differ), structured child-log
capture (server children are DEVNULL'd, so a failed graft's stderr is not surfaced).
"""

from __future__ import annotations

import asyncio
import fcntl
import json
import logging
import os
import socket
import sys
import time
from pathlib import Path

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
        # all-MiniLM-onnx (live chroma-S3/HF pull) was RETIRED 2026-07-05: it
        # spawned the byte-identical child to minilm-onnx-inhoused below, and
        # after any inhoused graft it silently served from the seeded cache
        # anyway. The catalog is the allowlist — keeping it kept an
        # admin-clickable ~80MB third-party egress on a zero-egress deployment.
        "minilm-onnx-inhoused": {
            "capability": "embedding",
            "server": "embedding",
            "backend": "onnx",
            "model": "all-MiniLM-L6-v2",
            "dim": 384,  # same width as the mock -> no reindex on swap
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
            "model": "chromadb vector DB + ML runtime (site-packages overlay)",
            "dim": 0,
            "delivery": "oci-artifact",
            "seed": "app-dir",
            "target": "/usr/local/lib/python3.11/site-packages",
            "sentinel": "chromadb",
            "post_graft_note": "Vector DB delivered. Restart the Rootstock™ to activate document search.",
            "ready_timeout_s": 180.0,
            "repo": "local-registry:5000/sprig-vector-chroma",
            # v2 (8.I.2): + numpy, tokenizers, huggingface_hub closure — these
            # left the base rootstock; the onnx embedding cultivars pre-check
            # for them and point here.
            "tag": "v2",
            "insecure": True,
            "binary_sha256": "382b37fd4e0bf4131a26163db075eb1e842f87443f0c9bd200cab2727b552553",
        },
        # GGUF cultivar (8.I.3, gates green 2026-07-02): e5-large Q8_0 served by
        # a static-PIE musl llama-server (llama.cpp b9859, built in-house) — ONE
        # binary + ONE model file, zero Python deps in the child, any libc.
        # Gate A: cos_min 0.99913 vs sentence-transformers, 0 tokenizer
        # mismatches (sentencepiece exact), 5/5 retrieval recall. Gate B: 0.85x
        # onnx CPU throughput. minilm/bge GGUF are HELD — llama.cpp's WPM
        # tokenizer diverges from HF on Hangul (22 vs 52 tokens); their onnx
        # cultivars remain canonical. Artifact is arm64; amd64 variety = 8.J.
        "e5-large-gguf": {
            "capability": "embedding",
            "server": "llama-binary",
            "model": "intfloat/multilingual-e5-large (GGUF Q8_0)",
            "dim": 1024,
            "gguf": "model.gguf",
            "delivery": "oci-artifact",
            "seed": "model-dir",
            "sentinel": "model.gguf",
            "ready_timeout_s": 240.0,
            "repo": "local-registry:5000/sprig-embedding-e5-gguf",
            "tag": "v1",
            "insecure": True,
            "binary_sha256": "16f01a8d37e0e0ced47d0faef2b64de69d072f81399ac0c8b7065d72c459cdec",
        },
        # Reranker cultivar — cross-encoder relevance scoring for hybrid search.
        # Same static-PIE llama-server (b9859) as e5-large-gguf, in --rerank
        # mode: /v1/rerank speaks the Jina/Cohere contract the existing
        # ExternalReranker client already parses (retrieval/models/external.py).
        # ONE binary + ONE model file, zero Python deps in the child. -ub/-c
        # 2048: each (query, doc) pair must fit one ubatch (non-causal encoder);
        # default CHUNK_SIZE chunks fit comfortably.
        "bge-reranker-v2-m3-gguf": {
            "capability": "reranker",
            "server": "llama-binary",
            "model": "BAAI/bge-reranker-v2-m3 (GGUF Q8_0)",
            "dim": 0,  # not an embedding; no collection width binding
            "gguf": "model.gguf",
            "server_args": ["--rerank", "-ub", "2048", "-c", "2048"],
            "delivery": "oci-artifact",
            "seed": "model-dir",
            "sentinel": "model.gguf",
            "ready_timeout_s": 240.0,
            "repo": "local-registry:5000/sprig-reranker-bge-gguf",
            "tag": "v1",
            "insecure": True,
            "binary_sha256": "7c84c1d90f3eb217bff7f414569dafcd8b129731d023d308559f115f6143056f",
        },
        # STT cultivar — static whisper.cpp whisper-server + ggml base
        # (multilingual, q8_0). Serves /v1/audio/transcriptions, which is
        # EXACTLY where audio.py's STT_ENGINE="openai" client already POSTs —
        # zero client changes. Kills the last local-STT HuggingFace pull.
        "whisper-base-ggml": {
            "capability": "stt",
            "server": "whisper-binary",
            "model": "whisper base multilingual (ggml q8_0)",
            "dim": 0,
            "ggml": "model.bin",
            "delivery": "oci-artifact",
            "seed": "model-dir",
            "sentinel": "model.bin",
            "ready_timeout_s": 120.0,
            "post_graft_note": (
                "Local speech-to-text active. For browser voice notes "
                "(webm/opus), also graft media-ffmpeg."
            ),
            "repo": "local-registry:5000/sprig-stt-whisper-base",
            "tag": "v1",
            "insecure": True,
            "binary_sha256": "5d570534a7f4524759ef1c9e4fa0fc5ea30652c0c7bd9008c732716582ebc641",
        },
        # RAG engines — langchain + langchain-community + numpy + format-loader
        # deps (pypdf, docx2txt, rank_bm25) as a site-packages overlay. The
        # overlay dir is on sys.path from boot, so document chunking/loading and
        # hybrid search work immediately after graft; ONLY web-page loading
        # needs a restart (web/utils.py subclasses loader bases at import).
        "rag-loaders": {
            "capability": "rag",
            "server": "deliver",
            "model": "langchain RAG engines + document loaders (overlay)",
            "dim": 0,
            "delivery": "oci-artifact",
            "seed": "app-dir",
            "target": "/usr/local/lib/python3.11/site-packages",
            "sentinel": "langchain",
            "post_graft_note": "Document processing active. Web-page loading activates after a restart.",
            "ready_timeout_s": 180.0,
            "repo": "local-registry:5000/sprig-rag-loaders",
            "tag": "v1",
            "insecure": True,
            "binary_sha256": "f207537072f6c055fe94cef57c27bef8213199770290708e8871ce132cd96c5d",
        },
        # PDF chat export — fpdf2 + fontTools + pillow into the overlay dir plus
        # the CJK Noto fonts into /app/static/fonts (frontend pdf-style.css uses
        # them too). Root-anchored tar; no restart needed (fpdf import is lazy).
        "export-document": {
            "capability": "export",
            "server": "deliver",
            "model": "PDF export (fpdf2 + CJK fonts)",
            "dim": 0,
            "delivery": "oci-artifact",
            "seed": "app-dir",
            "target": "/",
            "sentinel": "usr/local/lib/python3.11/site-packages/fpdf",
            "ready_timeout_s": 180.0,
            "repo": "local-registry:5000/sprig-export-document",
            "tag": "v1",
            "insecure": True,
            "binary_sha256": "5139f34d07ccbff59ae29fd041c2f7492cef28cee74aa08b58bf4523321235d8",
        },
        # Pyodide (browser code interpreter) — served from /app/build/pyodide
        # (workers load indexURL '/pyodide/'). Serves immediately after graft.
        "code-pyodide": {
            "capability": "code",
            "server": "deliver",
            "model": "pyodide browser code interpreter",
            "dim": 0,
            "delivery": "oci-artifact",
            "seed": "app-dir",
            "target": "/app/build/pyodide",
            "sentinel": "pyodide.js",
            "ready_timeout_s": 180.0,
            "repo": "local-registry:5000/sprig-code-pyodide",
            "tag": "v1",
            "insecure": True,
            "binary_sha256": "d7683230a86a8874abce78889f06acfb40d3f1f545f4d85d089e862a88e9bf00",
        },
        # onnxruntime-web wasm — in-browser ML (Evaluations leaderboard, kokoro
        # TTS worker); both consumers set wasmPaths='/wasm/'. Serves immediately.
        "browser-ml": {
            "capability": "browser-ml",
            "server": "deliver",
            "model": "onnxruntime-web wasm (in-browser ML)",
            "dim": 0,
            "delivery": "oci-artifact",
            "seed": "app-dir",
            "target": "/app/build/wasm",
            "sentinel": "ort-wasm-simd-threaded.jsep.wasm",
            "ready_timeout_s": 120.0,
            "repo": "local-registry:5000/sprig-browser-ml",
            "tag": "v1",
            "insecure": True,
            "binary_sha256": "b8b4617991ee2e1655dd9bee6a48f2e63d64ccacd578fe3301f3603a507e8b88",
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
        # Single-owner reconcile lock fd, held for the process lifetime (multi-worker
        # guard). None until start() acquires it; released in shutdown().
        self._reconcile_lock_fd: int | None = None
        # Suppresses state.json writes while reconcile is re-grafting, so a sprig
        # that fails to come up this boot stays in the desired-state for next boot.
        self._reconciling = False

    async def start(self) -> None:
        """Restore grafts recorded on the data volume (state.json) so a grafted
        capability survives a Rootstock™ restart. Exactly one worker reconciles
        (spawns children); other workers skip via the non-blocking lock."""
        workers = os.getenv("UVICORN_WORKERS", "1")
        if not self._acquire_reconcile_lock():
            log.info(
                "another worker owns Sprig™ reconcile (UVICORN_WORKERS=%s); "
                "this worker will not spawn children",
                workers,
            )
            return
        if workers not in ("", "1"):
            log.warning(
                "UVICORN_WORKERS=%s: Sprig™ child processes are spawned by ONE "
                "worker; the grafted view (GET /catalog) may differ per worker. "
                "Single-owner reconcile keeps the capability itself correct.",
                workers,
            )
        await self._reconcile()
        log.info("SprigSupervisor ready")

    async def shutdown(self) -> None:
        for name in list(self._sprigs):
            await self._terminate(name)
        if self._reconcile_lock_fd is not None:
            try:
                os.close(self._reconcile_lock_fd)  # releases the flock
            except OSError:
                pass
            self._reconcile_lock_fd = None

    # --- durable graft state (survives a Rootstock™ restart) -------------------

    def _state_path(self) -> Path:
        """state.json lives on the DATA volume so it survives container recreation."""
        from sage_is_ai.env import DATA_DIR

        return Path(DATA_DIR) / "sage-is" / "sprigs" / "state.json"

    def _read_state(self) -> list[dict]:
        path = self._state_path()
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text())
            return data.get("grafted", []) if isinstance(data, dict) else []
        except (OSError, ValueError) as exc:
            log.warning("could not read sprig state.json: %s", exc)
            return []

    def _persist_state(self) -> None:
        """Write the durable graft list (name/capability/tag/kind — NOT ephemeral
        ports or pids) to the volume. No-op during reconcile so a boot that fails to
        restore one sprig doesn't drop it from the desired-state."""
        if self._reconciling:
            return
        entries = [
            {
                "name": name,
                "capability": h.capability,
                "tag": self.CATALOG.get(name, {}).get("tag"),
                "kind": (
                    "deliver"
                    if self.CATALOG.get(name, {}).get("server") == "deliver"
                    else "server"
                ),
            }
            for name, h in self._sprigs.items()
        ]
        path = self._state_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps({"grafted": entries}, indent=2))
            tmp.replace(path)  # atomic
        except OSError as exc:
            log.warning("could not persist sprig state.json: %s", exc)

    def _acquire_reconcile_lock(self) -> bool:
        """Exclusive, non-blocking lock so exactly ONE worker reconciles/spawns.
        Held for the process lifetime (released in shutdown). Returns True if this
        worker owns reconcile; False if another worker holds it or locking failed."""
        lock_path = self._state_path().parent / ".reconcile.lock"
        try:
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o644)
        except OSError as exc:
            log.warning("could not open Sprig™ reconcile lock (%s); skipping restore", exc)
            return False
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, BlockingIOError):
            os.close(fd)
            return False
        self._reconcile_lock_fd = fd
        return True

    async def _reconcile(self) -> None:
        """Re-graft everything state.json says should be grafted, from the volume
        (offline — cached tar / volume-resident weights). Best-effort per entry."""
        entries = self._read_state()
        if not entries:
            return
        log.info("reconciling %d grafted Sprig(s)™ from state.json", len(entries))
        self._reconciling = True
        try:
            for entry in entries:
                name = entry.get("name")
                cap = entry.get("capability")
                if not name:
                    continue
                if name not in self.CATALOG:
                    # Image upgrade retired this entry. The capability's config
                    # was already backstop-reset at import; tell the operator
                    # WHY it came back un-grafted instead of skipping silently.
                    log.warning(
                        "state.json lists Sprig™ '%s' (%s) which this image's "
                        "catalog no longer carries — skipping. Graft a current "
                        "%s cultivar from Admin → Sprigs.",
                        name, cap, cap,
                    )
                    continue
                try:
                    handle = await self.graft(name, cap)
                    # Server capabilities each own a config slot that must be
                    # re-pointed at the FRESH loopback port after re-spawn.
                    if handle.process is not None:
                        if cap == "embedding":
                            from sage_is_ai.sprigs.embedding_dispatch import (
                                point_embedding_at,
                            )

                            point_embedding_at(self.app, handle)
                        elif cap == "reranker":
                            from sage_is_ai.sprigs.reranker_dispatch import (
                                point_reranker_at,
                            )

                            point_reranker_at(self.app, handle)
                        elif cap == "stt":
                            from sage_is_ai.sprigs.stt_dispatch import (
                                point_stt_at,
                            )

                            point_stt_at(self.app, handle)
                    log.info("reconciled Sprig™ '%s'", name)
                except Exception as exc:  # noqa: BLE001 — best-effort restore
                    log.warning("failed to reconcile Sprig™ '%s': %s", name, exc)
        finally:
            self._reconciling = False

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

            # The find_spec pre-checks below run in THIS (parent) process, whose
            # import-system directory listings were cached at boot — BEFORE a
            # vector-chroma delivery extracted its overlay into site-packages.
            # Reproducible tars carry a fixed mtime, so the stale FileFinder cache
            # never notices the new packages (the 8.I.2 trap; every retry-import
            # helper already invalidates). Without this, "graft vector-chroma →
            # graft an onnx cultivar" falsely fails until a restart, even though
            # the cultivar CHILD is a fresh python that imports the overlay fine.
            import importlib

            importlib.invalidate_caches()

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
            if backend in ("onnx", "onnx-transformer"):
                # 8.I.2: numpy/tokenizers/onnxruntime left the base rootstock —
                # they ride the vector-chroma Sprig™ overlay. Fail fast with the
                # fix instead of spawning a child that dies on import.
                import importlib.util

                needed = (
                    ("chromadb", "onnxruntime", "numpy")
                    if backend == "onnx"
                    else ("onnxruntime", "tokenizers", "numpy")
                )
                missing = [
                    m for m in needed if importlib.util.find_spec(m) is None
                ]
                if missing:
                    # No restart needed for THIS retry — invalidate_caches above
                    # makes the overlay visible as soon as vector-chroma delivers.
                    # (Document search / the vector DB client still needs its
                    # restart; that contract is vector-chroma's post_graft_note.)
                    raise ValueError(
                        f"cultivar '{name}' needs {', '.join(missing)} — the ML "
                        f"runtime rides with the vector-chroma Sprig™. Graft "
                        f"vector-chroma first, then retry."
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

        if server == "llama-binary":
            # GGUF cultivar (8.I.3, Gate A+B passed): ONE static-PIE llama-server
            # binary + ONE model file from the artifact — zero Python deps in the
            # child, runs on any libc. /health gates readiness (503 while the
            # model loads). "{artifact_dir}" is substituted after artifact.ensure()
            # in graft(). Mode/tuning args come from the catalog's server_args so
            # one binary serves embedding (--embeddings) AND reranking (--rerank);
            # the default keeps e5-large-gguf's argv byte-identical.
            return (
                [
                    "{artifact_dir}/llama-server",
                    "-m", "{artifact_dir}/" + spec.get("gguf", "model.gguf"),
                    "--host", "127.0.0.1",
                    "--port", "{port}",
                    *spec.get("server_args", ["--embeddings", "-ub", "512", "-c", "512"]),
                ],
                ready_timeout,
            )

        if server == "whisper-binary":
            # STT cultivar: static whisper.cpp whisper-server + ggml model — the
            # same one-binary-one-model shape as llama-binary. --inference-path
            # makes it serve {base_url}/audio/transcriptions (base_url ends in
            # /v1), which is EXACTLY where audio.py's STT_ENGINE="openai" client
            # already POSTs multipart {file}. /health is 200-when-ready /
            # 503-while-loading, same as llama-server — the poller needs nothing.
            return (
                [
                    "{artifact_dir}/whisper-server",
                    "-m", "{artifact_dir}/" + spec.get("ggml", "model.bin"),
                    "--host", "127.0.0.1",
                    "--port", "{port}",
                    "--inference-path", "/v1/audio/transcriptions",
                    *spec.get("server_args", ["-l", "auto"]),
                ],
                ready_timeout,
            )

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
        self._persist_state()
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
            if spec.get("server") in ("llama-binary", "whisper-binary"):
                # Binary+model cultivar: paths ride in argv, not env.
                argv = [a.replace("{artifact_dir}", served) for a in argv]
            elif spec.get("backend") == "onnx-transformer":
                # served == the extracted model dir (model.onnx + tokenizer.json)
                child_env["SPRIG_MODEL_DIR"] = served
            else:
                # served == the seeded chroma cache dir (MiniLM DefaultEmbeddingFunction)
                child_env["SPRIG_EMBEDDING_CACHE_DIR"] = served

        # TOP-GRAFT: the Rootstock™ holds ONE config slot per server capability
        # (RAG_EMBEDDING_*, RAG_RERANKING_*/RAG_EXTERNAL_RERANKER_*, STT_*), so
        # only one cultivar per capability may be rooted at a time. Terminate any
        # OTHER rooted same-capability sprig BEFORE spawning the new one — frees
        # its port deterministically, no process/port leak. If the new graft then
        # fails its health check, the except below prunes the new one, leaving
        # zero cultivars of that capability rooted (the honest state).
        if capability in ("embedding", "reranker", "stt"):
            for other in [
                n
                for n, h in list(self._sprigs.items())
                if n != name and h.capability == capability
            ]:
                log.info("top-grafting: pruning prior %s sprig '%s'", capability, other)
                await self._terminate(other)

        port = _reserve_loopback_port()
        # Binary sprigs exec the delivered static binary directly; python
        # cultivars run as `python -m <module>` children.
        if spec.get("server") in ("llama-binary", "whisper-binary"):
            exec_argv = [a.format(port=port) for a in argv]
        else:
            exec_argv = [sys.executable, "-m", *[a.format(port=port) for a in argv]]
        handle = SprigHandle(
            name=name,
            capability=capability,
            port=port,
            base_url=f"http://127.0.0.1:{port}/v1",
            health_url=f"http://127.0.0.1:{port}/health",
            model=spec["model"],
            process=await asyncio.create_subprocess_exec(
                *exec_argv,
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

        self._persist_state()
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
        self._persist_state()
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
