#!/usr/bin/env bash
# build-sprig-vector-chroma.sh — package the vector-chroma Sprig™ (the chromadb
# vector-DB runtime + ML closure) as a site-packages OVERLAY, per host arch.
#
# The tar carries the python-wheel closure (chromadb + onnxruntime + numpy +
# tokenizers + huggingface_hub + hnswlib + grpc + posthog) with the package dirs
# at its ROOT, so artifact.py's app-dir delivery extracts it straight into
# /usr/local/lib/python3.11/site-packages (sentinel: chromadb). This ALSO
# supplies the onnxruntime the multilingual-e5-large / bge / minilm ONNX
# embedding cultivars ride — so it unblocks BOTH document search and local
# embedding on a slim rootstock.
#
# Multi-arch: run once per arch. arm64 keeps the catalog's top-level tag (its
# artifact is already live); an amd64 run tags `${TAG}-amd64` and prints the
# sha256 to pin in the CATALOG entry's arches["amd64"] override. Wheels are
# manylinux (glibc), pulled for the *container* arch — so `--platform linux/amd64`
# under QEMU yields the amd64 closure natively, no pip --platform gymnastics.
#
# Version pins track app/backend/requirements.txt (the sprig closure comments):
#   chromadb==0.6.3, tokenizers<=0.23.0, huggingface-hub<1.0, numpy<2.
#
# Local dev (default): pushes to localhost:5000 over --plain-http via a
# DOCKERIZED oras (no host install — same container pattern as repack/publish/
# sign). Production publishing goes through publish-sprigs.sh (local -> ghcr).
# Requirements: docker (buildx/QEMU for cross-arch), sha256sum|shasum.
set -euo pipefail

# Shared boilerplate: constants, arch-normalize, sha256, registry, push, timing.
. "$(dirname "${BASH_SOURCE[0]}")/lib/sprig-build.sh"
NAME="${NAME:-sprig-vector-chroma}"
TAG="${TAG:-v2}"                        # catalog vector-chroma is at v2 (preserve before defaults)
sprig_build_defaults
sprig_timing_start

# Host arch this artifact serves. Default: the build host. amd64 gets a
# `-amd64`-suffixed tag so it sits beside the arm64 artifact under one repo.
sprig_arch_normalize

# Closure pins (keep in lockstep with app/backend/requirements.txt).
CHROMADB_PIN="${CHROMADB_PIN:-chromadb==0.6.3}"
# Each spec single-quoted so the CONTAINER shell keeps <= / < intact (these
# expand in the host shell into the docker bash -c string, quotes and all).
PIP_SPECS="'$CHROMADB_PIN' 'tokenizers<=0.23.0' 'huggingface-hub<1.0' 'numpy<2'"

WORK="${WORK:-/tmp/sprig-build/vector-chroma-$ARCH}"
OUT_DIR="${OUT_DIR:-$(pwd)}"
OUT="$OUT_DIR/$NAME-$ARCHTAG.tar.zst"


# --- preflight ----------------------------------------------------------------
command -v docker >/dev/null || { echo "ERROR: docker not on PATH" >&2; exit 1; }
rm -rf "$WORK"; mkdir -p "$WORK/pkg"

# --- 1. build the wheel closure for $PLATFORM (dockerized; QEMU for cross-arch) -
# pip --target installs the packages flat under /pkg (chromadb/, numpy/, ...) —
# exactly the layout artifact.py extracts into site-packages. --no-compile keeps
# the tree closer to reproducible (no .pyc timestamps); the child recompiles lazily.
echo "== building chromadb closure for $PLATFORM =="
docker run --rm --platform "$PLATFORM" -v "$WORK:/w" python:3.11-slim bash -c "
  set -e
  pip install --no-cache-dir --no-compile --target /w/pkg $PIP_SPECS 2>/w/pip.log || { tail -40 /w/pip.log; exit 1; }
  python - <<'PY'
import os
n = sum(len(f) for _,_,f in os.walk('/w/pkg'))
print('closure files:', n)
PY
"
[ -d "$WORK/pkg/chromadb" ] || { echo "ERROR: chromadb/ not in closure (pip failed?)" >&2; exit 1; }

# --- 2. stage: sprig.yaml at root alongside the package tree --------------------
cat > "$WORK/pkg/sprig.yaml" <<YAML
spec_version: v1
delivery: oci-artifact
capability: vector
cultivar: vector-chroma
variety: linux-$ARCH
sprig_version: v2.0.0
backend: site-packages-overlay
target: /usr/local/lib/python3.11/site-packages
sentinel: chromadb
license: Apache-2.0
offline: true
YAML

# --- 3. reproducible pack (GNU tar via docker: macOS bsdtar lacks --sort) -------
docker run --rm -v "$WORK/pkg:/pkg:ro" -v "$OUT_DIR:/out" alpine sh -c \
  "apk add --no-cache tar zstd >/dev/null && \
   tar --sort=name --owner=0 --group=0 --numeric-owner --mtime='UTC 2020-01-01' \
       --use-compress-program='zstd -19 -T0' \
       -cf /out/$(basename "$OUT") -C /pkg ."
TAR_SHA="$(sha256 "$OUT")"

# --- 4. SANITY GATE: the closure imports under the TARGET arch -----------------
echo "== sanity gate: import chromadb/onnxruntime/numpy/tokenizers on $PLATFORM =="
docker run --rm --platform "$PLATFORM" -v "$WORK/pkg:/site:ro" python:3.11-slim \
  python -c "import sys; sys.path.insert(0,'/site'); import chromadb, onnxruntime, numpy, tokenizers; print('closure imports OK:', chromadb.__version__)" \
  || { echo "SANITY GATE FAILED — closure does not import on $ARCH" >&2; exit 1; }

echo
echo "=================================================================="
echo "  artifact : $OUT   (arch: $ARCH)"
echo "  tar.zst sha256 (PIN in CATALOG):"
echo "    $TAR_SHA"
if [ "$ARCH" = "amd64" ]; then
  echo "  -> arches[\"amd64\"] = {\"tag\": \"$ARCHTAG\", \"binary_sha256\": \"$TAR_SHA\"}"
else
  echo "  -> top-level binary_sha256 (arm64): \"$TAR_SHA\""
fi
echo "=================================================================="

# --- 5. optional local registry --------------------------------------------------
sprig_ensure_registry

# --- 6. sign (optional) + push --------------------------------------------------
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
