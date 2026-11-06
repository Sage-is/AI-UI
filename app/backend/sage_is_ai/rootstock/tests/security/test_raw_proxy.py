"""The raw /openai/{path} proxy no longer lends connection 0's key to every verified user.

Before the fix, GET, POST, PUT and DELETE on any path went to the first connection with
its API key (routers/openai.py), past the privacy filter and model access control. The
SPA's own API modules call only routes the router declares, and docs/API-examples.md
documents no raw /openai path, so for non-admins every raw path answers 404 and is
logged; admins keep the deprecated proxy.

    cd app/backend && RS_BASE_URL=http://localhost:8183 python3 -m unittest -v \\
        sage_is_ai.rootstock.tests.security.test_raw_proxy
"""

import unittest
import uuid

from . import _fixtures
from ._http import admin, call, new_user


def unlisted() -> str:
    return f"rs-unlisted/{uuid.uuid4().hex}"


class RawProxyIsAdminOnly(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin = admin()
        _fixtures.connect_mock(cls.admin)
        cls.user = new_user("user", admin_user=cls.admin)

    def test_a_user_gets_404_and_the_provider_never_sees_it(self):
        path = unlisted()
        r = self.user.get(f"/openai/{path}")
        self.assertEqual(r.status, 404, f"HTTP {r.status} {r.text[:200]}")
        self.assertEqual(_fixtures.mock_saw(path), [], "the request reached the provider")

    def test_post_put_and_delete_are_refused_for_a_user_too(self):
        for method in ("POST", "PUT", "DELETE"):
            with self.subTest(method=method):
                path = unlisted()
                r = call(method, f"/openai/{path}", self.user.token, {"model": "mock-echo"})
                self.assertEqual(r.status, 404, f"HTTP {r.status} {r.text[:200]}")
                self.assertEqual(_fixtures.mock_saw(path), [], "the request reached the provider")

    def test_an_admin_still_reaches_the_provider(self):
        path = unlisted()
        r = self.admin.get(f"/openai/{path}")
        self.assertEqual(r.status, 200, f"HTTP {r.status} {r.text[:200]}")
        self.assertIs(r.json().get("ok"), True)
        self.assertEqual(len(_fixtures.mock_saw(path)), 1)

    def test_a_listed_path_still_works_for_a_user(self):
        r = self.user.get("/openai/models")  # the SPA's getOpenAIModels; a declared route
        self.assertEqual(r.status, 200, f"HTTP {r.status} {r.text[:200]}")
        self.assertIn("data", r.json())


if __name__ == "__main__":
    unittest.main()
