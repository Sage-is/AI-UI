"""Mock embedding Sprig™ — the grafted process for the first-graft walking skeleton.

Launched by SprigSupervisor via:
    python -m sage_is_ai.sprigs.mock_embedding_server --port <port> [--dim <dim>]

Exposes the minimal OpenAI-compatible surface the Rootstock™ dispatch expects:
    GET  /health        -> {"status": "ok", ...}
    POST /v1/embeddings -> OpenAI Embedding response shape

Vectors are deterministic (seeded from a sha256 of the input text) so retrieval is
reproducible across restarts in smoke tests. No model weights, no network, no GPU.

This stays the deterministic mock (smoke + zero-dep fallback). Real cultivars are
served by embedding_server.py (ONNX / sentence-transformers) or a static
llama-server binary (GGUF), delivered via OCI artifact (see artifact.py).

DEFERRED for the subsystem: sigstore/cosign signing of artifacts, structured stderr
log forwarding to the Rootstock™ (server children are currently DEVNULL'd).
"""

from __future__ import annotations

import argparse
import hashlib
import math
import random

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
    """Deterministic, L2-normalized pseudo-embedding for a piece of text.

    Pure stdlib (8.I.2: numpy left the base rootstock — the mock must run on
    the bare Bonsai™). random.Random reproducibility is documented stable
    across CPython versions. Vectors differ from the earlier numpy-seeded
    implementation; smoke collections are always freshly created, so no
    cross-version collection reuse exists for the mock.
    """
    seed = int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big")
    rng = random.Random(seed)
    vec = [rng.gauss(0.0, 1.0) for _ in range(dim)]
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


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
