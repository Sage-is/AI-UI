#!/usr/bin/env bash
# build-artifacts.sh — build everything parity_gate needs but the repo never shipped.
#
# The gate (run-gate.sh) SKIPs unless three artifacts exist. Only the first had
# a script:
#   bin/     llama-server + llama-quantize   <- scripts/build-llama-static.sh
#   gguf/    e5-f16.gguf, e5-q8.gguf         <- THIS script
#   harness/ reference.json, tokens_ref.json <- THIS script (via gen-reference.py)
#
# So parity_gate has been permanently skippable rather than merely unbuilt.
# Run this once and the gate becomes exercisable for good.
#
# Everything happens in ONE container: the conversion needs torch + transformers,
# which we deliberately do NOT install on the host (all app deps live in Docker).
# Egress IS required here — the HF model and llama.cpp sources are pulled. That
# is fine for a build-time gate artifact; the RUNTIME zero-egress property of the
# Sprig™ chain is unaffected, since nothing produced here ships in the image.
#
# Usage: [MODEL_SHORT=e5] [HF_MODEL=intfloat/multilingual-e5-large] build-artifacts.sh
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="${GATE_OUT:-/tmp/sprig-build/8i3}"
BIN="${GATE_BIN_DIR:-$OUT/bin}"
SHORT="${MODEL_SHORT:-e5}"
HF_MODEL="${HF_MODEL:-intfloat/multilingual-e5-large}"
# Must match scripts/build-llama-static.sh, or convert_hf_to_gguf.py can emit
# metadata the pinned llama-server does not understand.
LLAMA_CPP_REF="${LLAMA_CPP_REF:-b9859}"

[ -x "$BIN/llama-quantize" ] || {
  echo "missing $BIN/llama-quantize — run: OUT_DIR=$BIN scripts/build-llama-static.sh" >&2
  exit 1
}

mkdir -p "$OUT/gguf" "$OUT/harness" "$OUT/hf"

echo "== 8.I.3 parity artifacts: $SHORT <- $HF_MODEL =="
# Mount points must not nest: bind-mounting into a directory that is itself a
# bind mount fails on Docker Desktop's virtiofs. $BIN already lives inside $OUT,
# so /w/bin comes along for free, and the gate scripts land on their own path.
docker run --rm \
  -v "$OUT:/w" \
  -v "$HERE:/gate:ro" \
  -e HF_HUB_DISABLE_TELEMETRY=1 \
  -e SHORT="$SHORT" -e HF_MODEL="$HF_MODEL" -e LLAMA_CPP_REF="$LLAMA_CPP_REF" \
  python:3.11-bookworm bash -euo pipefail -c '
    echo "-- deps (cpu-only torch: the GPU wheels are ~2GB of nothing we use)"
    pip install --quiet --no-cache-dir \
      --extra-index-url https://download.pytorch.org/whl/cpu \
      torch --index-url https://download.pytorch.org/whl/cpu
    pip install --quiet --no-cache-dir \
      sentence-transformers transformers huggingface_hub sentencepiece protobuf numpy gguf

    echo "-- fetch $HF_MODEL"
    python3 - <<PY
from huggingface_hub import snapshot_download
# Skip the formats we do not convert from. A bare snapshot_download pulls
# safetensors AND pytorch bin AND onnx AND openvino — 9.0GB measured, against
# ~2.2GB of files actually used. Everything needed by convert_hf_to_gguf.py
# (config + tokenizer + safetensors) and by sentence-transformers
# (modules.json, sentence_bert_config.json, 1_Pooling/) is kept.
p = snapshot_download(
    "$HF_MODEL",
    local_dir="/w/hf/model",
    # Verified against the live repo file list: this keeps config, tokenizer,
    # safetensors and 1_Pooling/, and drops only onnx/, openvino/ and the
    # pytorch bin duplicate. No Flax or Rust checkpoint patterns — e5 ships
    # neither, so listing them would be speculation, not coverage.
    ignore_patterns=["onnx/*", "openvino/*", "*.bin", "*.h5", "*.msgpack"],
)
print("model at", p)
PY

    echo "-- llama.cpp $LLAMA_CPP_REF (for convert_hf_to_gguf.py)"
    apt-get -qq update && apt-get -qq install -y git >/dev/null
    git clone --quiet --depth 1 --branch "$LLAMA_CPP_REF" \
      https://github.com/ggml-org/llama.cpp /src

    echo "-- convert -> f16"
    python3 /src/convert_hf_to_gguf.py /w/hf/model \
      --outtype f16 --outfile "/w/gguf/${SHORT}-f16.gguf"

    echo "-- quantize -> q8_0"
    /w/bin/llama-quantize "/w/gguf/${SHORT}-f16.gguf" "/w/gguf/${SHORT}-q8.gguf" Q8_0

    echo "-- reference embeddings + tokenizer ids"
    python3 /gate/gen-reference.py "$SHORT" /w/hf/model /gate/testset.json /w/harness
  '

echo
echo "== artifacts =="
ls -la "$OUT/gguf" "$OUT/harness"
echo
echo "now run: make parity_gate"
