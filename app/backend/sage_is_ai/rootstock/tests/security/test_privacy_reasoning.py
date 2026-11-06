"""A model's reasoning comes back with real values, as its answer does (2026-11-03).

The mock gives a "think:" request its own text back as reasoning first, cut in
7-character pieces, so a stand-in straddles two deltas. Three paths: the API reply
not streamed and streamed, and the chat's own stream, whose reasoning block is
saved with the message. The provider must see only stand-ins throughout.
Card: "Privacy rules". Runs against a box (RS_BASE_URL) with rs-mock.
"""

import json
import time
import unittest
import uuid

from . import _http


class PrivacyReasoning(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin = _http.admin()
        _http.connect_mock(cls.admin)
        tag = uuid.uuid4().hex[:8]
        cls.real = f"erin.{tag}@example.com"  # the email detector is on by default
        cls.text = f"think: mail {cls.real}"
        cls.model = f"rs-think-{tag}"
        r = cls.admin.post("/api/v1/models/create", {
            "id": cls.model, "base_model_id": "mock-echo", "name": "Reasoning test agent",
            "meta": {}, "params": {}, "access_control": None})
        if r.status != 200:
            raise RuntimeError(f"model create: HTTP {r.status} {r.text[:200]}")

    def setUp(self):
        _http.mock_forget()

    def chat(self, **form):
        r = self.admin.post("/api/chat/completions", {
            "model": self.model, "messages": [{"role": "user", "content": self.text}], **form})
        self.assertEqual(r.status, 200, r.text[:300])
        return r

    def assert_provider_saw_only_stand_ins(self):
        bodies = [s["body"] for s in _http.mock_requests() if s["path"].startswith("/v1/chat/completions")]
        self.assertTrue(bodies, "no request reached the provider")
        self.assertNotIn(self.real, json.dumps(bodies), "the real address left the box")

    def test_an_api_reply_carries_real_reasoning(self):
        message = self.chat(stream=False).json()["choices"][0]["message"]
        self.assertEqual(message["reasoning_content"], f"Thinking about: {self.text}")
        self.assert_provider_saw_only_stand_ins()

    def test_a_streamed_api_reply_carries_real_reasoning(self):
        thought = ""
        for line in self.chat(stream=True).text.splitlines():
            body = line[len("data:"):].strip() if line.startswith("data:") else ""
            if body and body != "[DONE]":
                for choice in json.loads(body).get("choices") or []:
                    thought += (choice.get("delta") or {}).get("reasoning_content") or ""
        self.assertEqual(thought, f"Thinking about: {self.text}")
        self.assert_provider_saw_only_stand_ins()

    def test_the_chat_saves_its_reasoning_block_real(self):
        chat = self.admin.post("/api/v1/chats/new", {"chat": {
            "title": "rs reasoning", "models": [self.model], "history": {"messages": {}, "currentId": None}}})
        self.assertEqual(chat.status, 200, chat.text[:300])
        chat_id, message_id = chat.json()["id"], str(uuid.uuid4())
        self.chat(stream=True, chat_id=chat_id, id=message_id, session_id=f"rs-{uuid.uuid4().hex[:8]}")
        deadline, saved = time.time() + 60, ""
        while "You said" not in saved:  # the answer follows the reasoning once the stream ends
            self.assertLess(time.time(), deadline, f"the reply never saved: {saved[:300]!r}")
            time.sleep(0.5)
            messages = (self.admin.get(f"/api/v1/chats/{chat_id}").json() or {}).get("chat", {})
            saved = ((messages.get("history") or {}).get("messages") or {}).get(message_id, {}).get("content", "")
        reasoning = saved.split("</details>")[0]
        self.assertIn('type="reasoning"', reasoning)
        self.assertIn(self.real, reasoning, "the saved reasoning kept a stand-in")
        self.assert_provider_saw_only_stand_ins()


if __name__ == "__main__":
    unittest.main()
