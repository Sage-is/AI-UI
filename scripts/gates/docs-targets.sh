#!/usr/bin/env bash
# Fail when a doc tells someone to run a make target that does not exist.
#
# WHY THIS EXISTS. On 2026-08-02 a scripted diff found, in seconds, three doc
# defects that months of reading had missed: docs/development-workflow.md
# documented five `make test_*` commands (none existed) as part of a Testing
# Standards section describing a DJANGO project in a FastAPI repo, and
# docs/try-sage-docker-exploration.md asserted `try_sage_stop` existed in three
# places, twice as "already added". It was never written.
#
# Docs rot silently in exactly the places a grep can prove. So this is a gate
# rather than an audit somebody remembers to run.
#
# MATCHING IS DELIBERATELY NARROW, because "make sure", "make a" and "make the"
# are English, not commands. A candidate counts only when it is backticked or
# carries an underscore — the shape every real target in this repo has. That
# heuristic dropped ~20 false positives and kept every true one during the audit
# that motivated this file.
set -euo pipefail

cd "$(dirname "$0")/../.."

ALLOW="scripts/gates/docs-targets.allow"
FAILED=0

real=$(grep -oE '^[a-zA-Z_][a-zA-Z0-9_-]*:' Makefile | tr -d ':' | sort -u)

# Proposals are legitimate: a doc may say "Add a `make try_sage_smoke` target".
# Those live in the allowlist, WITH a reason, so an unbuilt target is a recorded
# intention rather than a lie.
allow=""
[ -f "$ALLOW" ] && allow=$(grep -vE '^\s*#|^\s*$' "$ALLOW" | awk '{print $1}' | sort -u)

# History is allowed to name things that are gone. A completed item records what
# was actually run at the time; rewriting it to match today's target names would
# make the record false in order to keep a gate quiet.
files=$(git ls-files '*.md' | grep -vE '^docs/archive/|^docs/completed-todos\.md$' || true)

for f in $files; do
  # Backticked form, then the bare form restricted to underscore-bearing names.
  cands=$( { grep -oE '`make [A-Za-z_][A-Za-z0-9_]*`' "$f" | tr -d '`' || true
             grep -oE '(^|[^`])make [a-z][A-Za-z0-9]*_[A-Za-z0-9_]*' "$f" || true
           } | sed -E 's/.*make //' | sort -u )
  for t in $cands; do
    grep -qx "$t" <<<"$real" && continue
    [ -n "$allow" ] && grep -qx "$t" <<<"$allow" && continue
    printf '%s: names `make %s`, which is not a target\n' "$f" "$t"
    FAILED=1
  done
done

if [ "$FAILED" -ne 0 ]; then
  echo
  echo "Either build the target, fix the doc, or — if the doc is PROPOSING it —"
  echo "add the name to $ALLOW with a one-line reason."
  exit 1
fi

echo "docs-targets: every make target named in a doc exists"
