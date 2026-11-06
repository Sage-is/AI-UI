"""Any signed-in user may ask whether the box can read a document, and learns only what
is missing (2026-11-03, card "An upload starts before anyone checks that the box can read
it"). The composer and the knowledge page ask before an upload starts. The admin-only
model status keeps its guard: the readiness answer names parts, never settings.

Runs against a box (RS_BASE_URL).
"""

from __future__ import annotations

import unittest

from . import _http

PARTS = {"document loaders", "embedding model", "vector store"}


class DocumentReadiness(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin = _http.admin()
        cls.member = _http.new_user(admin_user=cls.admin)

    def test_a_member_reads_the_answer_and_only_part_names(self):
        r = self.member.get("/api/v1/retrieval/readiness")
        self.assertEqual(r.status, 200, r.text[:200])
        body = r.json()
        self.assertEqual(set(body), {"ready", "missing"})
        self.assertLessEqual(set(body["missing"]), PARTS)
        self.assertIs(body["ready"], not body["missing"])

    def test_the_model_status_stays_admin_only(self):
        self.assertIn(
            self.member.get("/api/v1/retrieval/models/status").status, (401, 403)
        )

    def test_signed_out_gets_nothing(self):
        self.assertIn(
            _http.call("GET", "/api/v1/retrieval/readiness").status, (401, 403)
        )


if __name__ == "__main__":
    unittest.main()
