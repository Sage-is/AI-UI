#!/usr/bin/env bash
# wizard-smoke.sh — drive the AI Engine setup wizard end-to-end via API.
#
# Boots a clean container off the given image tag, signs up the canonical
# test user, triggers the wizard install, polls until the embedding model
# is ready, then exercises the file-upload → add-to-knowledge-base path
# that returns 400 ("Embedding model not loaded") when the wizard install
# leaves a broken ML stack on disk.
#
# Convention: test@example.com / zaq12wsx is the project-wide automated
# smoke user. Never create this user in production deployments.
#
# Usage:
#   scripts/wizard-smoke.sh [IMAGE_TAG]
#
#   IMAGE_TAG defaults to "bug-verify". Override to run against a different
#   built image (e.g. a release-tagged one).
#
# Exits 0 on PASS, non-zero with a diagnostic line on FAIL.

set -euo pipefail

# First arg is the FULL image reference (e.g. sage-is/ai-ui:bug-verify).
# Refusing a bare tag is intentional: the Makefile derives IMAGE_NAME from
# git remote, so a fork can have a different image name. Passing just the
# tag here used to silently smoke the upstream name on forks. Don't.
IMAGE="${1:-}"
if [ -z "$IMAGE" ] || [ "${IMAGE#*:}" = "$IMAGE" ]; then
  echo "Usage: $(basename "$0") IMAGE_NAME:TAG (e.g. sage-is/ai-ui:bug-verify)" >&2
  echo "       The Makefile normally passes \$(IMAGE_NAME):\$(IMAGE_TAG)." >&2
  exit 2
fi
CONTAINER="sage-ai-wizard-smoke"
VOLUME="sage-ai-wizard-smoke-data"
PORT="${PORT:-8181}"  # non-default so we don't collide with a running dev container on :8080
BASE="http://localhost:${PORT}"
EMAIL="test@example.com"
PASSWORD="zaq12wsx"
NAME="Test User"

# PLATFORM (optional) — set e.g. PLATFORM=linux/amd64 to smoke a cross-arch
# image on an Apple Silicon host via QEMU. Empty means use the host arch.
PLATFORM="${PLATFORM:-}"
PLATFORM_FLAG=""
if [ -n "$PLATFORM" ]; then
  PLATFORM_FLAG="--platform $PLATFORM"
fi

# Generous because multilingual-e5-large is ~1.1GB plus dependencies. The
# default suits a native run (~6 min wall time). QEMU emulation can be
# 3-5x slower — set INSTALL_TIMEOUT_SEC=2700 (45 min) for cross-arch runs.
INSTALL_TIMEOUT_SEC="${INSTALL_TIMEOUT_SEC:-900}"  # 15 minutes
POLL_INTERVAL_SEC=10

# Set KEEP_ON_FAIL=1 to preserve the container + volume after a failure so
# you can `docker exec` in and inspect. Default cleans up unconditionally.
KEEP_ON_FAIL="${KEEP_ON_FAIL:-1}"
FAILED=0

fail() {
  echo "FAIL: $*" >&2
  echo "---last 80 lines of container logs (search for the real error)---" >&2
  docker logs --tail 80 "$CONTAINER" 2>&1 | tail -80 >&2 || true
  FAILED=1
  exit 1
}

cleanup() {
  local code=$?
  if [ "$FAILED" = "1" ] && [ "$KEEP_ON_FAIL" = "1" ]; then
    echo "" >&2
    echo "Container $CONTAINER preserved on port $PORT for debugging." >&2
    echo "Inspect with: docker exec -it $CONTAINER bash" >&2
    echo "Clean up with: docker rm -f $CONTAINER && docker volume rm $VOLUME" >&2
  else
    docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
    docker volume rm "$VOLUME" >/dev/null 2>&1 || true
  fi
  exit "$code"
}
trap cleanup EXIT

require() {
  command -v "$1" >/dev/null || { echo "Missing required tool: $1" >&2; exit 1; }
}
require docker
require curl
require python3
require jq

echo "[smoke] image: $IMAGE"
docker image inspect "$IMAGE" >/dev/null || fail "image $IMAGE not present locally — run 'make it_build IMAGE_TAG=$IMAGE_TAG' first"

# 1. Clean slate
docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
docker volume rm "$VOLUME"  >/dev/null 2>&1 || true

# 2. Boot
echo "[smoke] booting container${PLATFORM:+ ($PLATFORM via QEMU)}"
docker run -d $PLATFORM_FLAG --name "$CONTAINER" -p "${PORT}:8080" -v "${VOLUME}:/app/backend/data" "$IMAGE" >/dev/null

# 3. Wait for healthcheck
for i in $(seq 1 30); do
  if curl -s -f "${BASE}/health" >/dev/null 2>&1; then break; fi
  sleep 2
  if [ "$i" -eq 30 ]; then fail "health check never returned 200 after 60s"; fi
done
echo "[smoke] healthy"

# 4. Sign up (first user becomes admin). If user already exists, fall through
#    to signin — keeps the script idempotent against a reused volume.
SIGNUP=$(curl -s -X POST "${BASE}/api/v1/auths/signup" \
  -H 'Content-Type: application/json' \
  -d "{\"name\":\"${NAME}\",\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}" || true)

