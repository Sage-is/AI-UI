"""Tool calls through the privacy filter, on what the provider and the tool see (2026-11-03).

The mock provider answers a request that offers tools with one call to the first
tool, the user's last message as its argument, so the call carries the stand-in
that left the box. Three paths. The API pass-through, not streamed and streamed:
the client gets the real value back. The chat's native tool loop: the tool gets
the real value, and the follow-up to the provider holds only stand-ins. The mock
also serves that tool, an OpenAPI `echo` that returns its input.

The loop runs when a request names a chat, a message and a session. Its events go
to a session nobody holds, which changes nothing it sends. Card: "Privacy: what the
tool-argument card left open". Runs against a box (RS_BASE_URL) with rs-mock.
"""

import json
import time
import unittest
import uuid

from . import _http

ECHO = {
    "type": "function",
    "function": {
        "name": "echo",
        "description": "Returns the text it was given.",
        "parameters": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
}


def streamed_arguments(text: str) -> str:
    """What a client gets by appending every tool-call argument fragment of an SSE reply."""
    out = ""
    for line in text.splitlines():
        body = line[len("data:") :].strip() if line.startswith("data:") else ""
        if body and body != "[DONE]":
            for choice in json.loads(body).get("choices") or []:
                for call in (choice.get("delta") or {}).get("tool_calls") or []:
                    out += (call.get("function") or {}).get("arguments") or ""
    return out


class PrivacyToolCalls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin = _http.admin()
        _http.connect_mock(cls.admin)
        tag = uuid.uuid4().hex[:8]
        cls.real = f"dana.{tag}@example.com"  # the email detector is on by default
        cls.text = f"mail {cls.real}"
        cls.model = f"rs-tools-{tag}"
        r = cls.admin.post(
            "/api/v1/models/create",
            {
                "id": cls.model,
                "base_model_id": "mock-echo",
                "name": "Tool-call test agent",
                "meta": {},
                "params": {"function_calling": "native"},
                "access_control": None,
            },
        )
        if r.status != 200:
            raise RuntimeError(f"model create: HTTP {r.status} {r.text[:200]}")

    def setUp(self):
        _http.mock_forget()

    def chat(self, **form):
        r = self.admin.post(
            "/api/chat/completions",
            {
                "model": self.model,
                "messages": [{"role": "user", "content": self.text}],
                **form,
            },
        )
        self.assertEqual(r.status, 200, r.text[:300])
        return r

    def assert_provider_saw_only_stand_ins(self):
        bodies = [
            s["body"]
            for s in _http.mock_requests()
            if s["path"].startswith("/v1/chat/completions")
        ]
        self.assertTrue(bodies, "no request reached the provider")
        self.assertNotIn(self.real, json.dumps(bodies), "the real address left the box")

    def test_an_api_reply_gets_real_tool_arguments(self):
        call = self.chat(stream=False, tools=[ECHO]).json()["choices"][0]["message"][
            "tool_calls"
        ][0]
        self.assertEqual(json.loads(call["function"]["arguments"]), {"text": self.text})
        self.assert_provider_saw_only_stand_ins()

    def test_a_streamed_api_reply_gets_real_tool_arguments(self):
        # The mock cuts the arguments in 7-character fragments, so the stand-in straddles two.
        arguments = streamed_arguments(self.chat(stream=True, tools=[ECHO]).text)
        self.assertEqual(json.loads(arguments), {"text": self.text})
        self.assert_provider_saw_only_stand_ins()

    def test_the_tool_loop_gives_the_tool_real_values_and_the_provider_stand_ins(self):
        before = _http.connect_mock_tools(self.admin)
        self.addCleanup(self.admin.post, "/api/v1/configs/tool_servers", before)
        chat = self.admin.post(
            "/api/v1/chats/new",
            {
                "chat": {
                    "title": "rs tool loop",
                    "models": [self.model],
                    "history": {"messages": {}, "currentId": None},
                }
            },
        )
        self.assertEqual(chat.status, 200, chat.text[:300])
        self.chat(
            stream=True,
            tool_ids=["server:0"],
            chat_id=chat.json()["id"],
            id=str(uuid.uuid4()),
            session_id=f"rs-{uuid.uuid4().hex[:8]}",
        )
        # The loop runs in the background; its follow-up carries the tool's result.
        deadline = time.time() + 60
        while not any(
            m.get("role") == "tool"
            for s in _http.mock_requests()
            for m in (s["body"] or {}).get("messages") or []
        ):
            self.assertLess(
                time.time(),
                deadline,
                f"no follow-up reached the provider: {_http.mock_requests()}",
            )
            time.sleep(0.5)
        echoed = [
            s["body"] for s in _http.mock_requests() if s["path"].startswith("/echo")
        ]
        self.assertEqual(
            echoed, [{"text": self.text}], "the tool did not get the real value"
        )
        self.assert_provider_saw_only_stand_ins()


if __name__ == "__main__":
    unittest.main()
