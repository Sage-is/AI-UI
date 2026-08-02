#!/usr/bin/env bash
# Dev-reload gate — proves the ON state of the development reloader.
#
# `pages-dev-reload.cy.ts` asserts the OFF state, which is what every shipped
# instance runs and what the e2e harness gives us. It cannot reach the ON state:
# that needs a container booted with PAGES_RELOAD_DIRS and a source tree mounted
# over the image, which is a container-creation-time shape, not something a
# browser driver can arrange.
#
# So this is the other half, and it exists because the feature's whole promise
# is "your edit lands by itself". A promise nothing checks is a promise that
# quietly stops being true — the reloader watching the wrong directory, or the
# include filter widening until every CSS save costs a restart, would both look
# exactly like it working until someone timed it.
#
# What it asserts, in order:
#   1. a .py edit restarts the app and is served, with NO manual restart
#   2. an asset edit is served and does NOT restart the app
#   3. the SSE endpoint exists and speaks text/event-stream
#   4. the page carries the reload island
#   5. a reload still completes while a stream is OPEN
#   6. the stream names its process, so a bare reconnect reloads nothing
#   7. diagnostics reports the reloader as degraded
#
# Every edit is made to a COPY under a temp mount, never to the working tree, so
# a failed run cannot leave a modified panel behind.
#
#   scripts/gates/dev-reload/run-gate.sh          # uses sage-is/ai-ui:develop
#   IMG=sage-is/ai-ui:3.0.0 scripts/gates/dev-reload/run-gate.sh
#
# EVERY curl here carries --max-time, and that is not belt-and-braces. Proving
# this gate could fail, one of the deliberate breaks — widening the reloader's
# include filter to '*' — put the app in a restart LOOP rather than making it
# wrong, and the gate hung for ten minutes instead of reporting. A gate that
# hangs on a broken product cannot tell you the product is broken, which is the
# same defect as one that passes on it. Deadlines everywhere.
set -uo pipefail

IMG="${IMG:-sage-is/ai-ui:develop}"
NAME="sage-reload-gate-$$"
VOL="sage-reload-gate-data-$$"
BASE="http://localhost:8109"
HERE="$(cd "$(dirname "$0")/../../.." && pwd)"
WORK="$(mktemp -d)"
EMAIL="admin@example.com"; PASSWORD="password"
FAILED=0

cleanup() {
  docker rm -f "$NAME" >/dev/null 2>&1 || true
  docker volume rm "$VOL" >/dev/null 2>&1 || true
  rm -rf "$WORK"
}
trap cleanup EXIT INT TERM

say()  { printf '  %s\n' "$*"; }
pass() { printf '  \033[32m✓\033[0m %s\n' "$*"; }
fail() { printf '  \033[31m✗\033[0m %s\n' "$*"; FAILED=1; }

# A COPY of the pages package. The gate mutates panels, and mutating the working
# tree would mean a killed run leaves edits behind for someone else to find.
cp -R "$HERE/app/backend/sage_is_ai/pages" "$WORK/pages"

echo "== booting $IMG with the reloader on =="
docker run -d --name "$NAME" -p 8109:8080 \
  -e ENABLE_SIGNUP=True -e WEBUI_AUTH=True \
  -e PAGES_RELOAD_DIRS=/app/backend/sage_is_ai/pages \
  -v "$WORK/pages:/app/backend/sage_is_ai/pages" \
  -v "$VOL:/app/backend/data" "$IMG" >/dev/null || { echo "docker run failed"; exit 1; }

for _ in $(seq 1 120); do
  [ "$(curl -s --max-time 5 -o /dev/null -w '%{http_code}' "$BASE/health" 2>/dev/null)" = "200" ] && break
  sleep 2
done
[ "$(curl -s --max-time 5 -o /dev/null -w '%{http_code}' "$BASE/health")" = "200" ] || {
  echo "failed to boot"; docker logs --tail 40 "$NAME"; exit 1; }
say "booted"

