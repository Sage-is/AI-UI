#!/usr/bin/env bash
# Cypress E2E gate (docker-only: no npm/cypress on the host).
# Spins a FRESH rootstock container, runs the top-level suites from a pinned
# cypress/included sibling container against it, mounts videos/screenshots
# back to app/cypress/, tears down.
#
# Usage: scripts/e2e/run-cypress.sh [image]      (default sage-is/ai-ui:develop)
#   KEEP=1        keep the rootstock container on failure (debugging)
#   SPEC=<glob>   override spec selection (e.g. 'cypress/e2e/upstream/*.cy.ts').
#                 Passed as --config specPattern=<glob>, NOT --spec: Cypress 15
#                 intersects --spec with the config's top-level-only specPattern,
#                 so subdir specs (upstream/, heavy/) are unreachable via --spec.
#   TARGET_URL=<url>  run against an ALREADY-RUNNING rootstock instead of a
#                 fresh one — e.g. the KEEP=1 container from upgrade-gate.sh:
#                   KEEP=1 make upgrade_gate
#                   TARGET_URL=http://sage-upgrade:8080 \
#                     SPEC='cypress/e2e/upgrade/*.cy.ts' scripts/e2e/run-cypress.sh
#                 (host is the container NAME on sage-network; the cypress
#                 container resolves it there.) No fresh boot, no teardown of
#                 the target, no TLS sidecar. This is how the upgrade Cypress
#                 half actually runs.
#
# The rootstock joins sage-network so deliver-sprigs can pull from
# local-registry (vector-chroma toast test). Videos land in app/cypress/videos.
set -euo pipefail
IMG="${1:-sage-is/ai-ui:develop}"

# Any CYPRESS_* variable in the caller's environment reaches the spec as
# Cypress.env(). Needed once a single spec has to run against two
# implementations of the same surface — the migration's whole test contract:
#   CYPRESS_SPRIGS_PANEL=/pages/admin/sprigs SPEC=cypress/e2e/sprigs-panel.cy.ts make e2e
# Collected BEFORE the explicit -e flags below so those still win on a clash
# (baseUrl in particular must stay the harness's, not the shell's).
# The +"${...}" guard keeps an EMPTY array from tripping `set -u` on bash 3.2,
# which is still what stock macOS ships as /bin/bash.
CY_ENV=()
while read -r name; do
  [ -n "$name" ] && CY_ENV+=(-e "$name")
done < <(env | sed -n 's/^\(CYPRESS_[A-Za-z0-9_]*\)=.*/\1/p' | sort -u)
CYPRESS_IMG="cypress/included:15.18.0"   # 15.x — see watch/Dockerfile note
NET="sage-network"; ROOT="sage-e2e"; VOL="sage-e2e-data"; PORT=8100
REPO="$(cd "$(dirname "$0")/../.." && pwd)"

docker network inspect "$NET" >/dev/null 2>&1 || docker network create "$NET" >/dev/null

# TARGET_URL mode: skip the fresh boot + TLS sidecar and point Cypress at an
# existing rootstock (e.g. the upgrade-gate KEEP=1 container). Reusable against
# a staging clone too. Never tears the target down.
if [ -n "${TARGET_URL:-}" ]; then
  echo "== cypress run against existing target: $TARGET_URL =="
  REPORT_ARGS=()
  [ "${REPORT:-0}" = "1" ] && REPORT_ARGS=(--reporter junit --reporter-options "mochaFile=cypress/reports/results-[hash].xml,toConsole=true")
  set +e
  docker run --rm --network "$NET" \
    -v "$REPO/app:/e2e" -w /e2e \
    ${CY_ENV[@]+"${CY_ENV[@]}"} \
    -e "CYPRESS_baseUrl=$TARGET_URL" \
    -e "CYPRESS_COMMERCIAL_RECOMMENDATIONS=0" \
    ${CYPRESS_ADMIN_EMAIL:+-e "CYPRESS_ADMIN_EMAIL=$CYPRESS_ADMIN_EMAIL"} \
    ${CYPRESS_ADMIN_PASSWORD:+-e "CYPRESS_ADMIN_PASSWORD=$CYPRESS_ADMIN_PASSWORD"} \
    "$CYPRESS_IMG" ${SPEC:+--config "specPattern=$SPEC"} "${REPORT_ARGS[@]}"
  RC=$?
  set -e
  echo "videos: app/cypress/videos/  screenshots: app/cypress/screenshots/"
  exit "$RC"
fi

