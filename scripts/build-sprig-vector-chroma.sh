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
#   chromadb==0.6.3, tokenizers<=0.23.0, huggingface-hub<1.0, numpy<2, and
#   opentelemetry-sdk + -exporter-otlp-proto-grpc at the base's opentelemetry-api.
#
# v3 (3.2.1): the OpenTelemetry SDK, gRPC exporter, grpcio and protobuf moved
# here from the base image, beside chromadb, the only thing that imports them.
# The overlay is the closure MINUS what the rootstock ships (step 1b), so this
# recipe needs a built 3.2.1+ rootstock: `make it_build` first (amd64: the
# build VM's `make it_build_amd64`). v2 stays published for 3.2.0 installs.
#
# Local dev (default): pushes to localhost:5000 over --plain-http via a
# DOCKERIZED oras (no host install — same container pattern as repack/publish/
# sign). Production publishing goes through publish-sprigs.sh (local -> ghcr).
# Requirements: docker (buildx/QEMU for cross-arch), sha256sum|shasum.
set -euo pipefail

# Shared boilerplate: constants, arch-normalize, sha256, registry, push, timing.
. "$(dirname "${BASH_SOURCE[0]}")/lib/sprig-build.sh"
NAME="${NAME:-sprig-vector-chroma}"
TAG="${TAG:-v3}"                        # catalog vector-chroma is at v3 (preserve before defaults)
sprig_build_defaults
sprig_timing_start

# Host arch this artifact serves. Default: the build host. amd64 gets a
# `-amd64`-suffixed tag so it sits beside the arm64 artifact under one repo.
sprig_arch_normalize
[ "$ARCH" = arm64 ] || "$(dirname "${BASH_SOURCE[0]}")/gates/docker-preflight.sh" amd64 "ARCH=amd64 $0"

# Closure pins (keep in lockstep with app/backend/requirements.txt).
CHROMADB_PIN="${CHROMADB_PIN:-chromadb==0.6.3}"
# Each spec single-quoted so the CONTAINER shell keeps <= / < intact (these
# expand in the host shell into the docker bash -c string, quotes and all).
PIP_SPECS="'$CHROMADB_PIN' 'tokenizers<=0.23.0' 'huggingface-hub<1.0' 'numpy<2'"

# v3 (3.2.1): OpenTelemetry rides HERE. chromadb imports the SDK and the gRPC
# exporter at import time, and the base image keeps only opentelemetry-api. The
# pin is READ from requirements.txt so the SDK always matches the API the
# rootstock loads; a hand-typed copy would drift.
REQS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/app/backend/requirements.txt"
OTEL_VERSION="$(sed -n 's/^opentelemetry-api==\([0-9.]*\)$/\1/p' "$REQS")"
[ -n "$OTEL_VERSION" ] || { echo "ERROR: no opentelemetry-api==X pin in $REQS" >&2; exit 1; }
PIP_SPECS="$PIP_SPECS 'opentelemetry-sdk==$OTEL_VERSION' 'opentelemetry-exporter-otlp-proto-grpc==$OTEL_VERSION'"

# The rootstock this overlay grafts onto. Its own package list decides what the
# overlay leaves out (step 1b), and the sanity gate runs inside it (step 4).
# Same rule as the Makefile's GIT_TAG: the highest v* tag, not `git describe`,
# which on develop reaches an older tag than the release on master.
IMAGE_TAG_DEFAULT="$(git -C "$(dirname "${BASH_SOURCE[0]}")" tag -l 'v[0-9]*' --sort=-v:refname | sed 's/^v//' | head -n 1)"
if [ "$ARCH" = amd64 ]; then
  ROOTSTOCK_IMG="${ROOTSTOCK_IMG:-sage-is/ai-ui:${IMAGE_TAG_DEFAULT}-amd64}"
else
  ROOTSTOCK_IMG="${ROOTSTOCK_IMG:-sage-is/ai-ui:latest}"
fi

WORK="${WORK:-${SPRIG_BUILD_ROOT:-$HOME/.cache/ai-ui/sprig-build}/vector-chroma-$ARCH}"
OUT_DIR="${OUT_DIR:-$(pwd)}"
OUT="$OUT_DIR/$NAME-$ARCHTAG.tar.zst"


# --- preflight ----------------------------------------------------------------
command -v docker >/dev/null || { echo "ERROR: docker not on PATH" >&2; exit 1; }
rm -rf "$WORK"; mkdir -p "$WORK/pkg"

# The rootstock must exist here and match this tree: the same opentelemetry-api,
# and no SDK of its own. A pre-3.2.1 rootstock still ships the SDK, so the trim
# would drop it from the overlay and v3 would break on every 3.2.1 install.
rootstock() { docker run --rm --platform "$PLATFORM" --entrypoint python3 "$ROOTSTOCK_IMG" "$@"; }
docker image inspect "$ROOTSTOCK_IMG" >/dev/null 2>&1 || {
  echo "ERROR: rootstock $ROOTSTOCK_IMG is not in this docker context. Build it first:" >&2
  echo "  make it_build   (arm64)   |   DOCKER_CONTEXT=colima-build make it_build_amd64" >&2
  echo "  or point ROOTSTOCK_IMG at one." >&2; exit 1; }
