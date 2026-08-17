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
#   LIVE=1 scripts/manual-check.sh       # mount + watch pages/ — no rebuild, no restart
#   REUSE_DATA=1 scripts/manual-check.sh # keep the volume, so a mode switch skips seeding
#   PORT=9443 scripts/manual-check.sh    # different port
#
# Most of the time you want the Make targets instead, which set these for you:
#   make review        baked image        — the pass that decides whether it ships
#   make review_live   mounted + watched  — while you are still changing it
#   make review_rebuild                   — after touching anything Svelte
#
# Ctrl-C tears everything down.
set -uo pipefail

# One runtime, resolved the same way the Makefile resolves it. Hardcoding
# `docker` here meant `make dev` and `make review` would use different
# runtimes the day podman is installed.
RUNTIME="${CONTAINER_RUNTIME:-$(command -v podman >/dev/null 2>&1 && echo podman || echo docker)}"
IMG="${IMG:-sage-is/ai-ui:develop}"
PORT="${PORT:-9443}"
NET="${NET:-sage-network}"
ROOT="sage-manual"; TLS="sage-manual-tls"; VOL="sage-manual-data"
# Canonical fresh-boot admin; override with EMAIL=/PASSWORD= for a one-off.
. "$(cd "$(dirname "$0")" && pwd)/lib/test-admin.env"
EMAIL="${EMAIL:-$TEST_ADMIN_EMAIL}"; PASSWORD="${PASSWORD:-$TEST_ADMIN_PASSWORD}"
HERE="$(cd "$(dirname "$0")/.." && pwd)"
BASE="http://localhost:8101"

