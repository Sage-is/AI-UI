#!/usr/bin/env bash
# build-sprig-whisper.sh — package the STT Sprig™ (whisper.cpp server + ggml base).
#
# Builds a static-PIE musl `whisper-server` for $ARCH (same 9-flag ggml recipe
# as the in-house llama.cpp b9859 build; the alpine build container runs under
# --platform linux/$ARCH, so ARCH=amd64 on Apple Silicon cross-builds via QEMU),
# fetches ggml-base-q8_0.bin ONCE here (at packaging time — never on the
# operator's box), SANITY-GATES the pair (boot, /health readiness, multipart
# /v1/audio/transcriptions -> {"text":...}), then packs a reproducible tar.zst
# and pushes it via oras. arm64 keeps the plain $TAG; amd64 pushes `${TAG}-amd64`
# for the CATALOG arches["amd64"] override.
#
# Prints the tar.zst sha256 to pin in the supervisor CATALOG (binary_sha256).
#
# Local dev (default): pushes to localhost:5000 over --plain-http.
# PRODUCTION swap: REGISTRY=ghcr.io/sage-is INSECURE=0 (oras login first).
#
# Requirements: docker, oras, zstd, tar, curl, jq, python3, sha256sum|shasum.
set -euo pipefail

# Shared boilerplate: constants, arch-normalize, sha256, registry, push, timing.
. "$(dirname "${BASH_SOURCE[0]}")/lib/sprig-build.sh"
NAME="${NAME:-sprig-stt-whisper-base}"
sprig_build_defaults
sprig_timing_start

# v1.9.1: newest release; /health (load-gated 503→200, needed by the supervisor
# poller) exists from v1.7.5 on — v1.7.4 and earlier have NO health endpoint.
WHISPER_CPP_REF="${WHISPER_CPP_REF:-v1.9.1}"
MODEL_FILE="ggml-base-q8_0.bin"   # multilingual base, q8_0 (~82MB)
MODEL_URL="https://huggingface.co/ggerganov/whisper.cpp/resolve/main/${MODEL_FILE}"

# Host arch this artifact serves. Default: the build host. amd64 gets a
# `-amd64`-suffixed tag so it sits beside the arm64 artifact under one repo.
sprig_arch_normalize

WORK="${WORK:-/tmp/sprig-build/whisper-$ARCH}"
OUT_DIR="${OUT_DIR:-$(pwd)}"
OUT="$OUT_DIR/$NAME-$ARCHTAG.tar.zst"


# oras runs DOCKERIZED (ORAS_IMG from sprig-build.sh) — no host install needed.
for c in docker curl jq python3; do command -v "$c" >/dev/null || { echo "ERROR: $c not on PATH" >&2; exit 1; }; done
mkdir -p "$WORK/bin" "$WORK/stage"

# --- 1. static whisper-server build (alpine/musl, mirrors build-llama.sh) -------
if [ ! -f "$WORK/bin/whisper-server" ]; then
  echo "== building static whisper-server @ $WHISPER_CPP_REF (docker/alpine, $PLATFORM) =="
  cat > "$WORK/build-whisper.sh" <<BUILD
#!/bin/sh
set -e
apk add --no-cache build-base cmake git linux-headers >/dev/null
git clone --quiet --depth 1 --branch ${WHISPER_CPP_REF} https://github.com/ggml-org/whisper.cpp /src
cd /src
cmake -B build -DCMAKE_BUILD_TYPE=Release \\
  -DCMAKE_EXE_LINKER_FLAGS=-static -DGGML_STATIC=ON -DGGML_NATIVE=OFF \\
  -DBUILD_SHARED_LIBS=OFF -DWHISPER_BUILD_TESTS=OFF -DWHISPER_BUILD_EXAMPLES=ON \\
  -DGGML_OPENMP=OFF \\
  -DGGML_CCACHE=OFF > /out/cmake.log 2>&1
cmake --build build -j"\$(nproc)" --target whisper-server >> /out/cmake.log 2>&1
cp build/bin/whisper-server /out/
echo "=== static check ==="
ldd /out/whisper-server 2>&1 || echo "(no dynamic deps — static)"
ls -lh /out/whisper-server
BUILD
  chmod +x "$WORK/build-whisper.sh"
  docker run --rm --platform "$PLATFORM" -v "$WORK/bin:/out" -v "$WORK/build-whisper.sh:/build.sh:ro" alpine sh /build.sh
fi
ls -lh "$WORK/bin/whisper-server"

# --- 2. model fetch (the one-time pull lives HERE) ------------------------------
if [ ! -f "$WORK/$MODEL_FILE" ]; then
  echo "== fetching $MODEL_FILE (one-time, packaging host) =="
  curl -fL --retry 3 -o "$WORK/$MODEL_FILE" "$MODEL_URL"
fi
ls -lh "$WORK/$MODEL_FILE"

# --- 3. stage --------------------------------------------------------------------
STAGE="$WORK/stage"
rm -rf "$STAGE"; mkdir -p "$STAGE"
cp "$WORK/bin/whisper-server" "$STAGE/whisper-server"; chmod 0755 "$STAGE/whisper-server"
cp "$WORK/$MODEL_FILE" "$STAGE/model.bin"
MODEL_SHA="$(sha256 "$STAGE/model.bin")"

