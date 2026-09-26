#!/usr/bin/env bash
# The Python linter for the backend.
#
# Adopted 2026-08-06. Nothing else in this repo reads Python semantics — bandit
# reads security, `ruff format` reads formatting (it replaced black as the
# format gate 2026-08-17; black survives only as the runtime dependency behind
# the routers/utils.py code-formatting endpoint), and the chat-path ratchet
# reads six shapes of one file. Ruff read all 218 backend files in 40
# milliseconds and found the single undefined name in the tree:
# chat_web_search_handler, the frozen NameError recorded in TODO.md.
#
# Configuration lives in app/pyproject.toml under [tool.ruff], including the
# reasoning for every ignored rule. The 20 violations that survive that config
# carry an explicit `# noqa` naming their rule, so they are greppable:
#
#     grep -rn 'noqa:' app/backend/sage_is_ai/
#
# Runs on the host. It reads source and imports nothing from the application, so
# it needs no image and no container.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../../.."

# Pinned in app/pyproject.toml under [tool.rye] dev-dependencies. A linter whose
# version drifts between machines reports different findings on the same code.
RUFF_VERSION="0.16.1"

if command -v ruff >/dev/null 2>&1; then
    RUFF=(ruff)
elif command -v uvx >/dev/null 2>&1; then
    RUFF=(uvx "ruff@${RUFF_VERSION}")
else
    echo "FAIL: ruff not found and uvx is unavailable." >&2
    echo "      Install it — 'pip install ruff==${RUFF_VERSION}' — or install uv" >&2
    echo "      so this gate can fetch the pinned version itself." >&2
    exit 1
fi

cd app

case "${1:-check}" in
    check)
        exec "${RUFF[@]}" check backend/
        ;;
    format-check)
        # Blocking since 2026-08-17: the backend went format-clean in the
        # ruff-format adoption and `lint` gates on it.
        exec "${RUFF[@]}" format --check backend/
        ;;
    format-fix)
        exec "${RUFF[@]}" format backend/
        ;;
    *)
        echo "usage: run-gate.sh [check|format-check|format-fix]" >&2
        exit 2
        ;;
esac
