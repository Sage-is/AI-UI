"""Knowledge access: retrieval reads only what the asking user may read.

User B owns a private knowledge base with one file. User A names B's knowledge id and
B's file on /api/v1/retrieval/query/collection and /query/doc, in a chat completion's
`files`, and as the knowledge of a client-supplied (direct) model. A gets nothing; B
and the admin still get results; a public knowledge base stays readable.

Needs a box with document reading on (vector store, loaders, embedding), else it
skips. The chat tests also need the mock provider (_mock_provider.py) reachable from
the box at RS_MOCK_INTERNAL_URL and from here at RS_MOCK_URL, else they skip. On the
box it lets users own knowledge bases, makes the mock connection 0 and records its
model as public: a throwaway box only.

    cd app/backend && RS_BASE_URL=http://localhost:8184 \\
        python3 -m unittest -v sage_is_ai.rootstock.tests.security.test_knowledge_access
"""

from __future__ import annotations

import json
import os
import unittest
import urllib.request
import uuid

from ._http import User, admin, call, new_user

MOCK_INTERNAL = os.environ.get("RS_MOCK_INTERNAL_URL", "http://rs-mock:8098/v1")
MOCK_URL = os.environ.get("RS_MOCK_URL", "http://localhost:8098").rstrip("/")

PASSPHRASE = "zebraquilt lanternorchard"
PRIVATE = {"read": {"group_ids": [], "user_ids": []}, "write": {"group_ids": [], "user_ids": []}}


def upload_text(user: User, text: str, name: str = "note.txt"):
    """A multipart upload of one small text file; returns the file record."""
    boundary = f"----rs{uuid.uuid4().hex}"
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{name}\"\r\n"
        f"Content-Type: text/plain\r\n\r\n{text}\r\n--{boundary}--\r\n"
    ).encode()
    r = call("POST", "/api/v1/files/", user.token, raw=body,
             headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}, timeout=180)
    if r.status != 200 or (r.json() or {}).get("error"):
        raise RuntimeError(f"upload failed: HTTP {r.status} {r.text[:300]}")
    return r.json()


def knowledge_with_file(user: User, text: str, access_control):
    """A knowledge base owned by `user` holding one processed text file; returns (knowledge id, file id)."""
    r = user.post("/api/v1/knowledge/create", {
        "name": f"rs-know-{uuid.uuid4().hex[:8]}", "description": "knowledge access test",
        "access_control": access_control})
    if r.status != 200:
        raise RuntimeError(f"knowledge create failed: HTTP {r.status} {r.text[:300]}")
    knowledge_id = r.json()["id"]
    file_id = upload_text(user, text)["id"]
    r = user.post(f"/api/v1/knowledge/{knowledge_id}/file/add", {"file_id": file_id}, timeout=180)
    if r.status != 200:
        raise RuntimeError(f"knowledge file/add failed: HTTP {r.status} {r.text[:300]}")
    return knowledge_id, file_id


def allow_knowledge(boss: User) -> None:
    """Let plain users own knowledge bases on this box (the default permission is off)."""
    permissions = boss.get("/api/v1/users/default/permissions").json() or {}
    if not (permissions.get("workshop") or {}).get("knowledge"):
        permissions.setdefault("workshop", {})["knowledge"] = True
        r = boss.post("/api/v1/users/default/permissions", permissions)
        if r.status != 200:
            raise RuntimeError(f"could not grant workshop.knowledge: HTTP {r.status} {r.text[:200]}")


def documents_of(result) -> str:
    """Every document text in a /query/* answer, joined."""
    docs = (result or {}).get("documents") or []
    return " ".join(d for group in docs for d in (group or []) if isinstance(d, str))


def documents_of_sources(response) -> str:
    """Every document text in the `sources` a non-streaming chat completion carries."""
    texts = []
    for source in (response or {}).get("sources") or []:
        texts.extend(d for d in source.get("document") or [] if isinstance(d, str))
    return " ".join(texts)


