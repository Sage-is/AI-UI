#!/usr/bin/env bash
# Surface budget — a migrated surface must weigh LESS than the one it replaces,
# and the app-wide floor must not grow.
#
# WHY THIS EXISTS. The migration's second leg is throughput, and until now that
# claim was checked by a human running a spec and reading a number. Two things
# went wrong that way in one week: a payload theory was published twice from
# reasoning rather than measurement, and a timing was reported that turned out to
# include the app's whole boot. Nothing stopped either. Nothing stopped a future
# surface shipping heavier than its predecessor either — the exact class of
# regression this repo keeps finding, where every test is green and the product
# is worse.
#
# WHAT IT JUDGES, and what it deliberately does not:
#
#   BYTES ONLY. Decoded bytes repeat to within 0.1 kB across runs; times swing 2x
#   on the same route (one measured 1,425 ms and then 3,241 ms). A gate on a
#   quantity that noisy is a flaky gate, and a flaky gate gets disabled — taking
#   the real check with it. Times are measured and reported, never gated.
#
#   MEDIANS, AGAINST THE SPREAD. Three samples per entry. A difference smaller
#   than the observed spread is not a result and this gate will not call it one.
#
# THE ASSERTION IS HERE, NOT IN THE SPEC. `route-payload.cy.ts` stays a
# measurement that asserts almost nothing. That separation is the point: a
# measurement which can fail its own run acquires a reason to report a number
# that passes.
#
# Usage: scripts/gates/surface-budget/run-gate.sh [image]
#   TARGET_URL=... reuses an already-booted snapshot instead of booting one.
#   FLOOR_KB=N overrides the floor ceiling (default: read from the run itself).
set -uo pipefail
HERE="$(cd "$(dirname "$0")/../../.." && pwd)"
IMG="${1:-sage-is/ai-ui:develop}"
SNAP="${SNAPSHOT:-$(ls -d "$HERE"/tools/db_snapshots/*/ 2>/dev/null | sort | tail -1)}"
NET="${SPRIG_SMOKE_NET:-sage-network}"
ROOT="sage-budget"; VOL="${ROOT}-data"
PORT="${SURFACE_BUDGET_PORT:-8098}"; BASE="http://localhost:${PORT}"
ADMIN_EMAIL="upgrade-gate@sage.is"; ADMIN_PW="upgrade-gate-pw-1234"
LEDGER="$HERE/app/cypress/perf-routes.json"

. "$(dirname "${BASH_SOURCE[0]}")/../../lib/gate.sh"   # PASS/FAIL + ok/no/require
require docker; require jq; require curl

