"""Point the Rootstock™ content-extraction config at a grafted Docling Sprig™.

Shared by the graft route (``routers/sprigs.py``) and the supervisor boot
reconcile (``supervisor.py``). The grafted child is ``docling-serve`` on a
loopback port; ``retrieval/loaders/main.py``'s ``engine == "docling"`` path
POSTs to ``DOCLING_SERVER_URL``, so pointing that config AND selecting the
engine routes layout-aware extraction through the in-container server — no
``docling`` sidecar, replacing the ``http://docling:5001`` default.
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def point_docling_at(app, handle) -> None:
    """Repoint ``DOCLING_SERVER_URL`` at ``handle``'s loopback and select the
    docling engine. ``handle.base_url`` ends in ``/v1``; docling-serve serves at
    the bare base, so the URL is rebuilt from the reserved port."""
    cfg = app.state.config
    base = f"http://127.0.0.1:{handle.port}"

    cfg.DOCLING_SERVER_URL = base
    cfg.CONTENT_EXTRACTION_ENGINE = "docling"

    from sage_is_ai.diagnostics import endpoint_health

    endpoint_health.record_success(base, capability="sprig:docling")
    log.info("Docling Sprig™ active at %s (CONTENT_EXTRACTION_ENGINE=docling)", base)
