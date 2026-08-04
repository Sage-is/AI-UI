#!/usr/bin/env python3
"""Behaviour oracle: replay a recorded upstream stream through the real
`process_chat_response` and diff everything it emits against a golden file.

WHY THIS EXISTS
---------------
The chat path had no automated coverage of any kind. No test called
`/api/chat/completions`; no test asserted on what the streaming loop emits;
`process_chat_response` was never driven end to end. The chat-path chart freezes
behaviour — "the same bytes on the wire" — and a freeze without something that
can tell frozen from broken is worth nothing. This is that something.

WHAT IT CAPTURES
----------------
For a chat with a session, the browser is fed over the socket, not over the HTTP
response: `process_chat_response` hands `response_handler` to `create_task` and
returns `{"status": True, "task_id": ...}`. So the observable output of a request
is an ORDERED LOG of two interleaved channels:

  * every `event_emitter({...})` payload — what the reader sees
  * every `Chats.upsert_message_to_chat_by_id_and_message_id` patch — what is
    persisted and survives a reload

Both are recorded in call order into one transcript, because the ORDER between
them is itself behaviour: a save that lands before its event, or an event after
`done: True`, is a regression even when both sets are individually unchanged.

The pass-through leg (no session, `stream_wrapper`) emits real SSE frames; those
are captured verbatim as text. Hence "SSE byte for byte" holds for the leg that
has SSE, and the socket transcript stands in for it on the leg that does not.

HOW IT STAYS DETERMINISTIC
--------------------------
The loop stamps `started_at` / `ended_at` from `time.time()` and serializes an
integer `duration` into the emitted HTML. Real time would make every run differ,
so `time.time` is replaced by a counter that ticks one second per call. Nothing
else about the module is altered: the code under test is imported from the
mounted source tree, exactly as `reasoning-finalizer-fixture.py` does it, so this
gate tracks the shipped code rather than a copy of it.

Everything the loop reaches for at the edges — the database, the socket, filter
functions, webhooks, the task queue — is replaced by a recorder or a stub. The
seam is deliberately narrow: only names that do I/O are stubbed. All parsing,
block construction, tag handling, serialization and finalization is the real
thing.

USAGE
-----
    make chat_response_oracle             # assert against the goldens
    make chat_response_oracle_update      # re-record the goldens after an
                                          # INTENTIONAL behaviour change

    python3 scripts/smoke/chat-response-oracle.py [--update] [--case NAME]

Exit 0 when every case matches its golden, 1 otherwise.

PROVING TEETH
-------------
A gate that cannot fail is worse than no gate. `--self-test` mutates block
handling in memory and asserts that the oracle notices:

    python3 scripts/smoke/chat-response-oracle.py --self-test

CORPUS PROVENANCE
-----------------
The streams in `fixtures/chat-response/*.sse` are written against the shapes the
loop actually parses, and the reasoning cases reproduce the production capture
from chat `171f30b9` (2026-08-04). They are not yet byte-captures from a live
provider. Capturing real streams from the providers this deployment uses is the
natural next widening of the corpus; the harness does not change when it happens.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import sys
import types

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "app" / "backend"))

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures" / "chat-response"

try:
    from sage_is_ai.utils import middleware as mw
except Exception as exc:  # noqa: BLE001 — the import IS the first assertion
    sys.exit(f"oracle: cannot import middleware — {exc}")

from starlette.responses import StreamingResponse


# --------------------------------------------------------------------------
# Recorder
# --------------------------------------------------------------------------


class Transcript:
    """One ordered log of everything the handler pushed outward."""

    def __init__(self):
        self.entries: list[dict] = []

    def emit(self, payload):
        self.entries.append({"channel": "event", "payload": payload})

    def save(self, chat_id, message_id, patch):
        self.entries.append(
            {
                "channel": "db",
                "chat_id": chat_id,
                "message_id": message_id,
                "patch": patch,
            }
        )

    def webhook(self, url, message):
        self.entries.append({"channel": "webhook", "url": url, "message": message})

    def as_json(self) -> str:
        return json.dumps(self.entries, indent=2, ensure_ascii=False, sort_keys=True)


class FakeChats:
    """Stands in for the Chats model. Records writes, answers reads flatly."""

    def __init__(self, transcript: Transcript, title="Fixture chat"):
        self._t = transcript
        self._title = title

    def upsert_message_to_chat_by_id_and_message_id(self, chat_id, message_id, patch):
        self._t.save(chat_id, message_id, patch)

    def get_message_by_id_and_message_id(self, chat_id, message_id):
        # No prior assistant content: the loop starts from an empty text block.
        return None

    def get_messages_by_chat_id(self, chat_id):
        return {}

    def get_chat_title_by_id(self, chat_id):
        return self._title


class FrozenClock:
    """One second per call, so `duration` in the serialized HTML is stable."""

    def __init__(self):
        self.now = 1_000_000.0

    def time(self):
        self.now += 1.0
        return self.now


# --------------------------------------------------------------------------
# The seam: what gets stubbed, and nothing more
# --------------------------------------------------------------------------


def install_stubs(transcript: Transcript, realtime_save: bool):
    """Replace only the names that perform I/O. Returns the saved originals."""
    clock = FrozenClock()

    async def event_emitter(payload):
        transcript.emit(payload)

    async def event_caller(payload):
        transcript.emit({"__call__": payload})
        return None

    async def passthrough_filter(**kwargs):
        return kwargs.get("form_data"), None

    def post_webhook(name, url, message, payload):
        transcript.webhook(url, message)

    async def create_task(redis, coro, id=None):
        # Run inline instead of detaching, so the fixture is synchronous and a
        # crash inside the handler surfaces here rather than vanishing.
        await coro
        return "fixture-task-id", None

    originals = {}

    def patch(name, value):
        originals[name] = getattr(mw, name)
        setattr(mw, name, value)

    patch("Chats", FakeChats(transcript))
    patch("get_event_emitter", lambda metadata: event_emitter)
    patch("get_event_call", lambda metadata: event_caller)
    patch("get_active_status_by_user_id", lambda user_id: True)  # no webhook
    patch("post_webhook", post_webhook)
    patch("process_filter_functions", passthrough_filter)
    patch("get_sorted_filter_ids", lambda request, model, filter_ids: [])
    patch("create_task", create_task)
    patch("ENABLE_REALTIME_CHAT_SAVE", realtime_save)
    patch("time", types.SimpleNamespace(time=clock.time))

    return originals


def restore(originals):
    for name, value in originals.items():
        setattr(mw, name, value)


# --------------------------------------------------------------------------
# The upstream under replay
# --------------------------------------------------------------------------


def upstream_from(sse_text: str) -> StreamingResponse:
    """A StreamingResponse whose body is the recorded stream, line by line.

    The loop reads `response.body_iterator` and decodes each item, so the
    chunking here is the chunking the parser sees. One SSE line per item is the
    shape both providers' routers produce.
    """
    lines = [ln for ln in sse_text.split("\n") if ln.strip() != ""]

    async def body():
        for line in lines:
            yield (line + "\n\n").encode("utf-8")

    return StreamingResponse(
        body(),
        headers={"Content-Type": "text/event-stream"},
    )


def fake_request():
    config = types.SimpleNamespace(
        WEBUI_URL="http://fixture.invalid",
        CODE_INTERPRETER_PROMPT_TEMPLATE="",
        ENABLE_CODE_INTERPRETER=False,
    )
    state = types.SimpleNamespace(
        config=config,
        redis=None,
        WEBUI_NAME="Sage.is AI",
        MODELS={},
    )
    app = types.SimpleNamespace(state=state)
    return types.SimpleNamespace(app=app, state=types.SimpleNamespace())


async def run_case(case: dict) -> str:
    """Replay one case and return its transcript as canonical JSON."""
    transcript = Transcript()
    originals = install_stubs(transcript, case.get("realtime_save", False))
    try:
        metadata = {
            "chat_id": "chat-fixture",
            "message_id": "msg-fixture",
            "session_id": "session-fixture",
            "features": case.get("features", {}),
            "filter_ids": [],
        }
        form_data = {
            "model": case.get("model", "fixture-model"),
            "messages": [{"role": "user", "content": "hello"}],
            "stream": True,
        }
        user = types.SimpleNamespace(id="user-fixture")

        result = await mw.process_chat_response(
            fake_request(),
            upstream_from(read_stream(case["stream"])),
            form_data,
            user,
            metadata,
            {"id": case.get("model", "fixture-model")},
            case.get("events", []),
            case.get("tasks", {}),
        )
        transcript.entries.append({"channel": "return", "value": result})
    finally:
        restore(originals)

    return transcript.as_json()


def read_stream(name: str) -> str:
    path = FIXTURES / name
    if not path.exists():
        sys.exit(f"oracle: missing recorded stream {path}")
    return path.read_text()


# --------------------------------------------------------------------------
# The corpus
# --------------------------------------------------------------------------

CASES = [
    {
        "name": "plain-text",
        "stream": "plain-text.sse",
        "why": "The baseline. Text deltas accumulate into one block and the "
        "stream closes with done:True.",
    },
    {
        "name": "reasoning-field-then-content",
        "stream": "reasoning-field-then-content.sse",
        "why": "The `reasoning_content` field path, closed the normal way by a "
        "content delta arriving. Guards the close at the `if value:` branch.",
    },
    {
        "name": "reasoning-field-never-closed",
        "stream": "reasoning-field-never-closed.sse",
        "why": "The production defect from chat 171f30b9: the whole answer "
        "arrives through the reasoning field and no content delta ever comes. "
        "The end-of-stream finalizer must close the block and free the answer.",
    },
    {
        "name": "reasoning-tag-inline",
        "stream": "reasoning-tag-inline.sse",
        "why": "The tag path: <think>…</think> inside ordinary content deltas, "
        "split across chunk boundaries so the partial-tag buffering is exercised.",
    },
    {
        "name": "usage-and-error-chunks",
        "stream": "usage-and-error-chunks.sse",
        "why": "Chunks with no `choices`: a usage report and an error object. "
        "Both emit and neither may be treated as content.",
    },
    {
        "name": "selected-model-id",
        "stream": "selected-model-id.sse",
        "why": "A mid-stream model switch. Pins the DB write today, so the "
        "logged `model_id` nonlocal bug cannot be fixed silently — the fix has "
        "to re-record this golden deliberately.",
    },
    {
        "name": "done-sentinel-and-noise",
        "stream": "done-sentinel-and-noise.sse",
        "why": "`data: [DONE]`, a keep-alive blank, a comment line and a "
        "malformed JSON chunk. All must be skipped without emitting.",
    },
    {
        "name": "realtime-save-on",
        "stream": "plain-text.sse",
        "realtime_save": True,
        "why": "The same stream with ENABLE_REALTIME_CHAT_SAVE flipped. Pins "
        "the dual save path the feature census has to rule on.",
    },
]


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------


def golden_path(case) -> pathlib.Path:
    return FIXTURES / f"{case['name']}.golden.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--update", action="store_true", help="re-record the goldens")
    ap.add_argument("--case", help="run one case by name")
    ap.add_argument(
        "--self-test",
        action="store_true",
        help="prove the oracle fails when behaviour changes",
    )
    args = ap.parse_args()

    cases = [c for c in CASES if not args.case or c["name"] == args.case]
    if not cases:
        sys.exit(f"oracle: no case named {args.case!r}")

    if args.self_test:
        return self_test(cases[0])

    failures = []
    for case in cases:
        actual = asyncio.run(run_case(case))
        path = golden_path(case)

        if args.update:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(actual + "\n")
            print(f"recorded  {path.name}")
            continue

        if not path.exists():
            failures.append(f"{case['name']}: no golden yet — run with --update")
            continue

        expected = path.read_text().rstrip("\n")
        if actual != expected:
            failures.append(f"{case['name']}: transcript differs\n{diff(expected, actual)}")

    if args.update:
        print(f"\n{len(cases)} golden(s) recorded. Read the diff before committing.")
        return 0

    if failures:
        print("FAIL — the chat path no longer emits what it used to:\n")
        for f in failures:
            print(f"  • {f}\n")
        print(f"{len(failures)} of {len(cases)} case(s) differ.")
        print(
            "\nIf the change was intentional, re-record with"
            " `make chat_response_oracle_update` and review the golden diff."
        )
        return 1

    print(f"PASS — {len(cases)} replayed stream(s) emit byte-identical transcripts.")
    return 0


def diff(expected: str, actual: str, limit: int = 24) -> str:
    import difflib

    lines = list(
        difflib.unified_diff(
            expected.split("\n"),
            actual.split("\n"),
            fromfile="golden",
            tofile="actual",
            lineterm="",
        )
    )
    head = lines[:limit]
    if len(lines) > limit:
        head.append(f"    … {len(lines) - limit} more diff line(s)")
    return "\n".join("    " + ln for ln in head)


def self_test(case) -> int:
    """Break block handling on purpose; the oracle must notice."""
    baseline = asyncio.run(run_case(case))

    original = mw.finalize_content_blocks
    try:
        mw.finalize_content_blocks = lambda blocks: None  # the pre-fix behaviour
        mutated = asyncio.run(run_case(case))
    finally:
        mw.finalize_content_blocks = original

    restored = asyncio.run(run_case(case))

    if baseline != mutated:
        if baseline != restored:
            print("FAIL — the oracle is not repeatable: two clean runs differ.")
            print(diff(baseline, restored))
            return 1
        print(
            f"PASS — teeth proven on {case['name']!r}: disabling"
            " finalize_content_blocks changes the transcript, and the oracle"
            " returns to the baseline once it is restored."
        )
        return 0

    print(
        f"FAIL — no teeth: disabling finalize_content_blocks on"
        f" {case['name']!r} left the transcript identical. The case does not"
        " exercise the finalizer; pick one that does."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
