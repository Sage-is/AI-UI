"""/api/v1/retrieval/process/file indexes only a file the caller may read into a
collection the caller may write (2026-11-02), the write twin of F0's read check.

It took any `collection_name` and any `file_id`, so a user could push chunks into
another user's knowledge base or copy someone's file into a collection they read.

Runs against a box (RS_BASE_URL); skips when the box cannot take an upload. The
admin indexing into its own knowledge base is the control: anything but 403.
"""

from __future__ import annotations

import unittest
import uuid

from ._http import admin, new_user
from .test_knowledge_access import upload_text


class ProcessFileAccess(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.boss = admin()
        cls.stranger = new_user("user", admin_user=cls.boss)
        try:
            cls.file_id = upload_text(
                cls.boss, "rs process-file probe", processed=False
            )["id"]
        except RuntimeError as e:
            raise unittest.SkipTest(f"this box cannot take an upload: {e}")
        r = cls.boss.post(
            "/api/v1/knowledge/create",
            {
                "name": f"rs-pf-{uuid.uuid4().hex[:8]}",
                "description": "process/file access test",
                "access_control": {},
            },
        )
        if r.status != 200:
            raise unittest.SkipTest(
                f"knowledge create failed: HTTP {r.status} {r.text[:200]}"
            )
        cls.knowledge_id = r.json()["id"]

    def process(self, user, **body) -> int:
        r = user.post(
            "/api/v1/retrieval/process/file",
            {"file_id": self.file_id, **body},
            timeout=180,
        )
        return r.status

    def test_a_stranger_cannot_index_into_someone_elses_knowledge(self):
        self.assertEqual(
            self.process(self.stranger, collection_name=self.knowledge_id), 403
        )

    def test_a_stranger_cannot_reindex_someone_elses_file(self):
        self.assertEqual(self.process(self.stranger), 403)

    def test_a_name_with_no_record_takes_no_chunks(self):
        self.assertEqual(
            self.process(
                self.boss, collection_name=f"rs-no-record-{uuid.uuid4().hex[:8]}"
            ),
            403,
        )

    def test_the_owner_still_indexes(self):
        self.assertNotEqual(
            self.process(self.boss, collection_name=self.knowledge_id),
            403,
            "the control: the knowledge base's owner must not be refused",
        )


if __name__ == "__main__":
    unittest.main()
