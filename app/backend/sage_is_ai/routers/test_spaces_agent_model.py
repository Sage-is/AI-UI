"""A Space agent's model (routers/spaces.py `_agent_model`): one reload when AI-UI's list lacks it.

Before this, an agent whose model was made after the list loaded stayed silent: the
mention was posted and nobody answered. Runs inside the image or the dev container:
    python3 -B -m unittest sage_is_ai.routers.test_spaces_agent_model
"""

import asyncio
import types
import unittest
from unittest import mock

from sage_is_ai.routers import spaces

LOADED = {"other": {"id": "other"}, "lia-crm": {"id": "lia-crm"}}


def request_with(models):
    return types.SimpleNamespace(app=types.SimpleNamespace(state=types.SimpleNamespace(MODELS=models)))


def reloads_to(models):
    async def reload(request, user=None):
        request.app.state.MODELS = dict(models)

    return mock.patch("sage_is_ai.utils.models.get_all_models", side_effect=reload)


class AgentModel(unittest.TestCase):
    def test_a_model_made_since_the_list_loaded_is_found_after_one_reload(self):
        request = request_with({"other": {"id": "other"}})
        with reloads_to(LOADED) as reload:
            self.assertEqual(asyncio.run(spaces._agent_model(request, "lia-crm", None)), {"id": "lia-crm"})
        reload.assert_called_once()

    def test_a_cold_start_loads_the_list(self):
        with reloads_to(LOADED) as reload:
            self.assertEqual(asyncio.run(spaces._agent_model(request_with({}), "lia-crm", None)), {"id": "lia-crm"})
        reload.assert_called_once()

    def test_a_listed_model_costs_no_reload(self):
        with reloads_to(LOADED) as reload:
            self.assertEqual(asyncio.run(spaces._agent_model(request_with(dict(LOADED)), "other", None)), {"id": "other"})
        reload.assert_not_called()

    def test_an_unknown_model_is_none_after_one_reload(self):
        with reloads_to(LOADED) as reload:
            self.assertIsNone(asyncio.run(spaces._agent_model(request_with(dict(LOADED)), "gone", None)))
        reload.assert_called_once()

    def test_no_model_id_never_reloads(self):
        with reloads_to(LOADED) as reload:
            self.assertIsNone(asyncio.run(spaces._agent_model(request_with({}), None, None)))
        reload.assert_not_called()


if __name__ == "__main__":
    unittest.main()
