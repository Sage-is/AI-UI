#!/usr/bin/env bash
# build-sprig-docling.sh — package the docling Sprig™: docling-serve in a
# bundled relocatable venv (CPU torch + pre-seeded models), per host arch.
# HEAVY: the artifact is multi-GB and the amd64 build runs torch under QEMU.
#
# The tar carries {venv/, models/, run-docling.sh} at its root. The supervisor
# runs `{artifact_dir}/run-docling.sh run --host 127.0.0.1 --port {port}`
# (server: docling-serve); the launcher sets HF_HOME at its pre-seeded model
# cache (HF_HUB_OFFLINE=1 — no runtime egress) and execs the venv docling-serve.
# docling_dispatch points DOCLING_SERVER_URL at the loopback and selects
# CONTENT_EXTRACTION_ENGINE=docling. Replaces the http://docling:5001 sidecar.
# Health = GET /health.
#
# ── VERIFY DURING FIRST BUILD (I could not run this multi-GB torch build): ──
#   * DOCLING_SERVE_PKG / the `docling-serve` console script name + `run` CLI
#     (--host/--port) against the pinned version.
#   * The model pre-seed step actually populates $HF_HOME (below warms it by
#     converting a tiny doc; swap for `docling-tools models download` if that
#     API is stable in the pinned version).
#   * Relocatability: the venv is invoked via absolute python, and torch .so use
#     $ORIGIN RPATHs, so it should run from the extract dir — confirm in the gate.
set -euo pipefail

REGISTRY="${REGISTRY:-localhost:5000}"
NAME="${NAME:-sprig-docling}"
TAG="${TAG:-v1}"
INSECURE="${INSECURE:-1}"
MANAGE_REGISTRY="${MANAGE_REGISTRY:-0}"
NETWORK="${NETWORK:-sage-network}"
ARTIFACT_TYPE="application/vnd.sage-is.sprig.v1"
LAYER_TYPE="application/vnd.sage-is.sprig.tar+zstd"
ORAS_IMG="${ORAS_IMG:-ghcr.io/oras-project/oras:v1.2.0}"

PY_IMAGE="${PY_IMAGE:-python:3.11-bookworm}"
DOCLING_SERVE_SPEC="${DOCLING_SERVE_SPEC:-docling-serve}"   # pin e.g. docling-serve==0.x.y
TORCH_SPEC="${TORCH_SPEC:-torch --extra-index-url https://download.pytorch.org/whl/cpu}"

_RAW_ARCH="$(uname -m)"
case "${ARCH:-$_RAW_ARCH}" in
  arm64|aarch64) ARCH=arm64 ;;
  amd64|x86_64)  ARCH=amd64 ;;
  *) echo "ERROR: unsupported ARCH='${ARCH:-$_RAW_ARCH}' (want arm64|amd64)" >&2; exit 1 ;;
esac
PLATFORM="${PLATFORM:-linux/$ARCH}"
ARCHTAG="$TAG"; [ "$ARCH" = "amd64" ] && ARCHTAG="$TAG-amd64"

WORK="${WORK:-/tmp/sprig-build/docling-$ARCH}"
OUT_DIR="$WORK/out"
OUT="$OUT_DIR/${NAME}-${ARCHTAG}.tar.zst"
rm -rf "$WORK"; mkdir -p "$WORK/stage" "$OUT_DIR"

sha256() { shasum -a 256 "$1" | awk '{print $1}'; }

# --- 1. relocatable venv + CPU torch + docling-serve + pre-seeded models --------
echo "== building docling-serve venv on $PLATFORM (heavy; amd64 runs under QEMU) =="
docker run --rm --platform "$PLATFORM" -v "$WORK/stage:/w" -e PIP_NO_CACHE_DIR=1 "$PY_IMAGE" bash -ec '
  cd /w
  python -m venv --copies venv
  ./venv/bin/pip install -U pip wheel >/dev/null
  ./venv/bin/pip install '"$TORCH_SPEC"'
  ./venv/bin/pip install "'"$DOCLING_SERVE_SPEC"'"
  # confirm the console script exists (fail early if the package name changed)
  test -x ./venv/bin/docling-serve || { echo "ERROR: venv/bin/docling-serve missing — check DOCLING_SERVE_SPEC"; exit 1; }

  # Pre-seed the models into an in-artifact HF cache so runtime is fully offline.
  # VERIFY: converting a tiny doc warms whatever models the pinned docling needs.
  mkdir -p /w/models
  export HF_HOME=/w/models TORCH_HOME=/w/models/torch
  printf "warm the docling models" > /tmp/warm.txt
  ./venv/bin/python - <<PY || { echo "ERROR: model pre-seed failed — see VERIFY note in the recipe"; exit 1; }
