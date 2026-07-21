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
