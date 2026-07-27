"""Graft API — the Rootstock™ Graft Union™ surface.

Mounted under ``/api/v1/retrieval/sprigs`` to match the Rootstock Spec™ URL
contract. Admin-gated. Endpoints:
    GET  /catalog  -> the catalog + currently-grafted handles
    POST /graft    -> graft a capability: spawn an embedding Sprig™ and point the
                      OpenAI-compatible dispatch at it, or deliver a "deliver" sprig
                      (oras pull + sha256 verify + extract). Top-grafts an embedding
                      cultivar over any prior one. Revive = re-graft the same name.
    POST /prune    -> terminate + remove a grafted Sprig™; resets the embedding
                      dispatch when the pruned sprig was the active cultivar.

Grafts survive a Rootstock™ restart: the supervisor persists a volume-resident
state.json and reconciles on boot (see supervisor.py). DEFERRED: sigstore/cosign
verify (sha256 pin is the trust anchor), service-endpoint delivery, catalog variety
selection.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

from sage_is_ai.retrieval.utils import get_embedding_function
from sage_is_ai.sprigs.models import (
    GraftRequest,
    GraftResponse,
    PruneRequest,
    UiScriptingGrantRequest,
)
from sage_is_ai.utils.auth import get_admin_user

log = logging.getLogger(__name__)

router = APIRouter()


@router.get("/catalog")
async def get_sprig_catalog(request: Request, user=Depends(get_admin_user)):
    supervisor = request.app.state.sprig_supervisor
    from sage_is_ai.sprigs.supervisor import HOST_ARCH, _graft_refusal

    # Annotate each entry with host compatibility so the admin UI can disable
    # the Graft button for a sprig this host would refuse, instead of offering a
    # click that 503s. Uses the SAME fail-closed rule graft() enforces, so the
    # button and the guard can't drift: `compatible` is True only for an arch
    # match or a positively-declared architecture-neutral entry.
    catalog = {}
    for name, spec in supervisor.CATALOG.items():
        catalog[name] = {
            **spec,
            "compatible": _graft_refusal(spec, HOST_ARCH) is None,
        }
    cfg = request.app.state.config
    return {
        "catalog": catalog,
        "grafted": supervisor.handles(),
        "host_arch": HOST_ARCH,
        "active_ui": str(cfg.SPRIG_ACTIVE_UI or ""),
        # Surfaced so the panel can SHOW which Sprig holds scripting permission.
        # A permission nobody can see is a permission nobody revokes.
        "ui_scripting_grant": str(cfg.SPRIG_UI_SCRIPTING_GRANT or ""),
    }


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

    # Reranker server child: point the EXISTING external-reranker dispatch at the
    # grafted loopback /v1/rerank (shared with boot reconcile — no drift).
    if handle.capability == "reranker":
        from sage_is_ai.sprigs.reranker_dispatch import point_reranker_at

        cfg = request.app.state.config
        point_reranker_at(request.app, handle)
        return GraftResponse(
            status=True,
            name=handle.name,
            capability=handle.capability,
            base_url=handle.base_url,
            reranking_engine=cfg.RAG_RERANKING_ENGINE,
            reranking_model=cfg.RAG_RERANKING_MODEL,
            warning=entry.get("post_graft_note"),
        )

    # STT server child: point the EXISTING openai-compatible STT client at the
    # grafted whisper-server (shared with boot reconcile — no drift).
    if handle.capability == "stt":
        from sage_is_ai.sprigs.stt_dispatch import point_stt_at

        point_stt_at(request.app, handle)
        return GraftResponse(
            status=True,
            name=handle.name,
            capability=handle.capability,
            base_url=handle.base_url,
            warning=entry.get("post_graft_note"),
        )

    # Tika / Docling server children: point the EXISTING content-extraction
    # client at the grafted loopback and select the engine (shared with boot
    # reconcile — no drift). Replaces the tika/docling sidecar containers.
    if handle.capability == "tika":
        from sage_is_ai.sprigs.tika_dispatch import point_tika_at

        point_tika_at(request.app, handle)
        return GraftResponse(
            status=True,
            name=handle.name,
            capability=handle.capability,
            base_url=handle.base_url,
            warning=entry.get("post_graft_note"),
        )

    if handle.capability == "docling":
        from sage_is_ai.sprigs.docling_dispatch import point_docling_at

        point_docling_at(request.app, handle)
        return GraftResponse(
            status=True,
            name=handle.name,
            capability=handle.capability,
            base_url=handle.base_url,
            warning=entry.get("post_graft_note"),
        )

    # Theme sprig: validate the delivered css (fail-closed — a theme that
    # imports, references external URLs, or looks executable never activates),
    # then flip the one persisted pointer that /themes/active.css serves.
    if handle.capability == "theme":
        from sage_is_ai.sprigs.theme_dispatch import (
            ThemeValidationError,
            point_theme_at,
        )

        try:
            point_theme_at(request.app, handle)
        except ThemeValidationError as e:
            await supervisor.prune(handle.name)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Graft failed: {e}",
            )
        return GraftResponse(
            status=True,
            name=handle.name,
            capability=handle.capability,
            delivered=True,
            warning=entry.get("post_graft_note"),
        )

    # ui-Sprig: validate the delivered fragment (fail-closed — a fragment that
    # reaches off-origin, frames a document, or carries script without a grant
    # never activates), then flip the pointer /ui/active.html serves. Mirrors
    # the theme branch above, deliberately: same lifecycle, same failure, so an
    # operator who has grafted a theme already knows how this behaves.
    if handle.capability == "ui":
        from sage_is_ai.sprigs.ui_dispatch import UiValidationError, point_ui_at

        try:
            point_ui_at(request.app, handle)
        except UiValidationError as e:
            await supervisor.prune(handle.name)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Graft failed: {e}",
            )
        return GraftResponse(
            status=True,
            name=handle.name,
            capability=handle.capability,
            delivered=True,
            warning=entry.get("post_graft_note"),
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

    # Point the existing embedding dispatch at the grafted loopback Sprig™. Shared
    # with the supervisor boot reconcile (sprigs/embedding_dispatch.py) so a graft
    # from a request and a re-graft on restart are byte-identical. Sets the RAG_*
    # config (auto-persists), rebuilds EMBEDDING_FUNCTION, and records diagnostics.
    from sage_is_ai.sprigs.embedding_dispatch import point_embedding_at

    cfg = request.app.state.config
    point_embedding_at(request.app, handle)

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
    was_active_reranker = (
        h.get("capability") == "reranker"
        # ExternalReranker persists the FULL endpoint (base_url + /rerank).
        and cfg.RAG_EXTERNAL_RERANKER_URL == (h.get("base_url") or "") + "/rerank"
    )
    was_active_stt = (
        h.get("capability") == "stt"
        and h.get("base_url") == cfg.STT_OPENAI_API_BASE_URL
    )
    # Themes have no process and no base_url; active = the config pointer
    # names this sprig. First deliver-kind capability with a prune-time reset.
    was_active_theme = (
        h.get("capability") == "theme"
        and form_data.name == str(cfg.SPRIG_ACTIVE_THEME or "")
    )
    was_active_ui = (
        h.get("capability") == "ui"
        and form_data.name == str(cfg.SPRIG_ACTIVE_UI or "")
    )
    # Independent of "active": an admin can grant scripting to a Sprig that was
    # never activated, and removing it must still take the grant with it.
    had_scripting_grant = form_data.name == str(cfg.SPRIG_UI_SCRIPTING_GRANT or "")

    await supervisor.prune(form_data.name)

    if was_active_embedding:
        # Dispatch pointed at the pruned loopback; reset to "no embedding
        # configured" so requests fail clearly instead of hitting a dead port.
        from sage_is_ai.routers.retrieval import get_ef

        cfg.RAG_EMBEDDING_ENGINE = ""
        cfg.RAG_EMBEDDING_MODEL = ""
        # Clear the loopback URL + sprig-local sentinel key too, so no stale graft
        # marker survives to confuse the boot restart-safety guard (main.py).
        cfg.RAG_OPENAI_API_BASE_URL = ""
        cfg.RAG_OPENAI_API_KEY = ""
        request.app.state.ef = get_ef("", "")
        request.app.state.EMBEDDING_FUNCTION = get_embedding_function(
            "", "", request.app.state.ef, "", "", cfg.RAG_EMBEDDING_BATCH_SIZE
        )
        if getattr(request.app.state, "MODEL_DOWNLOAD_STATUS", None):
            request.app.state.MODEL_DOWNLOAD_STATUS["embedding"] = "pending"
        log.info("pruned active embedding sprig '%s'; dispatch reset", form_data.name)

    if was_active_reranker:
        # Hybrid search null-checks RERANKING_FUNCTION, so this degrades to
        # "no rerank" — the honest state — instead of scoring against a dead port.
        cfg.RAG_RERANKING_ENGINE = ""
        cfg.RAG_RERANKING_MODEL = ""
        cfg.RAG_EXTERNAL_RERANKER_URL = ""
        cfg.RAG_EXTERNAL_RERANKER_API_KEY = ""
        request.app.state.rf = None
        request.app.state.RERANKING_FUNCTION = None
        log.info("pruned active reranker sprig '%s'; reranking reset", form_data.name)

    if was_active_stt:
        # Engine "" = the local faster-whisper path, which on a slim rootstock
        # fails with a clear ImportError instead of POSTing a dead loopback.
        cfg.STT_ENGINE = ""
        cfg.STT_MODEL = ""
        cfg.STT_OPENAI_API_BASE_URL = ""
        cfg.STT_OPENAI_API_KEY = ""
        request.app.state.faster_whisper_model = None
        if getattr(request.app.state, "MODEL_DOWNLOAD_STATUS", None):
            import os as _os

            _wdir = _os.environ.get("WHISPER_MODEL_DIR", "")
            request.app.state.MODEL_DOWNLOAD_STATUS["whisper"] = (
                "ready"
                if _wdir and _os.path.isdir(_wdir) and _os.listdir(_wdir)
                else "pending"
            )
        log.info("pruned active stt sprig '%s'; STT dispatch reset", form_data.name)

    if was_active_theme:
        # /themes/active.css falls back to the empty default sheet immediately;
        # the volume copy is gone with the prune, the pointer must follow.
        cfg.SPRIG_ACTIVE_THEME = ""
        log.info("pruned active theme sprig '%s'; default look restored", form_data.name)

    if was_active_ui:
        # Same shape as the theme reset: the bundle is gone, so the pointer goes
        # with it and /ui/active.html serves nothing.
        cfg.SPRIG_ACTIVE_UI = ""
        log.info("pruned active ui sprig '%s'; fragment removed", form_data.name)

    if had_scripting_grant:
        # Revoking at prune is the plan's rule, and it is also the only way the
        # grant cannot outlive what it was granted to: a name left behind here
        # would silently re-arm if the same Sprig were ever grafted again.
        cfg.SPRIG_UI_SCRIPTING_GRANT = ""
        log.info("revoked scripting grant for pruned sprig '%s'", form_data.name)

    # Pruning a delivered capability silently changes what the rest of the
    # product can do, so the response says which, in words. The booleans stay
    # for callers that branch on them; the sentences exist so that every panel
    # does not carry its own copy of them — the Svelte panel, the island and the
    # fragment view all restated these independently, which is precisely the
    # written-twice drift this codebase is trying to shed.
    resets = [
        (was_active_embedding,
         "Embedding dispatch reset — graft a cultivar to restore document search."),
        (was_active_reranker,
         "Reranking reset — hybrid search runs without rerank until a reranker is grafted."),
        (was_active_stt,
         "Speech-to-text reset — graft an STT Sprig™ to restore local voice input."),
        (was_active_theme,
         "Theme reset — the interface returns to the default look on reload."),
        (was_active_ui,
         "Fragment removed — the page returns to its default layout on reload."),
        (had_scripting_grant,
         "Scripting permission revoked with the Sprig™ it was granted to."),
    ]

    return {
        "status": True,
        "name": form_data.name,
        "pruned": True,
        "embedding_reset": was_active_embedding,
        "reranking_reset": was_active_reranker,
        "stt_reset": was_active_stt,
        "theme_reset": was_active_theme,
        "ui_reset": was_active_ui,
        "scripting_grant_revoked": had_scripting_grant,
        "messages": [text for fired, text in resets if fired],
    }


@router.post("/ui/scripting")
async def set_ui_scripting_grant(
    request: Request,
    form_data: UiScriptingGrantRequest,
    user=Depends(get_admin_user),
):
    """Grant or revoke one ui-Sprig's permission to carry script.

    Modelled on how Apple gates unsigned apps: the default contract is markup
    only, a fragment carrying script is refused at graft, and an admin who has
    read that fragment may deliberately widen the rule for that one Sprig.

    Exactly one grant exists at a time, held by NAME. Granting to a second
    Sprig moves it rather than adding to it, so "which fragment may run code"
    always has one answer an operator can read off the panel.

    Revoking takes effect on the next request without a regraft: /ui/active.html
    revalidates against the current grant before serving, so a fragment that
    only passed because of a grant stops being served the moment it is gone.
    """
    supervisor = request.app.state.sprig_supervisor
    entry = supervisor.CATALOG.get(form_data.name)
    # Same allowlist discipline as graft: a grant is only meaningful for a
    # catalog entry that could actually become the active fragment.
    if entry is None or entry.get("capability") != "ui":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{form_data.name}' is not a ui-Sprig in the catalog",
        )

    cfg = request.app.state.config
    if form_data.allow:
        cfg.SPRIG_UI_SCRIPTING_GRANT = form_data.name
        log.info("scripting granted to ui sprig '%s' by %s", form_data.name, user.id)
    else:
        if str(cfg.SPRIG_UI_SCRIPTING_GRANT or "") == form_data.name:
            cfg.SPRIG_UI_SCRIPTING_GRANT = ""
            log.info("scripting revoked for ui sprig '%s' by %s", form_data.name, user.id)

    return {
        "status": True,
        "name": form_data.name,
        "ui_scripting_grant": str(cfg.SPRIG_UI_SCRIPTING_GRANT or ""),
    }
