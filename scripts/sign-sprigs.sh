#!/usr/bin/env bash
# sign-sprigs.sh — minisign-sign Sprig™ artifacts in a registry, in place.
#
# For each repo:tag in $SRC (default the local dev registry): pull the tar,
# sign it, re-push the SAME tar bytes plus the .minisig as a second layer at
# the same tag. The tar is byte-identical, so the sha256 pins in the CATALOG
# stay valid; `oras cp` in publish-sprigs.sh carries the signature layer to
# the public registry unchanged (run it with FORCE=1 after signing, because
# the manifest digest changed).
#
# The Rootstock™ verifies offline at graft time (sprigs/minisign.py) against
# the pinned public key. Third parties verify with the stock CLI:
#   minisign -Vm <tar> -P <public key line>
#
# Usage:
#   SIGN_KEY=~/sage-keys/sprig.key scripts/sign-sprigs.sh          # every repo:tag
#   SIGN_KEY=... ONLY="sprig-backup-rclone" scripts/sign-sprigs.sh # subset
#   SIGN_NOPASS=1  -> key has no passphrase (the committed DEV fixture only)
#   TRUST_NOTE=... -> extra text for the signed trusted comment
# Fully dockerized: needs docker + jq + curl only. Safe to re-run (re-signs).
set -euo pipefail

SRC="${SRC:-localhost:5000}"                          # host-visible (curl)
SRC_INTERNAL="${SRC_INTERNAL:-local-registry:5000}"   # name on sage-network (oras)
NET="${NET:-sage-network}"
ORAS_IMG="ghcr.io/oras-project/oras:v1.2.0"
ALPINE_IMG="alpine:3.20"
ARTIFACT_TYPE="application/vnd.sage-is.sprig.v1"
LAYER_TYPE="application/vnd.sage-is.sprig.tar+zstd"
SIG_TYPE="application/vnd.sage-is.sprig.minisig"

[ -n "${SIGN_KEY:-}" ] || { echo "ERROR: SIGN_KEY=<path to minisign secret key> required"; exit 1; }
[ -f "$SIGN_KEY" ] || { echo "ERROR: SIGN_KEY $SIGN_KEY not found"; exit 1; }
KEY_DIR="$(cd "$(dirname "$SIGN_KEY")" && pwd)"; KEY_FILE="$(basename "$SIGN_KEY")"

. "$(dirname "${BASH_SOURCE[0]}")/lib/mount-tmp.sh"
WORK="$(mount_tmp sign-sprigs)"; trap 'rm -rf "$WORK"' EXIT
# Each tag gets a FRESH subfolder, and nothing a container wrote is deleted from
# the host before a container writes it again. Colima's krunkit file sharing
# keeps a stale entry after a host-side delete, so the container's next write to
# that path fails with "nonexistent directory" (2026-10-15: the re-sign of an
# already-signed artifact died exactly there).
ORAS(){ docker run --rm --network "$NET" -v "$TAGDIR:/w" -w /w "$ORAS_IMG" "$@"; }

# Interactive TTY only when the key needs a passphrase prompt.
MTTY=""; [ -z "${SIGN_NOPASS:-}" ] && MTTY="-it"

sha256(){ shasum -a 256 "$1" 2>/dev/null | awk '{print $1}' || sha256sum "$1" | awk '{print $1}'; }

REPOS="${ONLY:-$(curl -fsS "http://$SRC/v2/_catalog" | jq -r '.repositories[]')}"
SIGNED=0
for r in $REPOS; do
  for t in $(curl -fsS "http://$SRC/v2/$r/tags/list" | jq -r '.tags[]'); do
    TAGDIR="$WORK/$r-$t"; mkdir -p "$TAGDIR"
    printf "== %s:%s " "$r" "$t"
    ORAS pull --plain-http "$SRC_INTERNAL/$r:$t" >/dev/null
    tar_file="$(cd "$TAGDIR" && ls -- *.tar.zst 2>/dev/null | head -1)"
    [ -n "$tar_file" ] || { echo "SKIP (no tar.zst layer)"; continue; }
    sha="$(sha256 "$TAGDIR/$tar_file")"
    # A signed artifact pulls its old .minisig too; drop it INSIDE the container
    # that writes the new one (see the krunkit note above).
    docker run --rm $MTTY -v "$TAGDIR:/w" -v "$KEY_DIR:/keys:ro" "$ALPINE_IMG" sh -c \
      "rm -f /w/$tar_file.minisig && apk add --no-cache minisign >/dev/null 2>&1 && minisign -S ${SIGN_NOPASS:+-W} \
       -s /keys/$KEY_FILE -m /w/$tar_file \
       -t 'sage-is $r:$t sha256=$sha${TRUST_NOTE:+ }${TRUST_NOTE:-}'"
    ORAS push --plain-http "$SRC_INTERNAL/$r:$t" --artifact-type "$ARTIFACT_TYPE" \
      "$tar_file:$LAYER_TYPE" "$tar_file.minisig:$SIG_TYPE" >/dev/null
    echo "signed + re-pushed"
    SIGNED=$((SIGNED+1))
  done
done
echo "== SIGNED $SIGNED artifact tag(s). Next: FORCE=1 make sprig_publish (manifests changed)."
