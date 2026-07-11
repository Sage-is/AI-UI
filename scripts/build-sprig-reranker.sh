#!/usr/bin/env bash
# build-sprig-reranker.sh — package the reranker Sprig™ (bge-reranker-v2-m3 GGUF).
#
# Converts BAAI/bge-reranker-v2-m3 (pulled ONCE here, at packaging time — never
# on the operator's box) to GGUF at llama.cpp b9859, quantizes to Q8_0, stages
# it with the SAME in-house static-PIE llama-server used by e5-large-gguf,
# SANITY-GATES the pair (boot + /v1/rerank semantic ordering) in a container,
# then packs a reproducible tar.zst and pushes it via oras.
#
# Prints the tar.zst sha256 to pin in the supervisor CATALOG (binary_sha256).
#
# Local dev (default): pushes to localhost:5000 over --plain-http; with
# MANAGE_REGISTRY=1 it also runs a registry:2 container on $NETWORK.
# PRODUCTION swap: REGISTRY=ghcr.io/sage-is INSECURE=0 (oras login first).
#
# Requirements: docker, oras, zstd, tar, sha256sum|shasum. The llama binaries
# from the 8.I.3 build must exist (LLAMA_BIN/LLAMA_QUANTIZE below) — they also
# live inside the pushed sprig-embedding-e5-gguf artifact if /tmp was cleaned.
set -euo pipefail

REGISTRY="${REGISTRY:-localhost:5000}"
NAME="${NAME:-sprig-reranker-bge-gguf}"
TAG="${TAG:-v1}"
INSECURE="${INSECURE:-1}"
MANAGE_REGISTRY="${MANAGE_REGISTRY:-0}"
NETWORK="${NETWORK:-sage-network}"
ARTIFACT_TYPE="application/vnd.sage-is.sprig.v1"
LAYER_TYPE="application/vnd.sage-is.sprig.tar+zstd"

HF_REPO="BAAI/bge-reranker-v2-m3"
LLAMA_CPP_REF="b9859"                      # keep in lockstep with the binary
LLAMA_BIN="${LLAMA_BIN:-/tmp/sprig-build/8i3/bin/llama-server}"
LLAMA_QUANTIZE="${LLAMA_QUANTIZE:-/tmp/sprig-build/8i3/bin/llama-quantize}"

WORK="${WORK:-/tmp/sprig-build/reranker}"
OUT_DIR="${OUT_DIR:-$(pwd)}"
OUT="$OUT_DIR/$NAME-$TAG.tar.zst"

sha256() { if command -v sha256sum >/dev/null; then sha256sum "$1" | cut -d' ' -f1; else shasum -a 256 "$1" | cut -d' ' -f1; fi; }

# --- preflight ----------------------------------------------------------------
for c in docker oras zstd tar; do command -v "$c" >/dev/null || { echo "ERROR: $c not on PATH" >&2; exit 1; }; done
[ -f "$LLAMA_BIN" ] || { echo "ERROR: static llama-server not at $LLAMA_BIN (extract it from the sprig-embedding-e5-gguf artifact if /tmp was cleaned)" >&2; exit 1; }
[ -f "$LLAMA_QUANTIZE" ] || { echo "ERROR: llama-quantize not at $LLAMA_QUANTIZE" >&2; exit 1; }
mkdir -p "$WORK/gguf" "$WORK/stage"

# --- 1. convert + quantize (dockerized, one-time HF pull lives HERE) -----------
if [ ! -f "$WORK/gguf/model.gguf" ]; then
  echo "== converting $HF_REPO -> GGUF f16 @ $LLAMA_CPP_REF (docker) =="
  cat > "$WORK/convert-reranker.sh" <<'CONVERT'
#!/bin/bash
set -e
export HF_HOME=/w/hf-cache
pip install -q --no-cache-dir torch transformers sentencepiece protobuf 'numpy<2' > /w/pip.log 2>&1
git clone --quiet --depth 1 --branch b9859 https://github.com/ggml-org/llama.cpp /src
pip install -q --no-cache-dir /src/gguf-py >> /w/pip.log 2>&1
python - <<'PY'
from huggingface_hub import snapshot_download
p = snapshot_download(repo_id="BAAI/bge-reranker-v2-m3", local_dir="/w/models/bge-reranker-v2-m3")
print("downloaded:", p)
PY
python /src/convert_hf_to_gguf.py /w/models/bge-reranker-v2-m3 \
  --outfile /w/gguf/reranker-f16.gguf --outtype f16 > /w/gguf/convert.log 2>&1 \
  && echo "converted: reranker-f16.gguf" || { echo "CONVERT FAILED"; tail -20 /w/gguf/convert.log; exit 1; }
CONVERT
  chmod +x "$WORK/convert-reranker.sh"
  docker run --rm -v "$WORK:/w" -w /w python:3.11-slim bash -c "apt-get update -qq && apt-get install -y -qq git > /dev/null && bash /w/convert-reranker.sh"

  echo "== quantizing f16 -> Q8_0 (docker, static llama-quantize) =="
  docker run --rm -v "$WORK/gguf:/g" -v "$(dirname "$LLAMA_QUANTIZE"):/b:ro" alpine \
    /b/"$(basename "$LLAMA_QUANTIZE")" /g/reranker-f16.gguf /g/model.gguf Q8_0
fi
ls -lh "$WORK/gguf/model.gguf"

