"""Community sharing stays off until the sharing site exists (TODO.md, "Community sharing is still saved ON").

Against the box: the flag reads off after boot whatever the database saved, and an admin who
posts the admin config with it on gets the rest of the form saved and the flag still off, both
in the saved config and in /api/config's features.
"""

from __future__ import annotations

import unittest

from . import _http

ADMIN_CONFIG = "/api/v1/auths/admin/config"


class CommunitySharingStaysOff(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin = _http.admin()

    def features(self) -> dict:
        # /api/config reads the session from the cookie, and only a signed-in caller sees the flags.
        r = self.admin.get("/api/config", headers={"Cookie": f"token={self.admin.token}"})
        self.assertEqual(r.status, 200, r.text[:200])
        return r.json()["features"]

    def test_the_box_boots_with_it_off(self):
        self.assertIs(self.features()["enable_community_sharing"], False)
        self.assertIs(self.admin.get(ADMIN_CONFIG).json()["ENABLE_COMMUNITY_SHARING"], False)

    def test_an_admin_cannot_turn_it_on(self):
        config = self.admin.get(ADMIN_CONFIG).json()
        config["ENABLE_COMMUNITY_SHARING"] = True
        config["ENABLE_MESSAGE_RATING"] = not config["ENABLE_MESSAGE_RATING"]  # the rest of the form must still save
        r = self.admin.post(ADMIN_CONFIG, config)
        self.assertEqual(r.status, 200, r.text[:200])
        saved = r.json()
        self.assertIs(saved["ENABLE_COMMUNITY_SHARING"], False)
        self.assertIs(saved["ENABLE_MESSAGE_RATING"], config["ENABLE_MESSAGE_RATING"])
        self.assertIs(self.features()["enable_community_sharing"], False)
        self.admin.post(ADMIN_CONFIG, {**saved, "ENABLE_MESSAGE_RATING": not config["ENABLE_MESSAGE_RATING"]})
