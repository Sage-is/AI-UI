#!/usr/bin/env python3
"""Fail when a tracked file over 1 MB is not one of the few the repo already carries.

The repo tracks 97 MB against Tinker's 19 for about the same code (Rootstock card,
"Repo weight"); most of it is twelve files over 1 MB. Pre-commit's 500 kB check
sees only commits made with the hook installed; this runs in `gauntlet_fast`, so a
push catches the rest. KNOWN only shrinks: a file that leaves, or gets smaller,
comes off the list in the same change.

    python3 scripts/gates/tracked-size.py              check this checkout
    python3 scripts/gates/tracked-size.py --self-test  prove the check can fail
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIMIT = 1024 * 1024
# The files over the limit on 2026-11-03, each at its size then. The CJK fonts
# serve PDF export only and are to move into the export-document Sprig recipe.
KNOWN = {
    "app/static/fonts/NotoSansSC-Variable.ttf": 17_805_476,
    "app/static/fonts/NotoSansSC-Regular.ttf": 10_560_616,
    "app/static/fonts/NotoSansKR-Variable.ttf": 10_361_060,
    "app/static/fonts/NotoSansJP-Variable.ttf": 9_586_480,
    "app/static/fonts/NotoSansKR-Regular.ttf": 6_192_764,
    "app/static/icons/sage.2025-08-01.xcf": 5_774_363,
    "app/static/fonts/NotoSansJP-Regular.ttf": 5_732_824,
    "app/static/assets/images/galaxy.jpg": 2_981_700,
    "app/static/fonts/NotoSans-Variable.ttf": 2_490_816,
    "app/static/swagger-ui/swagger-ui-bundle.js": 2_239_154,
    "app/static/fonts/Twemoji.ttf": 1_496_648,
    "app/static/assets/images/adam.jpg": 1_318_500,
}


def problems(sizes: dict[str, int], known: dict[str, int]) -> list[str]:
    """A file over the limit that is new or grew past its size on the list."""
    out = []
    for path, size in sorted(sizes.items()):
        if size > LIMIT and size > known.get(path, 0):
            was = f"listed at {known[path]:,} bytes" if path in known else "new"
            out.append(f"{path}: {size:,} bytes ({was}); keep it out of git, or shrink it under 1 MB")
    return out


def tracked_sizes() -> dict[str, int]:
    names = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True).stdout
    return {
        name: (ROOT / name).stat().st_size
        for name in names.decode().split("\0")
        if name and (ROOT / name).is_file()
    }


def self_test() -> int:
    found = problems({"big.bin": LIMIT + 1, "old.ttf": 2 * LIMIT, "small.txt": 10}, {"old.ttf": 2 * LIMIT})
    if len(found) != 1 or not found[0].startswith("big.bin"):
        print(f"tracked-size self-test: expected only big.bin, got {found}", file=sys.stderr)
        return 1
    print("tracked-size self-test: ok")
    return 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    found = problems(tracked_sizes(), KNOWN)
    for line in found:
        print(f"tracked-size: {line}", file=sys.stderr)
    if not found:
        print(f"tracked-size: ok ({len(KNOWN)} known files over 1 MB, no new one)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