# --- 2. stage (flat root: llama-server + model.gguf + sprig.yaml) ---------------
STAGE="$WORK/stage"
rm -rf "$STAGE"; mkdir -p "$STAGE"
cp "$LLAMA_BIN" "$STAGE/llama-server"; chmod 0755 "$STAGE/llama-server"
cp "$WORK/gguf/model.gguf" "$STAGE/model.gguf"
MODEL_SHA="$(sha256 "$STAGE/model.gguf")"

cat > "$STAGE/sprig.yaml" <<YAML
spec_version: v1
delivery: oci-artifact
capability: reranker
cultivar: bge-reranker-v2-m3-gguf
variety: linux-arm64-cpu
sprig_version: v1.0.0
backend: llama-binary
model: BAAI/bge-reranker-v2-m3
quantization: Q8_0
llama_cpp_ref: ${LLAMA_CPP_REF}
model_sha256: ${MODEL_SHA}
license: Apache-2.0
offline: true
YAML

# --- 3. SANITY GATE: boot + semantic ordering BEFORE anything ships -------------
echo "== sanity gate: llama-server --rerank + /v1/rerank ordering =="
GATE_NAME="sprig-reranker-gate-$$"
docker run -d --rm --name "$GATE_NAME" -v "$STAGE:/s:ro" -p 18089:18089 alpine \
  /s/llama-server -m /s/model.gguf --rerank --host 0.0.0.0 --port 18089 -ub 2048 -c 2048 >/dev/null
for i in $(seq 1 120); do
  [ "$(curl -s -o /dev/null -w '%{http_code}' http://localhost:18089/health 2>/dev/null)" = "200" ] && break; sleep 2
done
RES=$(curl -s http://localhost:18089/v1/rerank -H 'Content-Type: application/json' -d '{
  "model":"reranker","query":"what is a panda?",
  "documents":["the kernel reserves an ephemeral loopback port",
               "The giant panda is a bear species endemic to China."],
  "top_n":2}')
docker rm -f "$GATE_NAME" >/dev/null 2>&1 || true
TOP=$(echo "$RES" | jq -r '.results | sort_by(-.relevance_score) | .[0].index' 2>/dev/null || echo "parse-fail")
if [ "$TOP" != "1" ]; then
  echo "SANITY GATE FAILED — rerank response: $(echo "$RES" | head -c 400)" >&2
  exit 1
fi
echo "  ✅ /v1/rerank orders the panda doc first (relevance contract holds)"

# --- 4. reproducible pack + pin -------------------------------------------------
# GNU tar via docker: macOS ships bsdtar, which lacks --sort=name (the
# reproducibility flag). Alpine's tar package is GNU tar; flags unchanged.
docker run --rm -v "$STAGE:/stage:ro" -v "$OUT_DIR:/out" alpine sh -c \
  "apk add --no-cache tar zstd >/dev/null && \
   tar --sort=name --owner=0 --group=0 --numeric-owner --mtime='UTC 2020-01-01' \
       --use-compress-program='zstd -19 -T0' \
       -cf /out/$(basename "$OUT") -C /stage sprig.yaml llama-server model.gguf"
TAR_SHA="$(sha256 "$OUT")"

echo
echo "=================================================================="
echo "  artifact : $OUT"
echo "  tar.zst sha256 (PIN THIS in CATALOG binary_sha256):"
echo "    $TAR_SHA"
echo "  model.gguf sha256: $MODEL_SHA"
echo "=================================================================="

# --- 5. optional registry + push -------------------------------------------------
if [ "$MANAGE_REGISTRY" = "1" ]; then
  docker network inspect "$NETWORK" >/dev/null 2>&1 || docker network create "$NETWORK"
  if ! docker ps --format '{{.Names}}' | grep -qx local-registry; then
    docker rm -f local-registry >/dev/null 2>&1 || true
    docker run -d --name local-registry --network "$NETWORK" -p 5000:5000 registry:2 >/dev/null
  fi
  for _ in $(seq 1 30); do curl -fsS "http://localhost:5000/v2/" >/dev/null 2>&1 && break; sleep 0.5; done
fi

# SIGN_KEY=<minisign secret key> signs the tar before push (SIGN_NOPASS=1 for
# the committed dev fixture; real keys prompt). Verify side: sprigs/minisign.py.
SIG_LAYER=()
if [ -n "${SIGN_KEY:-}" ]; then
  KEY_DIR="$(cd "$(dirname "$SIGN_KEY")" && pwd)"
  MTTY=""; [ -z "${SIGN_NOPASS:-}" ] && [ -t 0 ] && MTTY="-it"
  docker run --rm $MTTY -v "$OUT_DIR:/w" -v "$KEY_DIR:/keys:ro" alpine:3.20 sh -c \
    "apk add --no-cache minisign >/dev/null 2>&1 && minisign -S ${SIGN_NOPASS:+-W} \
     -s /keys/$(basename "$SIGN_KEY") -m /w/$(basename "$OUT") \
     -t 'sage-is $NAME:$TAG sha256=$TAR_SHA'"
  SIG_LAYER=("$(basename "$OUT").minisig:application/vnd.sage-is.sprig.minisig")
fi
PUSH=(oras push "$REGISTRY/$NAME:$TAG" --artifact-type "$ARTIFACT_TYPE")
[ "$INSECURE" = "1" ] && PUSH+=(--plain-http)
( cd "$OUT_DIR" && "${PUSH[@]}" "$(basename "$OUT"):$LAYER_TYPE" ${SIG_LAYER[@]+"${SIG_LAYER[@]}"} )

echo
echo "pushed: $REGISTRY/$NAME:$TAG"
echo "catalog: binary_sha256: \"$TAR_SHA\"   repo: \"$REGISTRY/$NAME\"   tag: \"$TAG\""
