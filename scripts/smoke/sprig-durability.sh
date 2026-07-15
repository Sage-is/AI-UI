#!/usr/bin/env bash
# Sprig™ graft durability gate — grafts survive a FULL container recreation,
# restored offline from the data volume (Workstream B: state.json + boot
# reconcile + volume-cached verified tar).
#
# Proof shape: graft an embedding cultivar (server child) + media-ffmpeg
# (deliver overlay, oci-artifact) -> `docker rm -f` the container -> STOP the
# local registry -> boot a fresh container on the SAME volume -> assert the
# supervisor reconciled both with NO network: the ffmpeg binary is back in the
# (brand-new) container layer, the embedding child re-spawned on a fresh port,
# and a direct /v1/embeddings call returns a vector.
#
# Usage: scripts/smoke/sprig-durability.sh [image]   (default sage-is/ai-ui:develop)
# Requires: local-registry on sage-network (make sprig_registry). Safe to re-run.
set -uo pipefail
IMG="${1:-sage-is/ai-ui:develop}"
NET="${SPRIG_SMOKE_NET:-sage-network}"; ROOT="sage-durability"; VOL="${ROOT}-data"
PORT="${SPRIG_DURABILITY_PORT:-8097}"; BASE="http://localhost:${PORT}"
PASS=0; FAIL=0; ok(){ echo "  ✅ $1"; PASS=$((PASS+1)); }; no(){ echo "  ❌ $1"; FAIL=$((FAIL+1)); }
X(){ docker exec "$ROOT" sh -lc "$1"; }

REGISTRY_STOPPED=0
cleanup(){
  # Never leave the shared registry down, even on an aborted run.
  [ "$REGISTRY_STOPPED" = "1" ] && docker start local-registry >/dev/null 2>&1
  docker rm -f "$ROOT" >/dev/null 2>&1 || true
  docker volume rm "$VOL" >/dev/null 2>&1 || true
}
trap cleanup EXIT

boot(){
  docker rm -f "$ROOT" >/dev/null 2>&1 || true
  docker run -d --name "$ROOT" --network "$NET" -p "${PORT}:8080" \
    -e SPRIG_REGISTRY=local-registry:5000 -e ENABLE_SIGNUP=True -e WEBUI_AUTH=True -v "$VOL:/app/backend/data" "$IMG" >/dev/null
  for i in $(seq 1 120); do
    [ "$(curl -s -o /dev/null -w '%{http_code}' "$BASE/health" 2>/dev/null)" = "200" ] && break; sleep 2
  done
  [ "$(curl -s -o /dev/null -w '%{http_code}' "$BASE/health")" = "200" ]
}

echo "== fresh container + fresh volume =="
docker volume rm "$VOL" >/dev/null 2>&1 || true
boot && ok "booted" || { no "initial boot"; docker logs --tail 30 "$ROOT"; exit 1; }

TOK=$(curl -s -X POST "$BASE/api/v1/auths/signup" -H 'Content-Type: application/json' \
  -d '{"name":"D","email":"durability@sage.is","password":"durability-pw-123"}' | jq -r '.token // empty')
AUTH="Authorization: Bearer $TOK"; [ -n "$TOK" ] && ok "admin signup" || { no "signup"; exit 1; }
G(){ curl -s --max-time 300 -X POST "$BASE/api/v1/retrieval/sprigs/graft" -H "$AUTH" -H 'Content-Type: application/json' -d "{\"name\":\"$1\",\"capability\":\"$2\"}"; }

echo "== graft: mock-embedding (server child) + media-ffmpeg (deliver overlay) =="
G mock-embedding embedding | jq -e '.status==true' >/dev/null 2>&1 && ok "mock-embedding grafted" || no "mock graft failed"
G media-ffmpeg media      | jq -e '.delivered==true' >/dev/null 2>&1 && ok "media-ffmpeg delivered" || no "ffmpeg delivery failed"
X 'test -x /usr/local/bin/ffmpeg' && ok "ffmpeg binary present pre-recreation" || no "ffmpeg missing pre-recreation"
X 'jq -e ".grafted | length == 2" /app/backend/data/sage-is/sprigs/state.json' >/dev/null 2>&1 \
  && ok "state.json records both grafts" || no "state.json wrong: $(X 'cat /app/backend/data/sage-is/sprigs/state.json' 2>/dev/null | head -c 200)"
X 'ls /app/backend/data/sage-is/sprigs/media-ffmpeg/*.tar.zst' >/dev/null 2>&1 \
  && ok "verified tar cached on the volume" || no "tar not cached on volume"

echo "== FULL recreation, registry OFFLINE (proves volume-only restore) =="
docker stop local-registry >/dev/null 2>&1 && REGISTRY_STOPPED=1 && echo "  local-registry stopped"
docker rm -f "$ROOT" >/dev/null 2>&1
boot && ok "fresh container on same volume (registry down)" || { no "reboot failed"; docker logs --tail 40 "$ROOT"; exit 1; }

echo "== assert boot reconcile restored both, offline =="
X 'test -x /usr/local/bin/ffmpeg' && ok "ffmpeg re-delivered into the new container layer (no network)" || no "ffmpeg NOT restored"
CAT=$(curl -s "$BASE/api/v1/retrieval/sprigs/catalog" -H "$AUTH")
echo "$CAT" | jq -e '.grafted["media-ffmpeg"].state=="delivered"' >/dev/null 2>&1 && ok "/catalog shows media-ffmpeg delivered" || no "ffmpeg absent from grafted view"
echo "$CAT" | jq -e '.grafted["mock-embedding"].state=="rooted"' >/dev/null 2>&1 && ok "/catalog shows mock-embedding rooted" || no "mock not rooted post-restart"
BURL=$(echo "$CAT" | jq -r '.grafted["mock-embedding"].base_url // empty')
DIM=$(X "curl -s ${BURL}/embeddings -H 'Content-Type: application/json' -d '{\"input\":[\"vector after full recreation\"]}' | jq '.data[0].embedding | length'")
[ "$DIM" = "384" ] && ok "re-spawned embedding serves a 384-dim vector" || no "embedding dead post-restart (dim=$DIM, url=$BURL)"

docker start local-registry >/dev/null 2>&1 && REGISTRY_STOPPED=0 && echo "  local-registry restarted"

echo ""
echo "================  DURABILITY: ${PASS} passed, ${FAIL} failed  ================"
[ "$FAIL" -eq 0 ]
