"""A retrieval query on a box without document search answers 503, in words a person can
act on (2026-11-02). Not a security test; the box harness lives here.

The query routes caught every exception and answered 400 "[ERROR: 503: Embedding model not
yet loaded. Complete setup wizard to download.]": the status lost, the wizard long gone.
An HTTPException now passes through unchanged, and the text names who fixes it and where.

Runs against a box (RS_BASE_URL); skips on a box that has document search.
"""

from __future__ import annotations

import unittest

from ._http import admin


class RetrievalKeepsItsStatus(unittest.TestCase):
    def test_a_box_without_document_search_answers_503_not_400(self):
        boss = admin()
        for path, body in (
            (
                "/api/v1/retrieval/query/doc",
                {"collection_name": "rs-probe-none", "query": "hi"},
            ),
            (
                "/api/v1/retrieval/query/collection",
                {"collection_names": ["rs-probe-none"], "query": "hi"},
            ),
        ):
            r = boss.post(path, body)
            if r.status == 200:
                self.skipTest("this box has document search")
            self.assertEqual(r.status, 503, f"{path}: {r.text[:200]}")
            self.assertNotIn("[ERROR:", r.text, path)
            self.assertIn("Admin → Sprigs", r.json()["detail"], path)


if __name__ == "__main__":
    unittest.main()
