"""Model access control applies to every non-admin role, not only `user`.

Before the fix, /api/models filtered and the chat routes checked access only when
`user.role == "user"` (main.py, utils/chat.py, routers/openai.py), so a facilitator or a
temporary account saw and called every model, restricted ones included. One helper,
`is_restricted(user)` in utils/access_control.py, now answers for every role but admin.

    cd app/backend && RS_BASE_URL=http://localhost:8183 python3 -m unittest -v \\
        sage_is_ai.rootstock.tests.security.test_model_access_roles
"""

import unittest

from . import _fixtures
from ._http import admin, new_user

ROLES = ("facilitator", "temporary")


class ModelAccessAppliesToEveryRole(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin = admin()
        _fixtures.connect_mock(cls.admin)
        cls.models = _fixtures.Models(cls.admin)
        cls.users = {role: new_user(role, admin_user=cls.admin) for role in ROLES}

    @classmethod
    def tearDownClass(cls):
        cls.models.remove()

    def listed(self, user) -> set:
        r = user.get("/api/models")
        self.assertEqual(r.status, 200, f"HTTP {r.status} {r.text[:200]}")
        return {m["id"] for m in r.json()["data"]}

    def test_admin_still_sees_the_restricted_model(self):
        self.assertIn(self.models.restricted, self.listed(self.admin))

    def test_restricted_model_is_absent_from_the_list(self):
        for role, user in self.users.items():
            with self.subTest(role=role):
                ids = self.listed(user)
                self.assertNotIn(self.models.restricted, ids, f"{role} sees the restricted model")
                self.assertIn(self.models.public, ids, f"{role} lost the public model")

    def test_chat_with_the_restricted_model_answers_403(self):
        for role, user in self.users.items():
            for route in ("/api/chat/completions", "/openai/chat/completions"):
                with self.subTest(role=role, route=route):
                    r = user.post(route, _fixtures.chat_body(self.models.restricted))
                    self.assertEqual(r.status, 403, f"{role}: HTTP {r.status} {r.text[:200]}")

    def test_chat_with_the_public_model_still_answers(self):
        for role, user in self.users.items():
            with self.subTest(role=role):
                r = user.post("/api/chat/completions", _fixtures.chat_body(self.models.public, "hello"))
                self.assertEqual(r.status, 200, f"{role}: HTTP {r.status} {r.text[:200]}")
                self.assertIn("You said: hello", r.json()["choices"][0]["message"]["content"])


if __name__ == "__main__":
    unittest.main()