TOK="$(curl -s --max-time 10 -X POST "$BASE/api/v1/auths/signup" -H 'Content-Type: application/json' \
  -d "{\"name\":\"Admin\",\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin).get("token",""))' 2>/dev/null)"
[ -n "$TOK" ] || { echo "could not seed an admin"; exit 1; }

auth_get() { curl -s --max-time 5 --cookie "token=$TOK" "$BASE$1"; }

# Wait for a string to appear, up to N seconds. Polling rather than a fixed
# sleep, because the number we are trying to learn IS how long this takes.
wait_for() { # path needle seconds -> prints elapsed, or empty on timeout
  local path="$1" needle="$2" limit="$3" start now
  start="$(python3 -c 'import time; print(time.time())')"
  while :; do
    if auth_get "$path" | grep -q "$needle"; then
      python3 -c "import time; print(f'{time.time() - $start:.1f}')"
      return 0
    fi
    now="$(python3 -c 'import time; print(time.time())')"
    python3 -c "import sys; sys.exit(0 if $now - $start > $limit else 1)" && return 1
    sleep 0.25
  done
}

echo ""
echo "== 1. a Python edit restarts the app by itself =="
# Edits a DATA table, not any panel's markup.
#
# This used to inject a marker into `welcome_panel.py`'s `<section>` string, and
# the templating spike moved that markup into a `.html` file — so the gate went
# red saying "the reloader did not pick it up" when the reloader was fine and
# the anchor was gone. (Its own assert message predicted exactly that, which is
# the only reason it took a minute rather than an hour.)
#
# `_SETUP_PAGES` is a dict of headings in `router.py`, rendered into the page
# shell. Appending to one is a Python change under the watched directory with
# no opinion about how any panel builds its HTML, which is what this check is
# actually about.
MARK="RELOAD-GATE-$$"
python3 - "$WORK/pages/router.py" "$MARK" <<'PY'
import sys, pathlib
p, mark = pathlib.Path(sys.argv[1]), sys.argv[2]
s = p.read_text()
old = '"welcome": ("Setup Wizard"'
assert old in s, "_SETUP_PAGES['welcome'] moved; this gate needs updating"
p.write_text(s.replace(old, f'"welcome": ("Setup Wizard {mark}"', 1))
PY
ELAPSED="$(wait_for "/pages/admin/setup/welcome" "$MARK" 60)"
if [ -n "$ELAPSED" ]; then
  pass "panel edit served after ${ELAPSED}s, no manual restart"
else
  fail "panel edit never appeared — the reloader did not pick it up"
  docker logs --tail 20 "$NAME"
fi

# The APP WORKER's pid set, not the container's start time.
#
# This check used `docker inspect .State.StartedAt` first, and that could not
# fail for the thing it claimed to test: uvicorn's reloader restarts a CHILD
# process inside the container, so the container's start time never moves. It
# only ever caught the deliberate break because that one crash-looped the whole
# container. Measured 2026-07-31 against a real reload: pids change, StartedAt
# does not.
workers() { docker exec "$NAME" sh -c 'ps -eo pid,comm | grep python3 | awk "{print \$1}" | sort | tr "\n" ","' 2>/dev/null; }

echo ""
echo "== 2. an asset edit does NOT restart the app =="
WORKERS_BEFORE="$(workers)"
printf '\n/* %s */\n' "$MARK" >> "$WORK/pages/assets/pages.css"
sleep 3
# Not `curl … | grep -q`: pages.css is far larger than a pipe buffer, so grep
# would exit on the match while curl still had bytes queued, curl would take
# SIGPIPE, and pipefail would report the MATCH as a failure. Same shape as
# `fetch_has` in scripts/lib/gate.sh, inlined because this gate keeps its own
# pass/fail counters.
CSS_BODY="$(curl -s --max-time 5 "$BASE/pages/_assets/pages.css")" || true
if [[ "$CSS_BODY" == *"$MARK"* ]]; then
  pass "asset edit served"
else
  fail "asset edit not served"
fi
WORKERS_AFTER="$(workers)"
if [ -z "$WORKERS_BEFORE" ]; then
  fail "could not read the app worker pids — this check cannot report"
elif [ "$WORKERS_BEFORE" = "$WORKERS_AFTER" ]; then
  pass "and the app worker did not restart"
else
  fail "the app RESTARTED on a CSS change — the reloader's include filter widened"
fi

echo ""
echo "== 3. the reload endpoint exists and streams =="
CT="$(curl -s -o /dev/null -w '%{content_type}' --cookie "token=$TOK" --max-time 3 "$BASE/pages/_dev/reload")"
case "$CT" in
  text/event-stream*) pass "content-type is $CT" ;;
  *)                  fail "expected text/event-stream, got '${CT:-<none>}'" ;;
esac

echo ""
echo "== 4. the page carries the reload island =="
if auth_get "/pages/admin/setup/welcome" | grep -q "dev-reload.js"; then
  pass "dev-reload.js is referenced"
else
  fail "the page does not load dev-reload.js — shell injection is not firing"
fi

