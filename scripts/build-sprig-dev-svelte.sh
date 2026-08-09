#!/usr/bin/env bash
# build-sprig-dev-svelte.sh — package the dev-svelte Sprig™ (the Svelte
# dev/build toolchain: node_modules + the bun binary), per host arch.
#
# The tar carries node_modules/ and bun at its root — artifact.py's app-dir
# delivery extracts them into /app (sentinel: node_modules); the image ships a
# dangling /usr/local/bin symlink that resolves once bun lands at /app/bun.
# Dev-only: production rootstocks never graft this.
#
# Deps resolve from the repo's OWN app/package.json + app/bun.lock
# (--frozen-lockfile — the lockfile IS the pin; a drifted lock fails loudly).
# Native modules (esbuild, rollup) are arch-bound, hence per-arch artifacts.
#
# Multi-arch: arm64 v2 is the live hand-built artifact — this recipe REFUSES
# to re-push over it (bump TAG or set ALLOW_RETAG=1). ARCH=amd64 tags
# `${TAG}-amd64` for the CATALOG arches["amd64"] override. NOTE: the amd64
# bun install runs under QEMU — expect a long build (dev-only, so it may land
# in a patch release rather than gate a platform ship).
#
# Local dev (default): pushes to localhost:5000 over --plain-http via a
# DOCKERIZED oras (no host install). Production publishing goes through
# publish-sprigs.sh (local -> ghcr).
set -euo pipefail

# Shared boilerplate: constants, arch-normalize, sha256, registry, push, timing.
. "$(dirname "${BASH_SOURCE[0]}")/lib/sprig-build.sh"
NAME="${NAME:-sprig-dev-svelte}"
TAG="${TAG:-v2}"                        # catalog dev-svelte is at v2 (preserve before defaults)
sprig_build_defaults
sprig_timing_start

sprig_arch_normalize

# POKA-YOKE: the arm64 v2 blob predates this recipe and is pinned/published.
if [ "$ARCH" = "arm64" ] && [ "$TAG" = "v2" ] && [ "${ALLOW_RETAG:-0}" != "1" ]; then
  echo "ERROR: arm64 $TAG is the live hand-built artifact (pinned in the CATALOG)." >&2
  echo "       Bump TAG=v3 for a recipe-built arm64, or set ALLOW_RETAG=1 to override." >&2
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
[ -f "$REPO_ROOT/app/package.json" ] || { echo "ERROR: app/package.json not found" >&2; exit 1; }
[ -f "$REPO_ROOT/app/bun.lock" ]     || { echo "ERROR: app/bun.lock not found" >&2; exit 1; }

WORK="${WORK:-/tmp/sprig-build/dev-svelte-$ARCH}"
OUT_DIR="${OUT_DIR:-$(pwd)}"
OUT="$OUT_DIR/$NAME-$ARCHTAG.tar.zst"


# --- preflight ----------------------------------------------------------------
command -v docker >/dev/null || { echo "ERROR: docker not on PATH" >&2; exit 1; }
mkdir -p "$WORK/stage"

# --- 1. bun install against the repo lockfile, on the TARGET arch --------------
# Same base + flow as the Dockerfile frontend stage (node:22-bookworm, npm-g
# bun, --frozen-lockfile). The bun binary itself ships in the artifact.
if [ ! -d "$WORK/stage/node_modules" ]; then
  echo "== bun install (frozen lockfile) for $PLATFORM — QEMU runs are SLOW =="
  docker run --rm --platform "$PLATFORM" \
    -v "$REPO_ROOT/app/package.json:/build/package.json:ro" \
    -v "$REPO_ROOT/app/bun.lock:/build/bun.lock:ro" \
    -v "$WORK/stage:/out" \
    node:22-bookworm bash -ec '
      npm install -g bun >/dev/null 2>&1
      cd /build
      bun install --frozen-lockfile
      mv node_modules /out/node_modules
      cp "$(command -v bun)" /out/bun && chmod 0755 /out/bun
    '
fi

# --- 2. SANITY GATE: the toolchain runs on the TARGET arch ----------------------
echo "== sanity gate: bun + vite run on $PLATFORM =="
docker run --rm --platform "$PLATFORM" -v "$WORK/stage:/s:ro" node:22-bookworm bash -ec '
  /s/bun --version
  cd /s && ./node_modules/.bin/vite --version
  echo "  toolchain runs on target arch"
' || { echo "SANITY GATE FAILED — dev toolchain broken on $ARCH" >&2; exit 1; }

# --- 3. reproducible pack (node_modules + bun at root) ---------------------------
echo "== packing (~1GB tree; zstd -19 takes a while) =="
docker run --rm -v "$WORK/stage:/stage:ro" -v "$OUT_DIR:/out" alpine sh -c \
  "apk add --no-cache tar zstd >/dev/null && \
   tar --sort=name --owner=0 --group=0 --numeric-owner --mtime='UTC 2020-01-01' \
       --use-compress-program='zstd -19 -T0' \
       -cf /out/$(basename "$OUT") -C /stage bun node_modules"
TAR_SHA="$(sha256 "$OUT")"

echo
echo "=================================================================="
echo "  artifact : $OUT   (arch: $ARCH)"
echo "  tar.zst sha256 (PIN in CATALOG):"
echo "    $TAR_SHA"
if [ "$ARCH" = "amd64" ]; then
  echo "  -> arches[\"amd64\"] = {\"tag\": \"$ARCHTAG\", \"binary_sha256\": \"$TAR_SHA\"}"
else
  echo "  -> arm64 pin (TAG=$TAG): \"$TAR_SHA\""
fi
echo "=================================================================="

# --- 4. optional local registry --------------------------------------------------
sprig_ensure_registry

# --- 5. sign (optional) + push ----------------------------------------------------
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
# Dockerized oras push (no host oras). Inside the container localhost is the
# container itself, so a localhost registry is reached by its on-network name.
sprig_push

echo
echo "pushed: $REGISTRY/$NAME:$ARCHTAG"
sprig_timing_end
