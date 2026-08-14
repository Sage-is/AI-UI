#!/usr/bin/env bash
# Fail when a document tells someone to run a make target that does not exist.
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
# WHY IT LOOKS OUTSIDE THE REPO (added 2026-08-12). Tracked .md files are not the
# only documents that issue instructions. Agent memory stores, private notes
# vaults and sibling checkouts all do, and they rot the same way with nobody
# reviewing them. Those trees are listed in docs-targets.roots, one directory per
# line, so which trees exist is DATA and this script stays generic.
#
# MATCHING IS DELIBERATELY NARROW, because "make sure", "make a" and "make the"
# are English, not commands. A candidate counts only when it is backticked or
# carries an underscore — the shape every real target in this repo has. That
# heuristic dropped ~20 false positives and kept every true one during the audit
# that motivated this file.
set -euo pipefail

# Resolve before any cd, so --self-test can re-invoke us from a temp root.
SELF="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"

# A gate nobody has watched fail is a gate nobody should trust. `--self-test`
# builds a throwaway repo and a throwaway extra root, then proves the behaviours
# that matter. It asserts on EXIT CODE, so a matcher that silently stops matching
# cannot pass it.
self_test() {
  local tmp; tmp=$(mktemp -d); trap 'rm -rf "$tmp"' RETURN
  local repo="$tmp/repo" pass=0 fail=0
  mkdir -p "$repo/scripts/gates"
  printf 'real_target:\n\t@true\n' > "$repo/Makefile"
  # The tracked-docs half reads `git ls-files`, so the sandbox must be a real
  # repo with a populated index. Without this the doc scenarios scan nothing and
  # pass vacuously — which is what the first run of this self-test did.
  git -C "$repo" init -q

  # Two roots: one that resolves through both expansions, one deliberately
  # absent. Every scenario below therefore also proves a missing root is skipped
  # rather than failing the run.
  printf '~/notes/projects/%%REPO_SLUG%%/memory\n/nonexistent/root/for/self/test\n' \
    > "$repo/scripts/gates/docs-targets.roots"
  local slug; slug=$(printf '%s' "$repo" | tr '/' '-')
  # NOT "$tmp/home/..." — that literal reads as /home/<user>/ and trips the
  # local-user-path rule in .gitleaks.toml, which is right to be suspicious of a
  # home-shaped absolute path in a tracked file. Keep the fake HOME named
  # something that cannot look like a real one.
  local extra="$tmp/fakehome/notes/projects/$slug/memory"
  mkdir -p "$extra"

  run() { # <expected-exit> <label>
    local want="$1" label="$2" got=0
    git -C "$repo" add -A >/dev/null 2>&1 || true
    DOCS_TARGETS_ROOT="$repo" HOME="$tmp/fakehome" "$SELF" >/dev/null 2>&1 || got=$?
    if [ "$got" -eq "$want" ]; then
      printf '  ok   %s\n' "$label"; pass=$((pass+1))
    else
      printf '  FAIL %s (wanted exit %s, got %s)\n' "$label" "$want" "$got"; fail=$((fail+1))
    fi
  }

  echo "docs-targets --self-test"
  printf 'Run `make real_target` to build.\n' > "$repo/doc.md"
  run 0 "tracked doc naming a real target passes"

  printf 'Run `make ghost_target` to build.\n' > "$repo/doc.md"
  run 1 "tracked doc naming a dead target fails"

  # Dates are literals here on purpose: a test that computes its own expiry
  # cannot tell you the comparison is wired the right way round.
  printf 'ghost_target  2999-01-01  # proposed, not built yet\n' > "$repo/scripts/gates/docs-targets.allow"
  run 0 "allowlisted dead target passes while unexpired"

  printf 'ghost_target  2000-01-01  # lapsed long ago\n' > "$repo/scripts/gates/docs-targets.allow"
  run 0 "LAPSED allowlist entry still allows (warns, never reds)"

  printf 'ghost_target  # no date at all\n' > "$repo/scripts/gates/docs-targets.allow"
  run 1 "UNDATED allowlist entry fails"

  rm -f "$repo/scripts/gates/docs-targets.allow"

  printf 'Run `make real_target` to build.\n' > "$repo/doc.md"
  printf 'Release with `make dead_door`.\n' > "$extra/note.md"
  run 1 "extra root naming a dead target fails"

  mkdir -p "$extra/.backup"
  printf 'Release with `make older_dead_door`.\n' > "$extra/.backup/note.md"
  rm -f "$extra/note.md"
  run 0 "nested subdirectory of an extra root is not scanned"

  rm -f "$repo/scripts/gates/docs-targets.roots"
  printf 'Release with `make dead_door`.\n' > "$extra/note.md"
  run 0 "no roots file means extra roots are not scanned at all"

  printf '%s passed, %s failed\n' "$pass" "$fail"
  [ "$fail" -eq 0 ]
}