BASE_OTEL="$(rootstock -c 'import importlib.metadata as m; print(m.version("opentelemetry-api"))')"
[ "$BASE_OTEL" = "$OTEL_VERSION" ] || {
  echo "ERROR: $ROOTSTOCK_IMG has opentelemetry-api $BASE_OTEL; requirements.txt pins $OTEL_VERSION. Rebuild it." >&2; exit 1; }
rootstock -c 'import importlib.util as u, sys; sys.exit(1 if u.find_spec("opentelemetry.sdk") else 0)' || {
  echo "ERROR: $ROOTSTOCK_IMG still ships opentelemetry-sdk (pre-3.2.1). Rebuild it." >&2; exit 1; }
rootstock -c 'import importlib.metadata as m
print("\n".join(sorted({d.metadata["Name"].lower().replace("_", "-") for d in m.distributions(path=["/usr/lib/python3.11/site-packages"])})))' \
  > "$WORK/base-dists.txt"

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

# --- 1b. leave out what the rootstock already ships ---------------------------
# The rootstock's site-packages wins on sys.path, so a copy here is dead weight.
# Computed from the rootstock itself, never a hand list: what remains is exactly
# what chromadb needs and the base lacks (since 3.2.1: the OpenTelemetry SDK,
# the gRPC exporter, grpcio, protobuf). The asserts below hold that line.
echo "== trimming what $ROOTSTOCK_IMG ships ($(wc -l < "$WORK/base-dists.txt" | tr -d ' ') dists) =="
docker run --rm -i -v "$WORK:/w" python:3.11-slim python - <<'TRIM'
import importlib.metadata as m, os, pathlib, shutil
pkg = pathlib.Path("/w/pkg").resolve()
base = set(open("/w/base-dists.txt").read().split())
kept, dropped = [], []
for d in m.distributions(path=[str(pkg)]):
    name = d.metadata["Name"].lower().replace("_", "-")
    if name not in base:
        kept.append(name)
        continue
    dropped.append(name)
    for f in d.files or []:
        p = (pkg / f).resolve()
        if pkg in p.parents and p.is_file():
            p.unlink()
    shutil.rmtree(d._path, ignore_errors=True)
for root, _, _ in os.walk(pkg, topdown=False):
    if pathlib.Path(root) != pkg and not os.listdir(root):
        os.rmdir(root)
open("/w/kept.txt", "w").write("\n".join(sorted(kept)) + "\n")
print(f"kept {len(kept)}, left out {len(dropped)} the rootstock ships")
TRIM
for need in chromadb onnxruntime tokenizers opentelemetry-sdk opentelemetry-exporter-otlp-proto-grpc grpcio protobuf; do
  grep -qx "$need" "$WORK/kept.txt" || { echo "ERROR: the trimmed overlay lacks $need" >&2; exit 1; }
done

# --- 2. stage: sprig.yaml at root alongside the package tree --------------------
cat > "$WORK/pkg/sprig.yaml" <<YAML
spec_version: v1
delivery: oci-artifact
capability: vector
cultivar: vector-chroma
variety: linux-$ARCH
sprig_version: v3.0.0
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

# --- 4. SANITY GATE: chromadb works INSIDE the rootstock, overlay mounted -------
# Mounted where the graft extracts it, so the rootstock's sitecustomize puts it
# behind the base on sys.path, exactly as in production. Proves the trim left
# nothing chromadb needs, and that the SDK matches the base's API.
echo "== sanity gate: chromadb on $ROOTSTOCK_IMG with the overlay, $PLATFORM =="
docker run --rm -i --platform "$PLATFORM" -e OTEL_VERSION="$OTEL_VERSION" \
  -v "$WORK/pkg:/usr/local/lib/python3.11/site-packages:ro" \
  --entrypoint python3 "$ROOTSTOCK_IMG" - <<'GATE' \
  || { echo "SANITY GATE FAILED — the overlay does not work on $ROOTSTOCK_IMG ($ARCH)" >&2; exit 1; }
import importlib.metadata as m, os, tempfile
import chromadb, grpc, numpy, onnxruntime, opentelemetry.sdk, tokenizers
for dist in ("opentelemetry-api", "opentelemetry-sdk", "opentelemetry-exporter-otlp-proto-grpc"):
    assert m.version(dist) == os.environ["OTEL_VERSION"], (dist, m.version(dist))
col = chromadb.PersistentClient(path=tempfile.mkdtemp()).create_collection("gate")
col.add(ids=["a", "b"], embeddings=[[0.1, 0.2, 0.3], [0.9, 0.8, 0.7]], documents=["rootstock", "graft"])
hit = col.query(query_embeddings=[[0.1, 0.2, 0.31]], n_results=1)
assert hit["ids"][0] == ["a"], hit
print("overlay OK: chromadb", chromadb.__version__, "| opentelemetry", os.environ["OTEL_VERSION"])
GATE
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
