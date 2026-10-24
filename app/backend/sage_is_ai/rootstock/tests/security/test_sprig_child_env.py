"""A Sprig child inherits an allowlist of the Rootstock's environment, never its secrets
(TODO.md, "Sprig children inherit the whole environment, WEBUI_SECRET_KEY included").

Unit tests on sprigs/supervisor.child_environment, plus a read of the source: graft() no longer
copies os.environ into a child.
"""

from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest import mock

from sage_is_ai.sprigs import supervisor

SUPERVISOR = Path(supervisor.__file__)

PARENT = {
    # The Rootstock's own secrets, and the ones it holds for providers and services.
    "WEBUI_SECRET_KEY": "sign", "PRIVACY_KEY": "priv", "JWT_SECRET": "s",
    "OPENAI_API_KEY": "sk", "ANTHROPIC_API_KEY": "sk", "DATABASE_PASSWORD": "pw", "SMTP_PASSWORD": "pw",
    "HF_TOKEN": "hf", "SPRIG_REGISTRY_TOKEN": "tok", "GITHUB_TOKEN": "tok",
    "DATABASE_URL": "postgresql://u:pw@db/ai", "REDIS_URL": "redis://x", "WEBUI_URL": "https://ai.example",
    "OLLAMA_BASE_URL": "http://ollama:11434",
    # What a child reads: the process basics, Python, the offline model caches, its own SPRIG_* switches.
    "PATH": "/usr/local/bin:/usr/bin", "HOME": "/root", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "TZ": "UTC",
    "PYTHONPATH": "/app/backend", "PYTHONDONTWRITEBYTECODE": "1", "HF_HOME": "/app/backend/data/cache/hf",
    "HF_HUB_OFFLINE": "1", "SPRIG_EMBEDDING_DEVICE": "cpu", "SPRIG_REGISTRY": "local-registry:5000",
    "RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE": "False", "HTTPS_PROXY": "http://proxy:3128", "no_proxy": "localhost",
    "OMP_NUM_THREADS": "4",
}
SECRETS = {k for k in PARENT if k.endswith(("_API_KEY", "_PASSWORD", "_TOKEN", "_URL"))
           or k in ("WEBUI_SECRET_KEY", "PRIVACY_KEY", "JWT_SECRET")}
NEEDED = set(PARENT) - SECRETS


class ChildEnvironment(unittest.TestCase):
    def test_no_secret_reaches_a_child(self):
        child = supervisor.child_environment(PARENT)
        self.assertEqual(sorted(set(child) & SECRETS), [])

    def test_what_a_child_reads_comes_through_unchanged(self):
        child = supervisor.child_environment(PARENT)
        self.assertEqual({k: child.get(k) for k in NEEDED}, {k: PARENT[k] for k in NEEDED})

    def test_the_default_source_is_this_process(self):
        with mock.patch.dict(os.environ, {"SPRIG_TEST_MARKER": "1", "WEBUI_SECRET_KEY": "x"}):
            child = supervisor.child_environment()
        self.assertEqual(child.get("SPRIG_TEST_MARKER"), "1")
        self.assertNotIn("WEBUI_SECRET_KEY", child)

    def test_graft_no_longer_copies_the_whole_environment(self):
        source = SUPERVISOR.read_text()
        self.assertFalse("**os.environ" in source, "graft() still copies os.environ into a child")
        self.assertTrue("child_environment()" in source, "graft() does not build the child's environment from the allowlist")