[ "${1:-}" = "--self-test" ] && { self_test; exit $?; }

# DOCS_TARGETS_ROOT exists for the self-test only. Real runs take the repo root.
cd "${DOCS_TARGETS_ROOT:-$(dirname "$0")/../..}"

ALLOW="scripts/gates/docs-targets.allow"
ROOTS="scripts/gates/docs-targets.roots"
FAILED=0

real=$(grep -oE '^[a-zA-Z_][a-zA-Z0-9_-]*:' Makefile | tr -d ':' | sort -u)

# Proposals are legitimate: a doc may say "Add a `make try_sage_smoke` target".
# Those live in the allowlist, WITH a reason, so an unbuilt target is a recorded
# intention rather than a lie.
# Each entry carries an expiry: `<target> <YYYY-MM-DD> # reason`. A missing or
# malformed date FAILS here and now, so an undated entry cannot be added. A date
# already past WARNS and still allows — failing on a date would red the gate on a
# day nobody chose, which is how a device becomes an obstacle and gets bypassed.
allow=""
allow_expired=""
if [ -f "$ALLOW" ]; then
  today=$(date +%F)
  while IFS= read -r line || [ -n "$line" ]; do
    line="${line%%#*}"
    line="$(printf '%s' "$line" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')"
    [ -z "$line" ] && continue
    entry_name=$(printf '%s' "$line" | awk '{print $1}')
    entry_exp=$(printf '%s' "$line" | awk '{print $2}')
    if ! printf '%s' "$entry_exp" | grep -qE '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'; then
      printf '%s: `%s` has no expiry date. Format: <target> <YYYY-MM-DD> # reason\n' \
        "$ALLOW" "$entry_name"
      FAILED=1
      continue
    fi
    allow="$allow$entry_name
"
    if [[ "$entry_exp" < "$today" ]]; then
      allow_expired="$allow_expired  $entry_name (lapsed $entry_exp)
"
    fi
  done < "$ALLOW"
fi

# History is allowed to name things that are gone. A completed item records what
# was actually run at the time; rewriting it to match today's target names would
# make the record false in order to keep a gate quiet.
files=$(git ls-files '*.md' 2>/dev/null | grep -vE '^docs/archive/|^docs/completed-todos\.md$' || true)

# Extra roots. Absent ones are announced and skipped: these trees are per-machine
# and failing on absence would make the gate unrunnable on a fresh clone.
if [ -f "$ROOTS" ]; then
  repo_slug=$(pwd | tr '/' '-')
  while IFS= read -r line || [ -n "$line" ]; do
    line="${line%%#*}"
    line="$(printf '%s' "$line" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')"
    [ -z "$line" ] && continue
    line="${line//%REPO_SLUG%/$repo_slug}"
    case "$line" in "~"*) line="${HOME}${line#\~}" ;; esac
    if [ -d "$line" ]; then
      found=$(find "$line" -maxdepth 1 -name '*.md' | sort)
      [ -n "$found" ] && files="$files
$found"
    else
      echo "docs-targets: extra root not present, skipping — $line"
    fi
  done < "$ROOTS"
else
  # Say it. $ROOTS is gitignored, so on every machine but the one that wrote it
  # this branch is the normal case, and a feature that silently does nothing is
  # how a gate turns absence into a green tick.
  echo "docs-targets: no $ROOTS — tracked repo docs only (see $ROOTS.example)"
fi

for f in $files; do
  [ -f "$f" ] || continue
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

# Printed even when the run fails, because a lapsed intention is worth seeing
# whether or not something else went wrong on the same run.
if [ -n "$allow_expired" ]; then
  echo
  echo "docs-targets: WARNING — allowlisted intentions have lapsed:"
  printf '%s' "$allow_expired"
  echo "  Build it, drop the claim from the doc, or push the date out on purpose."
fi

if [ "$FAILED" -ne 0 ]; then
  echo
  echo "Either build the target, fix the document, or — if it is PROPOSING the"
  echo "target — add it to $ALLOW as: <target> <YYYY-MM-DD> # reason"
  exit 1
fi

echo "docs-targets: every make target named in a scanned document exists"
