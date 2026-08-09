#!/usr/bin/env python3
"""The cognitive-complexity ratchet for the Python backend.

Cognitive complexity is not cyclomatic complexity. Cyclomatic counts branches.
Cognitive weights each branch by how deeply it is nested, which is the disease
this codebase actually has. The difference is not academic — it decided which
tool got adopted:

    commit      SLOC   radon mi    radon cc   complexipy
    6fc2271     1968   C (8.91)    F (58)     826
    7ff0001     1968   C (3.40)    F (58)     826
    c7c3fb3     1870   C (0.00)    F (58)     578   <- the three tightening passes
    9e06cc8     1870   C (0.00)    F (58)     578

Between the first two commits not one line of code changed — SLOC and LLOC are
identical on both sides. Only comments moved, 248 down to 107, and radon's
maintainability index fell 5.5 points because its formula carries a comment-ratio
term. It then floored at 0.00, where it can no longer register progress at all.
Cyclomatic complexity never moved: lifting a function to module level does not
change its branch count. Cognitive complexity fell 30% and landed exactly on the
commit that did the work. It is the only one of the five that saw it.

Ratchet rules, all three enforced together:

  1. No function may exceed the value recorded for it in baseline.json.
  2. No function absent from the baseline may exceed `watch_floor`. That is what
     stops a fresh 400-line horror from walking in unmeasured.
  3. The summary ceilings only go down.

Runs on the host in about a second. It reads source and imports nothing from the
application, so it needs no image and no container — same reasoning as the
chat-path ratchet next door. A gate that requires a 20-minute build is a gate
that gets skipped locally and only ever fails in CI.

  --tighten   lower the baseline to what the tree earns today
  --self-test prove the ratchet still bites, by feeding it a worsened tree
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
GATE_DIR = Path(__file__).resolve().parent
BASELINE = GATE_DIR / "baseline.json"
TARGET = REPO / "app" / "backend" / "sage_is_ai"

# Pinned in app/pyproject.toml under [tool.rye] dev-dependencies. A ratchet whose
# measuring stick drifts between machines is not a ratchet.
COMPLEXIPY_VERSION = "6.2.0"


def resolve_complexipy():
    """Prefer an installed complexipy; fall back to a pinned ephemeral run."""
    local = shutil.which("complexipy")
    if local:
        return [local]
    uvx = shutil.which("uvx")
    if uvx:
        return [uvx, f"complexipy@{COMPLEXIPY_VERSION}"]
    sys.exit(
        "FAIL: complexipy not found and uvx is unavailable.\n"
        f"      Install it — `pip install complexipy=={COMPLEXIPY_VERSION}` — or\n"
        "      install uv so this gate can fetch the pinned version itself."
    )


def measure(target: Path) -> dict:
    """Return {"relative/path.py::function": complexity} for every function.

    `-mx 0` disables the absolute ceiling so the snapshot dumps everything rather
    than only the functions already over it. `--snapshot-ignore` stops complexipy
    comparing against its own snapshot file; this gate owns the comparison, and
    two ratchets disagreeing about the baseline is worse than none.
    """
    cmd = resolve_complexipy()
    with tempfile.TemporaryDirectory() as tmp:
        proc = subprocess.run(
            cmd
            + ["-mx", "0", "--snapshot-create", "--snapshot-ignore", "--quiet",
               str(target)],
            cwd=tmp,
            capture_output=True,
            text=True,
        )
        snapshot = Path(tmp) / "complexipy-snapshot.json"
        if not snapshot.exists():
            sys.exit(
                "FAIL: complexipy produced no snapshot.\n"
                f"      stdout: {proc.stdout[-500:]}\n"
                f"      stderr: {proc.stderr[-500:]}"
            )
        data = json.loads(snapshot.read_text())

    out = {}
    for entry in data:
        rel = os.path.relpath(entry["path"], REPO)
        for fn in entry["functions"]:
            # A name can appear twice in one file — ruff reports three such sites
            # as F811, all FastAPI handlers. Keyed naively the second would
            # overwrite the first and one of the pair would go unmeasured.
            key = f"{rel}::{fn['name']}"
            if key in out:
                n = 2
                while f"{key}#{n}" in out:
                    n += 1
                key = f"{key}#{n}"
            out[key] = fn["complexity"]
    if not out:
        sys.exit("FAIL: measured zero functions. The target path is probably wrong.")
    return out


def summarise(measured: dict, floor: int) -> dict:
    """Summary numbers. Only the enforced two belong in `ceilings`.

    `total_complexity` is deliberately absent. A new five-complexity helper is
    ordinary, healthy work, and a total that ratchets down would fail on it. A
    ceiling that punishes writing a small function teaches people to write large
    ones. It is reported, never enforced.
    """
    return {
        "worst_function": max(measured.values()),
        "functions_over_floor": sum(1 for v in measured.values() if v > floor),
    }


def load_baseline() -> dict:
    if not BASELINE.exists():
        sys.exit(f"FAIL: no baseline at {BASELINE}. Run with --tighten to record one.")
    return json.loads(BASELINE.read_text())


def write_baseline(base: dict, measured: dict, floor: int) -> None:
    base["watch_floor"] = floor
    base["ceilings"] = summarise(measured, floor)
    base["per_function"] = {
        k: v for k, v in sorted(measured.items(), key=lambda kv: (-kv[1], kv[0]))
        if v > floor
    }
    BASELINE.write_text(json.dumps(base, indent=2) + "\n")


def check(measured: dict, base: dict) -> list:
    floor = base["watch_floor"]
    recorded = base["per_function"]
    failures = []

    for name, value in sorted(measured.items()):
        if name in recorded:
            if value > recorded[name]:
                failures.append(
                    f"{name}: cognitive complexity rose {recorded[name]} -> {value}"
                )
        elif value > floor:
            failures.append(
                f"{name}: {value} is over the watch floor of {floor} and is not in "
                f"the baseline. New code does not get a grandfather clause."
            )

    now = summarise(measured, floor)
    for key, ceiling in base["ceilings"].items():
        if now[key] > ceiling:
            failures.append(f"{key}: {now[key]} is over the ceiling of {ceiling}")

    return failures


def self_test(measured: dict, base: dict) -> int:
    """Prove the ratchet has teeth by handing it a tree that got worse."""
    worst = max(measured, key=measured.get)
    poisoned = dict(measured)
    poisoned[worst] += 1
    poisoned["app/backend/sage_is_ai/utils/brand_new_horror.py::handler"] = 400

    failures = check(poisoned, base)
    rose = any("rose" in f for f in failures)
    unmeasured = any("grandfather" in f for f in failures)

    print("Self-test — feeding the ratchet a worsened tree:")
    print(f"  {'PASS' if rose else 'FAIL'}  a regression on {worst} is caught")
    print(f"  {'PASS' if unmeasured else 'FAIL'}  an unmeasured new function is caught")
    if rose and unmeasured:
        print("\nPASS — the ratchet still bites.")
        return 0
    print("\nFAIL — the ratchet is toothless. It would pass a tree that got worse.")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tighten", action="store_true",
                    help="lower the baseline to what the tree earns today")
    ap.add_argument("--self-test", action="store_true",
                    help="prove the ratchet still fails a worsened tree")
    ap.add_argument("--floor", type=int, default=None,
                    help="watch floor for functions absent from the baseline")
    args = ap.parse_args()

    measured = measure(TARGET)

    if args.tighten:
        base = json.loads(BASELINE.read_text()) if BASELINE.exists() else {
            "_what": "Cognitive-complexity ceilings for the Python backend. They "
                     "ratchet DOWN only. Raising one is a decision that belongs in "
                     "a commit message, not a formality.",
        }
        floor = args.floor if args.floor is not None else base.get("watch_floor", 15)
        before = base.get("ceilings", {})
        write_baseline(base, measured, floor)
        after = summarise(measured, floor)
        print(f"Baseline written to {BASELINE.relative_to(REPO)}")
        for key, value in after.items():
            was = before.get(key)
            note = "unchanged" if was == value else f"was {was}"
            print(f"  {key}: {value}  ({note})")
        print(f"  watched functions: {len(base['per_function'])} over {floor}")
        return 0

    base = load_baseline()

    if args.self_test:
        return self_test(measured, base)

    failures = check(measured, base)
    now = summarise(measured, base["watch_floor"])
    total = sum(measured.values())

    if failures:
        print(f"FAIL — cognitive complexity regressed ({len(failures)} findings)\n")
        for f in failures:
            print(f"  {f}")
        print("\nEarn the number or change the baseline on purpose. Do not do both "
              "in silence.")
        return 1

    print(
        f"PASS — worst function {now['worst_function']}, "
        f"{now['functions_over_floor']} over the floor of {base['watch_floor']}, "
        f"{total} total across {len(measured)} functions (reported, not gated)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