TOKEN=$(echo "$SIGNUP" | jq -r '.token // empty')
if [ -z "$TOKEN" ]; then
  echo "[smoke] signup didn't yield token (user may already exist); signing in"
  TOKEN=$(curl -s -X POST "${BASE}/api/v1/auths/signin" \
    -H 'Content-Type: application/json' \
    -d "{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}" | jq -r '.token // empty')
fi
[ -n "$TOKEN" ] || fail "no auth token from signup OR signin: $SIGNUP"
AUTH="Authorization: Bearer ${TOKEN}"

# 5. Trigger the wizard install (admin-only endpoint)
echo "[smoke] triggering wizard install"
TRIGGER=$(curl -s -X POST "${BASE}/api/v1/retrieval/models/download" \
  -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"components":["embedding"]}')
echo "$TRIGGER" | jq -e '.status == true' >/dev/null || fail "install trigger rejected: $TRIGGER"

# 6. Poll status until embedding is ready (or hits error)
END=$(( $(date +%s) + INSTALL_TIMEOUT_SEC ))
LAST_PHASE=""
while [ "$(date +%s)" -lt "$END" ]; do
  STATUS_JSON=$(curl -s -H "$AUTH" "${BASE}/api/v1/retrieval/models/status")
  EMBEDDING=$(echo "$STATUS_JSON" | jq -r '.models.embedding')
  ERROR=$(echo "$STATUS_JSON" | jq -r '.models.error // empty')
  EF_READY=$(echo "$STATUS_JSON" | jq -r '.embedding_ready')
  VDB_READY=$(echo "$STATUS_JSON" | jq -r '.vector_db_ready')

  PHASE="embedding=${EMBEDDING} ef_ready=${EF_READY} vdb_ready=${VDB_READY}"
  if [ "$PHASE" != "$LAST_PHASE" ]; then
    echo "[smoke] $PHASE"
    LAST_PHASE="$PHASE"
  fi

  [ -n "$ERROR" ] && fail "install error: $ERROR"
  [ "$EMBEDDING" = "ready" ] && break
  sleep "$POLL_INTERVAL_SEC"
done
[ "$EMBEDDING" = "ready" ] || fail "embedding never reached ready (last: $EMBEDDING) within ${INSTALL_TIMEOUT_SEC}s"

# 7. Import smoke — confirms the install closure is mutually compatible.
#    Two contracts: on the Sprig™ path the embedding serves from a grafted
#    child and torch is DELIBERATELY absent — assert the delivered overlay
#    (chromadb/numpy) and bcrypt unshadowed. On the legacy path the full ML
#    closure must import.
echo "[smoke] running import smoke inside container"
if docker logs "$CONTAINER" 2>&1 | grep -q "Embedding served by Sprig"; then
  docker exec "$CONTAINER" python3 -c "
import numpy, chromadb, bcrypt
# bcrypt is a SYSTEM package; the overlay must not shadow it with a copy on the
# data volume (that's the real footgun — a stale/broken bcrypt breaking auth).
# System site-packages is /usr/lib (Wolfi) or /usr/local/lib (older base), so
# assert the negative: bcrypt is NOT served from the data-volume ml_packages.
assert not bcrypt.__file__.startswith('/app/backend/data'), f'bcrypt shadowed by overlay: {bcrypt.__file__}'
print(f'imports ok (Sprig path) | numpy {numpy.__version__} | chromadb {chromadb.__version__} | bcrypt {bcrypt.__file__}')
" || fail "post-install import smoke threw (Sprig path)"
else
  docker exec "$CONTAINER" python3 -c "
from sentence_transformers import SentenceTransformer
import torch, numpy, chromadb, bcrypt
assert not bcrypt.__file__.startswith('/app/backend/data'), f'bcrypt shadowed by overlay: {bcrypt.__file__}'
print(f'imports ok | torch {torch.__version__} | numpy {numpy.__version__} | bcrypt {bcrypt.__file__}')
" || fail "post-install import smoke threw"
fi

# 8. The regression target — file upload → add to KB.
echo "[smoke] testing file upload + add-to-KB"
TMPFILE=$(mktemp -t sage-smoke.XXXX.txt)
trap "rm -f $TMPFILE; cleanup" EXIT
echo "Hello world. Sage.is automated smoke fixture. $(date -u +%FT%TZ)" > "$TMPFILE"

KB_ID=$(curl -s -X POST "${BASE}/api/v1/knowledge/create" \
  -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"name":"wizard-smoke","description":"automated smoke","data":{},"access_control":null}' \
  | jq -r '.id')
[ -n "$KB_ID" ] && [ "$KB_ID" != "null" ] || fail "knowledge create failed"

FILE_ID=$(curl -s -X POST "${BASE}/api/v1/files/" \
  -H "$AUTH" -F "file=@${TMPFILE}" | jq -r '.id')
[ -n "$FILE_ID" ] && [ "$FILE_ID" != "null" ] || fail "file upload failed"

ADD_CODE=$(curl -s -o /dev/null -w '%{http_code}' \
  -X POST "${BASE}/api/v1/knowledge/${KB_ID}/file/add" \
  -H "$AUTH" -H 'Content-Type: application/json' \
  -d "{\"file_id\":\"${FILE_ID}\"}")
[ "$ADD_CODE" = "200" ] || fail "add-to-KB returned ${ADD_CODE} (expected 200) — this is the original regression"

echo "[smoke] PASS — wizard install + embedding + file index all green for $IMAGE"
