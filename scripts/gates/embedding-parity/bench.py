import json, sys, time, urllib.request
BASE = sys.argv[1]; LABEL = sys.argv[2]
ts = json.load(open(sys.argv[3]))
texts = (ts["parity"] + ts["corpus"] + [q["q"] for q in ts["queries"]])  # 40
batch = texts * 2  # 80 texts per round
def embed(items):
    r = urllib.request.Request(BASE + "/v1/embeddings", json.dumps({"input": items}).encode(), {"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=300).read())
embed(texts[:8])  # warmup
t0 = time.time()
ROUNDS = 3
for _ in range(ROUNDS):
    for i in range(0, len(batch), 8):
        embed(batch[i:i+8])
dt = time.time() - t0
n = ROUNDS * len(batch)
print(f"{LABEL}: {n} texts in {dt:.1f}s = {n/dt:.1f} texts/sec")
