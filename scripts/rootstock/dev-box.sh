#!/usr/bin/env bash
# A throwaway AI-UI box for the Rootstock tests: the published image with THIS
# tree's backend mounted over it, signup open, Sprigs from the local registry.
#   scripts/rootstock/dev-box.sh [NAME] [PORT] [TREE] [IMAGE]
#   scripts/rootstock/dev-box.sh --stop [NAME]
# Defaults: rs-f0, 8181, this checkout, ghcr.io/sage-is/ai-ui:<SERVER_TAG>.
# It always recreates the container: after a host edit, a restarted container
# on Colima's virtiofs can keep a stale view of a renamed file and fail to
# import the app (2026-10-24), so the mount is made fresh each time. The data
# volume <NAME>-data survives, so the admin account does too.
set -euo pipefail
HERE=$(cd "$(dirname "$0")/../.." && pwd)
if [ "${1:-}" = --stop ]; then docker rm -f "${2:-rs-f0}" >/dev/null 2>&1 && echo "stopped ${2:-rs-f0}"; exit 0; fi
NAME=${1:-rs-f0}; PORT=${2:-8181}; TREE=${3:-$HERE}
TAG=$(sed -n 's/^SERVER_TAG=//p' "$HERE/distribution.env")
IMAGE=${4:-ghcr.io/sage-is/ai-ui:$TAG}
docker network inspect sage-network >/dev/null 2>&1 || docker network create sage-network >/dev/null
docker rm -f "$NAME" >/dev/null 2>&1 || true
docker run -d --name "$NAME" --network sage-network -p "$PORT:8080" \
  -e ENABLE_SIGNUP=True -e WEBUI_AUTH=True -e DEFAULT_USER_ROLE=user \
  -e SPRIG_REGISTRY=local-registry:5000 -e PYTHONDONTWRITEBYTECODE=1 \
  -v "$TREE/app/backend/sage_is_ai:/app/backend/sage_is_ai:ro" \
  -v "$NAME-data:/app/backend/data" "$IMAGE" >/dev/null
for _ in $(seq 1 60); do
  if curl -fsS -m 3 "http://localhost:$PORT/health" >/dev/null 2>&1; then
    echo "$NAME: $IMAGE with $TREE mounted, http://localhost:$PORT"; exit 0
  fi
  sleep 2
done
echo "$NAME did not answer on :$PORT; last log lines:" >&2
docker logs --tail 15 "$NAME" >&2
exit 1
