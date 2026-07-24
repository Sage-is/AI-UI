#!/usr/bin/env bash
# build-sprig-rag-loaders.sh — package the rag-loaders Sprig™ (langchain RAG
# engines + document loaders) as a site-packages OVERLAY, per host arch.
#
# The tar carries the closure (langchain + langchain-community + pypdf +
# docx2txt + rank_bm25 + numpy) with package dirs at its ROOT; artifact.py's
# app-dir delivery extracts it into /usr/local/lib/python3.11/site-packages
# (sentinel: langchain). Restores document chunking/ingestion on a slim
# rootstock; web-page loading activates after a restart (catalog note).
#
# Multi-arch: arm64 keeps the live top-level tag; ARCH=amd64 tags `${TAG}-amd64`
# and prints the sha to pin in the CATALOG arches["amd64"] override. Same
# QEMU-container wheel strategy as build-sprig-vector-chroma.sh.
#
# Version pins track app/backend/requirements.txt (sprig closure comments):
#   langchain==0.3.30 (CVE-2026-45134), langchain-community==0.3.27
#   (CVE-2025-6984), pypdf==4.3.1, docx2txt==0.8, numpy<2, rank_bm25.
#
# Local dev (default): pushes to localhost:5000 over --plain-http via a
# DOCKERIZED oras (no host install). Production publishing goes through
# publish-sprigs.sh (local -> ghcr).
set -euo pipefail

# Shared boilerplate: constants, arch-normalize, sha256, registry, push, timing.
. "$(dirname "${BASH_SOURCE[0]}")/lib/sprig-build.sh"
NAME="${NAME:-sprig-rag-loaders}"
sprig_build_defaults
sprig_timing_start

sprig_arch_normalize

PIP_SPECS="'langchain==0.3.30' 'langchain-community==0.3.27' 'pypdf==4.3.1' 'docx2txt==0.8' 'rank_bm25' 'numpy<2'"

WORK="${WORK:-/tmp/sprig-build/rag-loaders-$ARCH}"
OUT_DIR="${OUT_DIR:-$(pwd)}"
OUT="$OUT_DIR/$NAME-$ARCHTAG.tar.zst"

# --- preflight ----------------------------------------------------------------
command -v docker >/dev/null || { echo "ERROR: docker not on PATH" >&2; exit 1; }
rm -rf "$WORK"; mkdir -p "$WORK/pkg"

# --- 1. build the wheel closure for $PLATFORM ----------------------------------
echo "== building rag-loaders closure for $PLATFORM =="
docker run --rm --platform "$PLATFORM" -v "$WORK:/w" python:3.11-slim bash -c "
  set -e
  pip install --no-cache-dir --no-compile --target /w/pkg $PIP_SPECS 2>/w/pip.log || { tail -40 /w/pip.log; exit 1; }
  python -c \"import os; print('closure files:', sum(len(f) for _,_,f in os.walk('/w/pkg')))\"
"
[ -d "$WORK/pkg/langchain" ] || { echo "ERROR: langchain/ not in closure (pip failed?)" >&2; exit 1; }

# --- 2. stage: sprig.yaml at root alongside the package tree --------------------
cat > "$WORK/pkg/sprig.yaml" <<YAML
spec_version: v1
delivery: oci-artifact
capability: rag
cultivar: rag-loaders
variety: linux-$ARCH
sprig_version: v1.0.0
backend: site-packages-overlay
target: /usr/local/lib/python3.11/site-packages
sentinel: langchain
license: MIT
offline: true
YAML

# --- 3. reproducible pack --------------------------------------------------------
docker run --rm -v "$WORK/pkg:/pkg:ro" -v "$OUT_DIR:/out" alpine sh -c \
  "apk add --no-cache tar zstd >/dev/null && \
   tar --sort=name --owner=0 --group=0 --numeric-owner --mtime='UTC 2020-01-01' \
       --use-compress-program='zstd -19 -T0' \
       -cf /out/$(basename "$OUT") -C /pkg ."
TAR_SHA="$(sha256 "$OUT")"

# --- 4. SANITY GATE: loaders import + split on the TARGET arch ------------------
echo "== sanity gate: langchain splitter + loaders import on $PLATFORM =="
docker run --rm --platform "$PLATFORM" -v "$WORK/pkg:/site:ro" python:3.11-slim \
  python -c "
import sys; sys.path.insert(0,'/site')
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
import pypdf, docx2txt, rank_bm25
chunks = RecursiveCharacterTextSplitter(chunk_size=20, chunk_overlap=0).split_text('the rootstock grafts its rag engines back on')
assert len(chunks) > 1, chunks
print('rag closure OK: split ->', len(chunks), 'chunks')
" || { echo "SANITY GATE FAILED — rag closure broken on $ARCH" >&2; exit 1; }

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

# --- 5. optional local registry ---------------------------------------------------
sprig_ensure_registry

# --- 6. sign (optional) + push -----------------------------------------------------
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
# Dockerized oras push (no host oras); rides the optional SIG_LAYER set above.
sprig_push

echo
echo "pushed: $REGISTRY/$NAME:$ARCHTAG"
sprig_timing_end
