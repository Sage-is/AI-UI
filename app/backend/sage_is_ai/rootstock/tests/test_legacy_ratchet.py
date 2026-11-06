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
# +469 python, 2026-11-02/03, bugs fixed where they live as F0 did. Retrieval lets
# a deliberate 503 through instead of a 400 "[ERROR: 503 ...]" (+8). Privacy parses
# tool arguments, maps objects both ways, stops writing stand-ins into the saved
# content block and restores only declared parameters (+86 with its tests);
# /process/file's write rule (+23); the prompt-slash validator and its repair
# migration (+31); the /api/config session rule, the community-sharing
# diagnostics row and the session lookup that answers 503, not 401, on a busy
# database (+71 with its test); the model index rebuilt after every write (+76
# with its test); vector re-activated after a graft and at boot (+55 with its
# test); one shared note rule, net -22 across notes, socket, retrieval. The
# streamed pass-through reverses tool-call arguments whole (+74 with its tests);
# ruff format over the files that were format-clean at HEAD (+56); +11 the
# first count missed. +50 more, same days: a Space agent made since the model
# list loaded answers after one reload (+9 in spaces.py, +41 its test).
# +8, 2026-11-03: COMMUNITY_HUB_URL, the hub's one address, in config and
# /api/config; the same change cut 100 frontend lines from five share copies.
# +83, 2026-11-03: a Space agent replies under the member's own model access,
# checked before the payload pipeline (+18 in spaces.py, +65 its test). +3:
# SAGE_RUNTIME, which `ai-ui` passes in and /api/config hands to admins. +28:
# /retrieval/readiness, so an upload is refused before it starts; frontend +18
# net after the share helper's -100: that check, the artifact panel's single
# render and the admin runtime notice (2026-11-03).
# +103 python, 2026-11-03: privacy reverses reasoning on all three paths and gives
# Ollama and direct connections their own switches, in hooks, middleware and the
# panel, with their tests. Frontend +2: the upload check, edited after its count.
# +256 python, 2026-11-04/05, fixed where they live for 3.3.0: reasoning blocks
# close mid-stream on both paths, with the orphan-close drop and implicit open
# (+101 in middleware.py); the env-only model connection, SAGE_LLM_* (+25, and
# +69 its test); the model list's nested "openai" copy dropped (-2, and +63 its
# test). +77, 2026-11-05, from the 3.3.0 gates: a guard that every caller of a model
# write route passes request= (the agents page did not, a 500; +24 in
# test_models_reindex.py); a vector graft whose import fails reports it instead of a
# 500 (+3, and +31 its tests); ruff format over the new model-list test (+19).
# +266, 2026-11-05, the bugs riding in 3.3.0: pruning Tika or Docling resets the
# extraction engine, an evicted Sprig says so, knowledge answers a real 503 and
# diagnostics shows it, the chat path's [DONE], model switch and title fixes
# (+17 net); their tests (+249).
CEILINGS = {"python": 53_894, "frontend": 67_305, "pages": 1_665}
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
