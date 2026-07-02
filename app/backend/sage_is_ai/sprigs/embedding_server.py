"""Real embedding Sprig™ — a grafted subprocess that serves a real embedding model.

Two backends, selected by ``--backend``:

  onnx                  -> chromadb's bundled ONNX ``DefaultEmbeddingFunction``
                           (all-MiniLM-L6-v2, 384-dim). ONNX runtime, NO torch —
                           the deps are already in the Rootstock™ image, so this
                           cultivar grafts on a slim box with no extra install.
  sentence-transformers -> ``SentenceTransformer(--model)``. Needs torch +
                           sentence-transformers (runtime-installed by the AI
                           Engine wizard, or bundled into the Sprig™ in graft #3).

Launched by SprigSupervisor:
    python -m sage_is_ai.sprigs.embedding_server --port P --backend onnx --dim 384
    python -m sage_is_ai.sprigs.embedding_server --port P --backend sentence-transformers \\
        --model intfloat/multilingual-e5-large --dim 1024

The OpenAI-compatible surface matches the mock Sprig™:
    GET  /health        -> 200 {"status":"ok",...} ONLY after the model has loaded
                           (503 "loading" during the first-graft weight download)
    POST /v1/embeddings -> OpenAI Embedding response shape

Loading happens in a background thread so uvicorn binds the port immediately and
``/health`` answers 503 while weights download; the supervisor's poller waits this
out within the cultivar's ``ready_timeout_s``. On a load failure the process exits
non-zero so the supervisor's boot-crash check fails the graft fast.

DEFERRED (graft #3 — the north-star "no end-user HuggingFace/pip pulls"):
sigstore-verified oras tar.zst weight+runtime delivery, offline/air-gapped caching,
structured stderr log forwarding. Runtime download is the graft-#2 bridge only.
"""

from __future__ import annotations

import argparse
import logging
import os

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

log = logging.getLogger("sprig.embedding")


class EmbeddingRequest(BaseModel):
    input: list[str] | str
    model: str | None = None


app = FastAPI(title="sprig-embedding")
app.state.ready = False
app.state.embed = None  # callable: list[str] -> list[list[float]]
app.state.label = None  # reported model name
app.state.dim = None


def _build_onnx():
    """chromadb's bundled ONNX all-MiniLM-L6-v2 (384-dim). No torch.

    Graft #3: when SPRIG_EMBEDDING_CACHE_DIR is set, the weights were pre-seeded
    into $HOME/.cache/chroma by the supervisor's artifact.ensure() (OCI-artifact
    delivery). Assert the cache is present so a seeding regression fails the graft
    loudly instead of silently triggering chromadb's S3 download.
    """
    from pathlib import Path

    from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

    if os.environ.get("SPRIG_EMBEDDING_CACHE_DIR"):
        onnx = (
            Path.home()
            / ".cache"
            / "chroma"
            / "onnx_models"
            / "all-MiniLM-L6-v2"
            / "onnx"
            / "model.onnx"
        )
        if not onnx.exists():
            raise RuntimeError(
                f"offline ONNX cache missing at {onnx}; refusing to fall back to "
                f"chroma-S3. artifact.ensure() seeding regressed."
            )

    ef = DefaultEmbeddingFunction()

    def embed(texts: list[str]) -> list[list[float]]:
        # Native python float per element — numpy float32 scalars trip the
        # downstream vector-store / JSON validators (same as the mock + the
        # _embed_chroma path in retrieval/utils.py).
        return [[float(x) for x in row] for row in ef(texts)]

    return embed, "all-MiniLM-L6-v2(onnx)"


def _build_sentence_transformers(model_id: str):
    """Real torch-backed SentenceTransformer. Reuses the Rootstock™ env knobs."""
    from sentence_transformers import SentenceTransformer

    device = os.environ.get("SPRIG_EMBEDDING_DEVICE", "cpu")
    trust = (
        os.environ.get("RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE", "True").lower() == "true"
    )
    model = SentenceTransformer(model_id, device=device, trust_remote_code=trust)

    def embed(texts: list[str]) -> list[list[float]]:
        return [[float(x) for x in row] for row in model.encode(texts).tolist()]

    return embed, model_id


