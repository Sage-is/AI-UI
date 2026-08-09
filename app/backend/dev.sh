#!/usr/bin/env bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR" || exit

# Initialize AI models at runtime (moved from Dockerfile for faster builds)
echo "🤖 Initializing AI models..."
if [ -f "./init_models.sh" ]; then
    ./init_models.sh
else
    echo "⚠️  init_models.sh not found, skipping model initialization"
fi

KEY_FILE=.webui_secret_key

PORT="${PORT:-8080}"

if test "$WEBUI_SECRET_KEY $WEBUI_JWT_SECRET_KEY" = " "; then
  if ! [ -e "$KEY_FILE" ]; then
    echo "Generating secret key..."
    echo $(head -c 32 /dev/random | base64) > "$KEY_FILE"
  fi

  echo "Secret key loaded"
  WEBUI_SECRET_KEY=$(cat "$KEY_FILE")
fi

# Set CORS for development mode
export CORS_ALLOW_ORIGIN=http://localhost:5173
export SKIP_STATIC_CLEANUP=true

# Vite's dev server (below) serves from /app/node_modules — the Svelte dev/build
# toolchain (~1.1GB) that ships OUTSIDE the slim rootstock, delivered by the
# dev-svelte Sprig™. Graft it here so `make dev_run` just works on a fresh --rm
# container without a manual Admin → Sprigs step. Runs BEFORE uvicorn so it can't
# race the app's own boot reconcile, and is idempotent: artifact.ensure()
# short-circuits when node_modules is already on hand at the catalog tag, so this
# is a no-op on warm runs and only pulls/extracts on first run or a dev-svelte bump.
echo "🌱 Ensuring dev-svelte toolchain for Vite (node_modules)..."
python3 -m sage_is_ai.sprigs.graft_cli dev-svelte \
  || echo "⚠️  dev-svelte graft failed — 'vite dev' needs /app/node_modules. Graft it in Admin → Sprigs, or check registry reachability."

# NOTE for anyone tempted to graft the example ui-Sprig™ here with graft_cli:
# it will not work, and it will not tell you. `graft_cli` reaches
# `SprigSupervisor.graft`, which DELIVERS the artifact but never activates it —
# `point_ui_at` is called from `routers/sprigs.py` alone, and it needs the live
# app that graft_cli only has as a stub. The fragment would land on disk with
# `SPRIG_ACTIVE_UI` still empty, and the slot would render nothing. So the ui
# graft goes over HTTP after uvicorn is up, beside the admin seed below.

WEBUI_SECRET_KEY="$WEBUI_SECRET_KEY" \
uvicorn sage_is_ai.main:app \
    --port $PORT \
    --host 0.0.0.0 \
    --forwarded-allow-ips '*' \
    --reload &

# Make the instance usable with no follow-up step: seed an admin, then graft the
# example ui-Sprig™ so the marketplace slot has something in it.
#
# Backgrounded, because uvicorn above is still booting and vite below must not
# wait on it. Over HTTP rather than in-process for one reason worth keeping: the
# ui graft only activates through the router (see the note further up), and
# going through the real endpoints means the dev loop exercises the same path a
# person clicking Admin → Sprigs does.
#
# Idempotent by the application's own rules — signup HARD-CLOSES once an admin
# exists, and a graft short-circuits when the artifact is already on hand.
# Credentials match scripts/manual-check.sh so the dev loop and the review
# instance agree.
DEV_EMAIL="${DEV_EMAIL:-admin@example.com}"
DEV_PASSWORD="${DEV_PASSWORD:-password}"
(
  API="http://localhost:$PORT"
  JSON='Content-Type: application/json'
  signin="{\"email\":\"$DEV_EMAIL\",\"password\":\"$DEV_PASSWORD\"}"
  signup="{\"name\":\"Admin\",\"email\":\"$DEV_EMAIL\",\"password\":\"$DEV_PASSWORD\"}"
  token() { sed -n 's/.*"token":"\([^"]*\)".*/\1/p'; }

  for _ in $(seq 1 60); do
    curl -sf -o /dev/null "$API/health" 2>/dev/null && break
    sleep 2
  done

  tok=$(curl -s -X POST "$API/api/v1/auths/signup" -H "$JSON" -d "$signup" 2>/dev/null | token)
  [ -n "$tok" ] || tok=$(curl -s -X POST "$API/api/v1/auths/signin" -H "$JSON" -d "$signin" 2>/dev/null | token)

  if [ -z "$tok" ]; then
    echo "⚠️  could not seed or sign in as $DEV_EMAIL — open $API and sign up."
    exit 0
  fi

  # Report the role the server ACTUALLY gave, never the one we hoped for. Only
  # the first account to sign up becomes an admin; every later one lands on
  # DEFAULT_USER_ROLE, which is `pending`. On a fresh dev volume this is always
  # admin — see VOLUME_DEV_DATA in the Makefile for why dev has its own.
  role=$(curl -s -b "token=$tok" "$API/api/v1/auths/" 2>/dev/null \
         | sed -n 's/.*"role":"\([^"]*\)".*/\1/p')
  echo "🔑 Sign in:  $DEV_EMAIL / $DEV_PASSWORD  (role: ${role:-unknown})"

  if [ "$role" != "admin" ]; then
    echo "⚠️  not an admin, so the ui-Sprig™ graft is skipped and the slot stays empty."
    echo "    This volume already had users. For a first-signup-is-admin instance:"
    echo "      docker volume rm sage-ai-dev-data && make dev"
    exit 0
  fi

  # OPT-IN, and it used to be automatic for about an hour on 2026-08-09. The
  # slot is ONE UNNAMED GLOBAL slot, so a grafted fragment renders on every
  # server-rendered page — all fifteen of them, `/pages/home` included. A
  # welcome card addressed to a workshop, on the screen you open every morning,
  # every time you start the dev loop, is not a dev loop anyone wants.
  #
  # Turn it on when you are working ON the slot:  DEV_GRAFT_UI=1 make dev
  # Named slots are the real fix and are filed in TODO.md, gated behind
  # multi-Sprig support — one pointer means only one can be live at a time, so
  # slots buy nothing until several can be.
  if [ "${DEV_GRAFT_UI:-0}" != "1" ]; then
    exit 0
  fi

  # -f so curl FAILS on a 4xx. Without it curl exits 0 on a permissions refusal
  # and the success message below prints over the top of an error — a message
  # that cannot fail, which is how this was found in the first place.
  if curl -sf -X POST "$API/api/v1/retrieval/sprigs/graft" \
       -H "Authorization: Bearer $tok" -H "$JSON" \
       -d '{"name":"ui-workshop-welcome","capability":"ui"}' >/dev/null 2>&1; then
    echo "🌱 ui-Sprig™ grafted — the marketplace slot is live."
  else
    echo "⚠️  ui-workshop-welcome graft failed; the slot will be empty."
  fi
) &

cd /app/ && exec bun run vite dev --host 0.0.0.0