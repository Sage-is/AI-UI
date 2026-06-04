#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR" || exit 1

# ============================================================
# Structured operator-facing message helpers
# ============================================================
# boot_fatal HEADLINE  (body via stdin)  emit FATAL block, exit 1
# boot_warn  HEADLINE  (body via stdin)  emit WARNING block, continue
# Both emit to stderr so CapRover surfaces them in the App Logs tail.

boot_fatal() {
  local headline="$1"
  {
    printf '\n'
    printf '============================================================\n'
    printf '  AI-UI BOOT FAILURE: %s\n' "$headline"
    printf '============================================================\n\n'
    cat
    printf '\nContainer will exit 1.\n'
    printf '============================================================\n\n'
  } >&2
  exit 1
}

boot_warn() {
  local headline="$1"
  {
    printf '\n'
    printf '============================================================\n'
    printf '  AI-UI BOOT WARNING: %s\n' "$headline"
    printf '============================================================\n\n'
    cat
    printf '\n============================================================\n\n'
  } >&2
}

# ============================================================
# Defaults for optional env vars (set -u safety)
# ============================================================
WEBUI_SECRET_KEY="${WEBUI_SECRET_KEY:-}"
WEBUI_JWT_SECRET_KEY="${WEBUI_JWT_SECRET_KEY:-}"
USE_OLLAMA_DOCKER="${USE_OLLAMA_DOCKER:-}"
USE_CUDA_DOCKER="${USE_CUDA_DOCKER:-}"
SPACE_ID="${SPACE_ID:-}"
LD_LIBRARY_PATH="${LD_LIBRARY_PATH:-}"
PORT="${PORT:-8080}"
HOST="${HOST:-0.0.0.0}"
KEY_FILE=data/.webui_secret_key

# ============================================================
# Pre-flight: data/ directory must be writable
# ============================================================
if ! ( mkdir -p data && touch data/.write_test && rm data/.write_test ) 2>/dev/null; then
  boot_fatal "data/ directory is not writable" <<EOF
WHAT HAPPENED:
  The container tried to write a test file to /app/backend/data
  and the write failed. The running process uid is $(id -u).
  This usually means the data volume is mounted read-only, not
  mounted at all, or owned by a different uid than the container.

WHAT THIS BREAKS:
  - WEBUI_SECRET_KEY cannot persist; JWTs invalidate on every restart
  - SQLite database cannot write; admin saves and chat creation will fail
  - Uploaded files and embedding caches cannot be stored

HOW TO FIX (CapRover):
  1. Dashboard -> your app -> "App Configs" tab
  2. Under "Persistent Directories", click "Add Persistent Directory":
       Path in App:  /app/backend/data
       Label:        ai-ui-data
  3. Click "Save & Update". Wait for redeploy.

HOW TO FIX (Docker Compose):
  Under your service, add:
     volumes:
       - ./data:/app/backend/data

HOW TO FIX (Brew install):
  Run: ai-ui start
  The brew formula provisions the persistent volume automatically.

IF NOTHING ABOVE APPLIES:
  The volume is mounted but owned by a different uid.
  On the host: sudo chown -R $(id -u) /path/to/volume
  Or run the container as the matching uid via --user.

MORE HELP:
  - /admin/diagnostics (once a working container is up)
  - https://sage.education/docs/troubleshooting/data-volume
EOF
fi

# ============================================================
# Model dependency check (non-fatal; wizard handles missing models)
# ============================================================
if [ -f "./init_models.sh" ]; then
  ./init_models.sh || boot_warn "init_models.sh exited non-zero" <<EOF
WHAT HAPPENED:
  The model dependency check (init_models.sh) returned a non-zero
  exit code. Boot is continuing because the AI Engine setup wizard
  handles missing models at runtime.

WHAT TO WATCH:
  - If chat fails with "embedding model not loaded", visit the setup
    wizard at the AI Engine page in admin to trigger model install.
  - If the failure repeats on every restart, check container logs above
    this block for the specific init_models.sh error.

MORE HELP:
  - /admin/diagnostics (Configured endpoints + Static-asset health sections)
EOF
fi

# ============================================================
# WEBUI_SECRET_KEY: env var > persistent key file > generate
# ============================================================
if [ -z "$WEBUI_SECRET_KEY" ] && [ -z "$WEBUI_JWT_SECRET_KEY" ]; then
  # Neither env var set; fall back to persistent key file in data/
  if [ ! -e "$KEY_FILE" ]; then
    echo "Generating secret key at $KEY_FILE..."
    head -c 32 /dev/random | base64 | tr -d '\n' > "$KEY_FILE"
  fi

  WEBUI_SECRET_KEY=$(cat "$KEY_FILE")

  # Validate length: 32 random bytes base64-encoded = 44 chars (with padding)
  if [ "${#WEBUI_SECRET_KEY}" -ne 44 ]; then
    boot_fatal "WEBUI_SECRET_KEY file contains an unexpected value" <<EOF
