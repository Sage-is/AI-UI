"""AI-UI answers web Tinker's GET /v1/model-login as its node (run sheet S10, 2026-11-17).

Web Tinker asks its node for a model once at start, with a bearer. AI-UI answers
provider `custom` at its own /api, so every build call comes back through
/api/chat/completions and the privacy filter. Runs inside the image or the dev
container with a throwaway key and database:
    python3 -B -m unittest sage_is_ai.routers.test_tinker_node
"""

import types
import unittest
from unittest import mock

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.testclient import TestClient

from sage_is_ai.routers import tinker_node
from sage_is_ai.utils.auth import get_verified_user

NODE_USER = types.SimpleNamespace(id="u-tinker", role="user")
KEY = {"Authorization": "Bearer sk-tinker-node"}


class ModelLogin(unittest.TestCase):
    def node(self, enabled=True, base_url="", model="tinker-build"):
        """The router plus a stand-in for main.py's SPA mount, which answers any
        unmatched non-api path with the shell and a 200."""
        for name, value in (
            ("ENABLE_TINKER_NODE", enabled),
            ("TINKER_NODE_BASE_URL", base_url),
            ("TINKER_NODE_MODEL", model),
        ):
            patcher = mock.patch.object(tinker_node, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        app = FastAPI()
        app.include_router(tinker_node.router)

        @app.get("/{path:path}")
        def spa_shell(path: str):
            return HTMLResponse("<!doctype html><title>Sage.is AI</title>")

        app.dependency_overrides[get_verified_user] = lambda: NODE_USER
        return TestClient(app)

    def test_off_answers_404_not_the_spa_shell(self):
        reply = self.node(enabled=False).get("/v1/model-login", headers=KEY)
        self.assertEqual(reply.status_code, 404)
        self.assertNotIn("text/html", reply.headers["content-type"])

    def test_off_answers_404_before_asking_for_a_key(self):
        reply = self.node(enabled=False).get("/v1/model-login")
        self.assertEqual(reply.status_code, 404)

    def test_no_key_answers_401_which_tinker_reads_as_refused(self):
        reply = self.node().get("/v1/model-login")
        self.assertEqual(reply.status_code, 401)

    def test_reply_is_a_custom_login_carrying_the_callers_key(self):
        reply = self.node(base_url="http://sage-is-ai-ui:8080/api").get(
            "/v1/model-login", headers=KEY
        )
        self.assertEqual(reply.status_code, 200)
        self.assertEqual(
            reply.json(),
            {
                "name": "Sage.is AI-UI",
                "provider": "custom",
                "base_url": "http://sage-is-ai-ui:8080/api",
                "api_key": "sk-tinker-node",
                "model": "tinker-build",
            },
        )

    def test_model_and_base_url_come_from_env(self):
        login = (
            self.node(base_url="https://ai.example.test/api/", model="other-preset")
            .get("/v1/model-login", headers=KEY)
            .json()
        )
        # Tinker posts to {base_url}/chat/completions, so no trailing slash.
        self.assertEqual(login["base_url"], "https://ai.example.test/api")
        self.assertEqual(login["model"], "other-preset")

    def test_base_url_falls_back_to_the_address_tinker_called(self):
        login = self.node().get("/v1/model-login", headers=KEY).json()
        self.assertEqual(login["base_url"], "http://testserver/api")


if __name__ == "__main__":
    unittest.main()
