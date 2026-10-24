"""Counted lines: neither blank nor comment, by each language's own syntax.

One rule for the Rootstock budget and the legacy ratchet, so the two numbers
are comparable. The shape follows CleanRoom's tests/test_budget.py; this file
adds block comments for templates, scripts and Svelte.
"""

from __future__ import annotations

from pathlib import Path

LINE = {".py": ("#",), ".js": ("//",), ".ts": ("//",), ".svelte": ("//",), ".css": ()}
BLOCK = {
    ".py": (),
    ".html": (("<!--", "-->"), ("{#", "#}")),
    ".js": (("/*", "*/"),),
    ".ts": (("/*", "*/"),),
    ".css": (("/*", "*/"),),
    ".svelte": (("<!--", "-->"), ("/*", "*/")),
}


def count_text(text: str, suffix: str) -> int:
    """Lines with any code left once comments are taken out."""
    singles, blocks = LINE.get(suffix, ()), BLOCK.get(suffix, ())
    total, closer = 0, None
    for raw in text.splitlines():
        rest, code = raw.strip(), False
        while rest:
            if closer:
                end = rest.find(closer)
                if end < 0:
                    rest = ""
                    break
                rest, closer = rest[end + len(closer):].strip(), None
                continue
            opened = next(((o, c) for o, c in blocks if rest.startswith(o)), None)
            if opened:
                rest, closer = rest[len(opened[0]):], opened[1]
                continue
            if any(rest.startswith(s) for s in singles):
                break
            code = True
            break
        total += code
    return total


def count(path: Path) -> int:
    return count_text(path.read_text(encoding="utf-8", errors="replace"), path.suffix)


def tree(root: Path, suffixes: set[str], skip: set[str] = frozenset()) -> dict[str, int]:
    """Counted lines per file under root, as root-relative posix paths."""
    out = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_file() and path.suffix in suffixes and not (set(Path(rel).parts) & skip):
            out[rel] = count(path)
    return out


def _selftest() -> None:
    assert count_text("x = 1\n\n# note\n  # indented\n", ".py") == 1
    assert count_text("<!-- a\nb -->\n<p>{# c #}</p>\n{# d #}\n", ".html") == 1
    assert count_text("/* a */ let x = 1;\n// b\n/*\n c\n*/\n", ".js") == 1
    assert count_text("<!-- a --><div>\n<script>\n// c\n</script>\n", ".svelte") == 3
    assert count_text("{#\nnote\n#}\n{{ x }}\n", ".html") == 1


if __name__ == "__main__":
    _selftest()
    print("linecount self-test: ok")