from docling.document_converter import DocumentConverter
DocumentConverter().convert("/tmp/warm.txt")
print("docling models warmed into", __import__("os").environ["HF_HOME"])
PY
  du -sh venv models
'

# in-artifact launcher: HF_HOME relative to itself, offline, exec the venv server
cat > "$WORK/stage/run-docling.sh" <<"SH"
#!/bin/sh
HERE="$(cd "$(dirname "$0")" && pwd)"
export HF_HOME="$HERE/models"
export TORCH_HOME="$HERE/models/torch"
export HF_HUB_OFFLINE=1
exec "$HERE/venv/bin/python" "$HERE/venv/bin/docling-serve" "$@"
SH
chmod 0755 "$WORK/stage/run-docling.sh"

# --- 2. SANITY GATE: launcher serves /health on the TARGET arch ----------------
echo "== sanity gate: docling-serve /health on $PLATFORM =="
docker run --rm --platform "$PLATFORM" -v "$WORK/stage:/s:ro" "$PY_IMAGE" bash -ec '
  cp -r /s /tmp/art
  /tmp/art/run-docling.sh run --host 127.0.0.1 --port 5001 >/tmp/docling.log 2>&1 &
  PID=$!
  for i in $(seq 1 120); do curl -fsS http://127.0.0.1:5001/health >/dev/null 2>&1 && break; sleep 2; done
  curl -fsS http://127.0.0.1:5001/health && echo "  /health OK"
  kill "$PID" 2>/dev/null || true
' || { echo "SANITY GATE FAILED — docling-serve broken on $ARCH (see VERIFY notes + /tmp/docling.log)" >&2; exit 1; }

# --- 3. reproducible pack {venv/, models/, run-docling.sh} ----------------------
docker run --rm -v "$WORK/stage:/stage:ro" -v "$OUT_DIR:/out" alpine sh -c \
  "apk add --no-cache tar zstd >/dev/null && \
   tar --sort=name --owner=0 --group=0 --numeric-owner --mtime='UTC 2020-01-01' \
       --use-compress-program='zstd -19 -T0' \
       -cf /out/$(basename "$OUT") -C /stage venv models run-docling.sh"
TAR_SHA="$(sha256 "$OUT")"

echo
echo "=================================================================="
echo "  artifact : $OUT   (arch: $ARCH, docling-serve)"
echo "  size     : $(du -h "$OUT" | awk '{print $1}')"
echo "  tar.zst sha256 (PIN in CATALOG 'docling'):"
echo "    $TAR_SHA"
if [ "$ARCH" = "amd64" ]; then
  echo "  -> arches[\"amd64\"] = {\"tag\": \"$ARCHTAG\", \"binary_sha256\": \"$TAR_SHA\"}"
else
  echo "  -> arm64 pin (TAG=$TAG): \"$TAR_SHA\""
fi
echo "=================================================================="

# --- 4. optional local registry ------------------------------------------------
if [ "$MANAGE_REGISTRY" = "1" ]; then
  docker network inspect "$NETWORK" >/dev/null 2>&1 || docker network create "$NETWORK"
  if ! docker ps --format '{{.Names}}' | grep -qx local-registry; then
    docker rm -f local-registry >/dev/null 2>&1 || true
    docker run -d --name local-registry --network "$NETWORK" -p 5000:5000 -v sprig-registry-data:/var/lib/registry registry:2 >/dev/null
  fi
  for _ in $(seq 1 30); do curl -fsS "http://localhost:5000/v2/" >/dev/null 2>&1 && break; sleep 0.5; done
fi

# --- 5. push (dockerized oras; no host install) --------------------------------
PUSH_REG="$REGISTRY"; ORAS_NET=()
case "$REGISTRY" in localhost:*|127.0.0.1:*)
  PUSH_REG="local-registry:${REGISTRY##*:}"; ORAS_NET=(--network "$NETWORK");;
esac
PUSH=(push "$PUSH_REG/$NAME:$ARCHTAG" --artifact-type "$ARTIFACT_TYPE")
[ "$INSECURE" = "1" ] && PUSH+=(--plain-http)
docker run --rm ${ORAS_NET[@]+"${ORAS_NET[@]}"} -v "$OUT_DIR:/w" -w /w "$ORAS_IMG" \
  "${PUSH[@]}" "$(basename "$OUT"):$LAYER_TYPE"

echo
echo "pushed: $REGISTRY/$NAME:$ARCHTAG"
