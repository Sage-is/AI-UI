"""The upload route's `internal` flag skipped the admin's file-type allowlist for any client.

Card "Client-set flags skip checks: ?bypass_filter=true and ?internal=true": `internal`
stays an argument for server-internal callers of upload_file and is never read from the request.
"""

import unittest
import uuid

from . import _http


def multipart(filename: str, content: bytes):
    boundary = uuid.uuid4().hex
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            "Content-Type: application/octet-stream\r\n\r\n").encode() + content + f"\r\n--{boundary}--\r\n".encode()
    return body, f"multipart/form-data; boundary={boundary}"


class UploadInternalFlag(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin = _http.admin()
        cls.before = (cls.admin.get("/api/v1/retrieval/config").json() or {}).get("ALLOWED_FILE_EXTENSIONS") or []
        r = cls.admin.post("/api/v1/retrieval/config/update", {"ALLOWED_FILE_EXTENSIONS": ["txt"]})
        if r.status != 200:
            raise RuntimeError(f"could not set the allowlist: HTTP {r.status} {r.text[:200]}")
        cls.user = _http.new_user(admin_user=cls.admin)

    @classmethod
    def tearDownClass(cls):
        cls.admin.post("/api/v1/retrieval/config/update", {"ALLOWED_FILE_EXTENSIONS": cls.before})

    def upload(self, path, filename):
        body, ctype = multipart(filename, b"not a text file")
        return self.user.post(path, raw=body, headers={"Content-Type": ctype})

    def test_internal_in_the_query_does_not_skip_the_allowlist(self):
        r = self.upload("/api/v1/files/?internal=true", f"rs-{uuid.uuid4().hex[:6]}.exe")
        self.assertEqual(r.status, 400, f"the allowlist was skipped: HTTP {r.status} {r.text[:200]}")

    def test_an_allowed_type_still_uploads(self):
        r = self.upload("/api/v1/files/?process=false", f"rs-{uuid.uuid4().hex[:6]}.txt")
        self.assertEqual(r.status, 200, r.text[:200])
        self.user.delete(f"/api/v1/files/{r.json()['id']}")


if __name__ == "__main__":
    unittest.main()
