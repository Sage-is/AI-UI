#!/usr/bin/env bash
# build-llama-static.sh — build a static-PIE llama-server + llama-quantize
# (llama.cpp b9859) for the target arch, headless (no embedded web UI).
#
# These are the binaries the GGUF Sprig™ recipes stage (build-sprig-reranker.sh
# and the e5-large-gguf packaging expect LLAMA_BIN/LLAMA_QUANTIZE). ONE binary,
# any libc: fully static, built in alpine (musl) so it runs on the slim Wolfi
# rootstock regardless of its libc — do NOT build this in the rootstock image
# (that would produce a glibc-linked binary and lose the any-libc property).
#
# THE WEB-UI YAK (why both flags): at b9859 `tools/CMakeLists.txt` adds the
# `ui` subdirectory unconditionally under LLAMA_BUILD_SERVER, and the server
# links `llama-ui`. `scripts/ui-assets.cmake` provisions the embedded UI in
# priority order: pre-built dist -> npm build (BUILD_UI) -> HF bucket download
# (USE_PREBUILT_UI). The b9859 HF bundle is missing `loading.html`, so the
# default (USE_PREBUILT_UI=ON) fails the embed. Turning OFF *both*
# LLAMA_BUILD_UI and LLAMA_USE_PREBUILT_UI takes the "no assets" path: the ui
# lib is emitted empty and the server builds headless — exactly what an
# embedding/rerank server wants. LLAMA_BUILD_UI=OFF alone is NOT enough (the
# HF fetch still runs).
#
# Output: $OUT_DIR/{llama-server,llama-quantize} (default /tmp/sprig-build/
# llama-$ARCH/bin). Cross-arch builds run under QEMU via --platform.
set -euo pipefail

LLAMA_CPP_REF="${LLAMA_CPP_REF:-b9859}"

_RAW_ARCH="$(uname -m)"
case "${ARCH:-$_RAW_ARCH}" in
  arm64|aarch64) ARCH=arm64 ;;
  amd64|x86_64)  ARCH=amd64 ;;
  *) echo "ERROR: unsupported ARCH='${ARCH:-$_RAW_ARCH}' (want arm64|amd64)" >&2; exit 1 ;;
esac
PLATFORM="${PLATFORM:-linux/$ARCH}"
OUT_DIR="${OUT_DIR:-/tmp/sprig-build/llama-$ARCH/bin}"

command -v docker >/dev/null || { echo "ERROR: docker not on PATH" >&2; exit 1; }
mkdir -p "$OUT_DIR"

if [ -f "$OUT_DIR/llama-server" ] && [ -f "$OUT_DIR/llama-quantize" ] && [ "${FORCE:-0}" != "1" ]; then
  echo "== llama binaries already staged in $OUT_DIR (FORCE=1 to rebuild) =="
  exit 0
fi

BUILD_SCRIPT="$(mktemp)"
cat > "$BUILD_SCRIPT" <<BUILD
#!/bin/sh
set -e
apk add --no-cache build-base cmake git linux-headers >/dev/null
git clone --quiet --depth 1 --branch ${LLAMA_CPP_REF} https://github.com/ggml-org/llama.cpp /src
cd /src
# Headless: LLAMA_BUILD_UI=OFF (no npm) AND LLAMA_USE_PREBUILT_UI=OFF (no HF
# fetch) => empty embedded-UI lib, server links it and builds without a web UI.
cmake -B build -DCMAKE_BUILD_TYPE=Release \\
  -DCMAKE_EXE_LINKER_FLAGS=-static -DGGML_STATIC=ON -DGGML_NATIVE=OFF \\
  -DBUILD_SHARED_LIBS=OFF -DLLAMA_OPENSSL=OFF -DLLAMA_CURL=OFF \\
  -DLLAMA_BUILD_SERVER=ON -DGGML_CCACHE=OFF \\
  -DLLAMA_BUILD_UI=OFF -DLLAMA_USE_PREBUILT_UI=OFF > /out/cmake.log 2>&1
cmake --build build -j"\$(nproc)" --target llama-server llama-quantize >> /out/cmake.log 2>&1
cp build/bin/llama-server build/bin/llama-quantize /out/
echo "=== static check ==="
file /out/llama-server
BUILD

echo "== building static llama-server + llama-quantize ($ARCH, $LLAMA_CPP_REF, headless) =="
echo "   (QEMU cross-build is SLOW for amd64 on arm64 hosts — ~20-40 min)"
docker run --rm --platform "$PLATFORM" -v "$OUT_DIR:/out" -v "$BUILD_SCRIPT:/build.sh:ro" alpine sh /build.sh
rm -f "$BUILD_SCRIPT"

echo
echo "== staged: =="
ls -lh "$OUT_DIR/llama-server" "$OUT_DIR/llama-quantize"
