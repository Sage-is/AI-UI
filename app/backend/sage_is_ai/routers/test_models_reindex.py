"""Every write to the models router rebuilds the model index (routers/models.py `_reindex`).

The chat path finds a model only in app.state.MODELS, so a model made through the API
answered "Model not found" until someone listed models. Runs inside the image or the dev
container with a throwaway key and database:
    python3 -B -m unittest sage_is_ai.routers.test_models_reindex
"""

import ast
import asyncio
import types
import unittest
from pathlib import Path
from unittest import mock

from sage_is_ai.routers import models as router

ADMIN = types.SimpleNamespace(id="u1", role="admin")
MODEL = types.SimpleNamespace(id="rs-model", user_id="u1", access_control=None)
REQUEST = types.SimpleNamespace(
    app=types.SimpleNamespace(state=types.SimpleNamespace())
)


def table(**overrides):
    """A stand-in Models table: the id is free for a create, taken for the rest."""
    fake = mock.MagicMock()
    fake.get_model_by_id.return_value = MODEL
    for name in ("insert_new_model", "toggle_model_by_id", "update_model_by_id"):
        getattr(fake, name).return_value = MODEL
    fake.configure_mock(**overrides)
    return fake


WRITES = {
    "create": lambda: router.create_new_model(
        REQUEST, mock.MagicMock(id="rs-model"), ADMIN
    ),
    "toggle": lambda: router.toggle_model_by_id(REQUEST, "rs-model", ADMIN),
    "update": lambda: router.update_model_by_id(
        REQUEST, "rs-model", mock.MagicMock(), ADMIN
    ),
    "delete": lambda: router.delete_model_by_id(REQUEST, "rs-model", ADMIN),
    "delete all": lambda: router.delete_all_models(REQUEST, ADMIN),
}


class EveryWriteReindexes(unittest.TestCase):
    def run_write(self, name, refresh):
        fake = table(
            **({"get_model_by_id.return_value": None} if name == "create" else {})
        )
        with (
            mock.patch.object(router, "Models", fake),
            mock.patch("sage_is_ai.utils.models.get_all_models", refresh),
        ):
            return asyncio.run(WRITES[name]())

    def test_each_write_rebuilds_the_index(self):
        for name in WRITES:
            with self.subTest(name):
                refresh = mock.AsyncMock()
                self.run_write(name, refresh)
                refresh.assert_awaited_once_with(REQUEST, user=ADMIN)

    def test_a_failed_refresh_never_fails_the_write(self):
        refresh = mock.AsyncMock(side_effect=RuntimeError("provider down"))
        self.assertIs(self.run_write("create", refresh), MODEL)

    def test_a_new_write_route_cannot_forget_the_index(self):
        # Every non-GET route in the router awaits _reindex, so the next one added does too.
        tree = ast.parse(Path(router.__file__).read_text())
        for func in tree.body:
            routes = [
                d
                for d in getattr(func, "decorator_list", [])
                if isinstance(d, ast.Call)
                and getattr(d.func, "attr", "") in ("post", "delete")
            ]
            if routes:
                calls = {
                    getattr(n.func, "id", "")
                    for n in ast.walk(func)
                    if isinstance(n, ast.Call)
                }
                self.assertIn(
                    "_reindex",
                    calls,
                    f"{func.name} writes but never rebuilds the index",
                )

    def test_every_caller_passes_the_request(self):
        # The write routes took `request` on 2026-11-02 and the agents page kept
        # calling toggle and delete without it: a TypeError, a 500 on the page
        # (pages-action-response.cy.ts, 2026-11-05). Every direct caller in the
        # backend must pass it by name.
        routes = {
            "create_new_model",
            "toggle_model_by_id",
            "update_model_by_id",
            "delete_model_by_id",
            "delete_all_models",
        }
        backend = Path(router.__file__).resolve().parents[1]
        missing = []
        for path in backend.rglob("*.py"):
            if path.name.startswith("test_") or path == Path(router.__file__).resolve():
                continue
            for node in ast.walk(ast.parse(path.read_text())):
                if (
                    isinstance(node, ast.Call)
                    and getattr(node.func, "id", getattr(node.func, "attr", ""))
                    in routes
                    and not isinstance(node.func, ast.Attribute)
                    and "request" not in {k.arg for k in node.keywords}
                    and not node.args
                ):
                    missing.append(f"{path.relative_to(backend)}:{node.lineno}")
        self.assertEqual(missing, [], "calls a model write route without request=")


if __name__ == "__main__":
    unittest.main()
