"""The model list carries each provider field once (routers/openai.py).

Both merge sites used to spread the provider's model AND nest it again as
`"openai"`, which nothing reads. OpenRouter alone is 453 models, so the copy
doubled the heaviest response on every page (card "The SPA floor crept 539 kB").
Runs inside the image or the dev container with a throwaway key and database:
    python3 -B -m unittest sage_is_ai.routers.test_openai_model_list
"""

import asyncio
import types
import unittest
from unittest import mock

from sage_is_ai.routers import openai as router

PROVIDER_MODEL = {
    "id": "deepseek/deepseek-r1",
    "name": "DeepSeek R1",
    "context_length": 163840,
    "pricing": {"prompt": "0.0000004", "completion": "0.000002"},
}


def request(base_urls=("https://openrouter.ai/api/v1",)):
    config = types.SimpleNamespace(
        ENABLE_OPENAI_API=True, OPENAI_API_BASE_URLS=list(base_urls)
    )
    return types.SimpleNamespace(
        app=types.SimpleNamespace(state=types.SimpleNamespace(config=config))
    )


def assert_flat(case, model):
    case.assertNotIn("openai", model)
    for value in model.values():
        case.assertNotEqual(
            value, PROVIDER_MODEL, "a nested copy of the provider's model"
        )
    for field in PROVIDER_MODEL:
        case.assertEqual(model[field], PROVIDER_MODEL[field])


class ModelListIsFlat(unittest.TestCase):
    def test_public_connections(self):
        get_all = getattr(router.get_all_models, "__wrapped__", router.get_all_models)
        with (
            mock.patch.object(
                router,
                "get_all_models_responses",
                mock.AsyncMock(return_value=[{"data": [dict(PROVIDER_MODEL)]}]),
            ),
            mock.patch.object(
                router, "_get_hidden_connection_models", mock.AsyncMock(return_value=[])
            ),
        ):
            models = asyncio.run(get_all(request(), user=None))["data"]
        [model] = models
        assert_flat(self, model)
        self.assertEqual(model["urlIdx"], 0)

    def test_hidden_connection(self):
        with (
            mock.patch.object(
                router,
                "get_hidden_connections",
                return_value=[
                    {
                        "id": "hidden-1",
                        "url": "https://openrouter.ai/api/v1",
                        "key": "k",
                    }
                ],
            ),
            mock.patch.object(
                router,
                "send_get_request",
                mock.AsyncMock(return_value={"data": [dict(PROVIDER_MODEL)]}),
            ),
            mock.patch.object(
                router,
                "filter_models_to_allowlist",
                side_effect=lambda models, _id: models,
            ),
        ):
            models = asyncio.run(
                router._get_hidden_connection_models(request(), user=None)
            )
        [model] = models
        assert_flat(self, model)
        self.assertEqual(model["_try_sage_hidden_id"], "hidden-1")


if __name__ == "__main__":
    unittest.main()
