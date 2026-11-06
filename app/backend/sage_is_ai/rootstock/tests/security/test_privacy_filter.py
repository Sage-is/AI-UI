"""Three privacy leaks, each shown on what actually reaches the provider.

The mock provider records every request; the box's connection 0 points at it,
so the filter is on (external connections are filtered by default). Cards:
"Privacy: the preset system prompt joins after the filter", "Privacy: the
reverse table is instance-wide", "Privacy: tool arguments leak on the follow-up".
"""

import re
import unittest
import uuid

from . import _http

POSTAL = "H2X 1Y4"  # the postal_ca detector is on by default; names are not detected


def chat(user, model, messages):
    r = user.post("/api/chat/completions", {"model": model, "messages": messages, "stream": False})
    if r.status != 200:
        raise AssertionError(f"chat answered HTTP {r.status}: {r.text[:300]}")
    return (r.json().get("choices") or [{}])[0].get("message", {}).get("content", "")


def last_sent():
    """The messages of the last request the provider received."""
    return _http.mock_requests()[-1]["body"].get("messages") or []


class PrivacyFilter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin = _http.admin()
        _http.connect_mock(cls.admin)
        cls.tag = uuid.uuid4().hex[:8]
        cls.model = f"rs-privacy-{cls.tag}"
        r = cls.admin.post("/api/v1/models/create", {
            "id": cls.model, "base_model_id": "mock-echo", "name": "Privacy test agent",
            "meta": {}, "params": {"system": "You help a user who lives at {{USER_LOCATION}}."},
            "access_control": None})
        if r.status != 200:
            raise RuntimeError(f"model create: HTTP {r.status} {r.text[:200]}")
        cls.admin.get("/api/models")  # the box's model cache learns the new entry on the next listing

    def setUp(self):
        _http.mock_forget()

    def test_system_prompt_goes_through_the_filter(self):
        user = _http.new_user(admin_user=self.admin)
        r = user.post("/api/v1/users/user/info/update", {"location": f"Montreal {POSTAL}"})
        self.assertEqual(r.status, 200, r.text[:200])
        chat(user, self.model, [{"role": "user", "content": "hello"}])
        system = [m["content"] for m in last_sent() if m.get("role") == "system"]
        self.assertEqual(len(system), 1, last_sent())
        self.assertNotIn(POSTAL, system[0], "the user's location left the box in clear")
        self.assertRegex(system[0], r"[A-Z]\d[A-Z] ?\d[A-Z]\d", "no postal-shaped stand-in took its place")

    def test_a_reply_reverses_only_this_requests_stand_ins(self):
        ada, bob = _http.new_user(admin_user=self.admin), _http.new_user(admin_user=self.admin)
        real = f"ada.{self.tag}@example.com"
        # Users see the workshop entry, not the bare connection model, so every chat goes through it.
        chat(ada, self.model, [{"role": "user", "content": f"write to {real}"}])
        sent = [m["content"] for m in last_sent() if m.get("role") == "user"][-1]
        fakes = [w for w in re.findall(r"[\w.+-]+@[\w.-]+", sent) if w != real]
        self.assertEqual(len(fakes), 1, f"no stand-in in what left the box: {sent!r}")
        # Bob's chat echoes Ada's stand-in. It must stay a stand-in for him.
        reply = chat(bob, self.model, [{"role": "user", "content": f"who is {fakes[0]}?"}])
        self.assertNotIn(real, reply, "another chat's stand-in reversed to a real address")

    def test_tool_arguments_leave_pseudonymized(self):
        user = _http.new_user(admin_user=self.admin)
        real = f"carol.{self.tag}@example.com"
        chat(user, self.model, [
            {"role": "user", "content": f"mail {real}"},
            {"role": "assistant", "content": None, "tool_calls": [
                {"id": "c1", "type": "function",
                 "function": {"name": "send_mail", "arguments": f'{{"to": "{real}"}}'}}]},
            {"role": "tool", "tool_call_id": "c1", "content": "sent"},
            {"role": "user", "content": "thanks, now summarize"},
        ])
        sent = last_sent()
        arguments = [c["function"]["arguments"] for m in sent for c in (m.get("tool_calls") or [])]
        self.assertTrue(arguments, f"no tool call reached the provider: {sent}")
        self.assertNotIn(real, "".join(arguments), "a tool argument left the box in clear")


if __name__ == "__main__":
    unittest.main()
