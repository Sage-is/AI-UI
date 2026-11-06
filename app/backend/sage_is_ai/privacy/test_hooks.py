"""Each admin off-switch stops the filter (ON by default from 3.2.0).
Host-only: the one DB import is stubbed; active_for never reads the map."""

import asyncio
import json
import re
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace

try:
    import sage_is_ai.models.privacy  # noqa: F401
except ImportError:
    sys.modules["sage_is_ai.models.privacy"] = types.ModuleType("stub")
    sys.modules["sage_is_ai.models.privacy"].PrivacyMaps = object

from sage_is_ai.privacy import hooks  # noqa: E402

EXT = {"id": "deepseek/x", "urlIdx": 0, "owned_by": "openai"}


def req(saved=None):
    cfg = SimpleNamespace(PRIVACY_CONFIG=saved)
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(config=cfg)))


def on(saved=None, model=EXT):
    return hooks.active_for(req(saved), model)


class OffSwitches(unittest.TestCase):
    def test_external_is_filtered_when_nobody_chose(self):
        self.assertTrue(on())

    def test_local_is_never_filtered_by_default(self):
        self.assertFalse(on(model={"id": "llama3", "owned_by": "ollama"}))

    def test_whole_instance_off(self):
        self.assertFalse(on({"enabled": False, "connections": {"0": True}}))

    def test_default_off_also_covers_a_saved_pre_3_2_config(self):
        self.assertFalse(on({"default_external": False}))

    def test_one_connection_off(self):
        self.assertFalse(on({"connections": {"0": False}}))

    def test_one_connection_on_when_default_off(self):
        self.assertTrue(on({"default_external": False, "connections": {"0": True}}))

    def test_an_admin_can_filter_a_local_connection(self):
        local = {**EXT, "connection_type": "local"}
        self.assertFalse(on(model=local))
        self.assertTrue(on({"connections": {"0": True}}, model=local))

    def test_config_py_and_hooks_defaults_agree(self):
        src = (Path(__file__).resolve().parents[1] / "config.py").read_text()
        m = re.search(
            r'"default_external":\s*(True|False)', src[src.index('"privacy.config"') :]
        )
        self.assertEqual(m.group(1) == "True", hooks.DEFAULTS["default_external"])


class ConnectionKinds(unittest.TestCase):
    """Ollama, OpenAI-style and a person's own direct connections each count from
    0, so each kind keeps its own panel key (2026-11-03)."""

    OLLAMA = {"id": "llama3", "owned_by": "ollama", "connection_type": "local", "ollama": {"urls": [1]}}
    DIRECT = {"id": "mine/x", "urlIdx": 0, "owned_by": "openai", "direct": True}

    def test_an_ollama_its_admin_marks_external_is_filtered(self):
        self.assertTrue(on(model={**self.OLLAMA, "connection_type": "external"}))

    def test_an_ollama_connection_has_its_own_switch(self):
        self.assertTrue(on({"connections": {"ollama:1": True}}, model=self.OLLAMA))
        self.assertFalse(on({"connections": {"1": True, "ollama:0": True}}, model=self.OLLAMA))

    def test_a_direct_connection_never_takes_an_admin_connections_flag(self):
        self.assertTrue(on({"connections": {"0": False}}, model=self.DIRECT))
        self.assertFalse(on({"connections": {"direct": False}}, model=self.DIRECT))

    def test_arena_and_pipes_are_never_filtered_by_a_connection(self):
        for model in ({"id": "a", "owned_by": "arena"}, {"id": "p", "pipe": {"type": "pipe"}}):
            self.assertFalse(on({"connections": {"0": True}}, model=model))


