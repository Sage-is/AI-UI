#!/usr/bin/env bash
# Poka-Yoke: no lightweight v* tag may be published.
#
# WHY THIS EXISTS. `finish_flow` cuts tags with `git tag -a`. A human typing
# `git tag -f` does not, and that is how v3.1.0 became lightweight. It is not
# alone: v2.0.0 is lightweight too (2 of 11 v* tags, counted 2026-08-12). An
# earlier version of this comment called v3.1.0 the only one, which was wrong
# and is the reason the count is now written down. Neither is worth repairing
# retroactively — re-cutting an old tag stamps today's date on a past release,
# which trades one wrong fact for another. An annotated tag carries an author, a date and a
# message; a lightweight one is a bare pointer, so `git describe`, `git for-each-ref`
# and every provenance question answer differently depending on which kind you
# got. One release cut one of each, which is the whole problem.
#
# WHY PRE-PUSH AND NOT reference-transaction. A `reference-transaction` hook
# would refuse the bad tag at creation, which is earlier and sounds better. It
# also fires on fetch. Any remote that already carries a lightweight tag — this
# one does, right now — could no longer be fetched, so the device would break
# `git fetch` on precisely the repos that need repairing. Push is where the
# mistake becomes irreversible and shared. That is the boundary worth holding.
#
# WHY ONLY UNPUBLISHED TAGS. A tag already on origin is somebody else's fact.
# Refusing it would block every push until it is repaired, which turns a safety
# device into an obstacle and gets it bypassed. This refuses what you are about
# to add, and stays silent about what is already out there.
#
#   make tags_annotated          run it by hand
#   make tags_annotated_teeth    prove it can fail
set -euo pipefail

# Resolved BEFORE anything changes directory: self_test re-invokes this script
# from inside a throwaway repo, and a relative $0 does not survive the cd.
SELF="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"

REMOTE="${1:-origin}"

published_tags() {
	git ls-remote --tags "$REMOTE" 2>/dev/null |
		sed -e 's|.*refs/tags/||' -e 's|\^{}$||' | sort -u
}

check() {
	local published bad=()

	# Unreachable remote: skip, and say so. This is NOT the parity_gate pattern
	# that was just deleted from gauntlet_full. That skip hid a live risk — the
	# models were absent, so the gate never ran while still reporting green. This
	# one fires only when the protected act is impossible: with no reachable
	# origin, no tag can be published, so there is nothing to protect. Treating it
	# as a failure would red every offline run and get the device switched off.
	if ! published="$(published_tags)"; then
		echo "tags_annotated: SKIPPED — '$REMOTE' unreachable, so nothing can be published" >&2
		return 0
	fi

	while IFS= read -r tag; do
		[ -n "$tag" ] || continue
		# Already on origin: not ours to judge.
		if grep -Fxq -- "$tag" <<<"$published"; then continue; fi
		# Annotated tags are `tag` objects. Lightweight ones point straight at a commit.
		if [ "$(git cat-file -t "$tag" 2>/dev/null)" != "tag" ]; then
			bad+=("$tag")
		fi
	done < <(git tag -l 'v*')

	[ ${#bad[@]} -eq 0 ] && return 0

	echo "" >&2
	echo "[ABORT] lightweight tag(s) would be published:" >&2
	for tag in "${bad[@]}"; do echo "  - $tag" >&2; done
	echo "" >&2
	echo "A lightweight tag is a bare pointer: no author, no date, no message." >&2
	echo "Every v* tag in this repo is annotated except the ones above." >&2
	echo "" >&2
	echo "Re-cut each at the same commit, then push again:" >&2
	for tag in "${bad[@]}"; do
		echo "  git tag -f -a $tag $tag^{commit} -m \"$tag\"" >&2
	done
	echo "" >&2
	echo "Releases cut tags through \`make ship\`, which uses \`git tag -a\`." >&2
	echo "If you reached for \`git tag\` by hand, that is the thing to stop doing." >&2
	return 1
}

# Prove the gate can fail. Builds a throwaway repo carrying one tag of each kind
# and asserts this script greens on the annotated one and reds on the lightweight
# one. A gate nobody has watched fail is a gate nobody should trust.
self_test() {
	local tmp rc fails=0
	tmp="$(mktemp -d)"
	trap 'rm -rf "$tmp"' RETURN

	git init -q --bare "$tmp/origin"
	git init -q "$tmp/work"
	git -C "$tmp/work" config user.email fixture@example.invalid
	git -C "$tmp/work" config user.name fixture
	git -C "$tmp/work" commit -q --allow-empty -m "fixture"
	git -C "$tmp/work" remote add origin "$tmp/origin"

	git -C "$tmp/work" tag -a v1.0.0 -m v1.0.0
	rc=0; (cd "$tmp/work" && "$SELF" origin >/dev/null 2>&1) || rc=$?
	if [ "$rc" -ne 0 ]; then
		echo "  FAIL: annotated-only repo was refused (exit $rc, wanted 0)" >&2
		fails=$((fails + 1))
	fi

	git -C "$tmp/work" tag v2.0.0
	rc=0; (cd "$tmp/work" && "$SELF" origin >/dev/null 2>&1) || rc=$?
	if [ "$rc" -eq 0 ]; then
		echo "  FAIL: lightweight tag was accepted (exit 0, wanted non-zero)" >&2
		fails=$((fails + 1))
	fi

	# The published-tag exemption: once v2.0.0 is on the remote, it stops counting.
	git -C "$tmp/work" push -q origin v2.0.0
	rc=0; (cd "$tmp/work" && "$SELF" origin >/dev/null 2>&1) || rc=$?
	if [ "$rc" -ne 0 ]; then
		echo "  FAIL: already-published lightweight tag still refused (exit $rc, wanted 0)" >&2
		fails=$((fails + 1))
	fi

	# Unreachable remote skips rather than reds: the lightweight v2.0.0 is still
	# sitting there, and this must still exit 0.
	rc=0; (cd "$tmp/work" && "$SELF" "$tmp/does-not-exist" >/dev/null 2>&1) || rc=$?
	if [ "$rc" -ne 0 ]; then
		echo "  FAIL: unreachable remote was treated as a failure (exit $rc, wanted 0)" >&2
		fails=$((fails + 1))
	fi

	if [ "$fails" -ne 0 ]; then
		echo "tags_annotated teeth: $fails/4 scenarios wrong" >&2
		return 1
	fi
	echo "tags_annotated teeth: 4/4 — reds on lightweight, greens on annotated, exempts published, skips offline"
}

case "${1:-}" in
--self-test) self_test ;;
*) check ;;
esac
