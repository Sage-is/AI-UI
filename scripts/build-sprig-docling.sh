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
# Everything (venv build, model pre-seed, sanity gate, reproducible pack) runs in
# ONE container on the container-native fs, so the multi-GB torch tree NEVER
# crosses the macOS Docker bind mount — which is slow AND hits "Directory not
# empty" on cleanup. Only the final .tar.zst crosses out, into $OUT_DIR.
#
# ── VERIFY DURING FIRST BUILD (I could not run this multi-GB torch build): ──
#   * DOCLING_SERVE_SPEC / the `docling-serve` console script + `run --host/--port`.
#   * The model pre-seed populates $HF_HOME (tries docling's model_downloader,
#     falls back to a convert-warm) so runtime is offline.
set -euo pipefail

# Shared boilerplate: constants, arch-normalize, sha256, registry, push, timing.
. "$(dirname "${BASH_SOURCE[0]}")/lib/sprig-build.sh"
NAME="${NAME:-sprig-docling}"
sprig_build_defaults
sprig_timing_start

PY_IMAGE="${PY_IMAGE:-python:3.11-bookworm}"
DOCLING_SERVE_SPEC="${DOCLING_SERVE_SPEC:-docling-serve}"   # pin e.g. docling-serve==0.x.y
# torch AND torchvision must be the SAME build — CPU torch + PyPI (CUDA)
# torchvision => "operator torchvision::nms does not exist". Installing both from
# the CPU extra index makes pip prefer the +cpu local versions (PEP 440), which
# match; deps like numpy still resolve from PyPI. CPU_INDEX is reused on the
# docling-serve install so it can't pull a CUDA torchvision back in.
CPU_INDEX="${CPU_INDEX:-https://download.pytorch.org/whl/cpu}"
PYPI_INDEX="${PYPI_INDEX:-https://pypi.org/simple}"
TORCH_SPEC="${TORCH_SPEC:-torch torchvision --extra-index-url $CPU_INDEX}"

sprig_arch_normalize

WORK="${WORK:-/tmp/sprig-build/docling-$ARCH}"
OUT_DIR="$WORK/out"
OUT="$OUT_DIR/${NAME}-${ARCHTAG}.tar.zst"

# Clean any prior build. A heavy torch tree can be container-owned and/or hit
# FUSE "Directory not empty" on a host rm, so nuke it from inside a root
# container and don't let it abort the run.
docker run --rm -v /tmp/sprig-build:/b alpine rm -rf "/b/docling-$ARCH" 2>/dev/null || true
rm -rf "$WORK" 2>/dev/null || true
mkdir -p "$OUT_DIR"