class PassThroughPath(unittest.TestCase):
    """Privacy off for a request: the chat path's calls change nothing."""

    def test_reverser_is_a_no_op(self):
        r = hooks.stream_reverser_for(SimpleNamespace(state=SimpleNamespace()))
        self.assertEqual(
            (r.feed("x"), r.feed(None), r.flush(), r.active), ("x", None, "", False)
        )

    def test_finish_leaves_tool_calls_alone(self):
        calls = [{"function": {"arguments": "p1234abcd@example.invalid"}}]
        tail = hooks.finish_stream(hooks.PassThrough(), calls)
        self.assertEqual(
            (tail, calls[0]["function"]["arguments"]), ("", "p1234abcd@example.invalid")
        )

    def test_sse_lines_come_back_untouched(self):
        lines = object()
        self.assertIs(
            hooks.reverse_sse_for(SimpleNamespace(state=SimpleNamespace()), lines),
            lines,
        )


class PerRequestTable(unittest.TestCase):
    """F0: a reply reverses only the stand-ins its own request sent, tool
    arguments go out pseudonymized, and a late system prompt joins the table."""

    def setUp(self):
        from sage_is_ai.privacy.engine import MemoryMapper

        self.shared = MemoryMapper("test-key")  # one box: the same mapper for every request
        self._mapper, hooks.mapper = hooks.mapper, lambda: self.shared

    def tearDown(self):
        hooks.mapper = self._mapper

    def _request(self):
        return SimpleNamespace(
            app=SimpleNamespace(state=SimpleNamespace(config=SimpleNamespace(PRIVACY_CONFIG=None))),
            state=SimpleNamespace(),
        )

    def _send(self, text):
        request = self._request()
        form = hooks.outbound(request, {"messages": [{"role": "user", "content": text}]})
        return request, form["messages"][0]["content"]

    def test_a_reply_reverses_only_what_its_request_sent(self):
        first, sent_first = self._send("write to ada.first@example.com")
        second, sent_second = self._send("write to bob.second@example.com")
        fake_first = [f for f in hooks.table_for(first) if "example.com" not in f][0]
        self.assertNotIn("ada.first", sent_first)
        self.assertIn(fake_first, sent_first)
        # The model answering the second request echoes a stand-in from the first.
        reply = {"choices": [{"message": {"content": f"ok: {fake_first}"}}]}
        hooks.reverse_completion(reply, hooks.table_for(second))
        self.assertEqual(reply["choices"][0]["message"]["content"], f"ok: {fake_first}")
        hooks.reverse_completion(reply, hooks.table_for(first))
        self.assertEqual(reply["choices"][0]["message"]["content"], "ok: ada.first@example.com")

    def test_tool_call_arguments_go_out_pseudonymized(self):
        request = self._request()
        form = hooks.outbound(request, {"messages": [
            {"role": "user", "content": "mail carol.tool@example.com"},
            {"role": "assistant", "content": None, "tool_calls": [
                {"id": "c1", "type": "function",
                 "function": {"name": "send", "arguments": '{"to": "carol.tool@example.com"}'}}]},
        ]})
        arguments = form["messages"][1]["tool_calls"][0]["function"]["arguments"]
        self.assertNotIn("carol.tool", arguments)
        fake = [f for f in hooks.table_for(request)][0]
        self.assertIn(fake, arguments)
        self.assertEqual(hooks.table_for(request)[fake], "carol.tool@example.com")

    def test_object_tool_arguments_go_out_pseudonymized_and_come_back(self):
        # Some providers send arguments as a parsed object, not a JSON string.
        args = {"to": "frank.obj@example.com", "cc": ["gail.obj@example.com"], "n": 2}
        request = self._request()
        form = hooks.outbound(request, {"messages": [
            {"role": "user", "content": "mail frank.obj@example.com"},
            {"role": "assistant", "content": None, "tool_calls": [
                {"id": "c2", "type": "function",
                 "function": {"name": "send", "arguments": dict(args)}}]},
        ]})
        sent = form["messages"][1]["tool_calls"][0]["function"]["arguments"]
        self.assertNotIn("frank.obj", str(sent))
        self.assertNotIn("gail.obj", str(sent))
        self.assertEqual((sorted(sent), sent["n"]), (["cc", "n", "to"], 2))
        # The model calls the tool with the stand-ins; the tool must see real values.
        reply = {"choices": [{"message": {"content": None, "tool_calls": [
            {"function": {"name": "send", "arguments": sent}}]}}]}
        hooks.reverse_completion(reply, hooks.table_for(request))
        self.assertEqual(reply["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"], args)

    def test_a_tool_round_keeps_a_non_ascii_name_out_and_the_block_real(self):
        # The middleware re-dumps arguments with json.dumps, which writes the
        # non-ASCII name as an escape sequence, so a match on the raw text would
        # miss it. The result names both values; the content block's own list
        # must stay real.
        real = {"to": "Renée Tool", "email": "renee.tool@example.com"}
        block = [{"id": "c3", "type": "function",
                  "function": {"name": "send", "arguments": json.dumps(real)}}]
        form = hooks.outbound(self._request(), {
            "metadata": {"privacy": {"known": [{"kind": "name", "value": "Renée Tool"}]}},
            "messages": [
                {"role": "user", "content": "mail Renée Tool"},
                {"role": "assistant", "content": "", "tool_calls": block},
                {"role": "tool", "content": "sent to Renée Tool at renee.tool@example.com"},
            ]})
        sent = json.loads(form["messages"][1]["tool_calls"][0]["function"]["arguments"])
        for text in (sent["to"], sent["email"], form["messages"][2]["content"]):
            self.assertNotIn("Renée", text)
            self.assertNotIn("renee.tool", text)
        self.assertEqual(json.loads(block[0]["function"]["arguments"]), real)

    def test_a_tool_gets_real_values_only_where_it_declares_a_parameter(self):
        # The model may put a stand-in anywhere; the real value reaches only a
        # parameter the called tool declares. Both reverse paths ask the same rule.
        request = self._request()
        hooks.outbound(request, {
            "tools": [{"type": "function", "function": {
                "name": "send", "parameters": {"properties": {"to": {"type": "string"}}}}}],
            "messages": [{"role": "user", "content": "mail hana.decl@example.com"}]})
        (fake,) = hooks.table_for(request)
        real = "hana.decl@example.com"

        def call(name):
            return {"function": {"name": name, "arguments": json.dumps({"to": fake, "smuggled": fake})}}

        reply = {"choices": [{"message": {"content": None, "tool_calls": [call("send"), call("undeclared")]}}]}
        hooks.reverse_completion(reply, hooks.table_for(request), hooks.tool_params_for(request))
        send, other = (json.loads(c["function"]["arguments"]) for c in reply["choices"][0]["message"]["tool_calls"])
        self.assertEqual(send, {"to": real, "smuggled": fake})
        self.assertEqual(other, {"to": fake, "smuggled": fake})
        request.state.privacy_active = True
        streamed = [call("send")]
        hooks.finish_stream(hooks.stream_reverser_for(request), streamed)
        self.assertEqual(json.loads(streamed[0]["function"]["arguments"]), {"to": real, "smuggled": fake})

    def test_a_late_system_prompt_uses_the_request_mapper(self):
        request, _ = self._send("hello from dan.late@example.com")
        form = hooks.outbound_system(request, {"messages": [
            {"role": "system", "content": "The user is dan.late@example.com"},
            {"role": "user", "content": "hi"}]})
        system = form["messages"][0]["content"]
        self.assertNotIn("dan.late", system)
        (fake,) = hooks.table_for(request)
        self.assertIn(fake, system)

    def test_outbound_system_is_a_no_op_without_outbound(self):
        form = {"messages": [{"role": "system", "content": "erin.none@example.com"}]}
        self.assertEqual(hooks.outbound_system(self._request(), form), form)