echo ""
echo "== 5. a reload still completes with a stream open =="
# The check this gate was MISSING, and the bug it would have caught.
#
# The dev-reload endpoint is a long-lived SSE stream, and uvicorn waits for
# in-flight responses before a reload can finish — so an open browser tab held
# the old worker alive and "Reloading..." never completed. Found by hand, on a
# live instance, with a tab left open. This gate ran checks 1 and 3 in an order
# that never overlapped them, so it stayed green through the whole defect.
#
# Order matters: OPEN the stream, THEN edit a panel, and require the edit to
# land anyway.
MARK2="RELOAD-GATE-STREAM-$$"
curl -s --max-time 45 --cookie "token=$TOK" -N "$BASE/pages/_dev/reload" >/dev/null 2>&1 &
STREAM_PID=$!
sleep 2
python3 - "$WORK/pages/router.py" "$MARK2" <<'EDIT'
import sys, pathlib
p, mark = pathlib.Path(sys.argv[1]), sys.argv[2]
s = p.read_text()
old = '"complete": ("You are all set"'
assert old in s, "_SETUP_PAGES['complete'] moved; this gate needs updating"
p.write_text(s.replace(old, f'"complete": ("You are all set {mark}"', 1))
EDIT
ELAPSED2="$(wait_for "/pages/admin/setup/complete" "$MARK2" 60)"
kill "$STREAM_PID" 2>/dev/null || true
# Assert the TIME, not just completion. The first version of this check only
# required the edit to land eventually, and with the defect reinstated it landed
# in 45.3s — because the client's own --max-time finally closed the stream and
# unblocked the shutdown. It PASSED on the broken build. A gate that reports the
# same verdict at 6s and at 45s measured neither.
#
# 20s discriminates with room to spare: healthy is ~6s (3s of graceful-shutdown
# wait plus the boot), broken is however long the client happens to hold on.
if [ -z "$ELAPSED2" ]; then
  fail "the reload HUNG while a dev-reload stream was open"
  docker logs --tail 15 "$NAME"
elif python3 -c "import sys; sys.exit(0 if float('$ELAPSED2') > 20 else 1)"; then
  fail "reload took ${ELAPSED2}s with a stream open — the stream is blocking shutdown"
else
  pass "reload completed in ${ELAPSED2}s with a stream open"
fi

echo ""
echo "== 6. the stream identifies the process, so a reconnect alone reloads nothing =="
# The mechanism has been wrong twice, so it gets its own check.
#
# v1 reloaded on any RECONNECT. That was a proxy for "the server restarted", and
# it broke the moment the stream began ending itself every minute to stop it
# blocking shutdown — the browser reconnected on a timer and the page reloaded
# with it, every 60 seconds, reported within minutes of shipping.
#
# The fact, not the proxy: each stream opens with `event: hello` naming the
# process. Two streams from the SAME process must agree, or the client reloads
# for no reason; a stream after a restart must differ, or it never reloads at
# all. Both halves, because either one alone passes on a constant.
TOKEN_A="$(curl -s --max-time 6 --cookie "token=$TOK" -N "$BASE/pages/_dev/reload" 2>/dev/null | grep -m1 -A1 '^event: hello' | tail -1 | sed 's/^data: //')"
TOKEN_B="$(curl -s --max-time 6 --cookie "token=$TOK" -N "$BASE/pages/_dev/reload" 2>/dev/null | grep -m1 -A1 '^event: hello' | tail -1 | sed 's/^data: //')"
if [ -z "$TOKEN_A" ]; then
  fail "the stream sent no hello — the client has nothing to compare"
elif [ "$TOKEN_A" != "$TOKEN_B" ]; then
  fail "two streams from one process disagreed ($TOKEN_A vs $TOKEN_B) — every reconnect would reload"
else
  pass "two streams from one process agree ($TOKEN_A)"
fi

# And it must CHANGE across a reload, or nothing ever reloads.
MARK3="RELOAD-GATE-TOKEN-$$"
python3 - "$WORK/pages/router.py" "$MARK3" <<'EDIT'
import sys, pathlib
p, mark = pathlib.Path(sys.argv[1]), sys.argv[2]
s = p.read_text()
old = '"auth": ("Authentication"'
assert old in s, "_SETUP_PAGES['auth'] moved; this gate needs updating"
p.write_text(s.replace(old, f'"auth": ("Authentication {mark}"', 1))
EDIT
wait_for "/pages/admin/setup/auth" "$MARK3" 45 >/dev/null
TOKEN_C="$(curl -s --max-time 6 --cookie "token=$TOK" -N "$BASE/pages/_dev/reload" 2>/dev/null | grep -m1 -A1 '^event: hello' | tail -1 | sed 's/^data: //')"
if [ -n "$TOKEN_C" ] && [ "$TOKEN_C" != "$TOKEN_A" ]; then
  pass "and it changed after a reload"
else
  fail "the token did not change across a reload — a real restart would go unnoticed"
fi

echo ""
echo "== 7. diagnostics reports it =="
STATUS="$(curl -s --max-time 10 -H "Authorization: Bearer $TOK" "$BASE/api/v1/diagnostics/health" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin).get("boot_status",{}).get("dev_reloader",{}).get("status",""))' 2>/dev/null)"
if [ "$STATUS" = "degraded" ]; then
  pass "boot_status.dev_reloader is degraded"
else
  fail "expected degraded, got '${STATUS:-<none>}'"
fi

echo ""
if [ "$FAILED" = "0" ]; then
  echo "PASS — the reloader works and stays out of the asset path"
else
  echo "FAIL — see above"
fi
exit "$FAILED"