# REUSE_DATA=1 keeps the data volume across a teardown.
#
# Switching between the baked image and LIVE=1 means RECREATING the container —
# a bind mount cannot be added to a running one — and deleting the volume with
# it made every flip cost a re-seeded admin and a re-grafted ui-Sprig on top of
# the boot. That is the friction, not typing the flag.
#
# Signup hard-closes once an admin exists, so booting onto an existing volume
# skips seeding entirely and the ui-Sprig is already there. The volume is still
# a dedicated throwaway that touches nothing real; the DEFAULT stays
# delete-on-exit so a plain run is a genuinely clean instance and the
# first-run-experience surfaces are still reviewable.
cleanup(){
  echo ""
  echo "tearing down…"
  $RUNTIME rm -f "$ROOT" "$TLS" >/dev/null 2>&1 || true
  if [ "${REUSE_DATA:-0}" = "1" ]; then
    echo "  keeping volume $VOL (REUSE_DATA=1) — remove it with: $RUNTIME volume rm $VOL"
  else
    $RUNTIME volume rm "$VOL" >/dev/null 2>&1 || true
  fi
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

$RUNTIME network inspect "$NET" >/dev/null 2>&1 || $RUNTIME network create "$NET" >/dev/null
cleanup >/dev/null 2>&1

# LIVE=1 mounts the no-build pages package over the image's copy, so editing a
# panel costs a refresh instead of a `make it_build`.
#
# The whole point of these pages is that there is no build step, and until this
# existed that promise stopped at the container wall: every one-line style tweak
# meant rebuilding a 619 MB image to look at it. `dev_run` already mounts
# `app/backend/`, so the capability was there — just not here, in the script
# whose entire job is letting a human look at these surfaces.
#
# OFF by default, and that is not timidity. Phase S made the human pass a
# standing condition precisely because a green suite is weak evidence, and a
# review of your working tree is not a review of the artifact you ship. Use the
# default when you are judging it. Use LIVE=1 while you are still changing it.
#
# Narrower than `dev_run`'s whole-backend mount on purpose: only
# `sage_is_ai/pages/` is shadowed, so everything the panels call into is still
# the baked code.
PAGES_SRC="$HERE/app/backend/sage_is_ai/pages"
LIVE_MOUNT=""
LIVE_ENV=""
if [ "${LIVE:-0}" = "1" ]; then
  [ -d "$PAGES_SRC" ] || { echo "LIVE=1 but $PAGES_SRC is missing"; exit 1; }
  LIVE_MOUNT="-v $PAGES_SRC:/app/backend/sage_is_ai/pages"
  # The SAME path the mount uses. Passing it twice from one variable is what
  # keeps the watched set and the mounted set from drifting — a reloader
  # watching a directory nothing writes to is a feature that silently does
  # nothing, which is the failure shape this repo keeps finding.
  LIVE_ENV="-e PAGES_RELOAD_DIRS=/app/backend/sage_is_ai/pages"
fi

echo "== booting $IMG on a throwaway volume =="
# SPRIG_REGISTRY points at the local registry so grafting works like it does in
# the gates. ENABLE_SIGNUP is on only long enough to seed the first admin —
# this fork hard-closes signup once one exists.
# shellcheck disable=SC2086  # LIVE_MOUNT/LIVE_ENV are empty or one flag pair each
$RUNTIME run -d --name "$ROOT" --network "$NET" -p 8101:8080 \
  -e SPRIG_REGISTRY=local-registry:5000 -e ENABLE_SIGNUP=True -e WEBUI_AUTH=True \
  ${ENABLE_TRY_SAGE:+-e "ENABLE_TRY_SAGE=$ENABLE_TRY_SAGE"} \
  $LIVE_MOUNT $LIVE_ENV \
  -v "$VOL:/app/backend/data" "$IMG" >/dev/null

for _ in $(seq 1 120); do
  [ "$(curl -s -o /dev/null -w '%{http_code}' "$BASE/health" 2>/dev/null)" = "200" ] && break
  sleep 2
done
[ "$(curl -s -o /dev/null -w '%{http_code}' "$BASE/health")" = "200" ] || {
  echo "failed to boot"; $RUNTIME logs --tail 30 "$ROOT"; exit 1; }
echo "  ✅ booted"

echo "== seeding admin =="
TOK="$(curl -s -X POST "$BASE/api/v1/auths/signup" -H 'Content-Type: application/json' \
  -d "{\"name\":\"Admin\",\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin).get("token",""))' 2>/dev/null)"
# An empty token is EXPECTED on a reused volume — signup hard-closes once an
# admin exists — and is a real problem on a fresh one. Saying which costs a
# branch and saves someone chasing a warning that means "it worked".
if [ -n "$TOK" ]; then
  echo "  ✅ $EMAIL / $PASSWORD"
elif [ "${REUSE_DATA:-0}" = "1" ]; then
  echo "  ✅ $EMAIL / $PASSWORD  (already seeded on the kept volume)"
else
  echo "  ⚠️  signup returned no token (an admin may already exist)"
fi

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
$RUNTIME run -d --name "$TLS" --network "$NET" -p "$PORT:$PORT" \
  -v /tmp/manual-Caddyfile:/etc/caddy/Caddyfile:ro caddy:2-alpine >/dev/null
for _ in $(seq 1 30); do
  curl -sk -o /dev/null "https://localhost:$PORT/health" 2>/dev/null && break; sleep 1
done
echo "  ✅ https://localhost:$PORT  (self-signed — accept the warning once)"

# What LIVE=1 buys you, said where you will read it. Nothing here needs a hand
# any more — the two halves just take different amounts of time, and knowing
# which is which is the difference between waiting and thinking it is broken.
if [ "${LIVE:-0}" = "1" ]; then
  LIVE_NOTE="
  LIVE — app/backend/sage_is_ai/pages/ is mounted and watched. No rebuild, and
  nothing to restart by hand:
    pages/assets/*.css, *.js   saved -> the stylesheet swaps IN PLACE, so the
                               page keeps its scroll and any open dialog
    pages/*.py                 saved -> the app restarts itself and the tab
                               reloads when it comes back
  You are looking at your WORKING TREE, not the image, and /admin/diagnostics
  reports the reloader as degraded on purpose. Re-run without LIVE=1 — or
  \`make review\` — for the pass that decides whether this ships."
else
  LIVE_NOTE="
  Editing these pages? \`make review_live\` mounts and watches pages/, so a
  change lands by itself. This run is the baked image."
fi

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

  Setup wizard — nine panels, now the only implementation.
    The SvelteKit modal and its nine step components are DELETED. What shows
    these panels to a reader is a native <dialog> that fetches the route and
    lifts the panel out of the response, so there are two ways in and they
    render the same bytes:

      in the app     Admin → Settings → General
                       "See what's new"     opens on the changelog
                       "Run Setup Wizard"   opens on Welcome
                     Links and forms inside the dialog do NOT reload the
                     page — the address bar should not move.
      at its own URL each row below


    changelog     new  https://localhost:$PORT/pages/admin/setup/changelog
    welcome       new  https://localhost:$PORT/pages/admin/setup/welcome
    auth          new  https://localhost:$PORT/pages/admin/setup/auth
    connection    new  https://localhost:$PORT/pages/admin/setup/connection
    users         new  https://localhost:$PORT/pages/admin/setup/users
    features      new  https://localhost:$PORT/pages/admin/setup/features
    search-audio  new  https://localhost:$PORT/pages/admin/setup/search-audio
    developer     new  https://localhost:$PORT/pages/admin/setup/developer
    complete      new  https://localhost:$PORT/pages/admin/setup/complete

    Changed by the cut-over, so you can judge it rather than report it:
      * "Continue" and "Let's Go" end the flow by sending you back to the
        app. In the dialog that reads as a close; at a URL it is a
        redirect to /. Either way the durable half is recorded first —
        changelog read, setup complete.
      * complete reports auth / connection / working-alone from the stored
        configuration. The deleted modal read the browser's loaded model
        list and what you clicked during that run, so the two disagreed on
        a fresh instance. This is the one to form an opinion about.
      * model status is rendered at request time with a Refresh, rather
        than polled every 5s.
      * connection and auth never render a stored secret back. The deleted
        panels loaded the API key, both OAuth client secrets and the SMTP
        password into their inputs, so those sat in the DOM. These render
        the fields empty and say a secret is stored — leave one blank and
        Save, and the stored value survives.
      * auth shows every checkbox every time. The old panel hid "Allow
        OAuth Signup" until sign-ups were on and a provider configured.
        A hidden checkbox posts nothing and this form reads absence as
        off, so hiding one would silently clear it on the next Save.
      * the panels answer in your language. Add ?lang=es-ES to any row
        above, or set your browser's preferred language and load one cold.

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

  3b. The wizard's graft button. It used to graft
     'mock-embedding' and say document search was ready — that mock seeds
     its vectors from a sha256 of the input text, so search returned noise
     while every message said success. Now: tick only Speech-to-Text and
     graft, then check Admin → Sprigs shows whisper-base-ggml rooted.
     Tick Document Search and it grafts vector-chroma first, because the
     ONNX cultivar will not start without the runtime that rides with it.
     That chain is a slow graft and there is no progress indicator yet —
     worth judging how bad that feels.

  3c. Untick a step on Welcome, then press Get Started. You should land
     on the first step you LEFT ticked, both in the dialog and at the URL.
     This used to open the step you unticked — the orchestrator skipped
     against a reactive value Svelte had not recomputed. The orchestrator
     is deleted and the server answers instead, so a regression here means
     welcome_panel.start_wizard, not a timing bug.

  3d. Open the wizard from Settings → General, then walk it with the
     Next links and a Save or two. The address bar must not change and
     the page behind must not reload. Press Escape: it should close, and
     re-opening should start fresh rather than on the panel you left.
     This is the only part of the wizard that is not server-rendered.

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
${LIVE_NOTE}
  Logs:  $RUNTIME logs -f $ROOT
  Ctrl-C to tear down.
────────────────────────────────────────────────────────────────────────────

WALKTHROUGH

if [ "${KEEP:-0}" = "1" ]; then
  echo "  KEEP=1 — the instance stays up after this exits."
  echo "  Tear it down with:  $RUNTIME rm -f $ROOT $TLS && $RUNTIME volume rm $VOL"
  echo ""
  exit 0
fi

while true; do sleep 3600; done
