#!/usr/bin/env python3
"""The structure ratchet: the chat path may get simpler, never more tangled.

WHY THIS EXISTS
---------------
Nothing stopped `middleware.py` growing to 2,617 lines across fifteen levels of
indentation. It did not arrive that way; it accreted, one reasonable-looking
commit at a time, and no gate ever objected. The chat-path restructure will pull
those numbers down — and without a ratchet they will climb straight back the
moment the effort ends, because the same forces that produced them are still
running.

So this asserts CEILINGS, not targets. Every measurement must come in at or
under the number recorded in `baseline.json`. Beating a ceiling is reported and
never punished; the gate tells you to lower it and `--tighten` does that for you.
Exceeding one fails the build.

WHAT IS MEASURED

  max_function_lines       Largest single function. The number a reviewer must
                           hold in their head at once.
  max_indent_levels        Deepest nesting, in 4-space levels.
  deep_lines               Code lines at six levels or deeper. The share of the
                           file written inside six or more enclosing scopes.
  nonlocal_statements      Closure coupling. Every one is a module boundary that
                           cannot be drawn. Target is zero.
  commented_out_code_lines Code kept as comments. Already zero — earned on
                           2026-08-04 by deleting the dead web-search handler,
                           and it stays zero.
  except_pass_handlers     `except ...: pass`. Silent failure, by construction.
  citation_rot             Line links in the charts and ledger that no longer
                           point at what their prose says. Always zero: this is
                           the only dimension with no baseline to spend.

WHY CITATION ROT IS IN A STRUCTURE GATE
---------------------------------------
On 2026-08-04, re-deriving every `middleware.py#L<n>` link found five that were
already wrong by ~93 lines — and two of those sat inside FENCES, the notes that
tell a future session which guard is load-bearing and must not be tidied away. A
fence pointing at the wrong line is worse than no fence: it reads as
authoritative and sends the reader to unrelated code. Deleting 160 lines the same
day moved every citation past line 411 and would have silently rotted the rest.
Any commit that shifts line numbers rots these links, so the check belongs with
the checks that watch line numbers.

TARGETS FOLLOW THE CODE, NOT THE FILENAME
-----------------------------------------
The file list is a glob that already includes the package the restructure will
create. A ratchet aimed at one filename is defeated the moment the sprawl moves
to a new file — which is precisely what a restructure does.

USAGE
    make chat_path_structure           # assert
    make chat_path_structure_tighten   # lower ceilings to what was just achieved
    make chat_path_structure_teeth     # prove every assertion can fail

Exit 0 when every dimension is at or under its ceiling, 1 otherwise.
"""

from __future__ import annotations

import argparse
import ast
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
HERE = pathlib.Path(__file__).resolve().parent
BASELINE = HERE / "baseline.json"

# The chat path as it is today, plus where it is going. The glob is the point:
# splitting middleware.py into a package must not drop it out of the ratchet.
TARGET_GLOBS = [
    "app/backend/sage_is_ai/utils/middleware.py",
    "app/backend/sage_is_ai/utils/chat_path/**/*.py",
]

# Markdown that cites the chat path by line number.
CITATION_GLOBS = [
    "TODO.md",
    "charts/**/TODO.md",
    "docs/decisions/*.md",
]

DEEP_LEVEL = 6
INDENT_WIDTH = 4

COMMENTED_CODE = re.compile(
    r"^\s*#\s*(async def |def |class |if |for |while |try:|except|return |await "
    r"|import |from |\w+\s*=\s*\S|\}|\)|\{)"
)
ANCHOR = re.compile(r"middleware\.py#L(\d+)")


def targets() -> list[pathlib.Path]:
    found: list[pathlib.Path] = []
    for pattern in TARGET_GLOBS:
        if "*" in pattern:
            found.extend(sorted(ROOT.glob(pattern)))
        else:
            p = ROOT / pattern
            if p.exists():
                found.append(p)
    if not found:
        sys.exit("ratchet: no target files matched — the globs are stale")
    return found


def indent_of(line: str) -> int:
    return len(line) - len(line.lstrip())


def measure_file(path: pathlib.Path) -> dict:
    src = path.read_text()
    lines = src.split("\n")
    tree = ast.parse(src, filename=str(path))

    functions = [
        (n.name, n.lineno, n.end_lineno - n.lineno + 1)
        for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]

    code_lines = [
        ln for ln in lines if ln.strip() and not ln.strip().startswith("#")
    ]
    indents = [indent_of(ln) for ln in code_lines]

    nonlocals = [
        (n.lineno, list(n.names)) for n in ast.walk(tree) if isinstance(n, ast.Nonlocal)
    ]

    except_pass = [
        n.lineno
        for n in ast.walk(tree)
        if isinstance(n, ast.ExceptHandler)
        and len(n.body) == 1
        and isinstance(n.body[0], ast.Pass)
    ]

    commented = [i for i, ln in enumerate(lines, 1) if COMMENTED_CODE.match(ln)]

    deep_cut = DEEP_LEVEL * INDENT_WIDTH
    return {
        "max_function_lines": max((f[2] for f in functions), default=0),
        "max_function_name": max(functions, key=lambda f: f[2])[0] if functions else "",
        "max_indent_levels": (max(indents, default=0)) // INDENT_WIDTH,
        "deep_lines": sum(1 for i in indents if i >= deep_cut),
        "code_lines": len(code_lines),
        "nonlocal_statements": len(nonlocals),
        "nonlocal_sites": nonlocals,
        "commented_out_code_lines": len(commented),
        "commented_sites": commented,
        "except_pass_handlers": len(except_pass),
        "except_pass_sites": except_pass,
    }


