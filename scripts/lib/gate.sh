#!/usr/bin/env bash
# gate.sh — shared pass/fail helpers for the smoke + verify gates.
#
# Every gate script used to redeclare the same PASS/FAIL counters, ok()/no() reporters, and require() tool-check. This is the one copy. Source it right after `set -uo pipefail`:
#
#   . "$(dirname "${BASH_SOURCE[0]}")/../lib/gate.sh"   # from scripts/smoke/*
#   . "$(dirname "${BASH_SOURCE[0]}")/lib/gate.sh"      # from scripts/*
#
# Provides: PASS, FAIL (ints, zeroed), ok "msg", no "msg", require TOOL, and gate_summary "LABEL" (prints the result bar, returns 0 iff FAIL==0). A script with a bespoke summary footer can keep it and just use the counters + ok/no.
#
# Safe under `set -u`; does NOT enable `set -e` (leaves control flow to the caller). Idempotent — sourcing twice is a no-op, so counters never reset out from under a caller that sources transitively.

[ -n "${_GATE_LIB_LOADED:-}" ] && return 0
_GATE_LIB_LOADED=1

PASS=0
FAIL=0

ok(){ echo "  ✅ $1"; PASS=$((PASS+1)); }
no(){ echo "  ❌ $1"; FAIL=$((FAIL+1)); }

# Hard-stop (exit 2) if a required tool is absent — a gate can't judge without it.
require(){ command -v "$1" >/dev/null || { echo "Missing required tool: $1" >&2; exit 2; }; }

# gate_summary "LABEL" — print the result bar and return success iff no failures.
# Use as the final line: `gate_summary "MY GATE"` (its return code is the exit).
gate_summary(){
  echo ""
  echo "================  ${1:-GATE}: ${PASS} passed, ${FAIL} failed  ================"
  [ "$FAIL" -eq 0 ]
}

# --- text matching that cannot lie ------------------------------------------
#
# `cmd | grep -q PATTERN` is a trap in any script with `set -o pipefail`, and
# every gate here sets it. `grep -q` exits the moment it matches; the writer
# still has output queued; the writer takes SIGPIPE and dies with 141; pipefail
# then reports 141 as the PIPELINE's status. So a MATCH is reported as a
# failure.
#
# It is intermittent, which is what makes it dangerous. When the writer's
# remaining output fits in the 64 KB pipe buffer it finishes before grep exits
# and the status is 0. So the same assertion passes on a quiet container and
# fails on a busy one — which is exactly how it behaved: `sprig_signing`'s
# "minisign OK" check passed in isolation and failed inside gauntlet_full, and
# `upgrade_gate`'s host-arch check spent weeks looking like a product bug.
#
# Worse, on a NEGATIVE assertion it inverts: `grep -q traceback && fail` reports
# 141 instead of 0 when a traceback IS present, so the gate passes on the
# failure it exists to catch.
#
# These helpers capture the text first and match it with bash's own operators.
# No pipe, no writer to kill, no status to misread.

# text_has "HAYSTACK" "ERE" — true iff HAYSTACK matches the extended regex.
text_has(){ [[ "$1" =~ $2 ]]; }

# log_has CONTAINER "ERE" — true iff the container's logs match.
log_has(){
  local logs
  logs="$(docker logs "$1" 2>&1)" || true
  [[ "$logs" =~ $2 ]]
}

# log_has_i CONTAINER "ERE" — case-insensitive variant.
# Bash's =~ is POSIX ERE, which has no inline (?i) flag; writing one would make
# the pattern a literal that never matches, and on a negative assertion that is
# a silent PASS. Lowercase both sides instead.
log_has_i(){
  local logs
  logs="$(docker logs "$1" 2>&1)" || true
  [[ "${logs,,}" =~ ${2,,} ]]
}

# wait_for_log CONTAINER "ERE" [TIMEOUT_S] — poll until the pattern appears.
# For lines written by work that outlives the request that triggered it, where
# the race is real asynchrony rather than a mis-read exit status.
wait_for_log(){
  local c="$1" pat="$2" t="${3:-30}" i=0
  while [ "$i" -lt "$t" ]; do
    log_has "$c" "$pat" && return 0
    i=$((i+1)); sleep 1
  done
  return 1
}

# fetch_has URL "ERE" [CURL_ARGS...] — true iff the response body matches.
# Same reason: a response larger than the pipe buffer makes `curl | grep -q`
# report a match as a failure.
fetch_has(){
  local url="$1" pat="$2"; shift 2
  local body
  body="$(curl -s "$@" "$url")" || true
  [[ "$body" =~ $pat ]]
}
