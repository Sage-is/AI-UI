#!/usr/bin/env python3
"""Reproduction fixture: reasoning blocks that never close and swallow the answer.

Symptom, reported 2026-08-03 before the Friday demo: a `<thinking>` block does
not always close, and when it does not, the model's ANSWER disappears into the
collapsed block. Nothing is lost server-side; it is simply never rendered as
text, so on screen the assistant appears to think and then say nothing.

Root cause, first found: `tag_content_handler` in `sage_is_ai/utils/middleware.py`
closed a block only on the exact end tag of the pair that opened it, so any
variation between the opening and closing tag was unrecoverable:

  * a different family     `<thinking>` opened, `</think>` emitted
  * different case         `</THINKING>`
  * stray whitespace       `</ thinking>`
  * no opener at all       the chat template pre-filled it into the PROMPT
  * no close at all        the model simply never emits one

The handler now closes reasoning on any reasoning end tag, treats an orphan
close as an implicit opener (or drops it after a closed block), and the stream
ends through `finalize_content_blocks`, as the middleware does.

This imports the real handler and finalizer, run in the image like its sibling
`reasoning-finalizer-fixture.py`, so it tests the shipped code rather than a
paraphrase of it.

Usage:
    make reasoning_tag_fixture

Exit 0 when every case behaves; exit 1 when any case leaves a block unclosed,
leaks a tag, or loses the answer.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(
    0, str(pathlib.Path(__file__).resolve().parents[2] / "app" / "backend")
)

try:
    from sage_is_ai.utils.middleware import (
        finalize_content_blocks,
        tag_content_handler,
    )
except Exception as exc:  # noqa: BLE001 — the import IS the first assertion
    sys.exit(f"fixture: cannot import the reasoning handlers — {exc}")

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


def stream(full_text: str, chunk: int = 7, blocks: list[dict] | None = None):
    """Mirror the middleware's streaming loop, verbatim in shape.

    Kept identical to `middleware.py` around the `content = f"{content}{value}"`
    line: accumulate into `content`, guard the empty-blocks case, append the
    delta to the last block, then run the handler, and finalize at the end.
    `blocks` seeds what came before, such as a field-path block already closed.
    Any divergence here reports fixture bugs as product bugs, which is worse
    than no fixture.
    """
    content = ""
    blocks = [dict(b) for b in blocks or []]
    for i in range(0, len(full_text), chunk):
        value = full_text[i : i + chunk]
        content = f"{content}{value}"
        if not blocks:
            blocks.append({"type": "text", "content": ""})
        blocks[-1]["content"] = blocks[-1]["content"] + value
        content, blocks, _ = tag_content_handler(
            "reasoning", REASONING_TAGS, content, blocks
        )
    return finalize_content_blocks(blocks)


ANSWER = "The answer is 42."

# Every case that expects the answer must actually CONTAIN the answer, or the
# fixture reports its own test data as a product defect. Checked at startup.
#
# (name, streamed text, must the answer survive as visible text?, options)
# Options: `seed` blocks already in the message, `literal` text that must stay
# visible (a tag the model writes about), `reasoning` text that must survive
# inside the reasoning block.
FIELD_CLOSED = [
    {
        "type": "reasoning",
        "start_tag": "think",
        "end_tag": "/think",
        "attributes": {"type": "reasoning_content"},
        "content": "The user wants summary statistics.",
        "started_at": 1000.0,
        "ended_at": 1001.0,
        "duration": 1,
    },
    {"type": "text", "content": ""},
]

CASES = [
    ("matched <think>", f"Hi. <think>weighing it</think> {ANSWER}", True, {}),
    ("matched <thinking>", f"Hi. <thinking>weighing it</thinking> {ANSWER}", True, {}),
    ("two blocks", f"<think>one</think> mid <think>two</think> {ANSWER}", True, {}),
    ("opened <thinking>, closed </think>", f"<thinking>weighing it</think> {ANSWER}", True, {}),
    ("opened <think>, closed </thinking>", f"<think>weighing it</thinking> {ANSWER}", True, {}),
    ("uppercase close", f"<thinking>weighing it</THINKING> {ANSWER}", True, {}),
    ("whitespace in close", f"<thinking>weighing it</ thinking> {ANSWER}", True, {}),
    ("nested same tag", f"<think>outer <think>inner</think> more</think> {ANSWER}", True, {}),
    # Kimi's tag is not shaped <...>; its pattern once had no capture group and
    # every later delta raised IndexError before the emit (found 2026-08-08).
    ("kimi ◁think▷", f"◁think▷weighing it◁/think▷ {ANSWER}", True, {}),
    ("never closed", "<thinking>weighing it and never finishing", False, {}),
    # The one captured in the wild, 2026-08-03. The chat template pre-fills the
    # opening tag into the PROMPT, so the completion begins inside the thought
    # and the first tag in the stream is the closing one. DeepSeek R1 and its
    # distillations do this by default.
    ("no opening tag (pre-filled)", f"weighing it</thinking> {ANSWER}", True, {}),
    ("no opening tag, <think> form", f"weighing it</think> {ANSWER}", True, {}),
    # Variant 3, 2026-08-06 (qwen3.5:9b via Ollama): the field path closed the
    # block, then a bare close arrived as content. Drop it; mint no second block.
    (
        "orphan close after a closed block",
        f"</think>\n\n{ANSWER}",
        True,
        {"seed": FIELD_CLOSED, "max_reasoning": 1},
    ),
    # The model writing ABOUT the tag. Nothing opens; the tag stays visible.
    (
        "close tag inside a code fence",
        f"Close it like this:\n```\n</think>\n```\n{ANSWER}",
        True,
        {"literal": "</think>", "max_reasoning": 0},
    ),
    # A literal `<<think>x>` span inside the reasoning. The old start-tag strip
    # deleted it silently.
    (
        "literal <<think>x> span",
        f"<think>compare <<think>x> spans</think> {ANSWER}",
        True,
        {"reasoning": "<<think>x>"},
    ),
]


def main() -> int:
    # Guard the fixture against itself first. A case that expects the answer
    # but never contains it fails forever and looks like a product bug.
    for name, text, expects, _ in CASES:
        if expects and ANSWER not in text:
            sys.exit(f"fixture bug: case {name!r} expects the answer but omits it")

    failures = []

    for name, text, answer_expected, opts in CASES:
        for chunk in (1, 7, 999):
            blocks = stream(text, chunk, opts.get("seed"))
            reasoning = [b for b in blocks if b["type"] == "reasoning"]
            unclosed = [b for b in reasoning if "ended_at" not in b]
            # Whitespace is normalised: chunking splits words across deltas, so
            # comparing raw spacing would fail on the harness rather than on the
            # product. The claim under test is "is the answer visible at all".
            # Words glued together ("Theanswer") still fail, which is the point.
            visible = " ".join(
                "".join(b["content"] for b in blocks if b["type"] == "text").split()
            )
            literal = opts.get("literal")

            # A closing tag rendered as literal prose means no block ever
            # opened. The reader sees the model's private reasoning and a raw
            # `</thinking>` in the answer. Checked before the others, because
            # the block count looks healthy while the output is wrong.
            leaked = [
                t
                for _, t in REASONING_TAGS
                if t in visible.replace(literal or "\0", "", 1)
            ]
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
            elif literal and literal not in visible:
                failures.append(
                    f"{name} (chunk={chunk}): {literal!r} the model wrote as text "
                    f"was swallowed — {visible[:60]!r}"
                )
            elif "max_reasoning" in opts and len(reasoning) > opts["max_reasoning"]:
                failures.append(
                    f"{name} (chunk={chunk}): {len(reasoning)} reasoning blocks, "
                    f"expected at most {opts['max_reasoning']}"
                )
            elif opts.get("reasoning") and not any(
                opts["reasoning"] in b["content"] for b in reasoning
            ):
                failures.append(
                    f"{name} (chunk={chunk}): {opts['reasoning']!r} deleted from "
                    f"the reasoning — {[b['content'][:60] for b in reasoning]!r}"
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
