#!/usr/bin/env bash
# Fail when tracked files outside the board cite more `TODO.md:NNN` lines than
# the ceiling allows.
#
# A board line number moves on every register pass, so a cite to one rots
# silently: on 2026-11-02, 76 of 104 such cites pointed at the wrong card or at
# none. Cite the card's bold title instead (docs/board-register-method.md, step
# 5). CEILING is the count of deliberate cites left that day: notes about stale
# cites, pointers into Trellis's own board, the frozen chat path. It only moves
# down. A path before `TODO.md` names another board and is not counted.
#
#   scripts/gates/board-cites.sh              check this checkout
#   scripts/gates/board-cites.sh --self-test  prove the check can fail
set -uo pipefail

CEILING=14
ROOT="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
PATTERN='(^|[^/A-Za-z])TODO\.md:[0-9]+'

count() { grep -o -E "$PATTERN" | wc -l | tr -d ' '; }

judge() {  # judge COUNT: at or under the ceiling passes; under it, say so
    if [ "$1" -gt "$CEILING" ]; then
        echo "board_cites: $1 TODO.md:NNN cites > $CEILING; cite the card's bold title instead (docs/board-register-method.md)" >&2
        return 1
    fi
    if [ "$1" -lt "$CEILING" ]; then
        echo "board_cites: $1 cites, under $CEILING; lower CEILING in scripts/gates/board-cites.sh"
    fi
    return 0
}

if [ "${1:-}" = "--self-test" ]; then
    [ "$(printf '%s\n' 'see `TODO.md:12`' 'charts/x/TODO.md:3 is another board' | count)" = 1 ] \
        || { echo "board_cites self-test: the pattern miscounts" >&2; exit 1; }
    if judge $((CEILING + 1)) 2>/dev/null; then
        echo "board_cites self-test: one cite over the ceiling passed" >&2
        exit 1
    fi
    judge "$CEILING" >/dev/null || { echo "board_cites self-test: the ceiling itself failed" >&2; exit 1; }
    echo "board_cites self-test: ok"
    exit 0
fi

n="$(git -C "$ROOT" grep -h -E "$PATTERN" -- . ':!TODO.md' ':!KANBAN.canvas' | count)"
judge "$n" && echo "board_cites: ok ($n of $CEILING)"
