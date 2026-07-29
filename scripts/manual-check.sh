#!/usr/bin/env bash
# manual-check.sh — bring up a Rootstock™ for a HUMAN to click through.
#
# Phase S made this a standing condition rather than a nicety: an autoscroll
# went 13/13 green under a real browser driver and was broken on a real
# trackpad, because synthetic input models neither trackpad jitter nor touch
# momentum. So every migrated surface gets a human pass before it is called
# done, and this is the thing that makes that cheap enough to actually do.
#
# It boots the image on a THROWAWAY volume, seeds an admin, puts Caddy in front
# for a secure context, and prints the old and new surfaces side by side so you
# can flip between them. Nothing here touches your real data.
#
# Usage:
#   scripts/manual-check.sh              # boot, seed, print the walkthrough
#   scripts/manual-check.sh --graft-ui   # also graft the example ui-Sprig
#   PORT=9443 scripts/manual-check.sh    # different port
#
# Ctrl-C tears everything down.
set -uo pipefail

IMG="${IMG:-sage-is/ai-ui:develop}"
PORT="${PORT:-9443}"
NET="${NET:-sage-network}"
ROOT="sage-manual"; TLS="sage-manual-tls"; VOL="sage-manual-data"
EMAIL="${EMAIL:-admin@example.com}"; PASSWORD="${PASSWORD:-password}"
HERE="$(cd "$(dirname "$0")/.." && pwd)"
BASE="http://localhost:8101"

cleanup(){
  echo ""
  echo "tearing down…"
  docker rm -f "$ROOT" "$TLS" >/dev/null 2>&1 || true
  docker volume rm "$VOL" >/dev/null 2>&1 || true
  rm -f /tmp/manual-Caddyfile
}
trap cleanup EXIT INT TERM

docker network inspect "$NET" >/dev/null 2>&1 || docker network create "$NET" >/dev/null
cleanup >/dev/null 2>&1

echo "== booting $IMG on a throwaway volume =="
# SPRIG_REGISTRY points at the local registry so grafting works like it does in
# the gates. ENABLE_SIGNUP is on only long enough to seed the first admin —
# this fork hard-closes signup once one exists.
docker run -d --name "$ROOT" --network "$NET" -p 8101:8080 \
  -e SPRIG_REGISTRY=local-registry:5000 -e ENABLE_SIGNUP=True -e WEBUI_AUTH=True \
  -v "$VOL:/app/backend/data" "$IMG" >/dev/null

for _ in $(seq 1 120); do
  [ "$(curl -s -o /dev/null -w '%{http_code}' "$BASE/health" 2>/dev/null)" = "200" ] && break
  sleep 2
done
[ "$(curl -s -o /dev/null -w '%{http_code}' "$BASE/health")" = "200" ] || {
  echo "failed to boot"; docker logs --tail 30 "$ROOT"; exit 1; }
echo "  ✅ booted"

echo "== seeding admin =="
TOK="$(curl -s -X POST "$BASE/api/v1/auths/signup" -H 'Content-Type: application/json' \
  -d "{\"name\":\"Admin\",\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin).get("token",""))' 2>/dev/null)"
[ -n "$TOK" ] && echo "  ✅ $EMAIL / $PASSWORD" || echo "  ⚠️  signup returned no token (an admin may already exist)"

if [ "${1:-}" = "--graft-ui" ] && [ -n "$TOK" ]; then
  echo "== grafting the example ui-Sprig so the marketplace slot is visible =="
  curl -s -X POST "$BASE/api/v1/retrieval/sprigs/graft" \
    -H "Authorization: Bearer $TOK" -H 'Content-Type: application/json' \
    -d '{"name":"ui-workshop-welcome","capability":"ui"}' \
    | python3 -c 'import sys,json; d=json.load(sys.stdin); print("  ✅ grafted" if d.get("status") else "  ❌ "+str(d.get("detail")))' 2>/dev/null \
    || echo "  ❌ graft failed (is local-registry up? make sprig_registry)"
fi

echo "== tls sidecar (secure context) =="
# https matters even for a click-through: over plain http on a non-localhost
# origin the browser silently denies clipboard, crypto.subtle and service
# workers, so you would be testing a different app than the one you ship.
cat > /tmp/manual-Caddyfile <<CADDY
{
	auto_https disable_redirects
}
https://localhost:$PORT {
	tls internal
	reverse_proxy $ROOT:8080
}
CADDY
docker run -d --name "$TLS" --network "$NET" -p "$PORT:$PORT" \
  -v /tmp/manual-Caddyfile:/etc/caddy/Caddyfile:ro caddy:2-alpine >/dev/null
for _ in $(seq 1 30); do
  curl -sk -o /dev/null "https://localhost:$PORT/health" 2>/dev/null && break; sleep 1
done
echo "  ✅ https://localhost:$PORT  (self-signed — accept the warning once)"

cat <<WALKTHROUGH

────────────────────────────────────────────────────────────────────────────
  Sign in:  $EMAIL  /  $PASSWORD      at  https://localhost:$PORT

  THE SAME SURFACE, BOTH WAYS — open each pair and flip between them.

  Sprigs
    old (SvelteKit)   https://localhost:$PORT/admin/sprigs
    new (no build)    https://localhost:$PORT/pages/admin/sprigs

  Diagnostics
    old (SvelteKit)   https://localhost:$PORT/admin/diagnostics
    new (no build)    https://localhost:$PORT/pages/admin/diagnostics
    ⚠️  the new one is PARTIAL — no how-to-fix modal, no command library,
        no per-row re-probe, no technical-detail expander. Expected.

  WHAT TO LOOK FOR

  1. First paint. Reload each with the network throttled. The new pages
     arrive with their content already in the HTML; the old ones show
     chrome, then fill in. View-source on a new page and you will see the
     rows. View-source on an old one and you will see an empty div.

  2. Graft and prune on the new Sprigs page. Watch the whole panel swap.
     Try grafting 'multilingual-e5-large' on a bare Rootstock — the error
     should name the fix ("graft vector-chroma first"), not just fail.

  3. Sign out, then hit a /pages/ URL directly. You should land on the
     sign-in screen, not a JSON error.

  4. Phone width. Both new pages are written mobile-first; the cards
     restack rather than squeeze. Worth a real device if you have one.

  5. The marketplace slot (re-run with --graft-ui). A grafted ui-Sprig's
     fragment renders inside the page, server-side.

  TELL ME WHAT FEELS WRONG. The suite is green and that is exactly the
  evidence Phase S showed to be weakest — it passed a broken autoscroll.

  Logs:  docker logs -f $ROOT
  Ctrl-C to tear down.
────────────────────────────────────────────────────────────────────────────

WALKTHROUGH

while true; do sleep 3600; done