class StreamedToolCalls(unittest.TestCase):
    """The streamed API pass-through puts real values back into tool-call
    arguments, even when a stand-in straddles two deltas."""

    FAKE, REAL = "p1234abcd@example.invalid", "ada@example.com"

    def _stream(self, events, tool_params=None):
        async def lines():
            for event in events:
                yield f"data: {event if isinstance(event, str) else json.dumps(event)}\n\n".encode()

        async def collect():
            return [line.decode() async for line in hooks.reverse_sse(lines(), {self.FAKE: self.REAL}, tool_params)]

        return [line[len("data: "):].strip() for line in asyncio.run(collect())]

    @staticmethod
    def _delta(arguments, **function):
        call = {"index": 0, "function": {"arguments": arguments, **function}}
        return {"choices": [{"index": 0, "delta": {"tool_calls": [call]}}]}

    @staticmethod
    def _arguments(bodies):
        """What a client gets by appending every argument fragment, as OpenAI's SDKs do."""
        events = [json.loads(b) for b in bodies if b != "[DONE]"]
        return "".join(
            call["function"]["arguments"]
            for event in events for choice in event["choices"]
            for call in choice["delta"].get("tool_calls") or []
        )

    def test_a_split_stand_in_comes_back_real_at_finish(self):
        bodies = self._stream([
            self._delta('{"to": "p1234ab', name="send"),
            self._delta('cd@example.invalid", "note": "p1234abcd@example.invalid"}'),
            {"choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}]},
            "[DONE]",
        ], {"send": frozenset({"to"})})
        self.assertEqual(json.loads(bodies[0])["choices"][0]["delta"]["tool_calls"][0]["function"]["name"], "send")
        # Undeclared `note` keeps its stand-in, as on the non-streamed path.
        self.assertEqual(json.loads(self._arguments(bodies)), {"to": self.REAL, "note": self.FAKE})
        self.assertEqual(bodies[-1], "[DONE]")

    def test_calls_without_a_finish_reason_come_back_before_done(self):
        bodies = self._stream([self._delta(json.dumps({"to": self.FAKE}), name="send"), "[DONE]"])
        self.assertEqual(json.loads(self._arguments(bodies)), {"to": self.REAL})
        self.assertEqual(bodies[-1], "[DONE]")


class Reasoning(unittest.TestCase):
    """A model's thinking is shown to the reader too, so it comes back real:
    streamed, through its own hold-back buffer, and whole (2026-11-03)."""

    FAKE, REAL = StreamedToolCalls.FAKE, StreamedToolCalls.REAL
    _stream = StreamedToolCalls._stream

    def test_a_split_stand_in_in_streamed_reasoning_comes_back_real(self):
        half = len(self.FAKE) // 2
        bodies = self._stream([
            {"choices": [{"index": 0, "delta": {"reasoning_content": f"Write to {self.FAKE[:half]}"}}]},
            {"choices": [{"index": 0, "delta": {"reasoning_content": self.FAKE[half:]}}]},
            {"choices": [{"index": 0, "delta": {"content": "Done."}}]},
            "[DONE]",
        ])
        events = [json.loads(b) for b in bodies if b != "[DONE]"]
        thought = "".join(e["choices"][0]["delta"].get("reasoning_content", "") for e in events)
        self.assertEqual(thought, f"Write to {self.REAL}")
        self.assertEqual("".join(e["choices"][0]["delta"].get("content", "") for e in events), "Done.")

    def test_a_whole_reply_reverses_its_reasoning(self):
        reply = {"choices": [{"message": {"content": "ok", "reasoning_content": f"to {self.FAKE}"}}]}
        hooks.reverse_completion(reply, {self.FAKE: self.REAL})
        self.assertEqual(reply["choices"][0]["message"]["reasoning_content"], f"to {self.REAL}")


class ReasoningTail(unittest.TestCase):
    """The chat stream adds the reasoning the reverser held back to its block."""

    class Held:
        def __init__(self, *tails):
            self.tails = list(tails)

        def flush(self):
            return self.tails.pop(0)

    def test_the_tail_lands_on_the_last_reasoning_block(self):
        blocks = [{"type": "reasoning", "content": "a"}, {"type": "text", "content": "b"}]
        held = self.Held("!", "")
        hooks.flush_reasoning(held, blocks)
        hooks.flush_reasoning(held, blocks)
        self.assertEqual([b["content"] for b in blocks], ["a!", "b"])


if __name__ == "__main__":
    unittest.main()
