#!/usr/bin/env bash
# Sprig™ artifact-signing gate — proves the minisign sign→verify chain end to
# end with the committed DEV fixture key (scripts/dev-keys/, worthless by
# design; production uses the operator's own key).
#
# Proof shape:
#   1. sign backup-rclone + browser-ml in the local registry (sign-sprigs.sh)
#   2. boot with the dev pubkey pinned AND SPRIG_REQUIRE_SIGNED=1
#   3. graft signed artifact        -> grafts (signature verified)
#   4. graft unsigned artifact      -> REFUSED, error names the missing .minisig
#   5. re-push browser-ml with a tampered trusted comment -> REFUSED (minisign)
#   6. restart container            -> boot reconcile re-verifies the cached
#                                      sig offline and restores the graft
#   7. restore a clean signature for browser-ml (leave the shared registry sane)
#
# Usage: scripts/smoke/sprig-signing.sh [image]   (default sage-is/ai-ui:develop)
# Requires: local-registry on sage-network (make sprig_registry). Safe to re-run.
set -uo pipefail
IMG="${1:-sage-is/ai-ui:develop}"
NET="${SPRIG_SMOKE_NET:-sage-network}"; ROOT="sage-signing"; VOL="${ROOT}-data"
PORT="${SPRIG_SIGNING_PORT:-8098}"; BASE="http://localhost:${PORT}"
HERE="$(cd "$(dirname "$0")/../.." && pwd)"
DEVKEY="$HERE/scripts/dev-keys/sprig-dev-TEST-ONLY.key"
DEVPUB="$(sed -n 2p "$HERE/scripts/dev-keys/sprig-dev-TEST-ONLY.pub")"
PASS=0; FAIL=0; ok(){ echo "  ✅ $1"; PASS=$((PASS+1)); }; no(){ echo "  ❌ $1"; FAIL=$((FAIL+1)); }

