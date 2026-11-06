#!/usr/bin/env python3
"""Check every `path:line` citation in research notes against the pinned tree.

    python3 check_cites.py NOTE.md [NOTE.md ...]   exit 1 on any bad cite

A cite is a backticked `path:N`, `path:N-M` or `path:N,M,...`. A path resolves
against the repo root, the backend package, the GitHub folder for `../Repo/...`,
or a unique file name in the repo. A bad cite is a path that does not resolve,
is ambiguous, or points past the end of its file. Stdlib only.
"""

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]  # this repo, wherever it is checked out
GITHUB = REPO.parent  # the sibling checkouts the notes cite live beside it
BACKEND = REPO / "app" / "backend" / "sage_is_ai"
# Sibling repos the notes cite by their own relative paths; the repo comes first.
# Shorthand a note may declare in its scope line, e.g. "`C/` means `app/src/lib/components/`".
ALIASES = {"C/": "app/src/lib/components/"}
ROOTS = [REPO, BACKEND, REPO / "app", REPO / "app" / "src", GITHUB / "WEB-AI-Sage-Trellis",
         GITHUB / "AI--Tinker.Click", GITHUB / "AI--Tinker.Click" / "server" / "src",
         GITHUB / "homebrew-apps", GITHUB / "BONSAI", GITHUB / "CleanRoom", GITHUB]
CITE = re.compile(r"`([A-Za-z0-9_./+()\-\[\]]+\.[A-Za-z0-9]+):(\d+(?:[-–]\d+)?(?:,\s?\d+(?:[-–]\d+)?)*)`")
SKIP = {".git", "node_modules", ".svelte-kit", "__pycache__", "static", "build"}
_names: dict[str, list[Path]] = {}
_lines: dict[Path, int] = {}


SIBLINGS = [GITHUB / n for n in ("WEB-AI-Sage-Trellis", "AI--Tinker.Click", "homebrew-apps", "BONSAI", "CleanRoom")]


def names() -> dict[str, list[Path]]:
    """Every file name in the repo and the sibling repos, each file once."""
    if not _names:
        for root in (REPO, *SIBLINGS):
            for p in root.rglob("*"):
                if p.is_file() and not set(p.relative_to(root).parts) & SKIP:
                    _names.setdefault(p.name, []).append(p)
    return _names


def resolve(raw: str) -> tuple[Path | None, str]:
    for short, full in ALIASES.items():
        if raw.startswith(short):
            raw = full + raw[len(short):]
    if raw.startswith("../"):
        p = (GITHUB / raw[3:]).resolve()
        return (p, "") if p.is_file() else (None, "missing")
    for base in ROOTS:
        p = base / raw
        if p.is_file():
            return p, ""
    hits = [p for p in names().get(Path(raw).name, []) if p.as_posix().endswith("/" + raw)]
    in_repo = [p for p in hits if REPO in p.parents]
    if len(in_repo) == 1 or len(hits) == 1:
        return (in_repo or hits)[0], ""
    return None, "ambiguous" if hits else "missing"


def length(path: Path) -> int:
    if path not in _lines:
        _lines[path] = len(path.read_text(encoding="utf-8", errors="replace").splitlines())
    return _lines[path]


def check(note: Path) -> list[str]:
    bad = []
    for lineno, text in enumerate(note.read_text(encoding="utf-8").splitlines(), 1):
        for raw, spans in CITE.findall(text):
            path, why = resolve(raw)
            if path is None:
                bad.append(f"{note.name}:{lineno}: `{raw}` {why}")
                continue
            top = max(int(n) for n in re.findall(r"\d+", spans))
            if top > length(path):
                bad.append(f"{note.name}:{lineno}: `{raw}:{spans}` past end ({length(path)} lines)")
    return bad


def main(argv: list[str]) -> int:
    total_bad, total = 0, 0
    for arg in argv[1:]:
        note = Path(arg)
        n = sum(len(CITE.findall(t)) for t in note.read_text(encoding="utf-8").splitlines())
        bad = check(note)
        total, total_bad = total + n, total_bad + len(bad)
        print(f"{note.parent.name}/{note.name}: {n} cites, {len(bad)} bad")
        for b in bad:
            print("  " + b)
    print(f"all notes: {total} cites, {total_bad} bad")
    return 1 if total_bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
