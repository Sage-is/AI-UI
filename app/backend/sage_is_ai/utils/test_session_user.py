"""A database error behind a session reads as 503, not "session expired" (utils/auth.py `session_user`).

`Users.get_user_by_id` turned every exception into None, so get_current_user answered 401
"your session has expired" when the database was busy. Runs inside the image or the dev
container with a throwaway key and database:
    python3 -B -m unittest sage_is_ai.utils.test_session_user
"""

import types
import unittest
from unittest import mock

from fastapi import HTTPException

from sage_is_ai.utils import auth

USER = types.SimpleNamespace(id="u1")


def lookup(*results):
    """A stand-in lookup that answers, or raises, in turn."""
    return mock.patch.object(auth.Users, "lookup_user_by_id", side_effect=list(results))


class SessionUser(unittest.TestCase):
    def test_a_user_comes_back(self):
        with lookup(USER):
            self.assertIs(auth.session_user("u1"), USER)

    def test_a_missing_row_is_none_so_the_caller_answers_401(self):
        with lookup(None):
            self.assertIsNone(auth.session_user("gone"))

    def test_one_database_error_is_read_again(self):
        with lookup(RuntimeError("database is locked"), USER) as found:
            self.assertIs(auth.session_user("u1"), USER)
        self.assertEqual(found.call_count, 2)

    def test_a_database_that_will_not_answer_is_503_not_401(self):
        with lookup(
            RuntimeError("database is locked"), RuntimeError("database is locked")
        ):
            with self.assertRaises(HTTPException) as refused:
                auth.session_user("u1")
        self.assertEqual(refused.exception.status_code, 503)


if __name__ == "__main__":
    unittest.main()
