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

# Shared boilerplate: constants, arch-normalize, sha256, registry, push, timing.
. "$(dirname "${BASH_SOURCE[0]}")/lib/sprig-build.sh"
NAME="${NAME:-sprig-backup-rclone}"
sprig_build_defaults
sprig_timing_start

RCLONE_VERSION="${RCLONE_VERSION:-v1.60.1}"

sprig_arch_normalize

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
sprig_ensure_registry

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
# Dockerized oras push (no host oras); rides the optional SIG_LAYER set above.
sprig_push

echo
echo "pushed: $REGISTRY/$NAME:$ARCHTAG"
sprig_timing_end