OWN_TARGET=0
cleanup(){
  [ "$OWN_TARGET" = "1" ] || return 0
  [ -n "${KEEP:-}" ] && { echo "KEEP=1: leaving $ROOT up at $BASE"; return; }
  docker rm -f "$ROOT" >/dev/null 2>&1 || true
  docker volume rm "$VOL" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo ""
echo "==============================================================="
echo "==            SURFACE BUDGET — bytes, not opinions           =="
echo "==============================================================="

if [ -n "${TARGET_URL:-}" ]; then
  echo "== using the already-booted target: $TARGET_URL =="
  CY_TARGET="$TARGET_URL"
else
  [ -d "$SNAP" ] || { echo "ERROR: no snapshot dir at '$SNAP'"; exit 1; }
  OWN_TARGET=1
  echo "== 0. copy snapshot -> fresh volume (pristine source: $SNAP) =="
  docker rm -f "$ROOT" >/dev/null 2>&1 || true
  docker volume rm "$VOL" >/dev/null 2>&1 || true
  docker volume create "$VOL" >/dev/null
  # cache/ excluded for the same reason the upgrade gate excludes it: ~2.4GB of
  # HF download cache the measurement never touches, and copying it is what
  # exhausted the VM disk once already.
  docker run --rm -v "$SNAP:/src:ro" -v "$VOL:/dst" alpine:3.20 \
    sh -c "tar -C /src --exclude=./cache -cf - . | tar -C /dst -xf - && rm -f /dst/readme.txt" >/dev/null \
    && ok "snapshot copied (the snapshot file itself is never written)" \
    || { no "snapshot copy failed"; exit 1; }

  docker run --rm -v "$VOL:/data" -v "$HERE/scripts/snapshots/inject-test-admin.py:/inject.py:ro" \
    -e WEBUI_SECRET_KEY=surface-budget --entrypoint python3 "$IMG" \
    /inject.py /data/webui.db "$ADMIN_EMAIL" "$ADMIN_PW" >/dev/null \
    && ok "throwaway admin injected into the COPY" \
    || { no "admin injection failed"; exit 1; }

  docker network inspect "$NET" >/dev/null 2>&1 || docker network create "$NET" >/dev/null
  docker run -d --name "$ROOT" --network "$NET" -p "${PORT}:8080" \
    -e WEBUI_AUTH=True -e WEBUI_SECRET_KEY=surface-budget-secret \
    -v "$VOL:/app/backend/data" "$IMG" >/dev/null
  BOOTED=0
  for _ in $(seq 1 150); do
    [ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$BASE/health" 2>/dev/null)" = "200" ] \
      && BOOTED=1 && break
    sleep 2
  done
  [ "$BOOTED" = "1" ] && ok "booted on a copy of production data" \
    || { no "boot failed"; docker logs --tail 40 "$ROOT"; exit 1; }
  CY_TARGET="http://${ROOT}:8080"
fi

echo ""
echo "== 1. measure every route and both sides of every surface =="
rm -f "$LEDGER"
TARGET_URL="$CY_TARGET" \
CYPRESS_ADMIN_EMAIL="$ADMIN_EMAIL" CYPRESS_ADMIN_PASSWORD="$ADMIN_PW" \
SPEC='cypress/e2e/upgrade/route-payload.cy.ts' "$HERE/scripts/e2e/run-cypress.sh" >/dev/null 2>&1
[ -s "$LEDGER" ] && ok "ledger written" || { no "the ledger produced no output — nothing to judge"; exit 1; }

echo ""
echo "== 2. every migrated surface must beat the one it replaces =="
# Pair `<name>-legacy` with `<name>-nobuild`, which route-payload.cy.ts emits for
# every entry in cypress/support/surfaces.ts. Registering a surface there is what
# enrols it here — there is no second list to keep in step.
JUDGED=0
while IFS=$'\t' read -r NAME LEG NOB SPREAD; do
  JUDGED=$((JUDGED+1))
  # Cut must EXCEED the spread. Anything smaller is noise wearing a number.
  if awk -v l="$LEG" -v n="$NOB" -v s="$SPREAD" 'BEGIN{exit !(l - n > s)}'; then
    ok "$(printf '%-12s %9.1f -> %-9.1f kB decoded  (-%.1f)' "$NAME" "$LEG" "$NOB" "$(awk -v l="$LEG" -v n="$NOB" 'BEGIN{print l-n}')")"
  else
    no "$NAME: server-rendered ${NOB} kB is NOT below legacy ${LEG} kB by more than the ${SPREAD} kB spread"
  fi
done < <(jq -r '
  . as $d
  | [ $d | keys[] | select(endswith("-legacy")) | sub("-legacy$";"") ][]
  | . as $n
  | select($d[$n + "-nobuild"] != null)
  | [ $n,
      $d[$n + "-legacy"].decodedKB.median,
      $d[$n + "-nobuild"].decodedKB.median,
      ([$d[$n + "-legacy"].decodedKB.spread, $d[$n + "-nobuild"].decodedKB.spread] | max)
    ] | @tsv' "$LEDGER")

[ "$JUDGED" -gt 0 ] && ok "$JUDGED surface pair(s) judged" \
  || no "NO surface pairs found in the ledger — this gate judged nothing and would have passed silently"

echo ""
echo "== 3. the app-wide floor must not grow =="
# `notes-empty` is a route with no data of its own, so it measures what every
# SvelteKit route pays before rendering anything. Fonts and icons took it from
# 7,576 kB to 6,642 kB on 2026-08-02; the ceiling is set just above that so the
# saving cannot quietly evaporate. Raise it deliberately, never to make a run go
# green.
FLOOR_CEILING="${FLOOR_KB:-6800}"
FLOOR=$(jq -r '."notes-empty".decodedKB.median // empty' "$LEDGER")
if [ -z "$FLOOR" ]; then
  no "the floor gauge (notes-empty) is missing from the ledger — the ceiling check cannot report"
elif awk -v f="$FLOOR" -v c="$FLOOR_CEILING" 'BEGIN{exit !(f <= c)}'; then
  ok "floor ${FLOOR} kB decoded, ceiling ${FLOOR_CEILING} kB"
else
  no "the floor GREW to ${FLOOR} kB, above the ${FLOOR_CEILING} kB ceiling — every route in the product just got heavier"
fi

gate_summary "SURFACE BUDGET"
