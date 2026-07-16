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

WEBUI_SECRET_KEY="$WEBUI_SECRET_KEY" \
uvicorn sage_is_ai.main:app \
    --port $PORT \
    --host 0.0.0.0 \
    --forwarded-allow-ips '*' \
    --reload &

cd /app/ && exec bun run vite dev --host 0.0.0.0