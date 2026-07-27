#!/usr/bin/env bash
# build-sprig-ui.sh — pack a ui-Sprig™ from scripts/ui-sprigs/<NAME>/.
#
# A ui-Sprig carries hypermedia: one self-contained fragment.html plus an
# optional fragment.css and the sprig.yaml manifest. It is the marketplace
# surface — a teacher theming their instance should not need a JavaScript
# toolchain — and the contract that keeps that safe is enforced twice: the
# sanity gate below, and the rootstock's graft-time validator
# (sprigs/ui_dispatch.py, fail-closed).
#
# The two must agree. When you change a rule, change it in both, and prefer
# making this gate the STRICTER of the pair: a bundle refused here never
# reaches a registry, while one refused at graft has already been published.
#
# Usage:
#   NAME=workshop-welcome scripts/build-sprig-ui.sh
#   NAME=workshop-welcome TAG=v1 SIGN_KEY=... scripts/build-sprig-ui.sh
# Env (conventions match build-sprig-theme.sh):
#   REGISTRY=localhost:5000  TAG=v1  INSECURE=1  MANAGE_REGISTRY=0
#   NETWORK=sage-network  OUT_DIR=/tmp/sprig-build/ui  SIGN_KEY/SIGN_NOPASS
set -euo pipefail

NAME_ARG="${NAME:?NAME=<dir under scripts/ui-sprigs> required (e.g. workshop-welcome)}"
HERE="$(cd "$(dirname "$0")" && pwd)"
SRC_DIR="$HERE/ui-sprigs/$NAME_ARG"
[ -f "$SRC_DIR/fragment.html" ] || { echo "ERROR: $SRC_DIR/fragment.html not found"; exit 1; }

REGISTRY="${REGISTRY:-localhost:5000}"
NAME="sprig-ui-$NAME_ARG"
TAG="${TAG:-v1}"
INSECURE="${INSECURE:-1}"
MANAGE_REGISTRY="${MANAGE_REGISTRY:-0}"
NETWORK="${NETWORK:-sage-network}"
OUT_DIR="${OUT_DIR:-/tmp/sprig-build/ui}"
ARTIFACT_TYPE="application/vnd.sage-is.sprig.v1"
LAYER_TYPE="application/vnd.sage-is.sprig.tar+zstd"
# oras runs DOCKERIZED — no host install needed.
ORAS_IMG="${ORAS_IMG:-ghcr.io/oras-project/oras:v1.2.0}"
command -v docker >/dev/null || { echo "ERROR: docker not on PATH" >&2; exit 1; }

sha256(){ shasum -a 256 "$1" 2>/dev/null | awk '{print $1}' || sha256sum "$1" | awk '{print $1}'; }

# --- 1. stage ---------------------------------------------------------------
STAGE="$(mktemp -d)"; trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$OUT_DIR"
cp "$SRC_DIR/fragment.html" "$STAGE/fragment.html"
HTML_SHA="$(sha256 "$STAGE/fragment.html")"
PACK=(sprig.yaml fragment.html)
CSS_SHA=""
if [ -f "$SRC_DIR/fragment.css" ]; then
  cp "$SRC_DIR/fragment.css" "$STAGE/fragment.css"
  CSS_SHA="$(sha256 "$STAGE/fragment.css")"
  PACK+=(fragment.css)
fi

cat > "$STAGE/sprig.yaml" <<YAML
spec_version: v1
delivery: oci-artifact
capability: ui
cultivar: $NAME_ARG
sprig_version: ${TAG}.0.0
license: CC-BY-4.0
fragment_html_sha256: $HTML_SHA
${CSS_SHA:+fragment_css_sha256: $CSS_SHA}
offline: true
YAML

# --- 2. SANITY GATE: the same rules the rootstock validator enforces ---------
# Comments come out first so a fragment may document the forbidden syntax
# without tripping on its own documentation — the graft-time validator does the
# same, and the example bundle relies on it.
echo "== sanity gate: fragment self-containment =="
STRIPPED="$STAGE/.fragment-nocomment.html"
perl -0777 -pe 's/<!--.*?-->//gs' "$STAGE/fragment.html" > "$STRIPPED"

fail(){ echo "GATE FAIL: $1"; exit 1; }

grep -Eiq '<\s*(iframe|object|embed|base)\b|javascript:|vbscript:|[[:space:]]srcdoc[[:space:]]*=' "$STRIPPED" \
  && fail "fragment.html frames or executes content the Rootstock cannot validate"
