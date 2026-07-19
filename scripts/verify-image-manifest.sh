#!/usr/bin/env bash
# verify-image-manifest.sh — poka-yoke: assert a PUSHED image is really there and
# really multi-arch, right after the release push, at YOUR terminal.
#
# The failure this closes: 3.0.0's release finish died before the image push, so
# CapRover pulled a 404 (manifest unknown) and nothing in the flow noticed. The
# sibling failure is a partial / --platform-typo push that lands a SINGLE-arch
# index — fine on arm64 (try.sage.is), broken on the amd64 prod host. This gate
# fails `make ship` loudly before either reaches a deploy.
#
# For every image ref given it asserts:
#   1. the manifest is PRESENT (inspect succeeds, not a 404), and
#   2. it is a multi-arch index carrying BOTH linux/amd64 AND linux/arm64.
#
# Mechanism: `docker buildx imagetools inspect --raw`. Registry-agnostic on
# purpose — it reads the index the push just created and keeps working when
# REGISTRY swaps from ghcr.io/sage-is to an in-house sprigs.sage.is/Zot, unlike a
# hardcoded ghcr.io/token dance. Requires only docker (buildx) + jq.
#
# Usage:
#   scripts/verify-image-manifest.sh IMAGE:TAG [IMAGE:TAG ...]
#     e.g. scripts/verify-image-manifest.sh \
#            ghcr.io/sage-is/ai-ui:3.0.1 ghcr.io/sage-is/ai-ui:latest
#
# Exits 0 when every ref is present AND multi-arch; non-zero otherwise.
set -uo pipefail

# Architectures a prod-ready release MUST carry. Override for a narrower assert:
#   REQUIRE_ARCHES="linux/amd64" scripts/verify-image-manifest.sh ...
REQUIRE_ARCHES="${REQUIRE_ARCHES:-linux/amd64 linux/arm64}"

PASS=0; FAIL=0
ok(){ echo "  ✅ $1"; PASS=$((PASS+1)); }
no(){ echo "  ❌ $1"; FAIL=$((FAIL+1)); }

require(){ command -v "$1" >/dev/null || { echo "Missing required tool: $1" >&2; exit 2; }; }
require docker
require jq

if [ "$#" -eq 0 ]; then
  echo "Usage: $(basename "$0") IMAGE:TAG [IMAGE:TAG ...]" >&2
  echo "       (the Makefile passes \$(GHCR_IMAGE_NAME):\$(IMAGE_TAG) and :latest)" >&2
  exit 2
fi

# Refuse a bare tag. The Makefile derives GHCR_IMAGE_NAME from the git remote, so
# a fork has a different image name; a bare tag here would verify nothing useful
# (and can't be inspected). Same guard as wizard-smoke.sh.
for ref in "$@"; do
  case "$ref" in
    *:*) : ;;   # has a tag (or a @sha256: digest — also fine)
    *)   echo "ERROR: '$ref' is not a full IMAGE:TAG reference" >&2; exit 2 ;;
  esac
done

for ref in "$@"; do
  echo "== $ref =="

  # --raw emits the manifest bytes as-is. A 404 / auth failure / bad ref makes
  # buildx exit non-zero and print to stderr — that IS the "not present" signal.
  RAW="$(docker buildx imagetools inspect --raw "$ref" 2>/tmp/vim-err.$$)"
  RC=$?
  if [ "$RC" -ne 0 ]; then
    no "$ref is NOT present in the registry (inspect failed — likely 404/manifest unknown)"
    sed 's/^/     /' /tmp/vim-err.$$ 2>/dev/null | head -4
    rm -f /tmp/vim-err.$$
    continue
  fi
  rm -f /tmp/vim-err.$$

  # Must be a manifest LIST / OCI index — a single-image manifest has no
  # .manifests[] and means the push landed only one platform (or was a plain
  # `docker push`, not a buildx multi-arch push).
  MT="$(printf '%s' "$RAW" | jq -r '.mediaType // empty' 2>/dev/null)"
  case "$MT" in
    *image.index*|*manifest.list*)
      ok "$ref is a multi-arch index ($MT)" ;;
    *)
      no "$ref is NOT a multi-arch index (mediaType='${MT:-?}') — single-arch or plain push"
      continue ;;
  esac

  # Collect real platforms, dropping the unknown/unknown provenance +
  # attestation rows buildx attaches to a multi-arch index.
  PLATFORMS="$(printf '%s' "$RAW" | jq -r '
    .manifests[]
    | select(.platform.os != "unknown" and .platform.architecture != "unknown")
    | "\(.platform.os)/\(.platform.architecture)"' 2>/dev/null | sort -u)"

  for want in $REQUIRE_ARCHES; do
    if printf '%s\n' "$PLATFORMS" | grep -qx "$want"; then
      ok "$ref carries $want"
    else
      no "$ref is MISSING $want (has: $(printf '%s' "$PLATFORMS" | paste -sd, -))"
    fi
  done
done

echo ""
echo "========== MANIFEST VERIFY: ${PASS} passed, ${FAIL} failed  =========="
[ "$FAIL" -eq 0 ]