def around(text: str, needle: str, width: int = 80) -> str:
    """The stretch of `text` around `needle`, for a failure message that stays readable."""
    i = text.find(needle)
    return text[max(0, i - width):i + len(needle) + width // 2] if i >= 0 else ""


def mock(method: str, path: str):
    req = urllib.request.Request(MOCK_URL + path, method=method,
                                 headers={"User-Agent": "sage-rootstock-security-tests"})
    with urllib.request.urlopen(req, timeout=30) as r:  # nosec B310 — MOCK_URL is the test mock's http URL
        return json.loads(r.read() or b"null")


def connect_mock(boss: User) -> bool:
    """Make the mock provider connection 0 and its model public, or say it is not there.

    A plain user may only chat with a model that has a model record (check_model_access),
    so the admin records mock-echo with no access_control, which means everyone."""
    try:
        mock("GET", "/v1/models")
    except OSError:
        return False
    r = boss.post("/openai/config/update", {
        "ENABLE_OPENAI_API": True, "OPENAI_API_BASE_URLS": [MOCK_INTERNAL],
        "OPENAI_API_KEYS": ["mock-key"], "OPENAI_API_CONFIGS": {"0": {}}})
    if r.status != 200:
        return False
    models = boss.get("/api/models").json() or {}
    if not any(m.get("id") == "mock-echo" for m in models.get("data", [])):
        return False
    if boss.get("/api/v1/models/model?id=mock-echo").status != 200:
        r = boss.post("/api/v1/models/create", {"id": "mock-echo", "name": "mock-echo", "meta": {}, "params": {},
                                                "access_control": None})
        if r.status != 200:
            return False
    return True


class KnowledgeAccessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin = admin()
        status = cls.admin.get("/api/v1/retrieval/models/status").json() or {}
        if not (status.get("vector_db_ready") and status.get("embedding_ready")):
            raise unittest.SkipTest(
                "document reading is off on this box (vector_db_ready="
                f"{status.get('vector_db_ready')}, embedding_ready={status.get('embedding_ready')}); "
                "graft vector-chroma, rag-loaders and an embedding Sprig, then POST "
                "/api/v1/retrieval/models/download {\"components\": []}")
        allow_knowledge(cls.admin)
        cls.b = new_user("user", admin_user=cls.admin)
        cls.a = new_user("user", admin_user=cls.admin)
        cls.knowledge_id, cls.file_id = knowledge_with_file(
            cls.b, f"The passphrase of the orchard is {PASSPHRASE}.", PRIVATE)
        cls.mock_ready = connect_mock(cls.admin)

    def query_collection(self, user: User, *names):
        return user.post("/api/v1/retrieval/query/collection",
                         {"collection_names": list(names), "query": "passphrase of the orchard"}, timeout=120)

    def query_doc(self, user: User, name):
        return user.post("/api/v1/retrieval/query/doc",
                         {"collection_name": name, "query": "passphrase of the orchard"}, timeout=120)

    def test_query_collection_refuses_a_stranger(self):
        r = self.query_collection(self.a, self.knowledge_id)
        self.assertEqual(r.status, 403, f"HTTP {r.status}: {documents_of(r.json())[:120] or r.text[:200]}")

    def test_query_doc_refuses_a_stranger(self):
        r = self.query_doc(self.a, f"file-{self.file_id}")
        self.assertEqual(r.status, 403, f"HTTP {r.status}: {documents_of(r.json())[:120] or r.text[:200]}")

    def test_query_collection_refuses_a_file_collection_name(self):
        """A `legacy` file item hands retrieval its raw id as the collection name; the check follows the name."""
        r = self.query_collection(self.a, f"file-{self.file_id}", self.knowledge_id)
        self.assertEqual(r.status, 403, f"HTTP {r.status}: {documents_of(r.json())[:120] or r.text[:200]}")

    def test_owner_and_admin_still_read(self):
        for who, user in (("owner", self.b), ("admin", self.admin)):
            r = self.query_collection(user, self.knowledge_id)
            self.assertEqual(r.status, 200, f"{who} /query/collection: HTTP {r.status} {r.text[:200]}")
            self.assertIn(PASSPHRASE, documents_of(r.json()), f"{who} /query/collection found no document")
            r = self.query_doc(user, f"file-{self.file_id}")
            self.assertEqual(r.status, 200, f"{who} /query/doc: HTTP {r.status} {r.text[:200]}")
            self.assertIn(PASSPHRASE, documents_of(r.json()), f"{who} /query/doc found no document")

    def test_public_knowledge_stays_readable(self):
        knowledge_id, file_id = knowledge_with_file(self.b, "The public notice is pinned on the orchard gate.", None)
        r = self.query_collection(self.a, knowledge_id)
        self.assertEqual(r.status, 200, f"public knowledge: HTTP {r.status} {r.text[:200]}")
        self.assertIn("public notice", documents_of(r.json()))
        r = self.query_doc(self.a, f"file-{file_id}")
        self.assertEqual(r.status, 200, f"file of a public knowledge base: HTTP {r.status} {r.text[:200]}")

    # -- chat completions -------------------------------------------------------------

    def chat(self, user: User, files=None, extra=None):
        body = {"model": "mock-echo", "stream": False,
                "messages": [{"role": "user", "content": "What is the passphrase of the orchard?"}]}
        if files is not None:
            body["files"] = files
        body.update(extra or {})
        return user.post("/api/chat/completions", body, timeout=180)

    def need_mock(self):
        if not self.mock_ready:
            self.skipTest(f"the mock provider is not reachable at {MOCK_URL} (box side {MOCK_INTERNAL}); "
                          "run _mock_provider.py on the box's docker network")
        mock("DELETE", "/_requests")

    def outbound_text(self) -> str:
        """Everything the box sent the provider since the last forget."""
        return json.dumps([req.get("body") for req in mock("GET", "/_requests")])

    def test_chat_files_leak_nothing_to_a_stranger(self):
        self.need_mock()
        for label, files in (
            ("collection", [{"type": "collection", "id": self.knowledge_id, "name": "b"}]),
            ("file", [{"type": "file", "id": self.file_id, "name": "note.txt"}]),
            ("file, full context", [{"type": "file", "id": self.file_id, "name": "note.txt", "context": "full"}]),
            ("collection, full context", [{"type": "collection", "id": self.knowledge_id, "name": "b", "context": "full"}]),
        ):
            with self.subTest(files=label):
                mock("DELETE", "/_requests")
                r = self.chat(self.a, files)
                self.assertEqual(r.status, 200, f"HTTP {r.status} {r.text[:200]}")
                found = documents_of_sources(r.json())
                self.assertNotIn(PASSPHRASE, found, f"A's completion carried B's text in sources: {found[:120]}")
                outbound = self.outbound_text()
                self.assertNotIn(PASSPHRASE, outbound,
                                 f"B's text reached the model for A: ...{around(outbound, PASSPHRASE)}...")

    def test_chat_files_serve_the_owner(self):
        self.need_mock()
        r = self.chat(self.b, [{"type": "collection", "id": self.knowledge_id, "name": "b"}])
        self.assertEqual(r.status, 200, f"HTTP {r.status} {r.text[:200]}")
        self.assertIn(PASSPHRASE, documents_of_sources(r.json()), f"B's own completion found nothing: {r.text[:200]}")

    def test_direct_model_knowledge_is_not_read(self):
        """A client-supplied model (model_item with direct: true) names B's knowledge; the knowledge stage must not run.

        A direct completion needs the client's socket, so it fails after the payload stage; the
        knowledge stage's `knowledge_search` status on the chat message is the witness that it ran."""
        message_id = str(uuid.uuid4())
        r = self.a.post("/api/v1/chats/new", {"chat": {
            "title": "rs direct", "models": ["mock-echo"], "messages": [],
            "history": {"currentId": message_id, "messages": {
                message_id: {"id": message_id, "role": "assistant", "content": "", "parentId": None, "childrenIds": []}}}}})
        self.assertEqual(r.status, 200, f"chat create: HTTP {r.status} {r.text[:200]}")
        chat_id = r.json()["id"]
        model_item = {"id": "mock-echo", "name": "mock-echo", "direct": True, "owned_by": "openai",
                      "info": {"meta": {"knowledge": [{"id": self.knowledge_id, "type": "collection", "name": "b"}]}}}
        self.chat(self.a, extra={"model_item": model_item, "chat_id": chat_id, "id": message_id})
        chat = self.a.get(f"/api/v1/chats/{chat_id}").json() or {}
        message = ((chat.get("chat") or {}).get("history") or {}).get("messages", {}).get(message_id, {})
        actions = [s.get("action") for s in message.get("statusHistory", [])]
        self.assertNotIn("knowledge_search", actions,
                         f"the knowledge stage ran on a client-supplied model: statusHistory={actions}")


if __name__ == "__main__":
    unittest.main()
