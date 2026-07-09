"""Point the Rootstock™ STT dispatch at a grafted whisper Sprig™.

Shared by the graft route (``routers/sprigs.py``) and the supervisor's boot
reconcile (``supervisor.py``). The grafted child is a static whisper.cpp
``whisper-server`` launched with ``--inference-path /v1/audio/transcriptions``,
so the EXISTING ``STT_ENGINE == "openai"`` client path in routers/audio.py
(POST multipart ``file`` to ``{base}/audio/transcriptions``, parse
``r.json()["text"]``) works against it untouched — this only points config.
"""

from __future__ import annotations

import logging

from sage_is_ai.sprigs.embedding_dispatch import SPRIG_API_KEY

log = logging.getLogger(__name__)


def point_stt_at(app, handle) -> None:
    """Repoint the STT config at ``handle`` (base_url already ends in /v1).

    Also flips MODEL_DOWNLOAD_STATUS["whisper"] to ready — the setup wizard
    reads that status, so grafting makes the HF whisper download skippable.
    The ``sprig-local`` key marks the config graft-owned for the main.py
    restart backstop, mirroring the embedding sentinel.
    """
    cfg = app.state.config

    cfg.STT_ENGINE = "openai"
    cfg.STT_MODEL = "whisper-base"  # label only; whisper-server ignores the field
    cfg.STT_OPENAI_API_BASE_URL = handle.base_url
    cfg.STT_OPENAI_API_KEY = SPRIG_API_KEY

    # Mirror audio.py's config-update behavior for the non-local engine: drop
    # any loaded in-process faster-whisper model.
    app.state.faster_whisper_model = None

    if getattr(app.state, "MODEL_DOWNLOAD_STATUS", None):
        app.state.MODEL_DOWNLOAD_STATUS["whisper"] = "ready"

    from sage_is_ai.diagnostics import endpoint_health

    endpoint_health.record_success(handle.base_url, capability="sprig:stt")
