#!/usr/bin/env bash
# manifest-verify-fixture.sh — prove the manifest guard's LOGIC is correct.
#
# Solution-C-style fixture: exercise scripts/verify-image-manifest.sh against
# three KNOWN public-image cases and assert its exit code each time. Read-only —
# it only `imagetools inspect`s public images (no push, no local build), so it is
# safe to run anytime and needs no registry credentials.
#
#   good        multi-arch index (alpine:TAG, amd64+arm64)      -> guard EXIT 0
#   single-arch alpine pinned to its amd64 digest (arm64 gone)  -> guard NON-ZERO
#   absent      a tag that does not exist (404)                 -> guard NON-ZERO
#
# The single-arch digest is discovered at runtime from alpine's own index, so it
# never rots into a stale hardcoded constant.
#
# Usage: scripts/smoke/manifest-verify-fixture.sh   (optional: FIXTURE_IMAGE=alpine:3.20)
set -uo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
GUARD="$HERE/verify-image-manifest.sh"
IMG="${FIXTURE_IMAGE:-alpine:3.20}"

PASS=0; FAIL=0
ok(){ echo "  ✅ $1"; PASS=$((PASS+1)); }
no(){ echo "  ❌ $1"; FAIL=$((FAIL+1)); }
require(){ command -v "$1" >/dev/null || { echo "Missing required tool: $1" >&2; exit 2; }; }
require docker
require jq
[ -x "$GUARD" ] || { echo "ERROR: guard not executable at $GUARD" >&2; exit 2; }

# assert_exit EXPECTED LABEL -- args-to-guard...
# Runs the guard quietly and checks its exit code is (0) or (non-0) as expected.
assert_exit(){
  local expect="$1" label="$2"; shift 2
  "$GUARD" "$@" >/tmp/mvf-out.$$ 2>&1; local rc=$?
  if [ "$expect" = "0" ]; then
    [ "$rc" -eq 0 ] && ok "$label -> guard PASSED (exit 0)" \
      || { no "$label -> guard should PASS but exited $rc"; sed 's/^/       /' /tmp/mvf-out.$$; }
  else
    [ "$rc" -ne 0 ] && ok "$label -> guard FAILED as expected (exit $rc)" \
      || no "$label -> guard should FAIL but exited 0"
  fi
  rm -f /tmp/mvf-out.$$
}

echo "== fixture image: $IMG =="

# 1. GOOD — a real multi-arch index passes.
assert_exit 0 "multi-arch index ($IMG)" "$IMG"

# 2. SINGLE-ARCH — pin to the amd64 leaf so arm64 is absent; guard must fail.
AMD64_DIGEST="$(docker buildx imagetools inspect --raw "$IMG" 2>/dev/null \
  | jq -r '.manifests[] | select(.platform.os=="linux" and .platform.architecture=="amd64") | .digest' \
  | head -1)"
if [ -n "$AMD64_DIGEST" ]; then
  SINGLE="${IMG%%:*}@${AMD64_DIGEST}"
  assert_exit 1 "single-arch (amd64 leaf $SINGLE)" "$SINGLE"
else
  no "could not resolve $IMG amd64 digest (network? image gone?) — single-arch case skipped"
fi

# 3. ABSENT — a tag that cannot exist; inspect 404s, guard must fail.
assert_exit 1 "absent tag" "${IMG%%:*}:this-tag-does-not-exist-poka-yoke"

echo ""
echo "========== MANIFEST-VERIFY FIXTURE: ${PASS} passed, ${FAIL} failed  =========="
[ "$FAIL" -eq 0 ]
