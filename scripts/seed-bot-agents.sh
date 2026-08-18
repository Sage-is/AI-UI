#!/usr/bin/env bash
# seed-bot-agents.sh — register the two Sage pullbot connections (bot9000 and
# bot9001) on a running AI-UI instance via its admin HTTP API. Idempotent: a
# bot URL already present in OPENAI_API_BASE_URLS keeps its position, so the
# stringified-index keys in OPENAI_API_CONFIGS stay valid, and its key is just
# overwritten in place. Safe to re-run.
#
# CAVEAT: POST /openai/config/update is a FULL REPLACE of the openai config, so
# the body is built as GET -> jq transform -> POST. A concurrent admin edit
# landing between the GET and the POST is lost. Acceptable for a dev rig.
#
# Usage: scripts/seed-bot-agents.sh
# Requires: a running instance at BASE (default http://localhost:8099) and
# PULLBOT_API_KEY (env, or PULLBOT_API_KEY= in $ROOT/.env).
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
. "$ROOT/scripts/lib/gate.sh"   # PASS/FAIL + ok/no/require/text_has/gate_summary
. "$ROOT/scripts/lib/test-admin.env"   # TEST_ADMIN_EMAIL/PASSWORD defaults
require curl
require jq

BASE="${BASE_URL:-http://localhost:8099}"
ADMIN_EMAIL="${ADMIN_EMAIL:-$TEST_ADMIN_EMAIL}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-$TEST_ADMIN_PASSWORD}"
PULLBOT_9000_URL="${PULLBOT_9000_URL:-https://bot9000.sage.is/v1}"; PREFIX_9000="${PREFIX_9000:-bot9000}"
PULLBOT_9001_URL="${PULLBOT_9001_URL:-https://bot9001.sage.is/v1}"; PREFIX_9001="${PREFIX_9001:-bot9001}"

# API key: env wins; else the PULLBOT_API_KEY= line from $ROOT/.env. Never
# source .env wholesale — only that one line is wanted.
if [ -z "${PULLBOT_API_KEY:-}" ]; then
  PULLBOT_API_KEY="$(sed -n 's/^PULLBOT_API_KEY=//p' "$ROOT/.env" 2>/dev/null)"
fi
if [ -z "$PULLBOT_API_KEY" ]; then
  echo "seed-bot-agents: PULLBOT_API_KEY unset and no PULLBOT_API_KEY= line in $ROOT/.env" >&2
  exit 2
fi
export PULLBOT_API_KEY   # so the jq transform reads it from $ENV (never on argv)

echo "== $BASE : sign in as $ADMIN_EMAIL =="
TOKEN="$(curl -s -X POST "$BASE/api/v1/auths/signin" -H 'Content-Type: application/json' -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}" | jq -r '.token // empty')"
[ -n "$TOKEN" ] && ok "signed in" || { no "signin failed (wrong admin credentials?)"; exit 1; }
AUTH="Authorization: Bearer $TOKEN"

CFG="$(curl -s -H "$AUTH" "$BASE/openai/config")"
echo "$CFG" | jq -e 'has("OPENAI_API_BASE_URLS")' >/dev/null 2>&1 \
  && ok "fetched openai/config" || { no "openai/config fetch failed: $(echo "$CFG" | head -c 150)"; exit 1; }

# ONE jq transform: for each bot URL, keep its position in
# OPENAI_API_BASE_URLS (or append), overwrite the key at that index, and set/
# overwrite the matching config entry to an enabled external connection.
BOTS="[{\"url\":\"$PULLBOT_9000_URL\",\"prefix\":\"$PREFIX_9000\"},{\"url\":\"$PULLBOT_9001_URL\",\"prefix\":\"$PREFIX_9001\"}]"
BODY="$(echo "$CFG" | jq --argjson bots "$BOTS" '
  .OPENAI_API_BASE_URLS as $urls |
  .OPENAI_API_KEYS as $keys |
  .OPENAI_API_CONFIGS as $cfgs |
  (reduce $bots[] as $b ($urls; if index($b.url) then . else . + [$b.url] end)) as $final_urls |
  {
    ENABLE_OPENAI_API: true,
    OPENAI_API_BASE_URLS: $final_urls,
    OPENAI_API_KEYS: (reduce $bots[] as $b ($keys; ($final_urls | index($b.url)) as $i | .[$i] = $ENV.PULLBOT_API_KEY)),
    OPENAI_API_CONFIGS: (reduce $bots[] as $b ($cfgs; ($final_urls | index($b.url)) as $i | .[($i|tostring)] = {enable:true, prefix_id:$b.prefix, tags:[], model_ids:[], connection_type:"external"}))
  }')"

echo "== register pullbot connections =="
UPD="$(curl -s -w $'\n%{http_code}' -X POST "$BASE/openai/config/update" -H "$AUTH" -H 'Content-Type: application/json' -d "$BODY")"
UCODE="${UPD##*$'\n'}"; UBODY="${UPD%$'\n'*}"
if [ "$UCODE" = "200" ]; then
  ok "openai/config/update -> 200"
else
  DETAIL="$(echo "$UBODY" | jq -r '.detail // empty')"
  no "config update failed (HTTP $UCODE): $DETAIL"
  echo "  note: the server probes each new URL for reachability — a 400 usually means the bot endpoint ($PULLBOT_9000_URL / $PULLBOT_9001_URL) is down." >&2
  exit 1
fi

echo "== verify via /api/models =="
MODELS="$(curl -s -H "$AUTH" "$BASE/api/models")"
text_has "$MODELS" 'bot9000\.Sage-Agent' && ok "bot9000.Sage-Agent listed" || no "bot9000.Sage-Agent missing from /api/models"
text_has "$MODELS" 'bot9001\.Sage-Agent' && ok "bot9001.Sage-Agent listed" || no "bot9001.Sage-Agent missing from /api/models"

gate_summary "PULLBOT SEED"
