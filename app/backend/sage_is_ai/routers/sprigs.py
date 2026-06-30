"""Graft API — Phase 8.0 first-graft walking skeleton.

Minimal Rootstock™ Graft Union™ surface: a catalog read and a single graft action
that spawns a local embedding Sprig™ and points the existing OpenAI-compatible
embedding dispatch at it. Mounted under ``/api/v1/retrieval/sprigs`` to match the
Rootstock Spec™ URL contract.

DEFERRED (graft #2+): prune / topgraft / revive, oras pull + sigstore verify,
service-endpoint delivery, variety selection. See Decision #19.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

from sage_is_ai.diagnostics import endpoint_health
from sage_is_ai.retrieval.utils import get_embedding_function
from sage_is_ai.sprigs.models import GraftRequest, GraftResponse
from sage_is_ai.utils.auth import get_admin_user

log = logging.getLogger(__name__)

router = APIRouter()


@router.get("/catalog")
async def get_sprig_catalog(request: Request, user=Depends(get_admin_user)):
    supervisor = request.app.state.sprig_supervisor
    return {"catalog": supervisor.CATALOG, "grafted": supervisor.handles()}


@router.post("/graft", response_model=GraftResponse)
async def graft_sprig(
    request: Request, form_data: GraftRequest, user=Depends(get_admin_user)
):
    supervisor = request.app.state.sprig_supervisor

    # Catalog allowlist (arbitrary-exec / SSRF defense): only known names and the
    # embedding capability may be grafted in this cut.
    if (
        form_data.name not in supervisor.CATALOG
        or form_data.capability != "embedding"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown sprig '{form_data.name}' or unsupported capability",
        )

    # Spawn the Sprig™ child process and poll it to healthy.
    try:
        handle = await supervisor.graft(form_data.name, form_data.capability)
    except Exception as e:
        log.exception("graft failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Graft failed: {e}",
        )

    # Point the existing embedding dispatch at the grafted loopback Sprig™.
    # Assigning to app.state.config.* auto-persists via PersistentConfig.save().
    cfg = request.app.state.config
    previous_url = cfg.RAG_OPENAI_API_BASE_URL
    if previous_url and previous_url != handle.base_url:
        log.info("graft replacing previous embedding base url %s", previous_url)
    cfg.RAG_EMBEDDING_ENGINE = "openai"
    cfg.RAG_EMBEDDING_MODEL = handle.model
    cfg.RAG_OPENAI_API_BASE_URL = handle.base_url
    cfg.RAG_OPENAI_API_KEY = "sprig-local"  # the mock ignores the key

    # Rebuild the embedding function (mirrors POST /embedding/update at
    # routers/retrieval.py:323-356). engine is hardcoded "openai" here, so we
    # pass the openai url/key directly instead of the nested-ternary selection.
    # Lazy import avoids any router import-order fragility.
    from sage_is_ai.routers.retrieval import get_ef

    request.app.state.ef = get_ef(cfg.RAG_EMBEDDING_ENGINE, cfg.RAG_EMBEDDING_MODEL)
    request.app.state.EMBEDDING_FUNCTION = get_embedding_function(
        cfg.RAG_EMBEDDING_ENGINE,
        cfg.RAG_EMBEDDING_MODEL,
        request.app.state.ef,
        cfg.RAG_OPENAI_API_BASE_URL,
        cfg.RAG_OPENAI_API_KEY,
        cfg.RAG_EMBEDDING_BATCH_SIZE,
        azure_api_version=None,
    )

    # Surface the grafted row in diagnostics immediately. (A real embedding would
    # otherwise register it on first call as capability "embedding/openai".)
    if getattr(request.app.state, "MODEL_DOWNLOAD_STATUS", None):
        request.app.state.MODEL_DOWNLOAD_STATUS["embedding"] = "ready"
    endpoint_health.record_success(handle.base_url, capability="sprig:embedding")

    return GraftResponse(
        status=True,
        name=handle.name,
        capability=handle.capability,
        base_url=handle.base_url,
        embedding_engine=cfg.RAG_EMBEDDING_ENGINE,
        embedding_model=cfg.RAG_EMBEDDING_MODEL,
    )
