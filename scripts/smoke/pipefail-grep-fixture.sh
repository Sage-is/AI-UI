#!/usr/bin/env bash
# Proof that the gate helpers fix the pipefail/grep trap, and that the trap was
# real to begin with.
#
# `cmd | grep -q PATTERN` under `set -o pipefail` reports a MATCH as failure:
# grep exits on the first hit, the writer takes SIGPIPE and dies 141, and
# pipefail surfaces 141 as the pipeline's status. It only fires when the writer
# still had output queued, which is why it looked like flakiness: the same
# assertion passed on a quiet container and failed on a busy one.
#
# It cost two gates before anyone chased it. `sprig_signing`'s "minisign OK"
# check failed inside gauntlet_full and passed on its own, and `upgrade_gate`'s
# host-arch check spent weeks recorded as a product bug that did not exist.
#
# This fixture asserts BOTH halves, because a device that fixes nothing and a
# device that fixes something look identical when you only test the new way:
#   1. the old shape really does return 141 on a match  (the trap is real)
#   2. the helpers return 0 on the same input           (the fix works)
#   3. the negative case does not invert                (the dangerous half)
#
# Usage: scripts/smoke/pipefail-grep-fixture.sh
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/../lib/gate.sh"

# Big enough that the writer cannot drain into the 64 KB pipe buffer before
# grep exits. This is the whole trigger condition.
BIG="$(seq 1 200000 | sed 's/^/MARKER line /')"
SMALL="nothing to see here"

echo "== 1. the trap is real: the OLD shape turns a match into a failure =="
printf '%s\n' "$BIG" | grep -q "MARKER"
OLD_STATUS=$?
[ "$OLD_STATUS" -ne 0 ] \
  && ok "\`| grep -q\` returned $OLD_STATUS on a MATCH (this is the bug)" \
  || no "old shape returned 0, so the trap did not reproduce and this fixture proves nothing"

echo "== 2. the helper returns success on the same input =="
text_has "$BIG" "MARKER" \
  && ok "text_has matched a 200k-line haystack and returned 0" \
  || no "text_has failed on a haystack that clearly contains the pattern"

echo "== 3. the helper still says NO when there is no match =="
text_has "$SMALL" "MARKER" \
  && no "text_has matched something that is not there" \
  || ok "text_has correctly reports no match"

echo "== 4. the dangerous half: a NEGATIVE assertion must not invert =="
# `grep -q traceback && fail` is how the upgrade gate checks for migration
# errors. Under the old shape a PRESENT traceback returns 141, so the gate
# reports "clean" on exactly the failure it exists to catch.
HAYSTACK="$(printf 'Traceback (most recent call last)\n%s\n' "$BIG")"
printf '%s\n' "$HAYSTACK" | grep -qi "traceback"
[ "$?" -ne 0 ] \
  && ok "old shape MISSED a traceback that is present (silent pass, the worst case)" \
  || no "old shape caught it; the inversion did not reproduce here"
text_has "${HAYSTACK,,}" "traceback" \
  && ok "text_has finds the traceback the old shape missed" \
  || no "text_has missed a traceback that is present"

echo "== 5. case-insensitive matching works without PCRE syntax =="
# Bash's =~ is POSIX ERE and has no inline (?i). Writing one makes the pattern a
# literal that never matches, which on a negative assertion is a silent pass.
text_has "SHOUTING TRACEBACK" "(?i)traceback" 2>/dev/null \
  && no "(?i) appeared to work; do not rely on it, bash =~ is ERE" \
  || ok "(?i) does NOT work in bash =~ (why log_has_i lowercases instead)"
text_has "${HAYSTACK,,}" "traceback" \
  && ok "lowercasing both sides is the working idiom" \
  || no "lowercase match failed"

gate_summary "PIPEFAIL-GREP FIXTURE"
