"""Point the Rootstock™ content-extraction config at a grafted Tika Sprig™.

Shared by the graft route (``routers/sprigs.py``) and the supervisor boot
reconcile (``supervisor.py``) so the two can never drift. The grafted child is
Apache Tika Server on a loopback port; ``retrieval/loaders/main.py``'s
``engine == "tika"`` path POSTs to ``TIKA_SERVER_URL``, so pointing that config
AND selecting the engine routes Office/PDF extraction through the in-container
server — no ``tika`` sidecar, replacing the ``http://tika:9998`` default.
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def point_tika_at(app, handle) -> None:
    """Repoint ``TIKA_SERVER_URL`` at ``handle``'s loopback and select the tika
    engine. ``handle.base_url`` ends in ``/v1`` (the generic sprig shape); Tika
    serves at the bare base, so the URL is rebuilt from the reserved port."""
    cfg = app.state.config
    base = f"http://127.0.0.1:{handle.port}"

    cfg.TIKA_SERVER_URL = base
    # Grafting Tika means the operator wants Tika extraction — select it so
    # uploads actually route through the server (the built-in extractor runs
    # when CONTENT_EXTRACTION_ENGINE is unset).
    cfg.CONTENT_EXTRACTION_ENGINE = "tika"

    from sage_is_ai.diagnostics import endpoint_health

    endpoint_health.record_success(base, capability="sprig:tika")
    log.info("Tika Sprig™ active at %s (CONTENT_EXTRACTION_ENGINE=tika)", base)
