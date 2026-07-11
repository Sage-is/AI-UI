#!/usr/bin/env bash
# build-sprig-minilm.sh — graft #3 packaging.
#
# Packs the cached chroma ONNX all-MiniLM-L6-v2 weights + a sprig.yaml manifest
# into an OCI artifact (one tar.zst layer) and pushes it to a registry via oras.
# Prints the tar.zst sha256 to pin in the supervisor CATALOG (binary_sha256).
#
# Local dev (default): pushes to localhost:5000 over --plain-http; with
# MANAGE_REGISTRY=1 it also runs a registry:2 container on $NETWORK.
#
# PRODUCTION (the user's one-line swap — NOT run here):
#   REGISTRY=ghcr.io/sage-is INSECURE=0  (oras login ghcr.io first)
#   and set the catalog entry repo -> ghcr.io/sage-is/... , insecure: False.
#
# Requirements: oras, zstd, tar, and sha256sum|shasum on PATH; the 6 ONNX files
# present. Populate once on the BUILD host (this is where the one-time pull
# lives, never the operator's box):
#   python3 -c 'from chromadb.utils.embedding_functions import DefaultEmbeddingFunction as D; D()(["seed"])'
set -euo pipefail

REGISTRY="${REGISTRY:-localhost:5000}"
NAME="${NAME:-sprig-embedding-minilm-onnx}"
TAG="${TAG:-v1}"
INSECURE="${INSECURE:-1}"             # 1 -> oras --plain-http (localhost dev)
MANAGE_REGISTRY="${MANAGE_REGISTRY:-0}"
NETWORK="${NETWORK:-sage-network}"
ARTIFACT_TYPE="application/vnd.sage-is.sprig.v1"
LAYER_TYPE="application/vnd.sage-is.sprig.tar+zstd"

CHROMA_CACHE="${CHROMA_CACHE:-$HOME/.cache/chroma}"
ONNX_SRC="$CHROMA_CACHE/onnx_models/all-MiniLM-L6-v2/onnx"
OUT_DIR="${OUT_DIR:-$(pwd)}"
OUT="$OUT_DIR/$NAME-$TAG.tar.zst"

REQUIRED=(model.onnx tokenizer.json tokenizer_config.json config.json vocab.txt special_tokens_map.json)

sha256() { if command -v sha256sum >/dev/null; then sha256sum "$1" | cut -d' ' -f1; else shasum -a 256 "$1" | cut -d' ' -f1; fi; }

# --- preflight ----------------------------------------------------------------
command -v oras >/dev/null || { echo "ERROR: oras not on PATH" >&2; exit 1; }
command -v zstd >/dev/null || { echo "ERROR: zstd not on PATH" >&2; exit 1; }
[ -d "$ONNX_SRC" ] || { echo "ERROR: ONNX cache not at $ONNX_SRC (graft an ONNX cultivar once to populate it)" >&2; exit 1; }
for f in "${REQUIRED[@]}"; do [ -f "$ONNX_SRC/$f" ] || { echo "ERROR: missing $ONNX_SRC/$f" >&2; exit 1; }; done

# --- assemble the artifact tree (root mirrors the chroma cache subtree) --------
STAGE="$(mktemp -d)"; trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$STAGE/onnx_models/all-MiniLM-L6-v2/onnx"
cp "$ONNX_SRC"/* "$STAGE/onnx_models/all-MiniLM-L6-v2/onnx/"
# zero-UUID telemetry id so chromadb treats the cache as initialized (offline)
printf '00000000-0000-0000-0000-000000000000' > "$STAGE/telemetry_user_id"
MODEL_SHA="$(sha256 "$STAGE/onnx_models/all-MiniLM-L6-v2/onnx/model.onnx")"

cat > "$STAGE/sprig.yaml" <<YAML
spec_version: v1
delivery: oci-artifact
capability: embedding
cultivar: minilm-onnx
variety: linux-any-cpu
sprig_version: v1.0.0
backend: onnx
model: all-MiniLM-L6-v2
dim: 384
model_sha256: ${MODEL_SHA}
license: Apache-2.0
offline: true
extract_to: cache/chroma
YAML

# --- pack tar.zst (sorted, no mtime/owner noise -> reproducible) ---------------
# zstd -19: bare `zstd` is level 3 — measurably fatter artifacts for the same
# decode speed. (--long=27 only for site-packages-shaped sprigs, and only with
# the extractor passing the matching flag: 128MB decode-window ceiling.)
tar --sort=name --owner=0 --group=0 --numeric-owner --mtime='UTC 2020-01-01' \
    --use-compress-program='zstd -19 -T0' \
    -cf "$OUT" -C "$STAGE" sprig.yaml telemetry_user_id onnx_models
TAR_SHA="$(sha256 "$OUT")"

echo
echo "=================================================================="
echo "  artifact : $OUT"
echo "  tar.zst sha256 (PIN THIS in CATALOG binary_sha256):"
echo "    $TAR_SHA"
echo "  model.onnx sha256: $MODEL_SHA"
echo "=================================================================="

# --- optional: bring up a local registry:2 ------------------------------------
if [ "$MANAGE_REGISTRY" = "1" ]; then
  docker network inspect "$NETWORK" >/dev/null 2>&1 || docker network create "$NETWORK"
  if ! docker ps --format '{{.Names}}' | grep -qx local-registry; then
    docker rm -f local-registry >/dev/null 2>&1 || true
    docker run -d --name local-registry --network "$NETWORK" -p 5000:5000 registry:2 >/dev/null
  fi
  for _ in $(seq 1 30); do curl -fsS "http://localhost:5000/v2/" >/dev/null 2>&1 && break; sleep 0.5; done
fi

# --- push (tar.zst layer + optional .minisig layer; sprig.yaml is inside) -----
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