WHAT HAPPENED:
  Expected the key file at $KEY_FILE to contain a 44-character base64
  string (32 random bytes encoded). Got a value of length ${#WEBUI_SECRET_KEY}.
  This usually means the previous write to the file failed silently or the
  file was truncated by another process.

WHAT THIS BREAKS:
  - JWT signing/verification will use a malformed key
  - All sign-in attempts will fail until this is fixed

HOW TO FIX:
  Option 1 (preserve existing sessions):
    Set the WEBUI_SECRET_KEY env var to a known 44-char base64 string
    in your deployment config, then redeploy.

  Option 2 (force regeneration; invalidates existing sessions):
    docker exec srv-captain--<app-name> sh -c "rm /app/backend/data/.webui_secret_key"
    then restart the container.

MORE HELP:
  - /admin/diagnostics (Boot status section)
EOF
  fi

  # Heuristic: if data/ is on tmpfs or overlay, persistence is not real
  data_fs_type=$(stat -f -c %T data 2>/dev/null || echo unknown)
  case "$data_fs_type" in
    tmpfs|overlay|overlay2|aufs)
      boot_warn "WEBUI_SECRET_KEY persistence not confirmed" <<EOF
WHAT HAPPENED:
  The data/ directory appears to be on a $data_fs_type filesystem,
  which is typically ephemeral (does not survive container restarts).
  The secret key was written, but it will be regenerated on the next
  restart, invalidating every JWT and logging every user out.

HOW TO FIX (CapRover, recommended):
  Dashboard -> your app -> App Configs -> Environmental Variables:
    WEBUI_SECRET_KEY=<paste a 44-char base64 value>
  Generate one with: head -c 32 /dev/random | base64
  Save & Update.

HOW TO FIX (alternative; add a persistent volume):
  Under App Configs -> Persistent Directories, add:
    Path in App: /app/backend/data
  Save & Update. The current $KEY_FILE will then survive restarts.

WHY THIS MATTERS:
  - JWT secret rotation forces every signed-in user to log in again.
  - On a deploy or restart loop this looks like "sessions randomly drop".
EOF
      ;;
  esac

  echo "Secret key loaded"
fi

# ============================================================
# Optional features
# ============================================================
if [[ "${USE_OLLAMA_DOCKER,,}" == "true" ]]; then
  echo "USE_OLLAMA is set to true, starting ollama serve."
  ollama serve &
fi

if [[ "${USE_CUDA_DOCKER,,}" == "true" ]]; then
  echo "CUDA is enabled, appending LD_LIBRARY_PATH to include torch/cudnn & cublas libraries."
  export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:/usr/local/lib/python3.11/site-packages/torch/lib:/usr/local/lib/python3.11/site-packages/nvidia/cudnn/lib"
fi

# ============================================================
# HuggingFace Space configuration (optional)
# ============================================================
if [ -n "$SPACE_ID" ]; then
  ADMIN_USER_EMAIL="${ADMIN_USER_EMAIL:-}"
  ADMIN_USER_PASSWORD="${ADMIN_USER_PASSWORD:-}"
  SPACE_HOST="${SPACE_HOST:-}"
  echo "Configuring for HuggingFace Space deployment"
  if [ -n "$ADMIN_USER_EMAIL" ] && [ -n "$ADMIN_USER_PASSWORD" ]; then
    echo "Admin user configured, creating"
    WEBUI_SECRET_KEY="$WEBUI_SECRET_KEY" uvicorn sage_is_ai.main:app --host "$HOST" --port "$PORT" --forwarded-allow-ips '*' &
    webui_pid=$!
    echo "Waiting for server to start..."
    while ! curl -s http://localhost:8080/health > /dev/null; do
      sleep 1
    done
    echo "Creating admin user..."
    curl \
      -X POST "http://localhost:8080/api/v1/auths/signup" \
      -H "accept: application/json" \
      -H "Content-Type: application/json" \
      -d "{ \"email\": \"${ADMIN_USER_EMAIL}\", \"password\": \"${ADMIN_USER_PASSWORD}\", \"name\": \"Admin\" }"
    echo "Shutting down server..."
    kill "$webui_pid"
  fi

  export WEBUI_URL="$SPACE_HOST"
fi

# ============================================================
# Launch
# ============================================================
WEBUI_SECRET_KEY="$WEBUI_SECRET_KEY" exec uvicorn sage_is_ai.main:app --host "$HOST" --port "$PORT" --forwarded-allow-ips '*' --workers "${UVICORN_WORKERS:-1}" --log-level warning