grep -Eiq '(src|href|action|data|poster|formaction)[[:space:]]*=[[:space:]]*["'\'']?[[:space:]]*(https?:|//)' "$STRIPPED" \
  && fail "fragment.html references something off-origin"
grep -Eiq '(^|[[:space:]])(_|script|data-script)[[:space:]]*=' "$STRIPPED" \
  && fail "fragment.html carries an interpreted script attribute (hyperscript form)"

# Script is refused HERE unconditionally, which is stricter than the rootstock —
# there the admin's per-Sprig grant can widen it. That asymmetry is deliberate:
# an author should have to think hard before publishing a fragment that only
# works if every operator grants it something.
grep -Eiq '<[[:space:]]*script\b|[[:space:]]on[a-z]+[[:space:]]*=' "$STRIPPED" \
  && fail "fragment.html carries script; a ui-Sprig ships hypermedia (see sprigs/ui_dispatch.py)"

rm -f "$STRIPPED"
HTML_BYTES=$(wc -c < "$STAGE/fragment.html" | tr -d ' ')
[ "$HTML_BYTES" -le 262144 ] || fail "fragment.html ${HTML_BYTES}B exceeds the 256KB cap"

if [ -n "$CSS_SHA" ]; then
  CSS_STRIPPED="$STAGE/.fragment-nocomment.css"
  sed -e 's|/\*[^*]*\*\+\([^/*][^*]*\*\+\)*/||g' "$STAGE/fragment.css" > "$CSS_STRIPPED"
  grep -Eiq '@import|url\([[:space:]]*(["'\'']?[[:space:]]*)?(https?:|//)|javascript:|<script|expression\(' "$CSS_STRIPPED" \
    && fail "fragment.css references external resources or executable content"
  rm -f "$CSS_STRIPPED"
  CSS_BYTES=$(wc -c < "$STAGE/fragment.css" | tr -d ' ')
  [ "$CSS_BYTES" -le 524288 ] || fail "fragment.css ${CSS_BYTES}B exceeds the 512KB cap"
fi
echo "  gate OK (${HTML_BYTES}B markup${CSS_SHA:+, ${CSS_BYTES}B css}, no script, no external refs)"

# --- 3. pack (dockerized GNU tar; macOS bsdtar lacks --sort=name) -----------
OUT="$OUT_DIR/$NAME-$TAG.tar.zst"
docker run --rm -v "$STAGE:/stage:ro" -v "$OUT_DIR:/out" alpine:3.20 sh -c \
  "apk add --no-cache tar zstd >/dev/null 2>&1 && \
   tar --sort=name --owner=0 --group=0 --numeric-owner --mtime='UTC 2020-01-01' \
       --use-compress-program='zstd -19 -T0' \
       -cf /out/$(basename "$OUT") -C /stage ${PACK[*]}"
TAR_SHA="$(sha256 "$OUT")"

echo
echo "=================================================================="
echo "  artifact : $OUT"
echo "  tar.zst sha256 (PIN THIS in CATALOG binary_sha256):"
echo "    $TAR_SHA"
echo "  fragment.html sha256: $HTML_SHA"
[ -n "$CSS_SHA" ] && echo "  fragment.css  sha256: $CSS_SHA"
echo "=================================================================="

if [ "$MANAGE_REGISTRY" = "1" ]; then
  docker network inspect "$NETWORK" >/dev/null 2>&1 || docker network create "$NETWORK"
  if ! docker ps --format '{{.Names}}' | grep -qx local-registry; then
    docker rm -f local-registry >/dev/null 2>&1 || true
    docker run -d --name local-registry --network "$NETWORK" -p 5000:5000 \
      -v sprig-registry-data:/var/lib/registry registry:2 >/dev/null
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

# Inside the oras container localhost is the container itself, so a localhost
# registry has to be reached by its on-network name.
PUSH_REG="$REGISTRY"; ORAS_NET=()
case "$REGISTRY" in localhost:*|127.0.0.1:*)
  PUSH_REG="local-registry:${REGISTRY##*:}"; ORAS_NET=(--network "$NETWORK");;
esac
PUSH=(push "$PUSH_REG/$NAME:$TAG" --artifact-type "$ARTIFACT_TYPE")
[ "$INSECURE" = "1" ] && PUSH+=(--plain-http)
docker run --rm ${ORAS_NET[@]+"${ORAS_NET[@]}"} -v "$OUT_DIR:/w" -w /w "$ORAS_IMG" \
  "${PUSH[@]}" "$(basename "$OUT"):$LAYER_TYPE" ${SIG_LAYER[@]+"${SIG_LAYER[@]}"}

echo
echo "pushed: $REGISTRY/$NAME:$TAG"
echo "catalog: binary_sha256: \"$TAR_SHA\"   repo: \"$REGISTRY/$NAME\"   tag: \"$TAG\""