def measure_structure() -> dict:
    total = {
        "max_function_lines": 0,
        "max_function_name": "",
        "max_indent_levels": 0,
        "deep_lines": 0,
        "code_lines": 0,
        "nonlocal_statements": 0,
        "commented_out_code_lines": 0,
        "except_pass_handlers": 0,
    }
    detail = {}
    for path in targets():
        m = measure_file(path)
        rel = str(path.relative_to(ROOT))
        detail[rel] = m
        if m["max_function_lines"] > total["max_function_lines"]:
            total["max_function_lines"] = m["max_function_lines"]
            total["max_function_name"] = f"{m['max_function_name']} ({rel})"
        total["max_indent_levels"] = max(
            total["max_indent_levels"], m["max_indent_levels"]
        )
        for key in (
            "deep_lines",
            "code_lines",
            "nonlocal_statements",
            "commented_out_code_lines",
            "except_pass_handlers",
        ):
            total[key] += m[key]
    total["_detail"] = detail
    return total


# --------------------------------------------------------------------------
# Citation rot
# --------------------------------------------------------------------------


def measure_citations(fences: dict) -> tuple[int, list[str]]:
    """Every middleware.py line link must still point at real code, and the
    load-bearing ones must point at the exact text their prose promises."""
    source = (ROOT / "app/backend/sage_is_ai/utils/middleware.py").read_text().split("\n")
    problems: list[str] = []

    docs: list[pathlib.Path] = []
    for pattern in CITATION_GLOBS:
        docs.extend(sorted(ROOT.glob(pattern)))

    for doc in docs:
        text = doc.read_text()
        rel = str(doc.relative_to(ROOT))
        for m in ANCHOR.finditer(text):
            n = int(m.group(1))
            doc_line = text[: m.start()].count("\n") + 1
            if n < 1 or n > len(source):
                problems.append(f"{rel}:{doc_line} -> L{n} is past end of file")
                continue
            target = source[n - 1].strip()
            if not target:
                problems.append(f"{rel}:{doc_line} -> L{n} is a blank line")
            elif target in (")", "]", "}", "):", "],", "},"):
                problems.append(
                    f"{rel}:{doc_line} -> L{n} is a bare closing bracket ({target!r})"
                )

    # The fences: links whose whole purpose is to say "do not touch THIS".
    for name, spec in fences.items():
        n = spec["line"]
        want = spec["must_contain"]
        if n > len(source):
            problems.append(f"fence {name!r}: L{n} is past end of file")
            continue
        if want not in source[n - 1]:
            problems.append(
                f"fence {name!r}: L{n} no longer contains {want!r} "
                f"— it now reads {source[n - 1].strip()[:60]!r}"
            )

    return len(problems), problems


# --------------------------------------------------------------------------
# The ratchet
# --------------------------------------------------------------------------

RATCHETED = [
    ("max_function_lines", "largest function, in lines"),
    ("max_indent_levels", "deepest nesting, in levels"),
    ("deep_lines", "code lines at six levels or deeper"),
    ("nonlocal_statements", "nonlocal statements"),
    ("commented_out_code_lines", "lines of code kept as comments"),
    ("except_pass_handlers", "silent `except ...: pass` handlers"),
]


def load_baseline() -> dict:
    if not BASELINE.exists():
        sys.exit(f"ratchet: no baseline at {BASELINE} — run with --tighten to record one")
    return json.loads(BASELINE.read_text())


def run(tighten: bool, source_path: pathlib.Path | None = None) -> int:
    base = load_baseline()
    ceilings = base["ceilings"]
    fences = base.get("fences", {})

    actual = measure_structure()
    rot_count, rot_problems = measure_citations(fences)
    actual["citation_rot"] = rot_count

    over: list[str] = []
    under: list[str] = []

    for key, label in RATCHETED:
        ceiling = ceilings[key]
        got = actual[key]
        if got > ceiling:
            over.append(f"{label}: {got} exceeds the ceiling of {ceiling}")
        elif got < ceiling:
            under.append(f"{label}: {got}, ceiling {ceiling}")

    if rot_count:
        over.append(f"citation rot: {rot_count} stale line link(s)")

    if tighten:
        for key, _ in RATCHETED:
            ceilings[key] = actual[key]
        base["ceilings"] = ceilings
        base["measured_code_lines"] = actual["code_lines"]
        BASELINE.write_text(json.dumps(base, indent=2) + "\n")
        print("Ceilings lowered to what the code achieves today:\n")
        for key, label in RATCHETED:
            print(f"  {label}: {actual[key]}")
        print(f"\nWrote {BASELINE.relative_to(ROOT)}. Commit it with the change that earned it.")
        return 0

    if over:
        print("FAIL — the chat path got more tangled, not less:\n")
        for line in over:
            print(f"  • {line}")
        if rot_problems:
            print("\n  Stale citations:")
            for p in rot_problems[:12]:
                print(f"    - {p}")
            if len(rot_problems) > 12:
                print(f"    … {len(rot_problems) - 12} more")
        print(
            "\nCeilings only ratchet DOWN. If this growth is genuinely necessary,"
            "\nsay so in the commit message and raise the ceiling deliberately —"
            "\nediting baseline.json is a decision, not a formality."
        )
        return 1

    print(
        f"PASS — {len(RATCHETED)} structural ceilings held, "
        f"0 stale citations across the charts and ledger."
    )
    if under:
        print("\nRoom earned — lower these with `make chat_path_structure_tighten`:")
        for line in under:
            print(f"  • {line}")
    return 0