def _build_onnx_transformer(pooling: str, model_id: str = ""):
    """Generic ONNX transformer embedder — onnxruntime + tokenizers, NO torch.

    Loads model.onnx + tokenizer.json from ``$SPRIG_MODEL_DIR`` (seeded by the
    supervisor's artifact.ensure() for oci-artifact delivery), tokenizes with the
    Rust ``tokenizers`` lib, runs onnxruntime, then pools (``mean`` for e5-style,
    ``cls`` for bge-style) and L2-normalizes. This runs 1024-dim cultivars like
    intfloat/multilingual-e5-large and BAAI/bge-large-en-v1.5 on a slim, torch-free
    Rootstock™. token_type_ids are fed only when the ONNX graph declares them.
    """
    import numpy as np
    import onnxruntime as ort
    from tokenizers import Tokenizer

    model_dir = os.environ.get("SPRIG_MODEL_DIR", "")
    onnx_path = os.path.join(model_dir, "model.onnx")
    tok_path = os.path.join(model_dir, "tokenizer.json")
    if not os.path.exists(onnx_path) or not os.path.exists(tok_path):
        raise RuntimeError(
            f"onnx-transformer needs model.onnx + tokenizer.json in SPRIG_MODEL_DIR "
            f"({model_dir!r}); artifact.ensure() seeding regressed."
        )

    tok = Tokenizer.from_file(tok_path)
    tok.enable_padding()
    tok.enable_truncation(max_length=512)
    sess = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])
    input_names = {i.name for i in sess.get_inputs()}

    def embed(texts: list[str]) -> list[list[float]]:
        encs = tok.encode_batch(texts)
        ids = np.array([e.ids for e in encs], dtype=np.int64)
        mask = np.array([e.attention_mask for e in encs], dtype=np.int64)
        feed = {"input_ids": ids, "attention_mask": mask}
        if "token_type_ids" in input_names:
            feed["token_type_ids"] = np.zeros_like(ids)
        last = sess.run(None, feed)[0]  # [batch, seq, hidden]
        if pooling == "cls":
            vecs = last[:, 0]
        else:  # mean pooling over non-pad tokens
            m = mask[..., None].astype(np.float32)
            vecs = (last * m).sum(1) / np.clip(m.sum(1), 1e-9, None)
        vecs = vecs / np.clip(np.linalg.norm(vecs, axis=1, keepdims=True), 1e-12, None)
        return [[float(x) for x in row] for row in vecs]

    label = f"{model_id or os.path.basename(model_dir.rstrip('/')) or 'onnx-transformer'}({pooling})"
    return embed, label


def _load(backend: str, model_id: str, dim: int, pooling: str = "mean") -> None:
    try:
        log.warning("loading embedding cultivar backend=%s model=%s ...", backend, model_id)
        if backend == "onnx":
            embed, label = _build_onnx()
        elif backend == "onnx-transformer":
            embed, label = _build_onnx_transformer(pooling, model_id)
        elif backend == "sentence-transformers":
            embed, label = _build_sentence_transformers(model_id)
        else:
            raise ValueError(f"unknown backend {backend!r}")

        # Warm the model + confirm the real output width (authoritative over catalog).
        probe = embed(["dimension probe"])
        actual = len(probe[0])
        if actual != dim:
            log.warning(
                "cultivar %s reports dim %s; catalog declared %s; using %s",
                label, actual, dim, actual,
            )
        app.state.embed = embed
        app.state.label = label
        app.state.dim = actual
        app.state.ready = True
        log.warning("cultivar %s ready (dim=%s)", label, actual)
    except Exception as exc:  # noqa: BLE001 — fail the graft fast and loudly
        log.error("cultivar load failed (backend=%s model=%s): %s", backend, model_id, exc)
        # Exit so the supervisor's returncode check fails the graft immediately
        # instead of hanging until ready_timeout_s.
        os._exit(1)


@app.get("/health")
def health():
    if not app.state.ready:
        # 503 -> supervisor poller keeps waiting until weights finish loading.
        return JSONResponse(
            status_code=503, content={"status": "loading", "spec_version": "v1"}
        )
    return {
        "status": "ok",
        "cultivar": app.state.label,
        "dim": app.state.dim,
        "spec_version": "v1",
    }


@app.post("/v1/embeddings")
def embeddings(req: EmbeddingRequest):
    texts = req.input if isinstance(req.input, list) else [req.input]
    vectors = app.state.embed(texts)
    data = [
        {"object": "embedding", "index": i, "embedding": vec}
        for i, vec in enumerate(vectors)
    ]
    return {
        "object": "list",
        "data": data,
        "model": req.model or app.state.label,
        "usage": {"prompt_tokens": 0, "total_tokens": 0},
    }


def main() -> None:
    import threading

    parser = argparse.ArgumentParser(description="sprig-embedding")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument(
        "--backend",
        required=True,
        choices=["onnx", "onnx-transformer", "sentence-transformers"],
    )
    parser.add_argument("--model", default="")
    parser.add_argument("--dim", type=int, required=True)
    parser.add_argument("--pooling", default="mean", choices=["mean", "cls"])
    args = parser.parse_args()

    threading.Thread(
        target=_load,
        args=(args.backend, args.model, args.dim, args.pooling),
        daemon=True,
    ).start()
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
