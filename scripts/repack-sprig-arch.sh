#!/usr/bin/env bash
# repack-sprig-arch.sh — produce an amd64 (or other-arch) variant of a binary
# Sprig™ by swapping ONLY the arch-specific binary into the existing artifact.
#
# The GGUF/ggml model files and sprig.yaml are architecture-NEUTRAL; only the
# server binary (llama-server / whisper-server) differs by arch. So an amd64
# artifact = the published arm64 tar with its one binary replaced by the amd64
# build, repacked reproducibly and pushed under an arch-suffixed tag.
#
# Usage:
#   NAME=sprig-stt-whisper-base BINARY=whisper-server \
#   NEW_BIN=/path/to/amd64/whisper-server \
#   SRC_TAG=v1 DST_TAG=v1-amd64 scripts/repack-sprig-arch.sh
#
# Env: REGISTRY (default local-registry:5000 host / local-registry:5000 for
#   the dockerized oras on sage-network), INSECURE=1, SIGN_KEY/SIGN_NOPASS.
# Prints the new tar.zst sha256 to pin as the arch override's binary_sha256.
set -euo pipefail

NAME="${NAME:?NAME=sprig-<...> required}"
BINARY="${BINARY:?BINARY=<filename in the tar> required (e.g. whisper-server)}"
NEW_BIN="${NEW_BIN:?NEW_BIN=<path to the replacement binary> required}"
SRC_TAG="${SRC_TAG:-v1}"
DST_TAG="${DST_TAG:-v1-amd64}"
[ -f "$NEW_BIN" ] || { echo "ERROR: NEW_BIN $NEW_BIN not found"; exit 1; }

REGISTRY_HOST="${REGISTRY_HOST:-localhost:5000}"          # curl-visible
REGISTRY_INTERNAL="${REGISTRY_INTERNAL:-local-registry:5000}"  # oras on sage-network
ARTIFACT_TYPE="application/vnd.sage-is.sprig.v1"
LAYER_TYPE="application/vnd.sage-is.sprig.tar+zstd"
NET="${NET:-sage-network}"
ORAS_IMG="ghcr.io/oras-project/oras:v1.2.0"

sha256(){ shasum -a 256 "$1" 2>/dev/null | awk '{print $1}' || sha256sum "$1" | awk '{print $1}'; }
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT

echo "== pull $NAME:$SRC_TAG (arm64 source) =="
docker run --rm --network "$NET" -v "$WORK:/w" -w /w "$ORAS_IMG" \
  pull --plain-http "$REGISTRY_INTERNAL/$NAME:$SRC_TAG" >/dev/null
SRC_TAR=$(cd "$WORK" && ls -- *.tar.zst | head -1)
[ -n "$SRC_TAR" ] || { echo "ERROR: no tar.zst in $NAME:$SRC_TAG"; exit 1; }

echo "== unpack, swap $BINARY, verify the new binary is really the target arch =="
mkdir -p "$WORK/stage"
docker run --rm -v "$WORK:/w" alpine:3.20 sh -c \
  "apk add --no-cache tar zstd >/dev/null 2>&1 && tar --use-compress-program=zstd -xf /w/$SRC_TAR -C /w/stage"
cp "$NEW_BIN" "$WORK/stage/$BINARY"; chmod 0755 "$WORK/stage/$BINARY"
ARCH_OF=$(docker run --rm -v "$WORK/stage:/s:ro" alpine:3.20 sh -c "apk add --no-cache file >/dev/null 2>&1 && file -b /s/$BINARY")
echo "  new $BINARY: $ARCH_OF"
echo "$ARCH_OF" | grep -qE 'x86-64|aarch64|ARM' || { echo "ERROR: replacement is not an ELF binary"; exit 1; }

# List the staged files in a stable order (sprig.yaml + binary + model files).
FILES=$(cd "$WORK/stage" && ls | sort | tr '\n' ' ')
echo "  repacking: $FILES"
OUT="$WORK/$NAME-$DST_TAG.tar.zst"
docker run --rm -v "$WORK/stage:/stage:ro" -v "$WORK:/out" alpine:3.20 sh -c \
  "apk add --no-cache tar zstd >/dev/null 2>&1 && \
   tar --sort=name --owner=0 --group=0 --numeric-owner --mtime='UTC 2020-01-01' \
       --use-compress-program='zstd -19 -T0' -cf /out/$(basename "$OUT") -C /stage $FILES"
TAR_SHA="$(sha256 "$OUT")"

echo
echo "=================================================================="
echo "  artifact : $NAME:$DST_TAG"
echo "  tar.zst sha256 (PIN as the arch override binary_sha256):"
echo "    $TAR_SHA"
echo "=================================================================="

# Optional signing, same convention as the build scripts.
SIG_LAYER=()
if [ -n "${SIGN_KEY:-}" ]; then
  KEY_DIR="$(cd "$(dirname "$SIGN_KEY")" && pwd)"
  MTTY=""; [ -z "${SIGN_NOPASS:-}" ] && [ -t 0 ] && MTTY="-it"
  docker run --rm $MTTY -v "$WORK:/w" -v "$KEY_DIR:/keys:ro" alpine:3.20 sh -c \
    "apk add --no-cache minisign >/dev/null 2>&1 && minisign -S ${SIGN_NOPASS:+-W} \
     -s /keys/$(basename "$SIGN_KEY") -m /w/$(basename "$OUT") \
     -t 'sage-is $NAME:$DST_TAG sha256=$TAR_SHA'"
  SIG_LAYER=("$(basename "$OUT").minisig:application/vnd.sage-is.sprig.minisig")
fi
docker run --rm --network "$NET" -v "$WORK:/w" -w /w "$ORAS_IMG" \
  push --plain-http "$REGISTRY_INTERNAL/$NAME:$DST_TAG" --artifact-type "$ARTIFACT_TYPE" \
  "$(basename "$OUT"):$LAYER_TYPE" ${SIG_LAYER[@]+"${SIG_LAYER[@]}"} >/dev/null
echo "pushed: $REGISTRY_INTERNAL/$NAME:$DST_TAG"
echo "catalog override: \"amd64\": {\"tag\": \"$DST_TAG\", \"binary_sha256\": \"$TAR_SHA\"}"