cleanup(){
  # Leave the shared registry with CLEAN signatures even on an aborted run.
  SIGN_KEY="$DEVKEY" SIGN_NOPASS=1 ONLY="sprig-browser-ml" "$HERE/scripts/sign-sprigs.sh" >/dev/null 2>&1 || true
  docker rm -f "$ROOT" >/dev/null 2>&1 || true
  docker volume rm "$VOL" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "== 1. sign backup-rclone + browser-ml with the DEV fixture key =="
SIGN_KEY="$DEVKEY" SIGN_NOPASS=1 ONLY="sprig-backup-rclone sprig-browser-ml" \
  "$HERE/scripts/sign-sprigs.sh" >/dev/null \
  && ok "signed + re-pushed both artifacts" || { no "sign-sprigs.sh failed"; exit 1; }

echo "== 2. boot with dev pubkey pinned + SPRIG_REQUIRE_SIGNED=1 =="
docker volume rm "$VOL" >/dev/null 2>&1 || true
docker rm -f "$ROOT" >/dev/null 2>&1 || true
docker run -d --name "$ROOT" --network "$NET" -p "${PORT}:8080" \
  -e SPRIG_REGISTRY=local-registry:5000 -e ENABLE_SIGNUP=True -e WEBUI_AUTH=True \
  -e SPRIG_MINISIGN_PUBKEY="$DEVPUB" -e SPRIG_REQUIRE_SIGNED=1 \
  -v "$VOL:/app/backend/data" "$IMG" >/dev/null
for i in $(seq 1 120); do
  [ "$(curl -s -o /dev/null -w '%{http_code}' "$BASE/health" 2>/dev/null)" = "200" ] && break; sleep 2
done
[ "$(curl -s -o /dev/null -w '%{http_code}' "$BASE/health")" = "200" ] \
  && ok "booted" || { no "boot"; docker logs --tail 30 "$ROOT"; exit 1; }

TOK=$(curl -s -X POST "$BASE/api/v1/auths/signup" -H 'Content-Type: application/json' \
  -d '{"name":"S","email":"signing@sage.is","password":"signing-pw-123"}' | jq -r '.token // empty')
AUTH="Authorization: Bearer $TOK"; [ -n "$TOK" ] && ok "admin signup" || { no "signup"; exit 1; }
G(){ curl -s --max-time 300 -X POST "$BASE/api/v1/retrieval/sprigs/graft" -H "$AUTH" -H 'Content-Type: application/json' -d "{\"name\":\"$1\",\"capability\":\"$2\"}"; }

echo "== 3. signed artifact grafts (signature verified) =="
G backup-rclone backup | jq -e '.delivered==true' >/dev/null 2>&1 \
  && ok "backup-rclone (signed) grafted under REQUIRE_SIGNED" || no "signed graft failed"
docker logs "$ROOT" 2>&1 | grep -q "minisign OK" \
  && ok "supervisor logged 'minisign OK'" || no "no minisign OK in logs"

echo "== 4. unsigned artifact is REFUSED =="
R=$(G media-ffmpeg media)
echo "$R" | jq -e '.status==true or .delivered==true' >/dev/null 2>&1 \
  && no "UNSIGNED artifact grafted — enforcement broken" \
  || ok "unsigned media-ffmpeg refused"
echo "$R" | grep -qi "signed artifact" \
  && ok "refusal names the missing signature" || no "refusal detail unclear: $(echo "$R" | head -c 160)"

echo "== 5. tampered signature is REFUSED =="
WORK=$(mktemp -d)
docker run --rm --network "$NET" -v "$WORK:/w" -w /w ghcr.io/oras-project/oras:v1.2.0 \
  pull --plain-http "local-registry:5000/sprig-browser-ml:v1" >/dev/null
TARF=$(cd "$WORK" && ls -- *.tar.zst | head -1)
# Swap the signed trusted comment -> the global signature must no longer verify.
awk 'NR==3{print "trusted comment: EVIL tampered comment"; next} {print}' \
  "$WORK/$TARF.minisig" > "$WORK/$TARF.minisig.tmp" && mv "$WORK/$TARF.minisig.tmp" "$WORK/$TARF.minisig"
docker run --rm --network "$NET" -v "$WORK:/w" -w /w ghcr.io/oras-project/oras:v1.2.0 \
  push --plain-http "local-registry:5000/sprig-browser-ml:v1" \
  --artifact-type "application/vnd.sage-is.sprig.v1" \
  "$TARF:application/vnd.sage-is.sprig.tar+zstd" \
  "$TARF.minisig:application/vnd.sage-is.sprig.minisig" >/dev/null
rm -rf "$WORK"
R=$(G browser-ml browser-ml)
echo "$R" | jq -e '.status==true or .delivered==true' >/dev/null 2>&1 \
  && no "TAMPERED signature accepted — verification broken" \
  || ok "tampered browser-ml refused"
echo "$R" | grep -qi "minisign" \
  && ok "refusal names minisign verification" || no "refusal detail unclear: $(echo "$R" | head -c 160)"

echo "== 6. restart: boot reconcile re-verifies the cached signature offline =="
docker restart "$ROOT" >/dev/null
for i in $(seq 1 120); do
  [ "$(curl -s -o /dev/null -w '%{http_code}' "$BASE/health" 2>/dev/null)" = "200" ] && break; sleep 2
done
CAT=$(curl -s "$BASE/api/v1/retrieval/sprigs/catalog" -H "$AUTH")
echo "$CAT" | jq -e '.grafted["backup-rclone"].state=="delivered"' >/dev/null 2>&1 \
  && ok "signed graft restored across restart (cached sig re-verified)" \
  || no "backup-rclone not restored: $(echo "$CAT" | jq -c '.grafted' 2>/dev/null | head -c 160)"

echo ""
echo "================  SIGNING: ${PASS} passed, ${FAIL} failed  ================"
[ "$FAIL" -eq 0 ]
