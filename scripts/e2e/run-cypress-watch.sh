#!/usr/bin/env bash
# Interactive Cypress GUI in a browser tab (noVNC) — watch the robot click.
# Same fresh-rootstock setup as run-cypress.sh, but the runner stays up with
# the Cypress desktop app served at http://localhost:6080/vnc.html.
# Ctrl-C tears everything down.
#
# Usage: scripts/e2e/run-cypress-watch.sh [image]
set -euo pipefail
IMG="${1:-sage-is/ai-ui:develop}"
WATCH_IMG="sage-is/cypress-watch:15.18.0-r2"   # prefix in lockstep with run-cypress.sh; -rN busts the image-exists cache below
NET="sage-network"; ROOT="sage-e2e"; VOL="sage-e2e-data"; PORT=8100
REPO="$(cd "$(dirname "$0")/../.." && pwd)"

docker image inspect "$WATCH_IMG" >/dev/null 2>&1 || {
  echo "== building $WATCH_IMG (one-time) =="
  # "fonts" build context: the Dockerfile subsets the app's Archivo at build
  # time instead of shipping a committed pre-subset binary. --load matters on
  # docker-container builders, which otherwise keep the image in build cache.
  docker build --load --build-context fonts="$REPO/app/static/assets/fonts" \
    -t "$WATCH_IMG" "$REPO/scripts/e2e/watch"
}

docker network inspect "$NET" >/dev/null 2>&1 || docker network create "$NET" >/dev/null
echo "== fresh rootstock for e2e ($IMG) =="
docker rm -f "$ROOT" >/dev/null 2>&1 || true
docker volume rm "$VOL" >/dev/null 2>&1 || true
docker run -d --name "$ROOT" --network "$NET" -p "$PORT:8080" \
  -e SPRIG_REGISTRY=local-registry:5000 -e ENABLE_SIGNUP=True -e WEBUI_AUTH=True \
  -v "$VOL:/app/backend/data" "$IMG" >/dev/null
for i in $(seq 1 120); do
  [ "$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:$PORT/health" 2>/dev/null)" = "200" ] && break
  sleep 2
done

# TLS sidecar — same secure-context story as run-cypress.sh
docker rm -f sage-e2e-tls >/dev/null 2>&1 || true
docker run -d --name sage-e2e-tls --network "$NET" -p 8443:8443 \
  -v "$REPO/scripts/e2e/tls/Caddyfile:/etc/caddy/Caddyfile:ro" \
  caddy:2-alpine >/dev/null
for i in $(seq 1 30); do
  [ "$(curl -sk -o /dev/null -w '%{http_code}' "https://localhost:8443/health")" = "200" ] && break
  sleep 1
done

cleanup() { docker rm -f "$ROOT" sage-e2e-watch sage-e2e-tls >/dev/null 2>&1 || true; docker volume rm "$VOL" >/dev/null 2>&1 || true; }
trap cleanup EXIT

# SYS_ADMIN: lets Firefox create unprivileged user namespaces inside the
# container, restoring its content sandbox (otherwise it runs degraded and
# says so with a banner). Local disposable test container — acceptable cap.
# GUI state volume: Cypress remembers "What's New" dismissal + browser choice
# across sessions (dismiss once per Cypress version, never again). Everything
# stays local — no Cypress Cloud: COMMERCIAL_RECOMMENDATIONS=0 silences the
# cloud upsells; debugging = time-travel in this GUI + Developer Tools menu.
docker run --rm --name sage-e2e-watch --network "$NET" -p 6080:6080 \
  --shm-size=2g --cap-add=SYS_ADMIN \
  -v "$REPO/app:/e2e" \
  -v "sage-cypress-watch-state:/root/.config/Cypress" \
  -e "CYPRESS_baseUrl=https://sage-e2e-tls:8443" \
  -e "CYPRESS_COMMERCIAL_RECOMMENDATIONS=0" \
  "$WATCH_IMG"
