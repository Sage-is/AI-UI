#!/usr/bin/env python3
"""Generate the sentence-transformers reference the parity gate compares against.

harness.py READS /w/harness/reference.json and tokens_ref.json; nothing wrote
them, which is why parity_gate could only ever SKIP. This is that missing half.

Emits, keyed by the gate's short model name:
  reference.json   {short: [[float, ...], ...]}  one embedding per text
  tokens_ref.json  {short: [[int, ...], ...]}    HF token ids, special tokens on

Order is fixed by harness.py and must not drift:
    testset["parity"] + testset["corpus"] + [q["q"] for q in testset["queries"]]

The tokenizer half is the point, not an extra: the Korean probe in testset.json
is the canary that held minilm/bge back (llama.cpp WPM Hangul divergence,
2026-07-02). A GGUF that embeds well but tokenizes differently is a silent
retrieval regression, so the reference has to pin the ids the HF tokenizer
produces and let the gate diff llama.cpp's /tokenize against them.

Usage: gen-reference.py <short> <hf-model-id> <testset.json> <out-dir>
"""
import json
import sys

from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer

short, model_id, testset_path, out_dir = sys.argv[1:5]

testset = json.load(open(testset_path))
texts = (
    testset["parity"]
    + testset["corpus"]
    + [q["q"] for q in testset["queries"]]
)
print(f"[ref] {short} <- {model_id}: {len(texts)} texts", flush=True)

# No normalization and no "query:"/"passage:" prefixes on purpose. The gate
# compares llama-server against this on byte-identical input, so anything we do
# to the text here we would have to mirror there; cosine is scale-invariant, so
# normalization would change nothing anyway.
model = SentenceTransformer(model_id)
vectors = model.encode(texts, batch_size=8, show_progress_bar=False)
print(f"[ref] dim={len(vectors[0])}", flush=True)

tokenizer = AutoTokenizer.from_pretrained(model_id)
token_ids = [tokenizer(t, add_special_tokens=True)["input_ids"] for t in texts]


def merge(path, payload):
    """Keep other models' references intact — the gate can hold several."""
    try:
        existing = json.load(open(path))
    except (FileNotFoundError, json.JSONDecodeError):
        existing = {}
    existing[short] = payload
    json.dump(existing, open(path, "w"))


merge(f"{out_dir}/reference.json", [[float(x) for x in v] for v in vectors])
merge(f"{out_dir}/tokens_ref.json", token_ids)
print(f"[ref] wrote reference.json + tokens_ref.json for '{short}'", flush=True)
