#!/usr/bin/env python3
"""Fixture: distribution_heal — the highest SERVER_TAG wins.

A version is integers read left to right; the leftmost outweighs the rest.
Python compares tuples that way already, so sorting them gives an ascending
ladder by definition and each adjacent pair is a known (lower, higher). Nothing
is predicted here — the fixture never re-implements the comparison it is testing.

Bumping a base of all nines means every step crosses a 9-to-10 carry, which is
exactly where a string sort inverts. All three pairs are traps by construction:

    9.9.9 < 9.9.10 < 9.10.9 < 10.9.9      numerically
    9.9.9 > 9.9.10 > 9.10.9 > 10.9.9      as strings

Two invariants hold for every scenario:
  * heal exits 0 — a non-zero post-checkout hook kills release_finish
  * heal never writes into this repo's copy — a backward write dirties a file
    the next `git merge` must touch, and git then refuses to merge

Runs on throwaway files. The sibling paths are `?=` in the Makefile, so the real
repos are never touched.

  make distribution_heal_fixture

To prove it has teeth: make heal propagate the lower version outward, re-run,
and watch the "holds" scenarios go red.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

BASE = (9, 9, 9)
VERSIONS = sorted({BASE} | {BASE[:i] + (n + 1,) + BASE[i + 1:] for i, n in enumerate(BASE)})
LADDER = [".".join(map(str, v)) for v in VERSIONS]
PAIRS = list(zip(LADDER, LADDER[1:]))

FAILURES = []


def body(tag, extra=""):
    return f"IMAGE=ghcr.io/sage-is/ai-ui\nSERVER_TAG={tag}\nCLI_VERSION=1.0.4\n{extra}"


def run(mine, theirs):
    """Lay out three severed copies, run heal, report what it did."""
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        me, *peers = (tmp / n / "distribution.env" for n in ("aiui", "brew", "docs"))
        for path in (me, *peers):
            path.parent.mkdir()
        me.write_text(mine)
        for peer in peers:
            peer.write_text(theirs)

        result = subprocess.run(
            ["make", "-C", str(ROOT), "-s", "distribution_heal",
             f"SIBLING_AI_UI={me.parent}",
             f"SIBLING_HOMEBREW={peers[0].parent}",
             f"SIBLING_DOCS={peers[1].parent}"],
            capture_output=True, text=True,
        )
        return result.returncode, me.read_text(), me.stat().st_nlink, {p.read_text() for p in peers}


def expect(self_tag, peer_tag, wins, extra=""):
    """`wins` says whether this repo should win — known from how the pair was built."""
    mine, theirs = body(self_tag, extra), body(peer_tag)
    code, after, links, peers = run(mine, theirs)

    for what, got, want in (
        ("exit code", code, 0),
        ("this repo untouched", after, mine),
        ("link count", links, 3 if wins else 1),
        ("peer content", peers, {mine if wins else theirs}),
    ):
        if got != want:
            FAILURES.append(f"self={self_tag} peer={peer_tag}: {what} was {got!r}, wanted {want!r}")


for lower, higher in PAIRS:
    expect(higher, lower, wins=True)    # this repo holds the higher tag — it wins
    expect(lower, higher, wins=False)   # this repo holds the lower tag — it holds

expect(LADDER[-1], LADDER[-1], wins=False, extra="EXTRA=x\n")  # equal tags: cannot rank, so hold

print(f"\n=== distribution_heal — highest SERVER_TAG wins ===")
print(f"    ladder: {' < '.join(LADDER)}")
print(f"\n{'=' * 8}  {len(PAIRS) * 2 + 1} scenarios, {len(FAILURES)} failed  {'=' * 8}\n")
for failure in FAILURES:
    print(f"  ❌ {failure}")
if FAILURES:
    print('\n"holds" red means heal propagates backward and will regress SERVER_TAG')
    print("in the sibling repos.\n")

sys.exit(1 if FAILURES else 0)
