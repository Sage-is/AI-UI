"""The legacy app only shrinks: each tree has a ceiling that moves down.

A tree over its ceiling fails: legacy code grew. A tree more than SLACK under
its ceiling also fails: something was deleted and the commit must lower the
ceiling to the new count, which docs/rootstock/deletion-ledger.md records.
Counting rules are shared with test_budget.py (linecount.py).
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from .linecount import tree
except ImportError:  # run as a script
    from linecount import tree

REPO = Path(os.environ.get("ROOTSTOCK_REPO") or Path(__file__).resolve().parents[5])
BACKEND = REPO / "app" / "backend" / "sage_is_ai"
TREES = {
    "python": (BACKEND, {".py"}, {"rootstock"}),
    "frontend": (REPO / "app" / "src", {".svelte", ".ts", ".js"}, set()),
    "pages": (BACKEND / "pages", {".html", ".js"}, set()),
}
# Baseline: develop with F0's eighteen fixes at source, measured 2026-10-24
# (3.2.2 stood at 52,095 / 67,277 / 1,665). F1's congestion fixes add legacy
# lines on purpose too; re-measure at each tag until the strangler starts.
CEILINGS = {"python": 52_551, "frontend": 67_285, "pages": 1_665}
SLACK = 0.02


def measure() -> dict[str, int]:
    return {name: sum(tree(root, suffixes, skip).values())
            for name, (root, suffixes, skip) in TREES.items()}


def check(counts: dict[str, int], ceilings: dict[str, int]) -> list[str]:
    problems = []
    for name, n in counts.items():
        ceiling = ceilings[name]
        if n > ceiling:
            problems.append(f"{name}: legacy grew to {n} > {ceiling}; build it in the Rootstock, "
                            f"or raise CEILINGS[{name!r}] in this commit with a reason")
        elif n < ceiling * (1 - SLACK):
            problems.append(f"{name}: legacy shrank to {n}; set CEILINGS[{name!r}] = {n} "
                            f"and add a deletion-ledger row")
    return problems


def test_legacy_only_shrinks() -> None:
    problems = check(measure(), CEILINGS)
    assert not problems, "; ".join(problems)


def test_check_has_teeth() -> None:
    assert check({"python": 101}, {"python": 100})
    assert check({"python": 97}, {"python": 100})
    assert not check({"python": 99}, {"python": 100})


if __name__ == "__main__":
    test_check_has_teeth()
    counts = measure()
    print(counts)
    test_legacy_only_shrinks()
    print("ratchet: ok")
