#!/usr/bin/env bash
# build-sprig-backup-rclone.sh — package the backup-rclone Sprig™ (rclone,
# official release build), per host arch.
#
# The tar carries ONLY the rclone binary at its root (matching the live
# hand-built v1 artifact) — artifact.py's app-dir delivery extracts it into
# /usr/local/bin (sentinel: rclone). No sprig.yaml inside: shared bin dir.
#
# Version PINNED to v1.60.1 — the version the live arm64 v1 artifact carries
# (that blob is a Debian "-DEV" build; this recipe uses the official release
# from downloads.rclone.org, verified against its published SHA256SUMS).
#
# Multi-arch: arm64 v1 is the live hand-built artifact — this recipe REFUSES
# to re-push over it (bump TAG or set ALLOW_RETAG=1). ARCH=amd64 tags
# `${TAG}-amd64` for the CATALOG arches["amd64"] override.
#
# NOTE: backup strategy is moving to volume-level backups (rclone leaves the
# image); this recipe exists so the artifact stays reproducible until then.
#
# Local dev (default): pushes to localhost:5000 over --plain-http via a
# DOCKERIZED oras (no host install). Production publishing goes through
# publish-sprigs.sh (local -> ghcr).
set -euo pipefail

REGISTRY="${REGISTRY:-localhost:5000}"
NAME="${NAME:-sprig-backup-rclone}"
TAG="${TAG:-v1}"
INSECURE="${INSECURE:-1}"
MANAGE_REGISTRY="${MANAGE_REGISTRY:-0}"
NETWORK="${NETWORK:-sage-network}"
ARTIFACT_TYPE="application/vnd.sage-is.sprig.v1"
LAYER_TYPE="application/vnd.sage-is.sprig.tar+zstd"
ORAS_IMG="${ORAS_IMG:-ghcr.io/oras-project/oras:v1.2.0}"

RCLONE_VERSION="${RCLONE_VERSION:-v1.60.1}"

_RAW_ARCH="$(uname -m)"
case "${ARCH:-$_RAW_ARCH}" in
  arm64|aarch64) ARCH=arm64 ;;
  amd64|x86_64)  ARCH=amd64 ;;
  *) echo "ERROR: unsupported ARCH='${ARCH:-$_RAW_ARCH}' (want arm64|amd64)" >&2; exit 1 ;;
esac
PLATFORM="${PLATFORM:-linux/$ARCH}"
ARCHTAG="$TAG"; [ "$ARCH" = "amd64" ] && ARCHTAG="$TAG-amd64"

# POKA-YOKE: the arm64 v1 blob predates this recipe and is pinned/published.
if [ "$ARCH" = "arm64" ] && [ "$TAG" = "v1" ] && [ "${ALLOW_RETAG:-0}" != "1" ]; then
  echo "ERROR: arm64 $TAG is the live hand-built artifact (pinned in the CATALOG)." >&2
  echo "       Bump TAG=v2 for a recipe-built arm64, or set ALLOW_RETAG=1 to override." >&2
  exit 1
fi

RC_ZIP="rclone-${RCLONE_VERSION}-linux-${ARCH}.zip"
RC_URL="https://downloads.rclone.org/${RCLONE_VERSION}/${RC_ZIP}"
RC_SUMS="https://downloads.rclone.org/${RCLONE_VERSION}/SHA256SUMS"

WORK="${WORK:-/tmp/sprig-build/backup-rclone-$ARCH}"
OUT_DIR="${OUT_DIR:-$(pwd)}"
OUT="$OUT_DIR/$NAME-$ARCHTAG.tar.zst"

sha256() { if command -v sha256sum >/dev/null; then sha256sum "$1" | cut -d' ' -f1; else shasum -a 256 "$1" | cut -d' ' -f1; fi; }

# --- preflight ----------------------------------------------------------------
command -v docker >/dev/null || { echo "ERROR: docker not on PATH" >&2; exit 1; }
mkdir -p "$WORK/stage"

# --- 1. download the pinned official release (one-time on the packaging host) --
if [ ! -f "$WORK/$RC_ZIP" ]; then
  echo "== downloading rclone ${RCLONE_VERSION} ($ARCH) =="
  curl -fL --retry 3 -o "$WORK/$RC_ZIP" "$RC_URL"
  curl -fL --retry 3 -o "$WORK/SHA256SUMS" "$RC_SUMS"
fi

# --- 2. verify publisher sha256 + extract (dockerized) --------------------------
echo "== verifying + extracting =="
docker run --rm -v "$WORK:/w" -e RC_ZIP="$RC_ZIP" alpine sh -ec '
  cd /w
  grep " $RC_ZIP\$" SHA256SUMS | sha256sum -c -
  unzip -oq "$RC_ZIP" "*/rclone" -d /tmp/rc
  mv /tmp/rc/*/rclone /w/stage/rclone
  chmod 0755 /w/stage/rclone
'

# --- 3. SANITY GATE: version + a real local-backend hash op on the TARGET arch --
# glibc image on purpose: official rclone builds link glibc, same as the
# Wolfi rootstock this delivers onto.
echo "== sanity gate: rclone version + hashsum on $PLATFORM =="
docker run --rm --platform "$PLATFORM" -v "$WORK/stage:/s:ro" python:3.11-slim sh -ec '
  /s/rclone version | head -1 | grep -q "'"$RCLONE_VERSION"'"
  echo "sprig gate fixture" > /tmp/f.txt
  /s/rclone hashsum md5 /tmp/f.txt | grep -q f.txt
  echo "  rclone runs + hashes on target arch"
' || { echo "SANITY GATE FAILED — rclone broken on $ARCH" >&2; exit 1; }

# --- 4. reproducible pack (binary only at root, matching the live artifact) -----
docker run --rm -v "$WORK/stage:/stage:ro" -v "$OUT_DIR:/out" alpine sh -c \
  "apk add --no-cache tar zstd >/dev/null && \
   tar --sort=name --owner=0 --group=0 --numeric-owner --mtime='UTC 2020-01-01' \
       --use-compress-program='zstd -19 -T0' \
       -cf /out/$(basename "$OUT") -C /stage rclone"
TAR_SHA="$(sha256 "$OUT")"

echo
echo "=================================================================="
echo "  artifact : $OUT   (arch: $ARCH, rclone $RCLONE_VERSION)"
echo "  tar.zst sha256 (PIN in CATALOG):"
echo "    $TAR_SHA"
if [ "$ARCH" = "amd64" ]; then
  echo "  -> arches[\"amd64\"] = {\"tag\": \"$ARCHTAG\", \"binary_sha256\": \"$TAR_SHA\"}"
else
  echo "  -> arm64 pin (TAG=$TAG): \"$TAR_SHA\""
fi
echo "=================================================================="

# --- 5. optional local registry -------------------------------------------------
if [ "$MANAGE_REGISTRY" = "1" ]; then
  docker network inspect "$NETWORK" >/dev/null 2>&1 || docker network create "$NETWORK"
  if ! docker ps --format '{{.Names}}' | grep -qx local-registry; then
    docker rm -f local-registry >/dev/null 2>&1 || true
    docker run -d --name local-registry --network "$NETWORK" -p 5000:5000 -v sprig-registry-data:/var/lib/registry registry:2 >/dev/null
  fi
  for _ in $(seq 1 30); do curl -fsS "http://localhost:5000/v2/" >/dev/null 2>&1 && break; sleep 0.5; done
fi

# --- 6. sign (optional) + push ---------------------------------------------------
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
