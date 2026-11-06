"""Pruning and top-grafting leave honest state behind (2026-11-05).

Pruning Tika or Docling left `CONTENT_EXTRACTION_ENGINE` aimed at a released
port, so uploads POSTed a dead loopback and the boot probe called it unreachable.
A cultivar evicted mid-boot by a top-graft reported "exited on boot (rc=-15)",
which reads as a crash. Runs inside the image or the dev container with a
throwaway key and database:
    python3 -B -m unittest sage_is_ai.sprigs.test_prune_and_evict
"""

import asyncio
import types
import unittest
from unittest import mock

from sage_is_ai import config
from sage_is_ai.sprigs.models import SprigHandle
from sage_is_ai.sprigs.supervisor import SprigSupervisor

PORT = 41000
LOOPBACK = f"http://127.0.0.1:{PORT}"


def prune(
    name,
    capability,
    engine,
    tika=config.TIKA_SERVER_URL.env_value,
    docling=config.DOCLING_SERVER_URL.env_value,
):
    """Prune `name` through the route with stand-ins; returns (answer, config)."""
    from sage_is_ai.routers import sprigs as route

    cfg = types.SimpleNamespace(
        RAG_OPENAI_API_BASE_URL="",
        RAG_EXTERNAL_RERANKER_URL="",
        STT_OPENAI_API_BASE_URL="",
        SPRIG_ACTIVE_THEME="",
        SPRIG_ACTIVE_UI="",
        SPRIG_UI_SCRIPTING_GRANT="",
        SPRIG_WIRES={},
        CONTENT_EXTRACTION_ENGINE=engine,
        TIKA_SERVER_URL=tika,
        DOCLING_SERVER_URL=docling,
    )
    sup = types.SimpleNamespace(
        handles=lambda: {
            name: {"capability": capability, "port": PORT, "base_url": LOOPBACK + "/v1"}
        },
        prune=mock.AsyncMock(),
        clear_error=lambda name: False,
    )
    request = types.SimpleNamespace(
        app=types.SimpleNamespace(
            state=types.SimpleNamespace(config=cfg, sprig_supervisor=sup)
        )
    )
    answer = asyncio.run(
        route.prune_sprig(
            request, types.SimpleNamespace(name=name), user=types.SimpleNamespace()
        )
    )
    return answer, cfg


def handle(name, capability, process=None):
    return SprigHandle(
        name=name,
        capability=capability,
        port=PORT,
        base_url=LOOPBACK + "/v1",
        health_url=LOOPBACK + "/health",
        model="fixture",
        process=process,
    )


class PruneResetsExtraction(unittest.TestCase):
    def test_pruning_the_active_tika_restores_the_environment(self):
        answer, cfg = prune("tika", "tika", "tika", tika=LOOPBACK)
        self.assertTrue(answer["extraction_reset"])
        self.assertEqual(
            cfg.CONTENT_EXTRACTION_ENGINE, config.CONTENT_EXTRACTION_ENGINE.env_value
        )
        self.assertEqual(cfg.TIKA_SERVER_URL, config.TIKA_SERVER_URL.env_value)
        self.assertTrue(any("Document reading" in m for m in answer["messages"]))

    def test_pruning_the_active_docling_restores_the_environment(self):
        answer, cfg = prune("docling", "docling", "docling", docling=LOOPBACK)
        self.assertTrue(answer["extraction_reset"])
        self.assertEqual(
            cfg.CONTENT_EXTRACTION_ENGINE, config.CONTENT_EXTRACTION_ENGINE.env_value
        )
        self.assertEqual(cfg.DOCLING_SERVER_URL, config.DOCLING_SERVER_URL.env_value)

    def test_an_engine_chosen_since_the_graft_stays(self):
        # Tika was grafted, then the admin pointed extraction at a Docling
        # server elsewhere. Pruning Tika must not undo that choice.
        answer, cfg = prune(
            "tika",
            "tika",
            "docling",
            tika=LOOPBACK,
            docling="http://docling.example:5001",
        )
        self.assertFalse(answer["extraction_reset"])
        self.assertEqual(cfg.CONTENT_EXTRACTION_ENGINE, "docling")
        self.assertEqual(cfg.DOCLING_SERVER_URL, "http://docling.example:5001")


class EvictionSaysWhatHappened(unittest.TestCase):
    def test_a_top_graft_marks_the_cultivar_it_replaces(self):
        sup = object.__new__(SprigSupervisor)
        sup._sprigs = {
            "minilm": handle("minilm", "embedding"),
            "whisper": handle("whisper", "stt"),
        }
        sup._terminate = mock.AsyncMock()
        asyncio.run(sup._evict("multilingual-e5-large", "embedding"))
        self.assertEqual(sup._sprigs["minilm"].evicted_by, "multilingual-e5-large")
        self.assertIsNone(sup._sprigs["whisper"].evicted_by)
        sup._terminate.assert_awaited_once_with("minilm")

    def test_an_evicted_cultivar_says_it_was_replaced(self):
        sup = object.__new__(SprigSupervisor)
        evicted = handle("minilm", "embedding", types.SimpleNamespace(returncode=-15))
        evicted.evicted_by = "multilingual-e5-large"
        with self.assertRaisesRegex(
            RuntimeError,
            "pruned while booting: 'multilingual-e5-large' took over the embedding",
        ):
            asyncio.run(sup._wait_until_healthy(evicted, timeout=1))

    def test_a_crash_still_reads_as_a_crash(self):
        sup = object.__new__(SprigSupervisor)
        crashed = handle("minilm", "embedding", types.SimpleNamespace(returncode=1))
        with self.assertRaisesRegex(RuntimeError, r"exited on boot \(rc=1\)"):
            asyncio.run(sup._wait_until_healthy(crashed, timeout=1))


if __name__ == "__main__":
    unittest.main()
