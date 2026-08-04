#!/usr/bin/env python3
"""Reproduction fixture: reasoning blocks that never close and swallow the answer.

Symptom, reported 2026-08-03 before the Friday demo: a `<thinking>` block does
not always close, and when it does not, the model's ANSWER disappears into the
collapsed block. Nothing is lost server-side; it is simply never rendered as
text, so on screen the assistant appears to think and then say nothing.

Root cause: `tag_content_handler` in `sage_is_ai/utils/middleware.py` picks a
tag PAIR when the block opens, then closes the block only on that pair's exact
end tag. Any variation between the opening and closing tag is unrecoverable:

  * a different family     `<thinking>` opened, `</think>` emitted
  * different case         `</THINKING>`
  * stray whitespace       `</ thinking>`
  * no close at all        the model simply never emits one

There is no end-of-stream finalizer, so an unclosed block stays open forever.

This fixture does NOT import the app. It extracts the handler verbatim from
middleware.py by line range and runs it, so it keeps testing the real code
rather than a paraphrase of it. If the extraction fails, the line range moved
and the fixture says so instead of silently passing.

Usage:
    python3 scripts/smoke/reasoning-tag-fixture.py

Exit 0 when every case behaves; exit 1 when any case leaves a block unclosed.
Expect it to FAIL until the handler is fixed. That is the point.
"""

from __future__ import annotations

import pathlib
import re
import sys
import time  # noqa: F401 — the extracted handler calls time.time()

MIDDLEWARE = (
    pathlib.Path(__file__).resolve().parents[2]
    / "app/backend/sage_is_ai/utils/middleware.py"
)

REASONING_TAGS = [
    ("<think>", "</think>"),
    ("<thinking>", "</thinking>"),
    ("<reason>", "</reason>"),
    ("<reasoning>", "</reasoning>"),
    ("<thought>", "</thought>"),
    ("<Thought>", "</Thought>"),
    ("<|begin_of_thought|>", "<|end_of_thought|>"),
    ("◁think▷", "◁/think▷"),
]


def load_handler():
    """Pull `tag_content_handler` out of middleware.py and compile it alone."""
    src = MIDDLEWARE.read_text(encoding="utf-8").split("\n")
    start = next(
        (i for i, l in enumerate(src) if "def tag_content_handler(" in l), None
    )
    if start is None:
        sys.exit("fixture: tag_content_handler not found — it was renamed or moved")

    indent = len(src[start]) - len(src[start].lstrip())
    end = start + 1
    while end < len(src):
        line = src[end]
        if line.strip() and (len(line) - len(line.lstrip())) <= indent:
            break
        end += 1

    body = "\n".join(l[indent:] for l in src[start:end])
    scope: dict = {"re": re, "time": time}
    exec(compile(body, str(MIDDLEWARE), "exec"), scope)  # noqa: S102
    return scope["tag_content_handler"]


def stream(handler, full_text: str, chunk: int = 7):
    """Mirror the middleware's streaming loop, verbatim in shape.

    Kept identical to `middleware.py` around the `content = f"{content}{value}"`
    line: accumulate into `content`, guard the empty-blocks case, append the
    delta to the last block, then run the handler. Any divergence here reports
    fixture bugs as product bugs, which is worse than no fixture.
    """
    content = ""
    blocks: list[dict] = []
    for i in range(0, len(full_text), chunk):
        value = full_text[i : i + chunk]
        content = f"{content}{value}"
        if not blocks:
            blocks.append({"type": "text", "content": ""})
        blocks[-1]["content"] = blocks[-1]["content"] + value
        content, blocks, _ = handler("reasoning", REASONING_TAGS, content, blocks)
    return blocks


ANSWER = "The answer is 42."

# Every case that expects the answer must actually CONTAIN the answer, or the
# fixture reports its own test data as a product defect. Checked at startup.
#
# (name, streamed text, must the answer survive as visible text?)
CASES = [
    ("matched <think>", f"Hi. <think>weighing it</think> {ANSWER}", True),
    ("matched <thinking>", f"Hi. <thinking>weighing it</thinking> {ANSWER}", True),
    ("two blocks", f"<think>one</think> mid <think>two</think> {ANSWER}", True),
    ("opened <thinking>, closed </think>", f"<thinking>weighing it</think> {ANSWER}", True),
    ("opened <think>, closed </thinking>", f"<think>weighing it</thinking> {ANSWER}", True),
    ("uppercase close", f"<thinking>weighing it</THINKING> {ANSWER}", True),
    ("whitespace in close", f"<thinking>weighing it</ thinking> {ANSWER}", True),
    ("nested same tag", f"<think>outer <think>inner</think> more</think> {ANSWER}", True),
    ("never closed", "<thinking>weighing it and never finishing", False),
    # The one captured in the wild, 2026-08-03. The chat template pre-fills the
    # opening tag into the PROMPT, so the completion begins inside the thought
    # and the first tag in the stream is the closing one. DeepSeek R1 and its
    # distillations do this by default; the trailing token below is DeepSeek's
    # own EOS, which is how the family was identified.
    ("no opening tag (pre-filled)", f"weighing it</thinking> {ANSWER}", True),
    ("no opening tag, <think> form", f"weighing it</think> {ANSWER}", True),
]


def main() -> int:
    # Guard the fixture against itself first. A case that expects the answer
    # but never contains it fails forever and looks like a product bug.
    for name, text, expects in CASES:
        if expects and ANSWER not in text:
            sys.exit(f"fixture bug: case {name!r} expects the answer but omits it")

    handler = load_handler()
    failures = []

    for name, text, answer_expected in CASES:
        for chunk in (1, 7, 999):
            blocks = stream(handler, text, chunk)
            unclosed = [
                b for b in blocks if b["type"] == "reasoning" and "ended_at" not in b
            ]
            # Whitespace is normalised: chunking splits words across deltas, so
            # comparing raw spacing would fail on the harness rather than on the
            # product. The claim under test is "is the answer visible at all".
            visible = " ".join(
                "".join(b["content"] for b in blocks if b["type"] == "text").split()
            )

            # A closing tag rendered as literal prose means no block ever
            # opened. The reader sees the model's private reasoning and a raw
            # `</thinking>` in the answer. Checked before the others, because
            # the block count looks healthy while the output is wrong.
            leaked = [t for _, t in REASONING_TAGS if t in visible]
            if leaked:
                failures.append(
                    f"{name} (chunk={chunk}): {leaked[0]} rendered as literal text; "
                    f"reasoning leaked to the reader — {visible[:60]!r}"
                )
            elif unclosed:
                failures.append(
                    f"{name} (chunk={chunk}): reasoning block never closed; "
                    f"swallowed {unclosed[0]['content'][:60]!r}"
                )
            elif answer_expected and ANSWER not in visible:
                failures.append(
                    f"{name} (chunk={chunk}): answer not visible as text; "
                    f"got {visible[:60]!r}"
                )

    if failures:
        print("FAIL — reasoning tag handling loses the answer:\n")
        for f in failures:
            print("  •", f)
        print(f"\n{len(failures)} failing case(s).")
        return 1

    print(f"PASS — {len(CASES)} cases across 3 chunk sizes, no block left open.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
