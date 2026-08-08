#!/usr/bin/env python3
"""Gate: the block renderer emits byte-identical output for every block shape.

Why this exists: the 12 chat-response oracle goldens never execute two whole
regions of `serialize_content_blocks`. No golden carries a `tool_calls` delta,
so the tool_calls branch is dark. No golden sets `features.code_interpreter`,
so the single `raw=True` call site (the code-interpreter continuation) never
runs — the entire raw axis is dark. This fixture is the only cover either
region has ever had.

It also pins two behaviours a tidy-up would silently change, and one bug:

  • Duplicate `tool_call_id` in results: the FIRST match wins (linear scan
    with break). A dict-keyed lookup would keep the last.
  • A result whose content is falsy ("" or None) renders as "Executing..." —
    the guard is truthiness, not `is not None`.
  • Under raw=True a tool_calls block renders as NOTHING — `_render_tool_calls`
    returns the accumulator untouched before building anything (historically:
    both arms guarded their append with `if not raw:`). This is the raw
    tool-call hole in the bug ledger. The golden freezes the hole ON PURPOSE:
    it goes red the day the fix lands, which is how we know the fix worked.
  • An unrecognised block type — even an unhashable one — renders via the
    fallback branch, never raises.

Every case runs at raw=False and raw=True. Output is compared byte-for-byte
against fixtures/serialize-blocks/cases.golden.json.

Usage:
    make serialize_blocks_fixture
    python3 scripts/smoke/serialize-blocks-fixture.py            # compare
    python3 scripts/smoke/serialize-blocks-fixture.py --update   # re-record
    python3 scripts/smoke/serialize-blocks-fixture.py --teeth    # self-test

Exit 0 when every output matches the golden, 1 otherwise.
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(
    0, str(pathlib.Path(__file__).resolve().parents[2] / "app" / "backend")
)

try:
    from sage_is_ai.utils import middleware as mw
except Exception as exc:  # noqa: BLE001 — the import IS the first assertion
    sys.exit(f"fixture: cannot import middleware — {exc}")

GOLDEN = pathlib.Path(__file__).parent / "fixtures" / "serialize-blocks" / "cases.golden.json"


def tc(id_, name="get_weather", args='{"city":"Paris"}'):
    return {"id": id_, "function": {"name": name, "arguments": args}}


# (name, blocks) — shapes the streaming loop actually builds, plus the edges
# it could build. Comments mark the trap each case pins.
CASES = [
    # --- text ---------------------------------------------------------------
    ("text-plain", [{"type": "text", "content": "Hello."}]),
    ("text-whitespace", [{"type": "text", "content": "  padded  \n\n"}]),
    ("text-empty", [{"type": "text", "content": ""}]),
    # --- tool_calls: dark in every oracle golden ----------------------------
    ("tc-no-results", [{"type": "tool_calls", "content": [tc("a1")]}]),
    ("tc-matched", [{
        "type": "tool_calls", "content": [tc("a1")],
        "results": [{"tool_call_id": "a1", "content": "18C and clear"}]}]),
    ("tc-unmatched-id", [{
        "type": "tool_calls", "content": [tc("a1")],
        "results": [{"tool_call_id": "SOMETHING-ELSE", "content": "orphan"}]}]),
    ("tc-falsy-content", [{  # truthiness guard: renders as Executing...
        "type": "tool_calls", "content": [tc("a1")],
        "results": [{"tool_call_id": "a1", "content": ""}]}]),
    ("tc-duplicate-ids", [{  # linear scan with break: FIRST match wins
        "type": "tool_calls", "content": [tc("a1")],
        "results": [
            {"tool_call_id": "a1", "content": "FIRST"},
            {"tool_call_id": "a1", "content": "SECOND"}]}]),
    ("tc-with-files", [{
        "type": "tool_calls", "content": [tc("a1")],
        "results": [{"tool_call_id": "a1", "content": "done",
                     "files": [{"url": "/f/1", "name": "x.png"}]}]}]),
    ("tc-two-calls-one-result", [{
        "type": "tool_calls",
        "content": [tc("a1"), tc("b2", "search", '{"q":"x"}')],
        "results": [{"tool_call_id": "b2", "content": "hit"}]}]),
    ("tc-empty-results-list", [  # [] took the else arm; both arms emit the same bytes
        {"type": "tool_calls", "content": [tc("a1")], "results": []}]),
    ("tc-unicode-and-quotes", [{  # pins ensure_ascii=False on the result dump
        "type": "tool_calls",
        "content": [tc("a1", "echo", '{"s":"a\\"b <tag> & é"}')],
        "results": [{"tool_call_id": "a1", "content": 'quote " and <b> é'}]}]),
    # --- reasoning ----------------------------------------------------------
    ("reason-with-duration", [{
        "type": "reasoning", "start_tag": "<think>", "end_tag": "</think>",
        "content": "step one\nstep two", "duration": 3}]),
    ("reason-no-duration", [{
        "type": "reasoning", "start_tag": "<think>", "end_tag": "</think>",
        "content": "still going"}]),
    ("reason-already-quoted", [{
        "type": "reasoning", "start_tag": "<think>", "end_tag": "</think>",
        "content": "> already a quote\nplain line", "duration": 1}]),
    ("reason-duration-zero", [{  # `is not None`: zero must take the done=true arm
        "type": "reasoning", "start_tag": "<think>", "end_tag": "</think>",
        "content": "fast", "duration": 0}]),
    ("reason-field-opened", [{  # field path: bare "think", not "<think>"
        "type": "reasoning", "start_tag": "think", "end_tag": "/think",
        "attributes": {"type": "reasoning_content"},
        "content": "from the field path", "duration": 2}]),
    # --- code_interpreter ---------------------------------------------------
    ("ci-with-output", [{
        "type": "code_interpreter", "attributes": {"lang": "python"},
        "content": "print(1)", "output": "1\n"}]),
    ("ci-no-output", [{
        "type": "code_interpreter", "attributes": {"lang": "python"},
        "content": "print(1)"}]),
    ("ci-after-opening-fence", [  # fence repair must strip the opening backticks
        {"type": "text", "content": "Here is code:\n```"},
        {"type": "code_interpreter", "attributes": {"lang": "python"},
         "content": "x=1", "output": ""}]),
    ("ci-after-closing-fence", [  # balanced fences must be left alone
        {"type": "text", "content": "a\n```\nb\n```"},
        {"type": "code_interpreter", "attributes": {"lang": "python"},
         "content": "x=1", "output": "ok"}]),
    ("ci-no-lang", [{
        "type": "code_interpreter", "attributes": {},
        "content": "echo hi", "output": "hi"}]),
    # --- fallback + composition --------------------------------------------
    ("unknown-type", [{"type": "solution", "content": "the answer is 42"}]),
    ("unhashable-type", [{"type": ["x"], "content": "c"}]),  # fallback, no raise
    ("mixed-full-message", [
        {"type": "text", "content": "Let me think."},
        {"type": "reasoning", "start_tag": "<think>", "end_tag": "</think>",
         "content": "hmm", "duration": 2},
        {"type": "tool_calls", "content": [tc("a1")],
         "results": [{"tool_call_id": "a1", "content": "18C"}]},
        {"type": "code_interpreter", "attributes": {"lang": "python"},
         "content": "x=1", "output": "1"},
        {"type": "text", "content": "Done."}]),
    ("empty-list", []),
]


def run() -> dict[str, str]:
    """Every case at raw=False and raw=True, in declaration order."""
    out = {}
    for name, blocks in CASES:
        for raw in (False, True):
            # deep-copy per run: the code_interpreter branch reads the growing
            # accumulator, and a shared list would let one run taint the next
            fresh = json.loads(json.dumps(blocks))
            out[f"{name}::raw={raw}"] = mw.serialize_content_blocks(fresh, raw=raw)
    return out


def teeth() -> int:
    """Prove the net can catch: disable the renderer in memory, expect a diff."""
    golden = json.loads(GOLDEN.read_text())
    original = mw.serialize_content_blocks
    try:
        mw.serialize_content_blocks = lambda blocks, raw=False: "TEETH"
        broken = run()
    finally:
        mw.serialize_content_blocks = original
    if broken == golden:
        print("FAIL — renderer disabled yet output matched the golden; the net is dead")
        return 1
    if run() != golden:
        print("FAIL — restored renderer no longer matches the golden")
        return 1
    print("PASS — teeth: a broken renderer diffs, the restored one matches.")
    return 0


def main() -> int:
    if "--teeth" in sys.argv:
        return teeth()

    got = run()

    if "--update" in sys.argv:
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(json.dumps(got, indent=1, ensure_ascii=False) + "\n")
        print(f"recorded {len(got)} outputs ({len(CASES)} cases x 2 raw modes)")
        return 0

    if not GOLDEN.exists():
        sys.exit(f"fixture: golden missing — run with --update first ({GOLDEN})")

    golden = json.loads(GOLDEN.read_text())
    diffs = [k for k in golden if got.get(k) != golden[k]]
    diffs += [k for k in got if k not in golden]

    if diffs:
        print("FAIL — renderer output drifted from the golden:\n")
        for k in diffs[:10]:
            print(f"  • {k}")
            print(f"      golden: {golden.get(k)!r:.120}")
            print(f"      got:    {got.get(k)!r:.120}")
        print(f"\n{len(diffs)} of {len(golden)} outputs differ.")
        return 1

    print(f"PASS — {len(golden)} outputs byte-identical ({len(CASES)} cases x 2 raw modes).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