cat > "$STAGE/sprig.yaml" <<YAML
spec_version: v1
delivery: oci-artifact
capability: stt
cultivar: whisper-base-ggml
variety: linux-$ARCH-cpu
sprig_version: v1.0.0
backend: whisper-binary
model: whisper base multilingual (ggml q8_0)
whisper_cpp_ref: ${WHISPER_CPP_REF}
model_sha256: ${MODEL_SHA}
license: MIT
offline: true
YAML

# --- 4. SANITY GATE: boot + /health + transcription shape ------------------------
echo "== sanity gate: whisper-server /health + /v1/audio/transcriptions =="
python3 - <<PY
import math, struct, wave
with wave.open("$WORK/gate.wav", "w") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
    # 1s 440Hz tone — content irrelevant; the gate asserts the response SHAPE.
    w.writeframes(b"".join(struct.pack("<h", int(12000*math.sin(2*math.pi*440*t/16000))) for t in range(16000)))
PY
GATE_NAME="sprig-whisper-gate-$$"
docker run -d --rm --platform "$PLATFORM" --name "$GATE_NAME" -v "$STAGE:/s:ro" -p 18090:18090 alpine \
  /s/whisper-server -m /s/model.bin --host 0.0.0.0 --port 18090 \
  --inference-path /v1/audio/transcriptions -l auto >/dev/null
HEALTH_OK=0
for i in $(seq 1 60); do
  [ "$(curl -s -o /dev/null -w '%{http_code}' http://localhost:18090/health 2>/dev/null)" = "200" ] && HEALTH_OK=1 && break; sleep 2
done
[ "$HEALTH_OK" = "1" ] || { docker logs "$GATE_NAME" 2>&1 | tail -5; docker rm -f "$GATE_NAME" >/dev/null 2>&1; echo "SANITY GATE FAILED: /health never 200" >&2; exit 1; }
RES=$(curl -s http://localhost:18090/v1/audio/transcriptions -F "file=@$WORK/gate.wav" -F "response_format=json")
docker rm -f "$GATE_NAME" >/dev/null 2>&1 || true
echo "$RES" | jq -e 'has("text")' >/dev/null 2>&1 || { echo "SANITY GATE FAILED — response: $(echo "$RES" | head -c 300)" >&2; exit 1; }
echo "  ✅ /health gated readiness + transcription response has {\"text\"}"

# --- 5. reproducible pack + pin ----------------------------------------------------
# GNU tar via docker: macOS ships bsdtar, which lacks --sort=name (the
# reproducibility flag). Alpine's tar package is GNU tar; flags unchanged.
docker run --rm -v "$STAGE:/stage:ro" -v "$OUT_DIR:/out" alpine sh -c \
  "apk add --no-cache tar zstd >/dev/null && \
   tar --sort=name --owner=0 --group=0 --numeric-owner --mtime='UTC 2020-01-01' \
       --use-compress-program='zstd -19 -T0' \
       -cf /out/$(basename "$OUT") -C /stage sprig.yaml whisper-server model.bin"
TAR_SHA="$(sha256 "$OUT")"

echo
echo "=================================================================="
echo "  artifact : $OUT"
echo "  tar.zst sha256 (PIN THIS in CATALOG binary_sha256):"
echo "    $TAR_SHA"
echo "  model.bin sha256: $MODEL_SHA"
echo "=================================================================="

sprig_ensure_registry

# SIGN_KEY=<minisign secret key> signs the tar before push (SIGN_NOPASS=1 for
# the committed dev fixture; real keys prompt). Verify side: sprigs/minisign.py.
SIG_LAYER=()
if [ -n "${SIGN_KEY:-}" ]; then
  KEY_DIR="$(cd "$(dirname "$SIGN_KEY")" && pwd)"
  MTTY=""; [ -z "${SIGN_NOPASS:-}" ] && [ -t 0 ] && MTTY="-it"
  docker run --rm $MTTY -v "$OUT_DIR:/w" -v "$KEY_DIR:/keys:ro" alpine:3.20 sh -c \
    "apk add --no-cache minisign >/dev/null 2>&1 && minisign -S ${SIGN_NOPASS:+-W} \
     -s /keys/$(basename "$SIGN_KEY") -m /w/$(basename "$OUT") \
     -t 'sage-is $NAME:$ARCHTAG sha256=$TAR_SHA'"
  SIG_LAYER=("$(basename "$OUT").minisig:application/vnd.sage-is.sprig.minisig")
fi
# Dockerized oras push (no host oras). Inside the container localhost is the container itself, so a localhost registry is reached by its on-network name.

# **Note** This may not be the right call for ASAP deployment initially.
sprig_push

echo
echo "pushed: $REGISTRY/$NAME:$ARCHTAG"
sprig_timing_end
if [ "$ARCH" = "amd64" ]; then
  echo "catalog: arches[\"amd64\"] = {\"tag\": \"$ARCHTAG\", \"binary_sha256\": \"$TAR_SHA\"}"
else
  echo "catalog: binary_sha256: \"$TAR_SHA\"   repo: \"$REGISTRY/$NAME\"   tag: \"$ARCHTAG\""
fi
