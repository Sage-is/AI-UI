"""Each admin off-switch stops the filter (ON by default from 3.2.0).
Host-only: the one DB import is stubbed; active_for never reads the map."""

import re
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace

try:
    import sage_is_ai.models.privacy  # noqa: F401
except ImportError:
    sys.modules["sage_is_ai.models.privacy"] = types.ModuleType("stub")
    sys.modules["sage_is_ai.models.privacy"].PrivacyMaps = object

from sage_is_ai.privacy import hooks  # noqa: E402

EXT = {"id": "deepseek/x", "urlIdx": 0, "owned_by": "openai"}


def req(saved=None):
    cfg = SimpleNamespace(PRIVACY_CONFIG=saved)
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(config=cfg)))


def on(saved=None, model=EXT):
    return hooks.active_for(req(saved), model)


class OffSwitches(unittest.TestCase):
    def test_external_is_filtered_when_nobody_chose(self):
        self.assertTrue(on())

    def test_local_is_never_filtered_by_default(self):
        self.assertFalse(on(model={"id": "llama3", "owned_by": "ollama"}))

    def test_whole_instance_off(self):
        self.assertFalse(on({"enabled": False, "connections": {"0": True}}))

    def test_default_off_also_covers_a_saved_pre_3_2_config(self):
        self.assertFalse(on({"default_external": False}))

    def test_one_connection_off(self):
        self.assertFalse(on({"connections": {"0": False}}))

    def test_one_connection_on_when_default_off(self):
        self.assertTrue(on({"default_external": False, "connections": {"0": True}}))

    def test_config_py_and_hooks_defaults_agree(self):
        src = (Path(__file__).resolve().parents[1] / "config.py").read_text()
        m = re.search(r'"default_external":\s*(True|False)', src[src.index('"privacy.config"'):])
        self.assertEqual(m.group(1) == "True", hooks.DEFAULTS["default_external"])


if __name__ == "__main__":
    unittest.main()
