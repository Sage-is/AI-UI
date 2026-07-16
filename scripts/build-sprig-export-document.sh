#!/usr/bin/env bash
# build-sprig-export-document.sh — package the export-document Sprig™ (chat →
# PDF export: fpdf2 + fontTools + pillow + the CJK Noto fonts), per host arch.
#
# ROOT-ANCHORED tar (catalog target: "/"): the closure lands under
# usr/local/lib/python3.11/site-packages/ and the fonts under app/static/fonts/
# — one extract restores both the python deps and the font files pdf_generator.py
# + the frontend pdf-style.css read. Sentinel:
# usr/local/lib/python3.11/site-packages/fpdf. Fonts come from the repo
# (app/static/fonts, the tree the Dockerfile dedups OUT of the runtime image).
#
# Multi-arch: pillow ships arch wheels, so run per arch. arm64 keeps the live
# top-level tag; ARCH=amd64 tags `${TAG}-amd64` for the arches["amd64"] pin.
#
# Version pins track app/backend/requirements.txt (sprig closure comments):
#   fpdf2==2.8.2, pillow==12.2.0 (CVE pins live HERE, not the base image).
#
# Local dev (default): pushes to localhost:5000 over --plain-http via a
# DOCKERIZED oras (no host install). Production publishing goes through
# publish-sprigs.sh (local -> ghcr).
set -euo pipefail

REGISTRY="${REGISTRY:-localhost:5000}"
NAME="${NAME:-sprig-export-document}"
TAG="${TAG:-v1}"
INSECURE="${INSECURE:-1}"
MANAGE_REGISTRY="${MANAGE_REGISTRY:-0}"
NETWORK="${NETWORK:-sage-network}"
ARTIFACT_TYPE="application/vnd.sage-is.sprig.v1"
LAYER_TYPE="application/vnd.sage-is.sprig.tar+zstd"
ORAS_IMG="${ORAS_IMG:-ghcr.io/oras-project/oras:v1.2.0}"

_RAW_ARCH="$(uname -m)"
case "${ARCH:-$_RAW_ARCH}" in
  arm64|aarch64) ARCH=arm64 ;;
  amd64|x86_64)  ARCH=amd64 ;;
  *) echo "ERROR: unsupported ARCH='${ARCH:-$_RAW_ARCH}' (want arm64|amd64)" >&2; exit 1 ;;
esac
PLATFORM="${PLATFORM:-linux/$ARCH}"
ARCHTAG="$TAG"; [ "$ARCH" = "amd64" ] && ARCHTAG="$TAG-amd64"

PIP_SPECS="'fpdf2==2.8.2' 'pillow==12.2.0' 'fonttools'"

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FONTS_SRC="${FONTS_SRC:-$REPO_ROOT/app/static/fonts}"
WORK="${WORK:-/tmp/sprig-build/export-document-$ARCH}"
OUT_DIR="${OUT_DIR:-$(pwd)}"
OUT="$OUT_DIR/$NAME-$ARCHTAG.tar.zst"

sha256() { if command -v sha256sum >/dev/null; then sha256sum "$1" | cut -d' ' -f1; else shasum -a 256 "$1" | cut -d' ' -f1; fi; }

# --- preflight ----------------------------------------------------------------
command -v docker >/dev/null || { echo "ERROR: docker not on PATH" >&2; exit 1; }
[ -f "$FONTS_SRC/NotoSansSC-Regular.ttf" ] || { echo "ERROR: CJK fonts not at $FONTS_SRC" >&2; exit 1; }
rm -rf "$WORK"; mkdir -p "$WORK/root/usr/local/lib/python3.11/site-packages" "$WORK/root/app/static"

# --- 1. build the wheel closure for $PLATFORM ----------------------------------
echo "== building export-document closure for $PLATFORM =="
docker run --rm --platform "$PLATFORM" -v "$WORK:/w" python:3.11-slim bash -c "
  set -e
  pip install --no-cache-dir --no-compile --target /w/root/usr/local/lib/python3.11/site-packages \
    $PIP_SPECS 2>/w/pip.log || { tail -40 /w/pip.log; exit 1; }
