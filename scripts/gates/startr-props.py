#!/usr/bin/env python3
"""Fail when a server-rendered page sets a startr.style prop that nothing reads.

A misspelt inline prop is silent: `--opacity:0.8` set nothing, because the kit
reads `--op`, and eleven such props sat in the pages until 2026-11-02 (try.sage
text never faded, list bullets never hid). This reads every `--prop:` in the
`style="..."` attributes of pages/templates and pages/*.py, and every
`var(--prop` in the vendored kit and the pages' own CSS and JS. A prop set but
never read fails, with its file.

    python3 scripts/gates/startr-props.py              check this checkout
    python3 scripts/gates/startr-props.py --self-test  prove the check can fail
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGES = ROOT / "app/backend/sage_is_ai/pages"
READERS = [*ROOT.glob("app/static/vendor/startr.style/*/style.css"),
           *PAGES.glob("assets/**/*.css"), *PAGES.glob("assets/**/*.js")]
WRITERS = [*PAGES.glob("templates/**/*.html"), *PAGES.glob("*.py")]

READ = re.compile(r"var\(\s*(--[A-Za-z0-9_-]+)")
STYLE = re.compile(r'style="([^"]*)"')
SET = re.compile(r"(--[A-Za-z0-9_-]+)\s*:")


def dead_props(readers: list[str], writers: dict[str, str]) -> dict[str, set[str]]:
    """Props each writer sets in a style attribute that no reader reads."""
    read = {prop for text in readers for prop in READ.findall(text)}
    dead: dict[str, set[str]] = {}
    for name, text in writers.items():
        for style in STYLE.findall(text):
            for prop in SET.findall(style):
                if prop not in read:
                    dead.setdefault(prop, set()).add(name)
    return dead


def self_test() -> int:
    found = dead_props(["a{opacity:var(--op)}"], {"t.html": '<p style="--op:1; --opacity:1">'})
    if found != {"--opacity": {"t.html"}}:
        print(f"startr-props self-test: expected only --opacity, got {found}", file=sys.stderr)
        return 1
    print("startr-props self-test: ok")
    return 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    if not READERS:
        print("startr-props: no vendored startr.style sheet found", file=sys.stderr)
        return 1
    dead = dead_props([p.read_text(encoding="utf-8", errors="replace") for p in READERS],
                      {p.name: p.read_text(encoding="utf-8") for p in WRITERS})
    for prop, files in sorted(dead.items()):
        print(f"startr-props: {prop} is set but nothing reads it ({', '.join(sorted(files))})", file=sys.stderr)
    if dead:
        return 1
    print(f"startr-props: ok ({len(WRITERS)} page files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