# --- ONE container: venv + torch + docling-serve + pre-seed + gate + pack -------
echo "== building docling-serve (venv+torch+models), gating, packing on $PLATFORM =="
echo "   (heavy; amd64 runs under QEMU — expect a long wait)"
docker run --rm --platform "$PLATFORM" -e PIP_NO_CACHE_DIR=1 \
  -v "$OUT_DIR:/out" "$PY_IMAGE" bash -ec '
  apt-get update -qq && apt-get install -y -qq zstd >/dev/null
  mkdir -p /build && cd /build

  # 1. relocatable venv + CPU torch + docling-serve, resolved with uv.
  #
  # SAFE index separation (poka-yoke — zero dependency-confusion surface). Each
  # install draws ONLY from the trusted index(es) it needs:
  #   * torch/torchvision  <- pytorch CPU index (+ PyPI for pure-python deps),
  #                           for the matched +cpu builds.
  #   * docling-serve + its huge tree (ray/codeflare/certifi/...) <- PyPI ONLY,
  #     pinned with --index-url so it can NEVER reach the pytorch index. That
  #     index hosts a handful of deps at ancient reproducibility-pins
  #     (certifi==2022.12.7); if the docling resolve could see it, the uv default
  #     first-index-match would take that certifi and fail docling
  #     certifi>=2024.7.4. The fix is pinning to PyPI — NOT
  #     --index-strategy=unsafe-best-match, which would let a high-version
  #     package on EITHER index win (the classic dependency-confusion hole, and
  #     the opposite of our sha-pinned supply-chain stance).
  # torch/torchvision are already installed and satisfy the docling loose pin, so
  # the PyPI-only docling resolve leaves them untouched. pip backtracks for
  # minutes on this tree; uv resolves it in seconds.
  pip install -q uv
  python -m venv --copies venv
  uv pip install --python /build/venv/bin/python '"$TORCH_SPEC"'
  uv pip install --python /build/venv/bin/python --index-url '"$PYPI_INDEX"' "'"$DOCLING_SERVE_SPEC"'"
  # Guard: prove torch<->torchvision ABI matches BEFORE the slow gate (this is
  # the torchvision::nms failure, caught early with a clear message).
  ./venv/bin/python -c "import torchvision; print(\"torchvision ABI ok:\", torchvision.__version__)" \
    || { echo "ERROR: torch/torchvision ABI mismatch — pin matching +cpu versions (torchvision::nms)"; exit 1; }
  test -x ./venv/bin/docling-serve \
    || { echo "ERROR: venv/bin/docling-serve missing — check DOCLING_SERVE_SPEC"; exit 1; }

  # docling/rapidocr pull opencv-python (the GUI build), which links libGL.so.1 —
  # absent in this build image AND in the slim Wolfi Rootstock at runtime. Swap
  # it for the API-compatible headless build (same cv2 module, no libGL) so the
  # table/OCR models import in a headless server, at both build and graft time.
  uv pip uninstall --python /build/venv/bin/python opencv-python || true
  uv pip install --python /build/venv/bin/python --index-url '"$PYPI_INDEX"' opencv-python-headless

  # 2. pre-seed models into an in-artifact HF cache (offline at runtime)
  mkdir -p models
  export HF_HOME=/build/models TORCH_HOME=/build/models/torch
  ./venv/bin/python - <<PY
# Warm EXACTLY what the docling-serve lifespan warm_up_caches loads: the
# StandardPdfPipeline (layout + tableformer models). Using the SAME
# initialize_pipeline the server calls guarantees the OFFLINE runtime finds
# every model it needs — a .txt convert / model_downloader warm missed
# docling-layout-heron, the model the boot warm-up actually downloads.
import os
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter
DocumentConverter().initialize_pipeline(InputFormat.PDF)
print("docling PDF pipeline models cached into", os.environ.get("HF_HOME"))
PY

  # 3. in-artifact launcher: HF_HOME relative to itself, offline, exec venv server
  cat > run-docling.sh <<"SH"
#!/bin/sh
HERE="$(cd "$(dirname "$0")" && pwd)"
export HF_HOME="$HERE/models" TORCH_HOME="$HERE/models/torch" HF_HUB_OFFLINE=1
exec "$HERE/venv/bin/python" "$HERE/venv/bin/docling-serve" "$@"
SH
  chmod 0755 run-docling.sh

  # 4. SANITY GATE: launcher serves /health (dumps the log on failure)
  ./run-docling.sh run --host 127.0.0.1 --port 5001 >/tmp/docling.log 2>&1 &
  PID=$!
  for i in $(seq 1 120); do curl -fsS http://127.0.0.1:5001/health >/dev/null 2>&1 && break; sleep 2; done
  curl -fsS http://127.0.0.1:5001/health \
    || { echo "GATE FAILED: /health never came up"; echo "--- docling.log ---"; cat /tmp/docling.log; kill "$PID" 2>/dev/null; exit 1; }
  echo "  /health OK"
  kill "$PID" 2>/dev/null || true

  # 5. reproducible pack -> /out (only the tar.zst crosses the bind mount)
  du -sh venv models
  tar --sort=name --owner=0 --group=0 --numeric-owner --mtime="UTC 2020-01-01" \
      --use-compress-program="zstd -19 -T0" \
      -cf "/out/'"$(basename "$OUT")"'" venv models run-docling.sh
'
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

# --- optional local registry + push (dockerized oras; no host install) ---------
sprig_ensure_registry
sprig_push

echo
echo "pushed: $REGISTRY/$NAME:$ARCHTAG"
sprig_timing_end
