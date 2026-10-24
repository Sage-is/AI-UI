"""Each admin off-switch stops the filter (ON by default from 3.2.0).
Host-only: the one DB import is stubbed; active_for never reads the map."""

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

    def test_config_py_and_hooks_defaults_agree(self):
        src = (Path(__file__).resolve().parents[1] / "config.py").read_text()
        m = re.search(
            r'"default_external":\s*(True|False)', src[src.index('"privacy.config"') :]
        )
        self.assertEqual(m.group(1) == "True", hooks.DEFAULTS["default_external"])


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


if __name__ == "__main__":
    unittest.main()
