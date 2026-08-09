#!/usr/bin/env bash
# build-sprig-media-ffmpeg.sh — package the media-ffmpeg Sprig™ (static ffmpeg
# + ffprobe, johnvansickle 7.0.2), per host arch.
#
# The tar carries ONLY the two static binaries at its root (matching the live
# hand-built v1 artifact) — artifact.py's app-dir delivery extracts them into
# /usr/local/bin (sentinel: ffmpeg). No sprig.yaml inside: the target is a
# shared bin dir and a stray manifest file would pollute it.
#
# Source: johnvansickle.com static builds (fully static — run on any libc).
# The version is PINNED (old-releases URL) so a rebuild is reproducible; the
# published .md5 is verified before staging, and our sha256 pin remains the
# real integrity anchor.
#
# Multi-arch: arm64 v1 is the live hand-built artifact — this recipe REFUSES
# to re-push over it (bump TAG or set ALLOW_RETAG=1). ARCH=amd64 tags
# `${TAG}-amd64` for the CATALOG arches["amd64"] override. Sanity gate runs
# the browser voice-note path on the TARGET arch: wav -> webm/opus -> wav.
#
# Local dev (default): pushes to localhost:5000 over --plain-http via a
# DOCKERIZED oras (no host install). Production publishing goes through
# publish-sprigs.sh (local -> ghcr).
set -euo pipefail

# Shared boilerplate: constants, arch-normalize, sha256, registry, push, timing.
. "$(dirname "${BASH_SOURCE[0]}")/lib/sprig-build.sh"
NAME="${NAME:-sprig-media-ffmpeg}"
sprig_build_defaults
sprig_timing_start

FFMPEG_VERSION="${FFMPEG_VERSION:-7.0.2}"

sprig_arch_normalize

# POKA-YOKE: the arm64 v1 blob predates this recipe and is pinned/published.
# A rebuild would change its sha out from under the CATALOG pin.
if [ "$ARCH" = "arm64" ] && [ "$TAG" = "v1" ] && [ "${ALLOW_RETAG:-0}" != "1" ]; then
  echo "ERROR: arm64 $TAG is the live hand-built artifact (pinned in the CATALOG)." >&2
  echo "       Bump TAG=v2 for a recipe-built arm64, or set ALLOW_RETAG=1 to override." >&2
  exit 1
fi

# Old-releases is version-stable; the current-release URL is unversioned and
# rolls forward. Try old-releases first, fall back to current — the versioned
# member path at extraction asserts we actually got $FFMPEG_VERSION either way.
JV_OLD="https://johnvansickle.com/ffmpeg/old-releases/ffmpeg-${FFMPEG_VERSION}-${ARCH}-static.tar.xz"
JV_CUR="https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-${ARCH}-static.tar.xz"

WORK="${WORK:-/tmp/sprig-build/media-ffmpeg-$ARCH}"
OUT_DIR="${OUT_DIR:-$(pwd)}"
OUT="$OUT_DIR/$NAME-$ARCHTAG.tar.zst"


# --- preflight ----------------------------------------------------------------
command -v docker >/dev/null || { echo "ERROR: docker not on PATH" >&2; exit 1; }
mkdir -p "$WORK/stage"

# --- 1. download the pinned static build (one-time on the packaging host) ------
if [ ! -f "$WORK/ffmpeg.tar.xz" ]; then
  echo "== downloading ffmpeg ${FFMPEG_VERSION} static ($ARCH) =="
  if curl -fsL --retry 3 -o "$WORK/ffmpeg.tar.xz" "$JV_OLD" 2>/dev/null; then
    curl -fL --retry 3 -o "$WORK/ffmpeg.tar.xz.md5" "$JV_OLD.md5"
  else
    echo "   (not in old-releases — ${FFMPEG_VERSION} is the current release)"
    curl -fL --retry 3 -o "$WORK/ffmpeg.tar.xz" "$JV_CUR"
    curl -fL --retry 3 -o "$WORK/ffmpeg.tar.xz.md5" "$JV_CUR.md5"
  fi
fi

# --- 2. verify publisher md5 + extract the two binaries (dockerized) -----------
echo "== verifying + extracting =="
docker run --rm -v "$WORK:/w" alpine sh -ec '
  apk add --no-cache xz >/dev/null
  cd /w
  # .md5 format: "<md5>  <filename>" — rewrite the filename to ours.
  awk "{print \$1\"  ffmpeg.tar.xz\"}" ffmpeg.tar.xz.md5 | md5sum -c -
  tar -xJf ffmpeg.tar.xz --strip-components=1 -C /w/stage \
    "ffmpeg-'"$FFMPEG_VERSION"'-'"$ARCH"'-static/ffmpeg" \
    "ffmpeg-'"$FFMPEG_VERSION"'-'"$ARCH"'-static/ffprobe"
  chmod 0755 /w/stage/ffmpeg /w/stage/ffprobe
'

# --- 3. SANITY GATE: the browser voice-note path on the TARGET arch ------------
# webm/opus is what MediaRecorder uploads; whisper needs wav. Prove the exact
# transcode round-trip the audio path performs.
echo "== sanity gate: wav -> webm/opus -> wav on $PLATFORM =="
docker run --rm --platform "$PLATFORM" -v "$WORK/stage:/s:ro" alpine sh -ec '
  /s/ffmpeg -hide_banner -loglevel error -f lavfi -i "sine=frequency=440:duration=1" /tmp/in.wav
  /s/ffmpeg -hide_banner -loglevel error -i /tmp/in.wav -c:a libopus /tmp/note.webm
  /s/ffprobe -v error -show_entries stream=codec_name -of csv=p=0 /tmp/note.webm | grep -qx opus
  /s/ffmpeg -hide_banner -loglevel error -i /tmp/note.webm -ar 16000 /tmp/out.wav
  [ -s /tmp/out.wav ]
  echo "  transcode round-trip OK (opus verified)"
' || { echo "SANITY GATE FAILED — ffmpeg transcode broken on $ARCH" >&2; exit 1; }

# --- 4. reproducible pack (binaries only at root, matching the live artifact) --
docker run --rm -v "$WORK/stage:/stage:ro" -v "$OUT_DIR:/out" alpine sh -c \
  "apk add --no-cache tar zstd >/dev/null && \
   tar --sort=name --owner=0 --group=0 --numeric-owner --mtime='UTC 2020-01-01' \
       --use-compress-program='zstd -19 -T0' \
       -cf /out/$(basename "$OUT") -C /stage ffmpeg ffprobe"
TAR_SHA="$(sha256 "$OUT")"

echo
echo "=================================================================="
echo "  artifact : $OUT   (arch: $ARCH, ffmpeg $FFMPEG_VERSION)"
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
# Dockerized oras push (no host oras). Inside the container localhost is the
# container itself, so a localhost registry is reached by its on-network name.
sprig_push

echo
echo "pushed: $REGISTRY/$NAME:$ARCHTAG"
sprig_timing_end
