#!/usr/bin/env python3
"""Startr Swap stays publishable.

`pages/assets/startr-swap.js` is written to be published for other projects,
including static sites. That claim decays quietly: the first time somebody
reaches for `/pages/` or a `data-cy` hook to fix a bug, the file still works
here and silently stops working anywhere else. Nothing would fail, and the
next person to copy it out would find out.

So this asserts the two properties that make it a library rather than a feature:

  1. IT NAMES NOTHING IN THIS APPLICATION. Every host-specific concern has to
     leave through an attribute value or an event listener, which is the whole
     design. A token from this repo appearing in the file means one did not.

  2. IT IS NOT GROWING INTO WHAT IT REPLACES. htmx is 16,367 bytes gzipped for
     the three attributes this covers. The ceiling is half of that: enough room
     to fix real bugs, not enough to drift into a framework.

`startr-swap.cy.ts` asserts the other half — that two bare HTML documents with
no attributes and no configuration actually swap. A static check cannot prove
behaviour, and a browser cannot prove absence, so both exist.

    scripts/gates/startr-swap/check.py             # report
    scripts/gates/startr-swap/check.py --check     # gate: non-zero on failure
    scripts/gates/startr-swap/check.py --self-test # prove the gate can fail
"""

from __future__ import annotations

import argparse
import gzip
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LIBRARY = ROOT / "app/backend/sage_is_ai/pages/assets/startr-swap.js"

# Half of htmx gzipped (16,367 bytes), which is the thing this replaces.
CEILING_GZIP = 8192

# Words that only mean something inside this repository. `htmz` is deliberately
# absent: crediting the lineage is not a dependency on it.
FORBIDDEN = (
    "sage",
    "sprig",
    "svelte",
    "jinja",
    "fastapi",
    "htmx",
    "ai-ui",
    "data-cy",
    "/pages/",
)


def findings(source: str, size_gzip: int) -> list[str]:
    """Every way the file has stopped being publishable, named."""
    out: list[str] = []
    for word in FORBIDDEN:
        for n, line in enumerate(source.splitlines(), 1):
            if word in line.lower():
                out.append(f"line {n} names `{word}` — that is this application, not a library")
    if size_gzip > CEILING_GZIP:
        out.append(
            f"{size_gzip} bytes gzipped is over the {CEILING_GZIP} ceiling "
            "— half of htmx, which is what this replaces"
        )
    # A published file has to say what it is and where it came from.
    if not re.search(r"htmz.*Lean Rada", source):
        out.append("the htmz attribution (MIT, (c) Lean Rada) is missing from the header")
    return out


def measure(path: Path) -> tuple[str, int]:
    raw = path.read_bytes()
    return raw.decode("utf-8"), len(gzip.compress(raw, 9))


def report(problems: list[str], size_gzip: int) -> None:
    for p in problems:
        print(f"  ✗ {p}")
    if not problems:
        print(
            f"PASS — startr-swap.js names nothing in this application "
            f"({size_gzip} bytes gzipped, ceiling {CEILING_GZIP})."
        )


def self_test() -> int:
    """Break it three ways on a copy and require the check to notice each one."""
    source, size = measure(LIBRARY)
    if findings(source, size):
        print("SELF-TEST INCONCLUSIVE — the real file is already failing.")
        return 1

    breaks = {
        "an application token": (source + "\n// fetch the sprig catalog\n", size),
        "a route prefix": (source.replace("data-swap", "/pages/data-swap", 1), size),
        "growth past the ceiling": (source, CEILING_GZIP + 1),
    }
    missed = [name for name, (text, n) in breaks.items() if not findings(text, n)]
    if missed:
        print(f"FAIL — the check did not detect: {', '.join(missed)}")
        return 1
    print(f"PASS — the check detected all {len(breaks)} perturbations.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="exit non-zero on any finding")
    ap.add_argument("--self-test", action="store_true", help="prove the check can fail")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    if not LIBRARY.exists():
        print(f"FAIL — {LIBRARY.relative_to(ROOT)} is missing.")
        return 1

    source, size = measure(LIBRARY)
    problems = findings(source, size)
    report(problems, size)
    return 1 if (problems and args.check) else 0


if __name__ == "__main__":
    sys.exit(main())
