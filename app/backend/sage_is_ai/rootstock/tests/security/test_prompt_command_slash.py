"""A prompt saved without its leading slash can still be fetched and deleted
(2026-11-02). Data integrity more than security; the box harness lives here.

Every reader looks a prompt up as `/<command>`, but the create route stored the
command verbatim, and the UI's import strips the slash, so those prompts could
never be fetched, edited or deleted. PromptForm now adds the slash on the way in.

Runs against a box (RS_BASE_URL). The prompt it creates is deleted again.
"""

from __future__ import annotations

import unittest
import uuid

from ._http import admin


class PromptCommandSlash(unittest.TestCase):
    def test_a_command_saved_without_its_slash_is_found_and_deleted(self):
        boss = admin()
        name = f"rs-noslash-{uuid.uuid4().hex[:8]}"
        r = boss.post(
            "/api/v1/prompts/create", {"command": name, "title": "rs", "content": "rs"}
        )
        self.assertEqual(r.status, 200, r.text[:200])
        self.assertEqual(
            r.json()["command"], f"/{name}", "the stored command lacks its slash"
        )
        self.assertEqual(boss.get(f"/api/v1/prompts/command/{name}").status, 200)
        self.assertEqual(
            boss.delete(f"/api/v1/prompts/command/{name}/delete").status, 200
        )
        # A missing prompt answers 401 here (routers/prompts.py), so assert only that it is gone.
        self.assertNotEqual(
            boss.get(f"/api/v1/prompts/command/{name}").status,
            200,
            "the delete did not land",
        )


if __name__ == "__main__":
    unittest.main()
