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
from sage_is_ai.sprigs.models import GraftRequest, GraftResponse, PruneRequest
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

    # Catalog allowlist (arbitrary-exec / SSRF defense): the name must be in the
    # catalog and the requested capability must match its entry.
    entry = supervisor.CATALOG.get(form_data.name)
    if entry is None or entry.get("capability") != form_data.capability:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown sprig '{form_data.name}' or capability mismatch",
        )

    # Capture prior embedding cultivar widths BEFORE grafting (top-graft will
    # terminate them) so we can warn on a dimensionality swap.
    new_dim = supervisor.CATALOG[form_data.name].get("dim")
    prior_dims = {
        supervisor.CATALOG.get(n, {}).get("dim")
        for n, h in supervisor.handles().items()
        if h.get("state") == "rooted"
        and supervisor.CATALOG.get(n, {}).get("capability") == "embedding"
    }
    prior_dims.discard(None)

    # Spawn the Sprig™ child process and poll it to healthy.
    try:
        handle = await supervisor.graft(form_data.name, form_data.capability)
    except Exception as e:
        log.exception("graft failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Graft failed: {e}",
        )

    # Non-embedding sprigs ("deliver": dev/build toolchain, vector DB, binaries)
    # don't touch the embedding dispatch — report the delivery and return. A
    # catalog post_graft_note (e.g. "restart to activate") surfaces as a warning.
    if handle.capability != "embedding":
        return GraftResponse(
            status=True,
            name=handle.name,
            capability=handle.capability,
            delivered=True,
            warning=entry.get("post_graft_note"),
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

    # Dimension-swap guard (best-effort, non-blocking): warn if we just top-grafted
    # away an embedding cultivar of a different width. Collections built at the old
    # width must be reindexed (Knowledge → Reindex) before they accept new vectors.
    # Full cross-session collection validation is deferred (graft #3).
    warning = None
    if new_dim is not None and any(d != new_dim for d in prior_dims):
        warning = (
            f"Embedding width changed to {new_dim}-dim. Knowledge bases embedded at "
            f"{sorted(prior_dims)}-dim must be reindexed (Knowledge → Reindex) before "
            f"they accept new queries."
        )
        log.warning(warning)

    return GraftResponse(
        status=True,
        name=handle.name,
        capability=handle.capability,
        base_url=handle.base_url,
        embedding_engine=cfg.RAG_EMBEDDING_ENGINE,
        embedding_model=cfg.RAG_EMBEDDING_MODEL,
        warning=warning,
    )


@router.post("/prune")
async def prune_sprig(
    request: Request, form_data: PruneRequest, user=Depends(get_admin_user)
):
    """Terminate + remove a grafted Sprig™. (Revive = re-graft via /graft.)"""
    supervisor = request.app.state.sprig_supervisor
    h = supervisor.handles().get(form_data.name)
    if h is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sprig '{form_data.name}' is not grafted",
        )

    cfg = request.app.state.config
    was_active_embedding = (
        h.get("capability") == "embedding"
        and h.get("base_url") == cfg.RAG_OPENAI_API_BASE_URL
    )

    await supervisor.prune(form_data.name)

    if was_active_embedding:
        # Dispatch pointed at the pruned loopback; reset to "no embedding
        # configured" so requests fail clearly instead of hitting a dead port.
        from sage_is_ai.routers.retrieval import get_ef

        cfg.RAG_EMBEDDING_ENGINE = ""
        cfg.RAG_EMBEDDING_MODEL = ""
        request.app.state.ef = get_ef("", "")
        request.app.state.EMBEDDING_FUNCTION = get_embedding_function(
            "", "", request.app.state.ef, "", "", cfg.RAG_EMBEDDING_BATCH_SIZE
        )
        if getattr(request.app.state, "MODEL_DOWNLOAD_STATUS", None):
            request.app.state.MODEL_DOWNLOAD_STATUS["embedding"] = "pending"
        log.info("pruned active embedding sprig '%s'; dispatch reset", form_data.name)

    return {
        "status": True,
        "name": form_data.name,
        "pruned": True,
        "embedding_reset": was_active_embedding,
    }
