"""The API-key endpoint allowlist must not fail open on an empty entry (2026-10-23).

`utils/auth.get_current_user` splits API_KEY_ALLOWED_ENDPOINTS on commas. An empty list,
a trailing comma or a blank entry left "" in the list, and every path starts with "" + "/",
so restrictions were on in name only. Runs against a box (RS_BASE_URL); the admin config
it changes is put back afterwards.
"""

from __future__ import annotations

import unittest

from ._http import admin, call, new_user

ADMIN_CONFIG = "/api/v1/auths/admin/config"


class ApiKeyAllowlistEmptyEntry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin = admin()
        r = cls.admin.get(ADMIN_CONFIG)
        if r.status != 200:
            raise RuntimeError(f"reading the admin config failed: HTTP {r.status} {r.text[:200]}")
        cls.original = r.json()
        cls.user = new_user("user", admin_user=cls.admin)
        cls.configure(ENABLE_API_KEY=True, ENABLE_API_KEY_ENDPOINT_RESTRICTIONS=False)
        r = cls.user.post("/api/v1/auths/api_key")
        if r.status != 200:
            raise RuntimeError(f"creating an API key failed: HTTP {r.status} {r.text[:200]}")
        cls.api_key = r.json()["api_key"]

    @classmethod
    def tearDownClass(cls):
        cls.user.delete("/api/v1/auths/api_key")
        cls.admin.post(ADMIN_CONFIG, cls.original)

    @classmethod
    def configure(cls, **changes):
        r = cls.admin.post(ADMIN_CONFIG, {**cls.original, **changes})
        if r.status != 200:
            raise RuntimeError(f"saving the admin config failed: HTTP {r.status} {r.text[:200]}")

    def restrict_to(self, allowlist: str):
        self.configure(ENABLE_API_KEY=True, ENABLE_API_KEY_ENDPOINT_RESTRICTIONS=True,
                       API_KEY_ALLOWED_ENDPOINTS=allowlist)

    def with_key(self, path: str):
        return call("GET", path, self.api_key)

    def assert_denied(self, path: str, allowlist: str):
        r = self.with_key(path)
        self.assertEqual(r.status, 403,
                         f"allowlist {allowlist!r} admitted {path}: HTTP {r.status} {r.text[:120]}")

    def test_an_empty_allowlist_denies_everything(self):
        self.restrict_to("")
        self.assert_denied("/api/v1/auths/", "")

    def test_blank_entries_deny_everything(self):
        self.restrict_to(" , ")
        self.assert_denied("/api/v1/auths/", " , ")

    def test_a_trailing_comma_does_not_open_the_list(self):
        self.restrict_to("/api/models,")
        r = self.with_key("/api/models")
        self.assertEqual(r.status, 200,
                         f"/api/models is on the list and was refused: HTTP {r.status} {r.text[:120]}")
        self.assert_denied("/api/v1/users/", "/api/models,")


if __name__ == "__main__":
    unittest.main()
