#!/usr/bin/env bash
# Refuse the pipefail/grep trap before it reaches a gate.
#
# `writer | grep -q PATTERN` under `set -o pipefail` reports a MATCH as a
# failure: grep exits on the first hit, the writer takes SIGPIPE and dies 141,
# and pipefail surfaces 141 as the pipeline's status. It only fires when the
# writer still had output queued, so it presents as flakiness rather than as a
# bug. On a negative assertion it inverts, passing on exactly the failure the
# check exists to catch.
#
# It cost two gates before anyone chased it: sprig_signing's "minisign OK"
# failed inside gauntlet_full and passed alone, and upgrade_gate's host-arch
# check spent weeks filed as a product bug that did not exist. The mechanism is
# proved both ways by scripts/smoke/pipefail-grep-fixture.sh.
#
# What this bans, and what it does not
#
# Only the two writers whose output is unbounded and will therefore outrun grep
# eventually: `docker logs` and `curl`. Those are the two that have bitten, and
# the two most likely to bite again.
#
# It does NOT ban `printf | grep -q` or `echo | grep -q`. Those writers are
# shell builtins on strings already in memory; they finish before grep can exit,
# so the trap cannot spring. Nor does it look inside `docker run sh -c '...'`
# bodies, where the host script's pipefail does not apply.
#
# That boundary is a deliberate judgement, written down here so the next person
# can move it on purpose. If a `printf` haystack ever grows past the 64 KB pipe
# buffer, widen the rule.
#
# The safe replacements live in scripts/lib/gate.sh: text_has, log_has,
# log_has_i, wait_for_log, fetch_has.
#
# Usage: scripts/lint-pipefail-grep.sh   (exits 1 on any finding)
set -uo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
FOUND=0

while IFS= read -r hit; do
  [ -z "$hit" ] && continue
  if [ "$FOUND" -eq 0 ]; then
    echo "Refusing the pipefail/grep trap. A match here would report as a failure:"
    echo ""
  fi
  echo "  $hit"
  FOUND=$((FOUND + 1))
done < <(
  grep -rnE '(docker logs|curl)[^|]*\|[[:space:]]*grep[[:space:]]+-[a-zA-Z]*q' \
    "$HERE/scripts" --include='*.sh' 2>/dev/null \
    | grep -v 'lint-pipefail-grep.sh' \
    | grep -v 'pipefail-grep-fixture.sh' \
    | grep -vE '^[^:]+:[0-9]+:[[:space:]]*#' \
    | sed "s|$HERE/||"
)

if [ "$FOUND" -gt 0 ]; then
  echo ""
  echo "Use scripts/lib/gate.sh instead:"
  echo "  docker logs C | grep -q P   ->  log_has C \"P\"   (or wait_for_log C \"P\" 15)"
  echo "  curl -s URL   | grep -q P   ->  fetch_has URL \"P\""
  echo "  case-insensitive            ->  log_has_i, or lowercase both sides"
  echo ""
  echo "Why: scripts/smoke/pipefail-grep-fixture.sh proves the trap and the fix."
  exit 1
fi

echo "✅ no unbounded-writer \`| grep -q\` pipelines in scripts/"