"
[ -d "$WORK/root/usr/local/lib/python3.11/site-packages/fpdf" ] || { echo "ERROR: fpdf/ not in closure" >&2; exit 1; }

# --- 2. stage fonts + sprig.yaml (root-anchored tree) ---------------------------
cp -R "$FONTS_SRC" "$WORK/root/app/static/fonts"
cat > "$WORK/root/sprig.yaml" <<YAML
spec_version: v1
delivery: oci-artifact
capability: export
cultivar: export-document
variety: linux-$ARCH
sprig_version: v1.0.0
backend: root-overlay
target: /
sentinel: usr/local/lib/python3.11/site-packages/fpdf
license: LGPL-3.0 (fpdf2) / OFL-1.1 (Noto fonts)
offline: true
YAML

# --- 3. reproducible pack ---------------------------------------------------------
docker run --rm -v "$WORK/root:/root_tree:ro" -v "$OUT_DIR:/out" alpine sh -c \
  "apk add --no-cache tar zstd >/dev/null && \
   tar --sort=name --owner=0 --group=0 --numeric-owner --mtime='UTC 2020-01-01' \
       --use-compress-program='zstd -19 -T0' \
       -cf /out/$(basename "$OUT") -C /root_tree ."
TAR_SHA="$(sha256 "$OUT")"

# --- 4. SANITY GATE: fpdf renders a CJK page on the TARGET arch --------------------
echo "== sanity gate: fpdf2 + Noto CJK render on $PLATFORM =="
docker run --rm --platform "$PLATFORM" -v "$WORK/root:/r:ro" python:3.11-slim \
  python -c "
import sys; sys.path.insert(0,'/r/usr/local/lib/python3.11/site-packages')
from fpdf import FPDF
pdf = FPDF()
pdf.add_font('NotoSansSC', '', '/r/app/static/fonts/NotoSansSC-Regular.ttf')
pdf.add_page(); pdf.set_font('NotoSansSC', size=12)
pdf.cell(text='PDF export sanity: 你好，Sprig')
out = pdf.output()
assert bytes(out[:5]) == b'%PDF-', out[:8]
print('fpdf2 renders CJK OK,', len(out), 'bytes')
" || { echo "SANITY GATE FAILED — pdf render broken on $ARCH" >&2; exit 1; }

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

# --- 5. optional local registry ------------------------------------------------------
if [ "$MANAGE_REGISTRY" = "1" ]; then
  docker network inspect "$NETWORK" >/dev/null 2>&1 || docker network create "$NETWORK"
  if ! docker ps --format '{{.Names}}' | grep -qx local-registry; then
    docker rm -f local-registry >/dev/null 2>&1 || true
    docker run -d --name local-registry --network "$NETWORK" -p 5000:5000 -v sprig-registry-data:/var/lib/registry registry:2 >/dev/null
  fi
  for _ in $(seq 1 30); do curl -fsS "http://localhost:5000/v2/" >/dev/null 2>&1 && break; sleep 0.5; done
fi

# --- 6. sign (optional) + push --------------------------------------------------------
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
PUSH_REG="$REGISTRY"; ORAS_NET=()
case "$REGISTRY" in localhost:*|127.0.0.1:*)
  PUSH_REG="local-registry:${REGISTRY##*:}"; ORAS_NET=(--network "$NETWORK");;
esac
PUSH=(push "$PUSH_REG/$NAME:$ARCHTAG" --artifact-type "$ARTIFACT_TYPE")
[ "$INSECURE" = "1" ] && PUSH+=(--plain-http)
docker run --rm ${ORAS_NET[@]+"${ORAS_NET[@]}"} -v "$OUT_DIR:/w" -w /w "$ORAS_IMG" \
  "${PUSH[@]}" "$(basename "$OUT"):$LAYER_TYPE" ${SIG_LAYER[@]+"${SIG_LAYER[@]}"}

echo
echo "pushed: $REGISTRY/$NAME:$ARCHTAG"
