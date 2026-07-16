#!/usr/bin/env python3
"""Gate A parity harness: llama-server GGUF embeddings vs sentence-transformers
reference. Pure stdlib (urllib + math). Run inside a glibc container with the
static llama-server + ggufs mounted at /w.

Usage: python3 harness.py <short> <gguf-path> <port>
Writes /w/harness/verdict-<short>-<quant>.json and prints a summary line.
"""
import json
import math
import subprocess
import sys
import time
import urllib.request

SHORT, GGUF, PORT = sys.argv[1], sys.argv[2], int(sys.argv[3])
QUANT = "q8" if "q8" in GGUF.lower() else "f16"
BASE = f"http://127.0.0.1:{PORT}"

ts = json.load(open("/w/testset.json"))
texts = ts["parity"] + ts["corpus"] + [q["q"] for q in ts["queries"]]
ref_all = json.load(open("/w/harness/reference.json"))[SHORT]
tok_ref = json.load(open("/w/harness/tokens_ref.json"))[SHORT]

proc = subprocess.Popen(
    ["/w/bin/llama-server", "-m", GGUF, "--embeddings",
     "--host", "127.0.0.1", "--port", str(PORT), "-ub", "512", "-c", "512"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def req(path, payload):
    r = urllib.request.Request(BASE + path, json.dumps(payload).encode(),
                               {"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=120).read())


for i in range(120):
    try:
        urllib.request.urlopen(BASE + "/health", timeout=2)
        break
    except Exception:
        if proc.poll() is not None:
            print(f"FATAL {SHORT}-{QUANT}: llama-server died on load")
            sys.exit(2)
        time.sleep(1)
else:
    sys.exit(2)

# --- embeddings for the full text set (batch of 8) ---
vecs = []
t0 = time.time()
for i in range(0, len(texts), 8):
    out = req("/v1/embeddings", {"input": texts[i:i + 8]})
    vecs += [d["embedding"] for d in sorted(out["data"], key=lambda d: d["index"])]
embed_secs = time.time() - t0


def cos(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(x * x for x in b)) or 1.0
    return dot / (na * nb)


cosines = [cos(v, r) for v, r in zip(vecs, ref_all)]
n_par = len(ts["parity"])

# --- tokenizer diff ---
tok_mismatch = []
for i, t in enumerate(texts):
    try:
        got = req("/tokenize", {"content": t, "add_special": True})["tokens"]
        if got != tok_ref[i]:
            tok_mismatch.append({"i": i, "text": t[:40], "got": len(got), "ref": len(tok_ref[i])})
    except Exception as e:
        tok_mismatch.append({"i": i, "text": t[:40], "error": str(e)})

# --- retrieval recall: rank corpus for each query, llama vs expectation ---
corpus_v = vecs[n_par:n_par + len(ts["corpus"])]
query_v = vecs[n_par + len(ts["corpus"]):]
ref_corpus = ref_all[n_par:n_par + len(ts["corpus"])]
ref_query = ref_all[n_par + len(ts["corpus"]):]
recall_hits, rank_agree = 0, 0
for qi, q in enumerate(ts["queries"]):
    top3 = sorted(range(len(corpus_v)), key=lambda d: -cos(query_v[qi], corpus_v[d]))[:3]
    ref3 = sorted(range(len(ref_corpus)), key=lambda d: -cos(ref_query[qi], ref_corpus[d]))[:3]
    if any(e in top3 for e in q["expect"]):
        recall_hits += 1
    rank_agree += len(set(top3) & set(ref3))

verdict = {
    "model": SHORT, "quant": QUANT, "gguf": GGUF,
    "dim": len(vecs[0]),
    "cosine_mean": sum(cosines) / len(cosines),
    "cosine_min": min(cosines),
    "cosine_min_text": texts[cosines.index(min(cosines))][:60],
    "tokenizer_mismatches": len(tok_mismatch),
    "tokenizer_detail": tok_mismatch[:5],
    "retrieval_recall": f"{recall_hits}/{len(ts['queries'])}",
    "top3_agreement_with_reference": f"{rank_agree}/{3 * len(ts['queries'])}",
    "embed_seconds_all_texts": round(embed_secs, 2),
    "gate_f16": (QUANT != "f16") or (min(cosines) >= 0.999),
    "gate_q8": (QUANT != "q8") or (recall_hits == len(ts["queries"]) and min(cosines) >= 0.99),
}
json.dump(verdict, open(f"/w/harness/verdict-{SHORT}-{QUANT}.json", "w"), indent=1)
print(f"{SHORT}-{QUANT}: dim={verdict['dim']} cos_mean={verdict['cosine_mean']:.5f} "
      f"cos_min={verdict['cosine_min']:.5f} tok_mismatch={len(tok_mismatch)} "
      f"recall={verdict['retrieval_recall']} top3agree={verdict['top3_agreement_with_reference']}")
proc.terminate()
