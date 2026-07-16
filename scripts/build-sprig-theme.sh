#!/usr/bin/env bash
# build-sprig-theme.sh — pack a theme Sprig™ from scripts/themes/<THEME>/.
#
# Theme Sprigs carry design tokens only: one self-contained theme.css plus the
# sprig.yaml manifest. No executable code, ever — the sanity gate below and
# the rootstock's graft-time validator both enforce it (no @import, no
# external url(), no javascript:, size-capped).
#
# Usage:
#   THEME=workshop-bio  scripts/build-sprig-theme.sh
#   THEME=workshop-math TAG=v1 SIGN_KEY=... scripts/build-sprig-theme.sh
# Env (conventions match build-sprig-whisper.sh):
#   REGISTRY=localhost:5000  TAG=v1  INSECURE=1  MANAGE_REGISTRY=0
#   NETWORK=sage-network  OUT_DIR=/tmp/sprig-build/themes  SIGN_KEY/SIGN_NOPASS
set -euo pipefail

THEME="${THEME:?THEME=<dir under scripts/themes> required (e.g. workshop-bio)}"
HERE="$(cd "$(dirname "$0")" && pwd)"
SRC_DIR="$HERE/themes/$THEME"
[ -f "$SRC_DIR/theme.css" ] || { echo "ERROR: $SRC_DIR/theme.css not found"; exit 1; }

REGISTRY="${REGISTRY:-localhost:5000}"
NAME="sprig-theme-$THEME"
TAG="${TAG:-v1}"
INSECURE="${INSECURE:-1}"
MANAGE_REGISTRY="${MANAGE_REGISTRY:-0}"
NETWORK="${NETWORK:-sage-network}"
OUT_DIR="${OUT_DIR:-/tmp/sprig-build/themes}"
ARTIFACT_TYPE="application/vnd.sage-is.sprig.v1"
LAYER_TYPE="application/vnd.sage-is.sprig.tar+zstd"

sha256(){ shasum -a 256 "$1" 2>/dev/null | awk '{print $1}' || sha256sum "$1" | awk '{print $1}'; }

# --- 1. stage ---------------------------------------------------------------
STAGE="$(mktemp -d)"; trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$OUT_DIR"
cp "$SRC_DIR/theme.css" "$STAGE/theme.css"
CSS_SHA="$(sha256 "$STAGE/theme.css")"

cat > "$STAGE/sprig.yaml" <<YAML
spec_version: v1
delivery: oci-artifact
capability: theme
cultivar: $THEME
sprig_version: ${TAG}.0.0
license: CC-BY-4.0
theme_css_sha256: $CSS_SHA
offline: true
YAML

# --- 2. SANITY GATE: same rules the rootstock validator enforces ------------
# Comments are stripped first so documentation can NAME the forbidden syntax
# without tripping the scan (the graft-time validator does the same).
echo "== sanity gate: theme.css self-containment =="
grep -q ':root' "$STAGE/theme.css" || { echo "GATE FAIL: no :root block"; exit 1; }
STRIPPED="$STAGE/.theme-nocomment.css"
sed -e 's|/\*[^*]*\*\+\([^/*][^*]*\*\+\)*/||g' "$STAGE/theme.css" > "$STRIPPED"
if grep -Eiq '@import|url\(\s*(["'\'']?\s*)?(https?:|//)|javascript:|<script|expression\(' "$STRIPPED"; then
  echo "GATE FAIL: theme.css references external resources or executable content"; exit 1
fi
rm -f "$STRIPPED"
CSS_BYTES=$(wc -c < "$STAGE/theme.css" | tr -d ' ')
[ "$CSS_BYTES" -le 524288 ] || { echo "GATE FAIL: theme.css ${CSS_BYTES}B exceeds 512KB cap"; exit 1; }
echo "  gate OK (${CSS_BYTES}B, no external refs)"

# --- 3. pack (dockerized GNU tar; macOS bsdtar lacks --sort=name) -----------
OUT="$OUT_DIR/$NAME-$TAG.tar.zst"
docker run --rm -v "$STAGE:/stage:ro" -v "$OUT_DIR:/out" alpine:3.20 sh -c \
  "apk add --no-cache tar zstd >/dev/null 2>&1 && \
   tar --sort=name --owner=0 --group=0 --numeric-owner --mtime='UTC 2020-01-01' \
       --use-compress-program='zstd -19 -T0' \
       -cf /out/$(basename "$OUT") -C /stage sprig.yaml theme.css"
TAR_SHA="$(sha256 "$OUT")"

echo
echo "=================================================================="
echo "  artifact : $OUT"
echo "  tar.zst sha256 (PIN THIS in CATALOG binary_sha256):"
echo "    $TAR_SHA"
echo "  theme.css sha256: $CSS_SHA"
echo "=================================================================="

if [ "$MANAGE_REGISTRY" = "1" ]; then
  docker network inspect "$NETWORK" >/dev/null 2>&1 || docker network create "$NETWORK"
  if ! docker ps --format '{{.Names}}' | grep -qx local-registry; then
    docker rm -f local-registry >/dev/null 2>&1 || true
    docker run -d --name local-registry --network "$NETWORK" -p 5000:5000 -v sprig-registry-data:/var/lib/registry registry:2 >/dev/null
  fi
  for _ in $(seq 1 30); do curl -fsS "http://localhost:5000/v2/" >/dev/null 2>&1 && break; sleep 0.5; done
fi

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
