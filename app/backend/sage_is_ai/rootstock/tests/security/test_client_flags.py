"""`?bypass_filter=true` and `?internal=true` are not read from the request.

Before the fix, `bypass_filter` was a query parameter of /openai/chat/completions
(routers/openai.py), so any verified user could skip model access control by adding
`?bypass_filter=true`. Both flags stay Python arguments for server-internal callers
(routers/spaces.py passes bypass_filter=True on purpose); the HTTP routes never read them.

    cd app/backend && RS_BASE_URL=http://localhost:8183 python3 -m unittest -v \\
        sage_is_ai.rootstock.tests.security.test_client_flags
"""

import unittest

from . import _fixtures
from ._http import admin, new_user

ROUTES = ("/openai/chat/completions", "/api/chat/completions")
FLAGS = ("bypass_filter=true", "internal=true", "bypass_filter=true&internal=true")


class ClientFlagsAreIgnored(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin = admin()
        _fixtures.connect_mock(cls.admin)
        cls.models = _fixtures.Models(cls.admin)
        cls.user = new_user("user", admin_user=cls.admin)

    @classmethod
    def tearDownClass(cls):
        cls.models.remove()

    def test_the_flags_do_not_open_the_restricted_model(self):
        for route in ROUTES:
            for flag in FLAGS:
                with self.subTest(route=route, flag=flag):
                    r = self.user.post(f"{route}?{flag}", _fixtures.chat_body(self.models.restricted))
                    self.assertEqual(r.status, 403, f"HTTP {r.status} {r.text[:200]}")

    def test_the_route_still_answers_for_a_model_the_user_may_use(self):
        r = self.user.post(f"{ROUTES[0]}?{FLAGS[0]}", _fixtures.chat_body(self.models.public, "hi"))
        self.assertEqual(r.status, 200, f"HTTP {r.status} {r.text[:200]}")
        self.assertIn("You said: hi", r.json()["choices"][0]["message"]["content"])


if __name__ == "__main__":
    unittest.main()
