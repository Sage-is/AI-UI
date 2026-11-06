"""The env-only LLM connection registers in any mode, from the mode's own names.

Outside trial mode `SAGE_LLM_*` drives it; trial mode keeps `TRY_SAGE_LLM_*`.
Either way the key lives on app.state only, never in app.state.config.
"""

import unittest
from types import SimpleNamespace
from unittest import mock

from sage_is_ai.utils import try_sage_hidden_connections as hc

URL = "https://openrouter.ai/api/v1"


def app():
    return SimpleNamespace(state=SimpleNamespace(config=SimpleNamespace()))


def env(try_mode=False, url="", key="", models=(), try_url="", try_key=""):
    return mock.patch.multiple(
        hc,
        ENABLE_TRY_SAGE=try_mode,
        SAGE_LLM_API_URL=url,
        SAGE_LLM_API_KEY=key,
        SAGE_LLM_MODELS=list(models),
        TRY_SAGE_LLM_API_URL=try_url,
        TRY_SAGE_LLM_API_KEY=try_key,
        TRY_SAGE_LLM_MODELS=[],
    )


class OutsideTrialMode(unittest.TestCase):
    def test_url_and_key_register_one_hidden_connection(self):
        a = app()
        with env(url=URL + "/", key="sk-or-test"):
            hc.register_hidden_connections(a)
        [conn] = hc.get_hidden_connections(a)
        self.assertEqual(conn["url"], URL)
        self.assertEqual(conn["key"], "sk-or-test")
        self.assertTrue(hc.is_hidden_connection(conn))
        self.assertEqual(vars(a.state.config), {})

    def test_unset_registers_nothing_and_clears_an_earlier_boot(self):
        a = app()
        with env(url=URL, key="sk-or-test"):
            hc.register_hidden_connections(a)
        with env():
            hc.register_hidden_connections(a)
        self.assertEqual(hc.get_hidden_connections(a), [])

    def test_a_url_without_a_key_registers_nothing(self):
        a = app()
        with env(url=URL):
            hc.register_hidden_connections(a)
        self.assertEqual(hc.get_hidden_connections(a), [])

    def test_trial_names_are_ignored(self):
        a = app()
        with env(try_url=URL, try_key="sk-trial"):
            hc.register_hidden_connections(a)
        self.assertEqual(hc.get_hidden_connections(a), [])

    def test_sage_llm_models_narrow_the_list(self):
        a = app()
        with env(url=URL, key="sk-or-test", models=["qwen3-32b"]):
            hc.register_hidden_connections(a)
            [conn] = hc.get_hidden_connections(a)
            mine = lambda i: {"id": i, "_try_sage_hidden_id": conn["id"]}  # noqa: E731
            kept = hc.filter_models_to_allowlist(
                [mine("qwen/qwen3-32b"), mine("openai/gpt-4o")], conn["id"]
            )
        self.assertEqual([m["id"] for m in kept], ["qwen/qwen3-32b"])


class TrialMode(unittest.TestCase):
    def test_trial_reads_its_own_names_and_turns_the_arena_off(self):
        a = app()
        with env(try_mode=True, url=URL, key="sk-or-test", try_url=URL, try_key="sk-trial"):
            hc.register_hidden_connections(a)
        [conn] = hc.get_hidden_connections(a)
        self.assertEqual(conn["key"], "sk-trial")
        self.assertIs(a.state.config.ENABLE_EVALUATION_ARENA_MODELS, False)


if __name__ == "__main__":
    unittest.main()
