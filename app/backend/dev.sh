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
  echo "Loading WEBUI_SECRET_KEY from file, not provided as an environment variable."

  if ! [ -e "$KEY_FILE" ]; then
    echo "Generating WEBUI_SECRET_KEY"
    # Generate a random value to use as a WEBUI_SECRET_KEY in case the user didn't provide one.
    echo $(head -c 12 /dev/random | base64) > "$KEY_FILE"
  fi

  echo "Loading WEBUI_SECRET_KEY from $KEY_FILE"
  WEBUI_SECRET_KEY=$(cat "$KEY_FILE")
fi

# Set CORS for development mode
export CORS_ALLOW_ORIGIN=http://localhost:5173
export SKIP_STATIC_CLEANUP=true

WEBUI_SECRET_KEY="$WEBUI_SECRET_KEY" \
exec uvicorn open_webui.main:app \
    --port $PORT \
    --host 0.0.0.0 \
    --forwarded-allow-ips '*' \
    --reload \
    & cd /app/ && npm run dev