#!/usr/bin/env python3
"""Gate: a stream may never end with a content block left open.

The defect this guards, captured in production chat `171f30b9` on 2026-08-04:
a reasoning block opened from the `reasoning_content` FIELD path has exactly one
close path, and it is guarded on a content delta arriving. When a provider
streams the whole answer through the `reasoning` field and never sends a
`content` delta, nothing closes the block. It renders as a perpetual "Thinking…"
with the model's answer sealed inside it.

Two properties are asserted, and the second is the one that matters to a reader:

  1. No block is left open. Every block that was started has been ended.
  2. The ANSWER is visible as text. Closing a block is not enough on its own —
     if the answer is inside the reasoning content, closing it merely renders the
     answer collapsed behind a disclosure triangle. The finalizer splits at a
     stray end tag the model wrote itself and moves the answer out.

This imports `finalize_content_blocks` from the real module rather than copying
it, so the gate tracks the shipped code. It does NOT simulate the streaming loop;
it drives the finalizer against block lists shaped exactly as the loop leaves
them, which is what makes it deterministic. The trigger in the wild is model
compliance variance and cannot be summoned on demand.

Usage:
    make reasoning_finalizer_fixture
    python3 scripts/smoke/reasoning-finalizer-fixture.py

Exit 0 when every case holds, 1 otherwise.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(
    0, str(pathlib.Path(__file__).resolve().parents[2] / "app" / "backend")
)

try:
    from sage_is_ai.utils.middleware import finalize_content_blocks
except Exception as exc:  # noqa: BLE001 — the import IS the first assertion
    sys.exit(f"fixture: cannot import finalize_content_blocks — {exc}")

ANSWER = "RAD and Agile are both iterative."
T0 = 1000.0


def reasoning(content, started=True):
    b = {"type": "reasoning", "start_tag": "think", "end_tag": "/think", "content": content}
    if started:
        b["started_at"] = T0
    return b


def text(content):
    return {"type": "text", "content": content}


def tool_calls(started=True):
    b = {"type": "tool_calls", "content": [{"id": "1", "name": "search"}], "results": []}
    if started:
        b["started_at"] = T0
    return b


def code_interpreter(content, started=True):
    b = {"type": "code_interpreter", "start_tag": "code_interpreter",
         "end_tag": "/code_interpreter", "content": content, "attributes": {}}
    if started:
        b["started_at"] = T0
    return b


# (name, blocks as the streaming loop leaves them, must the answer be visible?)
CASES = [
    # The production capture: everything arrived through the `reasoning` field,
    # including the model's own closing tag and the answer after it.
    ("field path, answer trapped after a stray tag",
     [reasoning(f"weighing it up</thinking> {ANSWER}")], True),

    ("same, <think> form",
     [reasoning(f"weighing it up</think> {ANSWER}")], True),

    ("same, uppercase tag",
     [reasoning(f"weighing it up</THINKING> {ANSWER}")], True),

    ("same, whitespace inside the tag",
     [reasoning(f"weighing it up</ thinking > {ANSWER}")], True),

    # No stray tag at all. Nothing can be recovered as an answer, but the block
    # must still stop claiming to be in progress.
    ("field path, no tag, nothing to split",
     [reasoning("weighing it up and never finishing")], False),

    # The orphaning path: a tool_calls block pushed on top buries the open
    # reasoning block, so a tail-only finalizer would miss it.
    ("reasoning buried under tool_calls",
     [reasoning(f"weighing it up</thinking> {ANSWER}"), tool_calls()], True),

    # The other two block types leak too.
    ("tool_calls left open", [tool_calls()], False),
    ("code_interpreter left open", [code_interpreter("print(1)")], False),

    # Control: an already-closed block must not be touched or double-stamped.
    ("already closed, left alone",
     [dict(reasoning("done thinking"), ended_at=T0 + 3, duration=3), text(ANSWER)], True),

    # Control: a normal completed stream.
    ("normal stream", [reasoning("thought"), text(ANSWER)], True),

    ("empty list", [], False),
]


def main() -> int:
    failures = []

    for name, blocks, answer_expected in CASES:
        before = [dict(b) for b in blocks]
        finalize_content_blocks(blocks)

        still_open = [
            b for b in blocks
            if b.get("started_at") is not None and b.get("ended_at") is None
        ]
        visible = " ".join(
            "".join(b.get("content") or "" for b in blocks if b["type"] == "text").split()
        )

        if still_open:
            failures.append(
                f"{name}: {len(still_open)} block(s) left open "
                f"({still_open[0]['type']})"
            )
        if answer_expected and ANSWER not in visible:
            failures.append(f"{name}: answer not visible as text; got {visible[:70]!r}")

        # A reasoning block must never keep a raw end tag in its content.
        for b in blocks:
            if b["type"] == "reasoning" and "</" in (b.get("content") or ""):
                failures.append(f"{name}: raw end tag left in reasoning content")

        # Idempotence: a second pass must change nothing.
        snapshot = [dict(b) for b in blocks]
        finalize_content_blocks(blocks)
        if [dict(b) for b in blocks] != snapshot:
            failures.append(f"{name}: not idempotent — a second call changed the blocks")

        # A closed block must never be re-stamped.
        for b_before, b_after in zip(before, blocks):
            if b_before.get("ended_at") is not None:
                if b_after.get("ended_at") != b_before.get("ended_at"):
                    failures.append(f"{name}: re-stamped an already-closed block")

    if failures:
        print("FAIL — blocks can still be left open, or the answer is lost:\n")
        for f in failures:
            print("  •", f)
        print(f"\n{len(failures)} failing assertion(s) across {len(CASES)} cases.")
        return 1

    print(f"PASS — {len(CASES)} cases. No block left open, no answer lost, idempotent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
