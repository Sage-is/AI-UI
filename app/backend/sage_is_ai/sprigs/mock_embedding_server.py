"""Mock embedding Sprig™ — the grafted process for the first-graft walking skeleton.

Launched by SprigSupervisor via:
    python -m sage_is_ai.sprigs.mock_embedding_server --port <port> [--dim <dim>]

Exposes the minimal OpenAI-compatible surface the Rootstock™ dispatch expects:
    GET  /health        -> {"status": "ok", ...}
    POST /v1/embeddings -> OpenAI Embedding response shape

Vectors are deterministic (seeded from a sha256 of the input text) so retrieval is
reproducible across restarts in smoke tests. No model weights, no network, no GPU.

DEFERRED (graft #2+): real model weights, sigstore-signed tar.zst packaging, oras
pull, structured stderr log forwarding to the Rootstock™.
"""

from __future__ import annotations

import argparse
import hashlib

import numpy as np
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

# Default matches the app's default embedding model all-MiniLM-L6-v2 (384-dim).
# The vector store binds dimensionality per-collection at first ingest, so on a
# clean dev box 384 is the safe match. Override with --dim for other collections
# (e.g. --dim 1024 for an e5-large collection when graft #2 swaps in the real Sprig™).
DIM = 384

app = FastAPI(title="sprig-embedding-mock")


class EmbeddingRequest(BaseModel):
    input: list[str] | str
    model: str | None = None


def _vector(text: str, dim: int) -> list[float]:
    """Deterministic, L2-normalized pseudo-embedding for a piece of text."""
    seed = int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big")
    rng = np.random.default_rng(seed)
    vec = rng.standard_normal(dim).astype(np.float32)
    norm = float(np.linalg.norm(vec)) or 1.0
    vec = vec / norm
    # Native python float per element — numpy float32 scalars trip the
    # downstream vector-store and JSON validators (same reason as the
    # _embed_chroma path in retrieval/utils.py).
    return [float(x) for x in vec]


@app.get("/health")
def health():
    return {"status": "ok", "cultivar": "mock-embedding", "spec_version": "v1"}


@app.post("/v1/embeddings")
def embeddings(req: EmbeddingRequest):
    dim = getattr(app.state, "dim", DIM)
    texts = req.input if isinstance(req.input, list) else [req.input]
    data = [
        {"object": "embedding", "index": i, "embedding": _vector(t, dim)}
        for i, t in enumerate(texts)
    ]
    return {
        "object": "list",
        "data": data,
        "model": req.model or "mock-embedding",
        "usage": {"prompt_tokens": 0, "total_tokens": 0},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="sprig-embedding-mock")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--dim", type=int, default=DIM)
    args = parser.parse_args()
    app.state.dim = args.dim
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
