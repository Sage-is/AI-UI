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
#   KEEP=1 scripts/manual-check.sh      # leave it running after the script exits
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
# KEEP=1 leaves the instance running after this script exits.
#
# The default (tear down on exit) is right for an interactive look, but it makes
# the instance a hostage of whatever shell launched it: close the terminal, drop
# the SSH session, or have an agent's process tree cleaned up, and the review
# instance you were halfway through vanishes. That happened, so this exists.
#
# With KEEP=1 the containers outlive the script and you tear them down when you
# are actually finished — the command is printed at the end.
if [ "${KEEP:-0}" != "1" ]; then
  trap cleanup EXIT INT TERM
else
  # Still clean up a HALF-BUILT instance: a boot that fails partway should not
  # leave a broken container behind wearing the name of a good one.
  trap 'rc=$?; [ "$rc" = "0" ] || cleanup; exit $rc' EXIT
  trap cleanup INT TERM
fi

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
    at parity — the how-to-fix remedy is a <details> disclosure rather than
    a modal, and the timestamp is absolute rather than a live relative label.

  Theme & Branding
    old (SvelteKit)   https://localhost:$PORT/admin/settings/theme
    new (no build)    https://localhost:$PORT/pages/admin/branding
    the new one previews SAVED values; the old one previews as you type.
    Deliberate — matching it would need a round-trip per keystroke.

  Setup wizard — five panels, and the old side has NO URL.
    Reach the old ones from Admin → Settings → General:
      "See what's new"     opens the changelog panel
      "Run Setup Wizard"   opens on Welcome; the progress dots jump between
                           panels once you are past it

    changelog     new  https://localhost:$PORT/pages/admin/setup/changelog
    features      new  https://localhost:$PORT/pages/admin/setup/features
    developer     new  https://localhost:$PORT/pages/admin/setup/developer
    complete      new  https://localhost:$PORT/pages/admin/setup/complete
    search-audio  new  https://localhost:$PORT/pages/admin/setup/search-audio

    Known and deliberate differences, so you can judge them rather than
    report them:
      * "Continue" and "Let's Go" close the modal on the old side. At a
        route there is nothing to close, so they record the durable half —
        changelog read, setup complete — and re-render.
      * complete shows auth / connection / working-alone from the stored
        configuration; the modal reads the browser's loaded model list and
        what you clicked during that run. They disagree on a fresh
        instance. This is the one to form an opinion about.
      * the modal polls model status every 5s while a download runs; the
        page renders status at request time and offers Refresh.

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

  3b. The wizard's graft button, on BOTH sides. It used to graft
     'mock-embedding' and say document search was ready — that mock seeds
     its vectors from a sha256 of the input text, so search returned noise
     while every message said success. Now: tick only Speech-to-Text and
     graft, then check Admin → Sprigs shows whisper-base-ggml rooted.
     Tick Document Search and it grafts vector-chroma first, because the
     ONNX cultivar will not start without the runtime that rides with it.
     That chain is a slow graft and there is no progress indicator yet —
     worth judging how bad that feels.

  3c. Untick a step on Welcome, then press Get Started. The wizard opens
     on the step you unticked. That is a known defect, filed, NOT fixed
     here — it self-corrects on the next click, which is why nobody
     noticed. Included so you can tell it apart from anything new.

  4. Phone width. Both new pages are written mobile-first; the cards
     restack rather than squeeze. Worth a real device if you have one.

  5. The marketplace slot (re-run with --graft-ui). A grafted ui-Sprig's
     fragment renders inside the page, server-side.

  6. The branding colour pickers. Both directions of the sync are tested
     now, because a synthetic input event reaches the same code a human
     does. What no driver can check is the part above that: the swatch
     opening the OS dialog at all, and whether picking a colour there
     feels immediate. That is what a human still adds here.

  TELL ME WHAT FEELS WRONG. The suite is green and that is exactly the
  evidence Phase S showed to be weakest — it passed a broken autoscroll.

  Logs:  docker logs -f $ROOT
  Ctrl-C to tear down.
────────────────────────────────────────────────────────────────────────────

WALKTHROUGH

if [ "${KEEP:-0}" = "1" ]; then
  echo "  KEEP=1 — the instance stays up after this exits."
  echo "  Tear it down with:  docker rm -f $ROOT $TLS && docker volume rm $VOL"
  echo ""
  exit 0
fi

while true; do sleep 3600; done
