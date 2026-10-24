#!/usr/bin/env python3
"""Gate: nothing calls curl, jq, wget, pip or oras INSIDE the rootstock.

Since 3.2.1 the image ships none of them (the Dockerfile's cuts-stay-cut check
fails the build if one returns). A call that still expects one fails only when
it runs, often minutes into a long gate. This finds it at lint time and names
the replacement. `--self-test` proves the detector catches what it claims.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = re.compile(r"(?<![\w./-])(curl|jq|wget|pip3?|oras)(?![\w.-])")
FIX = {
    "shell": "use scripts/lib/rootstock-net.sh (netcurl), or pipe `X 'cat …'` into host jq",
    "runtime": "use `python3 -m sage_is_ai.utils.localhttp`, or uv for installs",
    "python": "installs: utils/runtime_install.py; pulls: sprigs/oci.py",
    "docker": "HEALTHCHECK/CMD run in the image: use sage_is_ai.utils.localhttp",
    "import": "the module left the image; see the Dockerfile's cuts-stay-cut table",
}


def _until_unquoted_pipe(s: str) -> str:
    quote = None
    for i, ch in enumerate(s):
        if quote:
            quote = None if ch == quote else quote
        elif ch in "'\"":
            quote = ch
        elif ch == "|":
            return s[:i]
    return s


def _tools(text: str) -> list[str]:
    return TOOLS.findall(text.replace("uv pip", "uv-pip"))


def shell_line(line: str) -> list[str]:
    """In-container segments of a host-side script line: X '…' and docker exec …"""
    if line.lstrip().startswith("#"):
        return []
    hits = []
    for m in re.finditer(r"""(?:^|[\s(;&|$])X\s+(['"])(.*?)(?<!\\)\1""", line):
        hits += _tools(m.group(2))
    m = re.search(r"\bdocker exec\b(.*)$", line)
    if m:
        hits += _tools(_until_unquoted_pipe(m.group(1)))
    return hits


def runtime_line(line: str) -> list[str]:
    """A line of a script that itself runs inside the image."""
    return [] if line.lstrip().startswith("#") else _tools(line)


def python_line(line: str) -> list[str]:
    lit = re.findall(r"""\[\s*["'](curl|jq|wget|pip3?|oras)["']""", line)
    lit += re.findall(r"""["']-m["']\s*,\s*["'](pip)["']""", line)
    return lit


def docker_line(line: str) -> list[str]:
    s = line.strip()
    return _tools(s) if re.match(r"(HEALTHCHECK|CMD|ENTRYPOINT)\b", s) else []


# Modules the image no longer has AT ALL (no Sprig brings them back). Importing
# one anywhere fails at run time; scripts mounted into the image count too
# (scripts/snapshots/inject-test-admin.py imported passlib until 2026-10-15).
# Each must also appear in the Dockerfile's cuts-stay-cut table: checked below.
GONE_FOR_GOOD = (
    "pip", "setuptools", "pkg_resources", "wheel", "typer", "rich", "pygments",
    "passlib", "peewee", "peewee_migrate", "playhouse",
)  # fmt: skip
_GONE_IMPORT = re.compile(
    r"^\s*(?:import|from)\s+(" + "|".join(GONE_FOR_GOOD) + r")(?:[.\s]|$)"
)


def import_line(line: str) -> list[str]:
    return _GONE_IMPORT.findall(line)


def dockerfile_drift() -> list[str]:
    """Every GONE_FOR_GOOD module (bar playhouse, part of peewee) is in the Dockerfile's table."""
    text = (ROOT / "Dockerfile").read_text()
    return [
        f"Dockerfile: cuts-stay-cut table lacks {m!r}; add it there or drop it here"
        for m in GONE_FOR_GOOD
        if m != "playhouse" and f'"{m}": (' not in text
    ]


def scan() -> list[str]:
    jobs = [
        ("shell", shell_line, [*ROOT.glob("scripts/**/*.sh"), ROOT / "Makefile"]),
        ("runtime", runtime_line, list(ROOT.glob("app/backend/*.sh"))),
        ("python", python_line, list(ROOT.glob("app/backend/sage_is_ai/**/*.py"))),
        ("docker", docker_line, [ROOT / "Dockerfile"]),
        ("import", import_line, [*ROOT.glob("app/backend/**/*.py"), *ROOT.glob("scripts/**/*.py")]),
    ]
    out = dockerfile_drift()
    for kind, check, files in jobs:
        for f in files:
            if f.name.startswith("test_"):
                continue
            for n, line in enumerate(f.read_text(errors="replace").splitlines(), 1):
                for tool in check(line):
                    out.append(
                        f"{f.relative_to(ROOT)}:{n}: `{tool}` would run in the image, "
                        f"which has none. Fix: {FIX[kind]}"
                    )
    return out


def self_test() -> None:
    bad = [
        (shell_line, """DIM=$(X "curl -s $U/embeddings | jq '.x'")"""),
        (shell_line, """docker exec "$ROOT" sh -c "jq -e .a /f" """),
        (runtime_line, "  curl -sf http://localhost:8080/health"),
        (python_line, """subprocess.run(["pip", "install", x])"""),
        (python_line, """[sys.executable, "-m", "pip", "install"]"""),
        (docker_line, "HEALTHCHECK CMD curl --fail http://x | jq -ne 'input.status'"),
        (import_line, "from passlib.hash import bcrypt"),
        (import_line, "    import peewee as pw"),
    ]
    good = [
        (shell_line, """X 'cat /app/state.json' | jq -e '.grafted'"""),
        (shell_line, """RES=$(netcurl -s "$U/rerank" | jq -r '.x')"""),
        (shell_line, "# X 'curl' in a comment"),
        (runtime_line, "  # No curl in the image since 3.2.1"),
        (runtime_line, "  uv pip install --system six"),
        (python_line, """cmd = ["uv", "pip", "install"]"""),
        (docker_line, "RUN apk add --virtual .fetch curl && apk del .fetch"),
        (import_line, "from sage_is_ai.utils.passwords import get_password_hash"),
        (import_line, "import richtext  # a different module"),
    ]
    assert not dockerfile_drift(), dockerfile_drift()
    for check, line in bad:
        assert check(line), f"missed: {line}"
    for check, line in good:
        assert not check(line), f"false alarm: {line}"
    print(f"self-test: {len(bad)} caught, {len(good)} left alone")


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        self_test()
        sys.exit(0)
    problems = scan()
    for p in problems:
        print(p)
    mark = "❌" if problems else "✅"
    print(f"{mark} in-container tools: {len(problems)} use(s) of tools or modules the image lacks")
    sys.exit(1 if problems else 0)
