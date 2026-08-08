#!/usr/bin/env python3
"""Gate: streamed tool-call deltas accumulate into complete calls.

First test of tool-call accumulation in this codebase. No oracle golden
carries a `tool_calls` delta, so until this fixture the accumulator ran in
no test of any kind.

Pins the behaviours a tidy-up would silently change:

  • Fragmented arguments join in arrival order across deltas sharing an index.
  • An unseen index starts a new call; `setdefault` fills a missing `function`.
  • A delta with index None is dropped entirely.
  • The delta dict itself is appended (mutation is shared with the parsed
    chunk) — the accumulator must NOT copy it.

Usage:
    make tool_call_accumulator_fixture
    python3 scripts/smoke/tool-call-accumulator-fixture.py

Exit 0 when every case holds, 1 otherwise.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(
    0, str(pathlib.Path(__file__).resolve().parents[2] / "app" / "backend")
)

try:
    from sage_is_ai.utils.middleware import accumulate_tool_call_deltas
except Exception as exc:  # noqa: BLE001 — the import IS the first assertion
    sys.exit(f"fixture: cannot import accumulate_tool_call_deltas — {exc}")


def d(index, name=None, arguments=None, **extra):
    """One streamed delta, shaped as providers send them."""
    out = {"index": index, **extra}
    fn = {}
    if name is not None:
        fn["name"] = name
    if arguments is not None:
        fn["arguments"] = arguments
    if fn:
        out["function"] = fn
    return out


def main() -> int:
    failures = []

    def check(name, cond, detail=""):
        if not cond:
            failures.append(f"{name}: {detail}")

    # one delta, one call
    acc = []
    accumulate_tool_call_deltas(acc, [d(0, "get_weather", '{"city":')])
    check("single", len(acc) == 1 and acc[0]["function"]["name"] == "get_weather",
          f"got {acc!r}")

    # arguments arrive in three fragments, joined in order
    acc = []
    for frag in ['{"city":', '"Paris"', "}"]:
        accumulate_tool_call_deltas(acc, [d(0, arguments=frag)])
    check("fragmented-args", acc[0]["function"]["arguments"] == '{"city":"Paris"}',
          f"got {acc[0]['function']['arguments']!r}")

    # name arrives first, arguments later, same index
    acc = []
    accumulate_tool_call_deltas(acc, [d(0, "search")])
    accumulate_tool_call_deltas(acc, [d(0, arguments='{"q":"x"}')])
    check("name-then-args",
          acc[0]["function"] == {"name": "search", "arguments": '{"q":"x"}'},
          f"got {acc[0]['function']!r}")

    # two indexes come back as two calls
    acc = []
    accumulate_tool_call_deltas(acc, [d(0, "a", ""), d(1, "b", "")])
    accumulate_tool_call_deltas(acc, [d(1, arguments="1")])
    check("two-calls", len(acc) == 2 and acc[1]["function"]["arguments"] == "1",
          f"got {acc!r}")

    # index None is dropped
    acc = []
    accumulate_tool_call_deltas(acc, [{"function": {"name": "ghost"}}])
    accumulate_tool_call_deltas(acc, [d(None, "ghost2")])
    check("index-none-dropped", acc == [], f"got {acc!r}")

    # a delta with no function key is filled by setdefault
    acc = []
    accumulate_tool_call_deltas(acc, [{"index": 0, "id": "call_1"}])
    check("setdefault-fills",
          acc[0]["function"] == {"name": "", "arguments": ""},
          f"got {acc[0]!r}")

    # empty delta list is a no-op
    acc = [d(0, "keep", "{}")]
    accumulate_tool_call_deltas(acc, [])
    check("empty-noop", len(acc) == 1 and acc[0]["function"]["name"] == "keep",
          f"got {acc!r}")

    # the FIRST delta dict itself is appended — mutation stays shared
    first = d(0, "shared", "")
    acc = []
    accumulate_tool_call_deltas(acc, [first])
    check("shared-object", acc[0] is first,
          "accumulator copied the delta; the parsed chunk no longer shares it")

    # extra keys on the first delta (id, type) survive into the accumulator
    acc = []
    accumulate_tool_call_deltas(acc, [d(0, "x", "", id="call_9", type="function")])
    check("extra-keys-survive", acc[0].get("id") == "call_9", f"got {acc[0]!r}")

    if failures:
        print("FAIL — tool-call deltas no longer accumulate correctly:\n")
        for f in failures:
            print("  •", f)
        print(f"\n{len(failures)} failing assertion(s).")
        return 1

    print("PASS — 9 cases. Deltas merge by index, order preserved, mutation shared.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
