#!/usr/bin/env bash
# Phase 4 gate probe — do biomes share ONE Svelte runtime? THROWAWAY.
#
# Builds the same three components twice, in the two shapes that matter:
#   dist/shared/   one Rollup build, three entries   (what we would ship)
#   dist/split-*/  three independent builds          (the negative control)
# then serves both pages and runs probe.mjs against each. The shared page must
# pass every check; the split page must FAIL them. A probe that cannot go red
# proves nothing.
#
# Everything runs in containers. The Playwright image already carries Node 22
# and the browsers, so one image does both the build and the probe.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
IMG="mcr.microsoft.com/playwright:v1.49.0-jammy"
NET="${BIOME_NET:-biome-probe}"
PORT="${BIOME_PORT:-8144}"
# The image ships browsers, not the playwright npm package. Install it once
# into a scratch dir outside the repo and mount it.
PW_DEPS="${PW_DEPS:-/tmp/biome-probe-deps}"

cleanup() { docker rm -f biome-web >/dev/null 2>&1 || true
            docker network rm "$NET" >/dev/null 2>&1 || true; }
trap cleanup EXIT
cleanup

# --- build ------------------------------------------------------------------
# app/node_modules holds the svelte + vite the app itself builds with, so the
# probe measures OUR toolchain rather than a fresh one that might chunk
# differently. Mounted into place rather than symlinked, so nothing lands in the
# repo that git would have to ignore.
echo "== build =="
docker run --rm \
  -v "$HERE:/b" -v "$ROOT/app/node_modules:/b/node_modules:ro" -w /b "$IMG" bash -c '
  set -e
  V=node_modules/vite/bin/vite.js
  node $V build --config vite.shared.config.js
  HOST_EXPORTS=0 node $V build --config vite.shared.config.js
  for b in a b c; do BIOME=$b node $V build --config vite.split.config.js; done
  node $V build --config vite.late.config.js
'

# --- serve ------------------------------------------------------------------
docker network create "$NET" >/dev/null 2>&1 || true
docker run -d --name biome-web --network "$NET" -p "$PORT:8000" \
  -v "$HERE:/site:ro" -w /site python:3.11-slim \
  python3 -m http.server 8000 >/dev/null

for _ in $(seq 1 30); do
  curl -sf -o /dev/null "http://localhost:$PORT/shared.html" && break; sleep 1
done

# --- probe ------------------------------------------------------------------
mkdir -p "$PW_DEPS"
if [ ! -d "$PW_DEPS/node_modules/playwright" ]; then
  echo "== installing playwright client (once) =="
  docker run --rm -v "$PW_DEPS:/deps" -w /deps "$IMG" \
    npm install --silent --no-audit --no-fund playwright@1.49.0
fi

# ESM resolution walks up from the importing FILE, not from cwd, so NODE_PATH
# does not help here. Mount the spike one level inside the scratch dir instead;
# `import 'playwright'` then finds /probe/node_modules on the way up.
echo
docker run --rm --network "$NET" \
  -v "$PW_DEPS:/probe" -v "$HERE:/probe/spike:ro" -w /probe/spike "$IMG" \
  node probe.mjs
