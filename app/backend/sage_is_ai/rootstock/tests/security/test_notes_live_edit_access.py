"""A note's reader can watch it live but never change it (2026-11-02).

The live-edit socket checked only read access before saving, and its update
handler checked nothing, so anyone a note was shared with read-only could
rewrite it, and their edits reached every writer's editor. The join asks for
read, the update and the save for write (`note_access` in socket/main.py).

Runs against a box (RS_BASE_URL). The owner's own live edit is the control:
it must save, or the reader's refusal proves nothing.
"""

from __future__ import annotations

import ast
import json
import time
import unittest
from pathlib import Path

from ._http import BASE, admin, new_user
from .test_session_token_expiry_and_cutoff import SOCKET_PATH, WebSocket


def push_live_edit(token: str, note_id: str, text: str) -> None:
    """Join the note's live document as the token's user, as the editor does, and
    push one update whose data carries `text`; the box saves it 0.5 s later."""
    ws = WebSocket(BASE, SOCKET_PATH)
    try:
        ws.recv()  # Engine.IO open
        ws.send("40" + json.dumps({"token": token}))
        ws.recv()  # Socket.IO connect ack
        ws.send("421" + json.dumps(["user-join", {"auth": {"token": token}}]))
        while not ws.recv().startswith("431"):  # the join ack: the session is signed in
            pass
        doc = f"note:{note_id}"
        ws.send(
            "42"
            + json.dumps(
                ["ydoc:document:join", {"document_id": doc, "user_name": "rs"}]
            )
        )
        ws.send(
            "42"
            + json.dumps(
                [
                    "ydoc:document:update",
                    {
                        "document_id": doc,
                        "update": [0, 0],  # an empty Yjs update
                        "data": {"content": {"md": text}},
                    },
                ]
            )
        )
        time.sleep(2)  # past the save's debounce
    finally:
        ws.close()


class NotesLiveEditAccess(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = admin()
        cls.owner = new_user("user", admin_user=root)
        cls.reader = new_user("user", admin_user=root)

    def shared_note(self, text: str) -> str:
        """A note of the owner's that the reader may read and not write."""
        r = self.owner.post(
            "/api/v1/notes/create",
            {
                "title": "rs live edit",
                "data": {"content": {"md": text}},
                "access_control": {
                    "read": {"group_ids": [], "user_ids": [self.reader.id]},
                    "write": {"group_ids": [], "user_ids": []},
                },
            },
        )
        self.assertEqual(r.status, 200, r.text[:200])
        return r.json()["id"]

    def text_of(self, note_id: str) -> str | None:
        r = self.owner.get(f"/api/v1/notes/{note_id}")
        self.assertEqual(r.status, 200, r.text[:200])
        return ((r.json().get("data") or {}).get("content") or {}).get("md")

    def test_the_owner_edits_live(self):
        note_id = self.shared_note("owner text")
        push_live_edit(self.owner.token, note_id, "owner edit")
        self.assertEqual(
            self.text_of(note_id),
            "owner edit",
            "the control: the owner's live edit must save",
        )

    def test_a_reader_cannot_edit_live(self):
        note_id = self.shared_note("owner text")
        push_live_edit(self.reader.token, note_id, "reader edit")
        self.assertEqual(
            self.text_of(note_id), "owner text", "a read-only reader rewrote the note"
        )

    def test_the_router_applies_the_same_rule(self):
        note_id = self.shared_note("owner text")
        self.assertEqual(
            self.reader.get(f"/api/v1/notes/{note_id}").status,
            200,
            "the reader may read",
        )
        r = self.reader.post(
            f"/api/v1/notes/{note_id}/update",
            {"title": "rs", "data": {"content": {"md": "x"}}},
        )
        self.assertEqual(r.status, 403, f"the reader may not write: HTTP {r.status}")
        stranger = new_user("user", admin_user=admin())
        self.assertEqual(
            stranger.get(f"/api/v1/notes/{note_id}").status,
            403,
            "a stranger may not read",
        )


def hand_made_note_checks(source: str) -> list[int]:
    """Lines that call has_access on a note instead of asking note_allows."""
    return [
        node.lineno
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
        and getattr(node.func, "id", "") == "has_access"
        and "note" in ast.unparse(node)
    ]


class EveryNoteCheckIsTheSharedRule(unittest.TestCase):
    """The router, the socket and retrieval each ask note_allows, so the rule cannot
    drift between them (retrieval skipped the owner and crashed on a missing note).
    Reads the source; needs no box."""

    def test_no_caller_checks_a_note_by_hand(self):
        pkg = Path(__file__).resolve().parents[3]
        for rel in ("routers/notes.py", "socket/main.py", "retrieval/utils.py"):
            self.assertEqual(hand_made_note_checks((pkg / rel).read_text()), [], rel)

    def test_the_check_has_teeth(self):
        old = 'if user.role == "admin" or has_access(user.id, "read", note.access_control):\n    pass\n'
        self.assertEqual(hand_made_note_checks(old), [1])


if __name__ == "__main__":
    unittest.main()
