"""POST /api/v1/knowledge/reindex keeps every knowledge base, data or no data.

The admin creates a knowledge base, nulls its data through /update, reindexes, and the
knowledge base is still there. Needs the vector store on (reindex answers 503 without
it), else it skips.

    cd app/backend && RS_BASE_URL=http://localhost:8184 \\
        python3 -m unittest -v sage_is_ai.rootstock.tests.security.test_knowledge_reindex
"""

from __future__ import annotations

import unittest
import uuid

from ._http import admin


class KnowledgeReindexTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin = admin()
        status = cls.admin.get("/api/v1/retrieval/models/status").json() or {}
        if not status.get("vector_db_ready"):
            raise unittest.SkipTest("the vector store is off on this box (vector_db_ready false); "
                                    "POST /api/v1/retrieval/models/download {\"components\": []} first")

    def test_reindex_keeps_a_knowledge_base_without_data(self):
        name = f"rs-reindex-{uuid.uuid4().hex[:8]}"
        r = self.admin.post("/api/v1/knowledge/create", {"name": name, "description": "reindex test"})
        self.assertEqual(r.status, 200, f"create: HTTP {r.status} {r.text[:200]}")
        knowledge_id = r.json()["id"]
        self.addCleanup(self.admin.delete, f"/api/v1/knowledge/{knowledge_id}/delete")

        r = self.admin.post(f"/api/v1/knowledge/{knowledge_id}/update",
                            {"name": name, "description": "reindex test", "data": None})
        self.assertEqual(r.status, 200, f"update: HTTP {r.status} {r.text[:200]}")
        self.assertIsNone(self.admin.get(f"/api/v1/knowledge/{knowledge_id}").json().get("data"))

        r = self.admin.post("/api/v1/knowledge/reindex", timeout=600)
        self.assertEqual(r.status, 200, f"reindex: HTTP {r.status} {r.text[:200]}")

        r = self.admin.get(f"/api/v1/knowledge/{knowledge_id}")
        self.assertEqual(r.status, 200, f"the knowledge base is gone after reindex: HTTP {r.status} {r.text[:120]}")
        self.assertEqual((r.json() or {}).get("id"), knowledge_id)
        listed = [k.get("id") for k in self.admin.get("/api/v1/knowledge/").json() or []]
        self.assertIn(knowledge_id, listed, "the knowledge base left the list after reindex")


if __name__ == "__main__":
    unittest.main()
