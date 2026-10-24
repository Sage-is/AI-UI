"""The direct-connections admin switch is enforced, not advisory.

Before the fix, no request path read ENABLE_DIRECT_CONNECTIONS: a body carrying
`model_item: {"direct": true}` walked through /api/chat/completions, /api/chat/completed
and /api/chat/actions/{action_id} (main.py) with the switch off. Now each of the three
answers 403 before it reads anything else, and the switch on still lets the body through.

    cd app/backend && RS_BASE_URL=http://localhost:8183 python3 -m unittest -v \\
        sage_is_ai.rootstock.tests.security.test_direct_connections_switch
"""

import unittest
import uuid

from . import _fixtures
from ._http import admin, new_user

SWITCH = "/api/v1/configs/connections"
DIRECT = {"direct": True, "url": _fixtures.MOCK_INTERNAL, "key": "x", "id": "mock-echo", "name": "mock-echo"}


class DirectConnectionsSwitchIsEnforced(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin = admin()
        cls.saved = cls.admin.get(SWITCH).json()
        cls.user = new_user("user", admin_user=cls.admin)

    @classmethod
    def tearDownClass(cls):
        cls.admin.post(SWITCH, cls.saved)

    def set_switch(self, on: bool):
        r = self.admin.post(SWITCH, {**self.saved, "ENABLE_DIRECT_CONNECTIONS": on})
        self.assertEqual(r.status, 200, f"HTTP {r.status} {r.text[:200]}")
        self.assertIs(r.json()["ENABLE_DIRECT_CONNECTIONS"], on)

    @staticmethod
    def body(marker: str) -> dict:
        # chat_id, id and session_id are what /completed and /actions read off the body.
        return {**_fixtures.chat_body("mock-echo", marker), "model_item": DIRECT,
                "chat_id": "rs-chat", "id": "rs-msg", "session_id": "rs-session"}

    def test_direct_completion_is_refused_while_the_switch_is_off(self):
        self.set_switch(False)
        marker = f"rs-direct-{uuid.uuid4().hex}"
        # No session_id: a relayed request would fail fast instead of waiting on a socket.
        r = self.user.post("/api/chat/completions", {**_fixtures.chat_body("mock-echo", marker), "model_item": DIRECT})
        self.assertEqual(r.status, 403, f"HTTP {r.status} {r.text[:200]}")
        self.assertEqual(_fixtures.mock_saw(marker), [], "the request reached the provider")

    def test_completed_and_actions_are_refused_while_the_switch_is_off(self):
        self.set_switch(False)
        for path in ("/api/chat/completed", "/api/chat/actions/rs-no-such-action"):
            with self.subTest(path=path):
                r = self.user.post(path, self.body("ping"))
                self.assertEqual(r.status, 403, f"HTTP {r.status} {r.text[:200]}")

    def test_the_switch_on_still_lets_a_direct_body_through(self):
        self.set_switch(True)
        r = self.user.post("/api/chat/completed", self.body("ping"))
        self.assertEqual(r.status, 200, f"HTTP {r.status} {r.text[:200]}")


if __name__ == "__main__":
    unittest.main()
