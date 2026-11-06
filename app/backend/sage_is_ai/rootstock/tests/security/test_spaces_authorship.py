"""Spaces: who may edit, delete and manage (TODO.md, "Spaces: any reader can edit or delete anyone's message").

Over HTTP against the box: a message is edited or deleted only by its author, the Space's owner
or an admin; a Space is updated or deleted only by its owner or an admin; anyone who can read a
Space still posts to it. The last class reads socket/main.py: the live-edit handler
ydoc:document:update names the session's user, never a client-sent user_id.
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

from . import _http

SPACES = "/api/v1/spaces"
SOCKET_MAIN = Path(__file__).resolve().parents[3] / "socket" / "main.py"


class SpacesAuthorship(unittest.TestCase):
    """`owner`, a facilitator, owns a Space anyone may read; `reader` reads it; `other` is another facilitator."""

    @classmethod
    def setUpClass(cls):
        cls.admin = _http.admin()
        cls.owner = _http.new_user("facilitator", admin_user=cls.admin)
        cls.reader = _http.new_user("user", admin_user=cls.admin)
        cls.other = _http.new_user("facilitator", admin_user=cls.admin)
        cls.space_id = cls.create_space(cls.owner)

    @staticmethod
    def create_space(user) -> str:
        # access_control None means everyone may read (utils/access_control.has_access).
        r = user.post(f"{SPACES}/create", {"name": "rs authorship", "access_control": None})
        if r.status != 200:
            raise RuntimeError(f"create space: HTTP {r.status} {r.text[:200]}")
        return r.json()["id"]

    def post_as(self, user) -> str:
        r = user.post(f"{SPACES}/{self.space_id}/messages/post", {"content": "hello"})
        self.assertEqual(r.status, 200, r.text[:200])
        return r.json()["id"]

    def update(self, user, message_id):
        return user.post(f"{SPACES}/{self.space_id}/messages/{message_id}/update", {"content": "edited"})

    def delete(self, user, message_id):
        return user.delete(f"{SPACES}/{self.space_id}/messages/{message_id}/delete")

    def update_space(self, user):
        return user.post(f"{SPACES}/{self.space_id}/update", {"name": "rs authorship", "access_control": None})

    def test_a_reader_still_reads_and_posts(self):
        self.assertEqual(self.reader.get(f"{SPACES}/{self.space_id}").status, 200)
        self.post_as(self.reader)

    def test_a_reader_cannot_edit_another_users_message(self):
        message_id = self.post_as(self.owner)
        r = self.update(self.reader, message_id)
        self.assertEqual(r.status, 403, f"HTTP {r.status} {r.text[:200]}")
        r = self.owner.get(f"{SPACES}/{self.space_id}/messages/{message_id}")
        self.assertEqual(r.json()["content"], "hello")

    def test_a_reader_cannot_delete_another_users_message(self):
        message_id = self.post_as(self.owner)
        r = self.delete(self.reader, message_id)
        self.assertEqual(r.status, 403, f"HTTP {r.status} {r.text[:200]}")
        self.assertEqual(self.owner.get(f"{SPACES}/{self.space_id}/messages/{message_id}").status, 200)

    def test_the_author_edits_and_deletes_their_own_message(self):
        message_id = self.post_as(self.reader)
        self.assertEqual(self.update(self.reader, message_id).status, 200)
        self.assertEqual(self.delete(self.reader, message_id).status, 200)

    def test_the_space_owner_edits_and_deletes_any_message(self):
        message_id = self.post_as(self.reader)
        self.assertEqual(self.update(self.owner, message_id).status, 200)
        self.assertEqual(self.delete(self.owner, message_id).status, 200)

    def test_an_admin_edits_and_deletes_any_message(self):
        message_id = self.post_as(self.reader)
        self.assertEqual(self.update(self.admin, message_id).status, 200)
        self.assertEqual(self.delete(self.admin, message_id).status, 200)

    def test_only_the_owner_or_an_admin_updates_a_space(self):
        for user in (self.reader, self.other):
            r = self.update_space(user)
            self.assertEqual(r.status, 403, f"{user.role}: HTTP {r.status} {r.text[:200]}")
        self.assertEqual(self.update_space(self.owner).status, 200)
        self.assertEqual(self.update_space(self.admin).status, 200)

    def test_only_the_owner_or_an_admin_deletes_a_space(self):
        space_id = self.create_space(self.other)
        for user in (self.reader, self.owner):
            r = user.delete(f"{SPACES}/{space_id}/delete")
            self.assertEqual(r.status, 403, f"{user.role}: HTTP {r.status} {r.text[:200]}")
        self.assertEqual(self.other.delete(f"{SPACES}/{space_id}/delete").status, 200)
        self.assertEqual(self.admin.delete(f"{SPACES}/{self.create_space(self.other)}/delete").status, 200)


def handler(tree: ast.AST, name: str) -> ast.AST:
    return next(n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name)


def reads_client_user_id(func: ast.AST) -> list[int]:
    """Lines where the handler reads "user_id" from the client's data: data.get("user_id", ...) or data["user_id"]."""
    lines = []
    for node in ast.walk(func):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get"
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "data"
                and node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == "user_id"):
            lines.append(node.lineno)
        if (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == "data"
                and isinstance(node.slice, ast.Constant) and node.slice.value == "user_id"):
            lines.append(node.lineno)
    return sorted(set(lines))


def own_calls(func: ast.AST):
    """Calls in the handler's own body, not in a coroutine nested inside it."""
    todo = list(func.body)
    while todo:
        node = todo.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if isinstance(node, ast.Call):
            yield node
        todo.extend(ast.iter_child_nodes(node))


def takes_session_user(func: ast.AST) -> bool:
    return any(isinstance(c.func, ast.Attribute) and c.func.attr == "get" and isinstance(c.func.value, ast.Name)
               and c.func.value.id == "SESSION_POOL" for c in own_calls(func))


class YdocUpdateTakesTheSessionUser(unittest.TestCase):
    """The live-edit handler broadcast every update under whatever user_id the client sent."""

    def setUp(self):
        self.handler = handler(ast.parse(SOCKET_MAIN.read_text()), "yjs_document_update")

    def test_the_handler_never_reads_a_client_sent_user_id(self):
        self.assertEqual(reads_client_user_id(self.handler), [], "socket/main.py reads data[\"user_id\"] at these lines")

    def test_the_handler_names_the_sessions_user(self):
        self.assertTrue(takes_session_user(self.handler), "no SESSION_POOL.get(sid) in the handler's own body")

    def test_the_checks_have_teeth(self):
        old = handler(ast.parse(
            'async def h(sid, data):\n'
            '    user_id = data.get("user_id", sid)\n'
            '    async def save():\n'
            '        SESSION_POOL.get(sid)\n'), "h")
        self.assertEqual(reads_client_user_id(old), [2])
        self.assertFalse(takes_session_user(old))