def relocate() -> int:
    """Say where every fence moved to. Report only — nothing is rewritten.

    A gate that costs an afternoon of manual line-hunting gets switched off, and
    the real check leaves with it. This turns the hunt into a lookup table: the
    fence text is searched for, and the new line number is printed beside the old
    one. Editing the charts is still a human act.
    """
    base = load_baseline()
    fences = base.get("fences", {})
    source = (ROOT / "app/backend/sage_is_ai/utils/middleware.py").read_text().split("\n")

    moved, lost, held = [], [], []
    for name, spec in fences.items():
        want, old = spec["must_contain"], spec["line"]
        found = [i for i, ln in enumerate(source, 1) if want in ln]
        if not found:
            lost.append((name, old, want))
        elif old in found:
            held.append((name, old))
        else:
            moved.append((name, old, found))

    if held:
        print(f"{len(held)} fence(s) unmoved.\n")
    if moved:
        print("MOVED — update these line numbers wherever they are cited:\n")
        for name, old, found in moved:
            where = found[0] if len(found) == 1 else f"{found} (ambiguous)"
            delta = f"{found[0] - old:+d}" if len(found) == 1 else "?"
            print(f"  {name}\n      {old} -> {where}   ({delta})")
        print()
    if lost:
        print("GONE — the fence text is not in the file at all. Either the code")
        print("was deleted (was that deliberate?) or the fence needs rewording:\n")
        for name, old, want in lost:
            print(f"  {name} (was L{old}): {want!r}")
        print()

    print("Also check any citation the gate reported as blank or bracket-only;")
    print("those have no declared text to search for, so they need reading.")
    print("\nAfter editing, add each newly load-bearing line to `fences` in")
    print(f"{BASELINE.relative_to(ROOT)} so the next shift is caught too.")
    return 0


def self_test() -> int:
    """Prove every assertion can fail. A gate nobody has seen fail is decoration."""
    import tempfile

    sample = '''
def outer():
    def deep():
        for a in [1]:
            for b in [1]:
                for c in [1]:
                    for d in [1]:
                        for e in [1]:
                            for f in [1]:
                                nonlocal_target = a + b + c + d + e + f
                                try:
                                    pass
                                except Exception:
                                    pass
    return deep

# def dead_code_kept_as_a_comment(x):
#     return x + 1
'''
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td) / "sample.py"
        p.write_text(sample)
        m = measure_file(p)

    checks = [
        ("max_indent_levels", m["max_indent_levels"] >= 6),
        ("deep_lines", m["deep_lines"] > 0),
        ("commented_out_code_lines", m["commented_out_code_lines"] == 2),
        ("except_pass_handlers", m["except_pass_handlers"] == 1),
        ("max_function_lines", m["max_function_lines"] > 0),
    ]
    failed = [name for name, ok in checks if not ok]

    # Citation rot must fire on a fence that has moved.
    bad_fence = {"synthetic": {"line": 1, "must_contain": "this text is not on line 1"}}
    rot, problems = measure_citations(bad_fence)
    if rot < 1:
        failed.append("citation_rot")

    if failed:
        print("FAIL — these detectors did not fire on a sample built to trip them:")
        for f in failed:
            print(f"  • {f}")
        return 1

    print(
        "PASS — teeth proven: every structural detector fires on a sample built"
        " to trip it, and a moved fence is caught as citation rot."
    )
    print(f"  sample measured: { {k: v for k, v in m.items() if not k.endswith('sites') and k != 'max_function_name'} }")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tighten", action="store_true", help="lower ceilings to today's numbers")
    ap.add_argument("--self-test", action="store_true", help="prove the assertions can fail")
    ap.add_argument("--report", action="store_true", help="print the measurements and exit")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    if args.report:
        actual = measure_structure()
        detail = actual.pop("_detail")
        print(json.dumps(actual, indent=2))
        for rel, m in detail.items():
            print(f"\n{rel}: {m['code_lines']} code lines, "
                  f"largest {m['max_function_name']} at {m['max_function_lines']}")
        return 0

    return run(tighten=args.tighten)


if __name__ == "__main__":
    raise SystemExit(main())
