"""Shared set-up for the access tests: the mock provider as connection 0, a group the
test accounts are not in, and two model entries on top of mock-echo, one restricted to
that group and one public. Standard library only; runs against the box RS_BASE_URL names.

The mock is shared by every box on the docker network, so a test that reads what the
mock saw looks for its own marker (a unique path or message) and never clears the log.
"""

from __future__ import annotations

import json
import os
import urllib.request
import uuid

from ._http import User

MOCK_INTERNAL = os.environ.get("RS_MOCK_INTERNAL_URL", "http://rs-mock:8098/v1")
MOCK_URL = os.environ.get("RS_MOCK_URL", "http://localhost:8098").rstrip("/")
UA = {"User-Agent": "sage-rootstock-security-tests"}

try:  # develop's _http.py carries these two; this copy of the harness predates them
    from ._http import connect_mock, mock_requests  # noqa: F401
except ImportError:

    def connect_mock(admin_user: User) -> None:
        """Make the mock provider connection 0, and load its one model, mock-echo."""
        r = admin_user.post("/openai/config/update", {  # the OpenAI router is mounted at /openai
            "ENABLE_OPENAI_API": True, "OPENAI_API_BASE_URLS": [MOCK_INTERNAL],
            "OPENAI_API_KEYS": ["mock-key"], "OPENAI_API_CONFIGS": {"0": {}}})
        if r.status != 200:
            raise RuntimeError(f"connecting the mock failed: HTTP {r.status} {r.text[:200]}")
        models = admin_user.get("/api/models").json() or {}
        if not any(m.get("id") == "mock-echo" for m in models.get("data", [])):
            raise RuntimeError("mock-echo is not in /api/models; is rs-mock running on sage-network?")

    def mock_requests() -> list:
        """Every request the mock provider has seen: method, path, authorization, JSON body."""
        req = urllib.request.Request(MOCK_URL + "/_requests", headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:  # nosec B310 — MOCK_URL is the mock's http URL
            return json.loads(r.read())


def chat_body(model_id: str, text: str = "ping") -> dict:
    return {"model": model_id, "messages": [{"role": "user", "content": text}], "stream": False}


def mock_saw(marker: str) -> list:
    """The mock's requests whose path or body carries `marker`."""
    return [q for q in mock_requests() if marker in q["path"] or marker in json.dumps(q["body"])]


class Models:
    """Two entries on top of mock-echo, made by the admin: `restricted` is readable by one
    group that no test account belongs to; `public` has no access list. `remove()` deletes
    both and the group."""

    def __init__(self, admin_user: User):
        self.admin = admin_user
        tag = uuid.uuid4().hex[:8]
        r = admin_user.post("/api/v1/groups/create", {"name": f"rs-closed-{tag}", "description": "access tests"})
        if r.status != 200:
            raise RuntimeError(f"creating a group failed: HTTP {r.status} {r.text[:200]}")
        self.group_id = r.json()["id"]
        closed = {"group_ids": [self.group_id], "user_ids": []}
        self.restricted = self._create(f"rs-restricted-{tag}", {"read": closed, "write": closed})
        self.public = self._create(f"rs-public-{tag}", None)
        # The box rebuilds its in-memory model map when someone lists models, as the SPA
        # does after a save; until then a chat with a new entry is a 400 "Model not found".
        admin_user.get("/api/models")

    def _create(self, model_id: str, access_control) -> str:
        r = self.admin.post("/api/v1/models/create", {
            "id": model_id, "base_model_id": "mock-echo", "name": model_id,
            "meta": {}, "params": {}, "access_control": access_control})
        if r.status != 200:
            raise RuntimeError(f"creating model {model_id} failed: HTTP {r.status} {r.text[:200]}")
        return model_id

    def remove(self) -> None:
        for model_id in (self.restricted, self.public):
            self.admin.delete(f"/api/v1/models/model/delete?id={model_id}")
        self.admin.delete(f"/api/v1/groups/id/{self.group_id}/delete")