echo "== fresh rootstock for e2e ($IMG) =="
# "Fresh" has to be PROVEN, not attempted.
#
# This used to be `docker rm -f` followed by `docker volume rm … || true`, and
# the `|| true` was the bug: a container that has not finished going away still
# holds its volume, so the removal fails, and the run then boots on the PREVIOUS
# run's data with no sign anything is wrong. Caught 2026-07-29 after two e2e
# runs were killed mid-flight (SIGKILL skips the cleanup trap): the next run
# came up with vector-chroma already delivered, and `sprigs-panel` failed
# looking for a Graft button that was a Prune button. The suite reported a
# normal-looking failure on an unrelated surface — the worst possible symptom,
# because it sends you debugging the wrong thing.
#
# So: wait for the container to actually be gone, then insist the volume goes
# with it. A gate that cannot guarantee its own starting state is not measuring
# what it claims to, and must stop rather than carry on quietly.
docker rm -f "$ROOT" >/dev/null 2>&1 || true
for _ in $(seq 1 30); do
  docker inspect "$ROOT" >/dev/null 2>&1 || break
  sleep 1
done
for _ in $(seq 1 30); do
  docker volume inspect "$VOL" >/dev/null 2>&1 || break
  docker volume rm "$VOL" >/dev/null 2>&1 || sleep 1
done
if docker volume inspect "$VOL" >/dev/null 2>&1; then
  echo "FATAL: volume '$VOL' survived removal — this run would inherit the last"
  echo "       run's data and its results would be meaningless. Still holding it:"
  docker ps -a --filter "volume=$VOL" --format '         {{.Names}} ({{.Status}})'
  exit 1
fi
# ENABLE_TRY_SAGE passes through when set, off otherwise — the trial replaces
# the whole anonymous surface, so it must never be on for the default suite.
# Usage: ENABLE_TRY_SAGE=true SPEC=try-sage-welcome.cy.ts make e2e
#
# WEBUI_URL likewise. The welcome page emits its social-graph block ONLY when
# that value is set, so without this the og:image assertions take the
# "absent" branch and never fetch anything. Set it to the TLS sidecar's
# address to exercise the branch a crawler actually sees:
#   ENABLE_TRY_SAGE=true WEBUI_URL=https://sage-e2e-tls:8443 make e2e
docker run -d --name "$ROOT" --network "$NET" -p "$PORT:8080" \
  -e SPRIG_REGISTRY=local-registry:5000 -e ENABLE_SIGNUP=True -e WEBUI_AUTH=True \
  ${ENABLE_TRY_SAGE:+-e "ENABLE_TRY_SAGE=$ENABLE_TRY_SAGE"} \
  ${WEBUI_URL:+-e "WEBUI_URL=$WEBUI_URL"} \
  -v "$VOL:/app/backend/data" "$IMG" >/dev/null
for i in $(seq 1 120); do
  [ "$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:$PORT/health" 2>/dev/null)" = "200" ] && break
  sleep 2
done
[ "$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:$PORT/health")" = "200" ] || {
  echo "e2e: rootstock failed to boot"; docker logs --tail 30 "$ROOT"; exit 1; }

# TLS sidecar (Caddy internal CA): https = secure context, so clipboard/
# crypto.subtle/service-worker/getUserMedia features are actually testable.
echo "== tls sidecar =="
docker rm -f sage-e2e-tls >/dev/null 2>&1 || true
docker run -d --name sage-e2e-tls --network "$NET" -p 8443:8443 \
  -v "$REPO/scripts/e2e/tls/Caddyfile:/etc/caddy/Caddyfile:ro" \
  caddy:2-alpine >/dev/null
for i in $(seq 1 30); do
  [ "$(curl -sk -o /dev/null -w '%{http_code}' "https://localhost:8443/health")" = "200" ] && break
  sleep 1
done

echo "== cypress run (https) =="
# REPORT=1 adds machine-readable junit XML to app/cypress/reports/ — all run
# artifacts stay local (videos, screenshots, reports); no Cypress Cloud.
REPORT_ARGS=()
[ "${REPORT:-0}" = "1" ] && REPORT_ARGS=(--reporter junit --reporter-options "mochaFile=cypress/reports/results-[hash].xml,toConsole=true")
set +e
docker run --rm --network "$NET" \
  -v "$REPO/app:/e2e" -w /e2e \
  ${CY_ENV[@]+"${CY_ENV[@]}"} \
  -e "CYPRESS_baseUrl=https://sage-e2e-tls:8443" \
  -e "CYPRESS_COMMERCIAL_RECOMMENDATIONS=0" \
  "$CYPRESS_IMG" ${SPEC:+--config "specPattern=$SPEC"} "${REPORT_ARGS[@]}"
RC=$?
set -e

if [ "$RC" -ne 0 ] && [ "${KEEP:-0}" = "1" ]; then
  echo "e2e FAILED — keeping $ROOT (:$PORT) + sage-e2e-tls (:8443) for debugging (KEEP=1)"
else
  docker rm -f "$ROOT" sage-e2e-tls >/dev/null 2>&1 || true
  docker volume rm "$VOL" >/dev/null 2>&1 || true
fi
echo "videos: app/cypress/videos/  screenshots: app/cypress/screenshots/"
exit "$RC"
