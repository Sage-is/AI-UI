"""A signed-in account must not edit the server-owned parts of its own `info` (2026-10-23).

`/api/v1/users/user/info/update` merged any client JSON into `user.info`, where a trial
account's expiry lives (`info.temporary.expires_at`), so a try.sage persona could stay
forever. The route keeps only user-editable keys; the frontend sends exactly one,
`location`. Runs against a box (RS_BASE_URL).
"""

from __future__ import annotations

import time
import unittest

from ._http import admin, new_user

INFO_UPDATE = "/api/v1/users/user/info/update"
FAR_FUTURE = 9999999999


class TemporaryAccountExpirySelfEdit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin = admin()

    def info_of(self, user) -> dict:
        r = user.get("/api/v1/auths/")
        self.assertEqual(r.status, 200, r.text[:200])
        return r.json().get("info") or {}

    def test_server_owned_keys_are_dropped_and_the_editable_one_kept(self):
        user = new_user("user", admin_user=self.admin)
        r = user.post(INFO_UPDATE, {"temporary": False, "expires_at": FAR_FUTURE, "location": "Montreal"})
        self.assertEqual(r.status, 200, r.text[:200])
        info = self.info_of(user)
        self.assertEqual(info.get("location"), "Montreal", f"the editable key was not stored: {info}")
        self.assertNotIn("temporary", info, f"a client wrote `temporary`: {info}")
        self.assertNotIn("expires_at", info, f"a client wrote `expires_at`: {info}")

    def test_a_temporary_account_cannot_move_its_own_expiry(self):
        user = new_user("temporary", admin_user=self.admin)
        expires_at = int(time.time()) + 3600
        # The server owns the expiry; an admin write stands in for the magic-link redeem that sets it.
        r = self.admin.post(f"/api/v1/users/{user.id}/update", {
            "role": "temporary", "name": "RS temporary", "email": user.email,
            "profile_image_url": "/user.png", "info": {"temporary": {"expires_at": expires_at}}})
        self.assertEqual(r.status, 200, r.text[:200])
        r = user.post(INFO_UPDATE, {"temporary": {"expires_at": FAR_FUTURE, "claimed": True}})
        self.assertEqual(r.status, 200, r.text[:200])
        self.assertEqual(self.info_of(user).get("temporary"), {"expires_at": expires_at},
                         "the account moved its own expiry")


if __name__ == "__main__":
    unittest.main()
