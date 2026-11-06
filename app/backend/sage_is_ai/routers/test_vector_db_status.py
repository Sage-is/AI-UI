"""Search with no vector client answers 503, and diagnostics says why (2026-11-05).

On sage.startr.cloud every knowledge base answered 200 with zero hits while the
vector client was off (2026-10-20): `query_collection` swallowed the error, so
the page read "nothing matched" instead of "search is off". Runs inside the
image or the dev container with a throwaway key and database:
    python3 -B -m unittest sage_is_ai.routers.test_vector_db_status
"""

import types
import unittest
from unittest import mock

from fastapi import HTTPException

from sage_is_ai.retrieval.vector import factory

ADMIN = types.SimpleNamespace(id="u1", role="admin")


class VectorDbStatus(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(factory, "VECTOR_DB_CLIENT", None)
        patcher.start()
        self.addCleanup(patcher.stop)

    def query(self, handler, form):
        from sage_is_ai.routers import retrieval as route

        request = types.SimpleNamespace(
            app=types.SimpleNamespace(state=types.SimpleNamespace())
        )
        with mock.patch.object(route, "can_read_collection", lambda user, name: True):
            with self.assertRaises(HTTPException) as caught:
                getattr(route, handler)(request, form, user=ADMIN)
        return caught.exception

    def test_a_collection_query_answers_503_not_an_empty_200(self):
        from sage_is_ai.routers.retrieval import QueryCollectionsForm

        error = self.query(
            "query_collection_handler",
            QueryCollectionsForm(collection_names=["kb-1"], query="hi"),
        )
        self.assertEqual(error.status_code, 503)
        self.assertIn("Admin → Sprigs", error.detail)

    def test_a_document_query_answers_503_not_400(self):
        from sage_is_ai.routers.retrieval import QueryDocForm

        error = self.query(
            "query_doc_handler", QueryDocForm(collection_name="kb-1", query="hi")
        )
        self.assertEqual(error.status_code, 503)

    def test_diagnostics_reports_search_off_then_on(self):
        from sage_is_ai.routers.diagnostics import _check_vector_db

        off = _check_vector_db()
        self.assertEqual(off["status"], "degraded")
        self.assertEqual(off["issue_type"], "vector_db_off")
        with mock.patch.object(factory, "VECTOR_DB_CLIENT", object()):
            self.assertEqual(_check_vector_db()["status"], "ok")


if __name__ == "__main__":
    unittest.main()
