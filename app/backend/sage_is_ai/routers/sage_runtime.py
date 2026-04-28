"""
try.sage trial-mode runtime endpoints.

This router is the public face of the trial subsystem. It exposes:

  - GET  /status      banner countdown + tutorial step list (public when on)
  - GET  /personas    persona list with magic-link login URLs (public when on)
  - GET  /limits      trial caps + allowed model list (public when on)
  - GET  /llm-status  admin diagnostic — whether the hidden LLM is wired up
  - POST /extend      admin — advance the reset deadline by one extension
  - POST /reset       admin — force a reset right now

All endpoints return 404 (not 403) when ENABLE_TRY_SAGE is False, so the
surface is invisible — and unprobeable — in non-trial deployments.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from sage_is_ai.env import ENABLE_TRY_SAGE, SRC_LOG_LEVELS
from sage_is_ai.utils.auth import get_admin_user
from sage_is_ai.utils.try_sage_hidden_connections import get_hidden_status
from sage_is_ai.utils.try_sage_seed import (
    get_persona_definitions,
    mint_persona_magic_link,
    reset_persona_state,
)


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MAIN", "INFO"))

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Why 404, not 403: a 403 confirms the route exists, which would let an
# attacker probe whether a deployment runs in trial mode. 404 makes the
# trial subsystem look like it was never installed.
_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND)


def _require_try_sage_enabled() -> None:
    """Single guard used by every public endpoint. Module-level constant
    rather than a Depends() dependency so admin endpoints can stack the
    enabled check before authentication failures generate misleading 401s."""
    if not ENABLE_TRY_SAGE:
        raise _NOT_FOUND


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_reset_at(raw: str) -> Optional[datetime]:
    """The reset timestamp is stored as an ISO8601 string so it survives
    config persistence. Empty string means "never set" — first call
    initialises it. Parse failures degrade to None and are recovered by
    the caller setting a fresh timestamp."""
    if not raw:
        return None
    try:
        # fromisoformat accepts both naive and tz-aware; we always emit
        # tz-aware UTC, but be tolerant of operator-edited values.
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        log.warning("TRY_SAGE_RESET_AT failed to parse: %r", raw)
        return None


def _ensure_reset_at(request: Request) -> datetime:
    """Returns the current reset deadline, initialising it on first read.
    Persisted via PersistentConfig so a pod that bounces mid-window picks
    up where it left off."""
    cfg = request.app.state.config
    parsed = _parse_reset_at(cfg.TRY_SAGE_RESET_AT)
    if parsed is None:
        parsed = _now_utc() + timedelta(hours=cfg.TRY_SAGE_RESET_INTERVAL_HOURS)
        cfg.TRY_SAGE_RESET_AT = parsed.isoformat()
    return parsed


def _get_persona_link(
    request: Request, persona_key: str, email: str, ttl_hours: int
) -> str:
    """Return the cached magic-link URL for a persona.

    No silent rotation. The seed populates the cache once at boot and
    every entry survives across resets — operators want stable URLs
    they can hand out before a workshop and trust across the full
    `TRY_SAGE_PERSONA_LINK_TTL_DAYS` window (7 days by default).

    The only path that mints a fresh link from this endpoint is the
    cold-start race: lifespan startup hadn't populated the cache yet
    when the first `/personas` request landed. After that the cache
    serves every read.

    To force fresh URLs (e.g., after a JWT-secret rotation, or when
    the operator wants to invalidate previously-shared links), restart
    the container — the cache lives on `app.state` and is rebuilt on
    boot.
    """
    cache = getattr(request.app.state, "try_sage_persona_links", None)
    cached = cache.get(persona_key) if cache else None
    if cached:
        return cached

    # Cold-start fallback. Mint and cache so subsequent reads are stable.
    fresh = mint_persona_magic_link(email, ttl_hours)
    if cache is None:
        request.app.state.try_sage_persona_links = {}
        cache = request.app.state.try_sage_persona_links
    cache[persona_key] = fresh
    return fresh


# ---------------------------------------------------------------------------
# Response models — kept minimal; the frontend stores accept dicts directly.
# ---------------------------------------------------------------------------


class StatusResponse(BaseModel):
    enabled: bool
    reset_at: str
    hours_until_reset: float
    banner_text: str
    tutorial_steps: list  # List[dict] — opaque shape, defined by config


class PersonaEntry(BaseModel):
    key: str
    label: str
    role: str
    login_url: str


class LimitsResponse(BaseModel):
    allowed_models: list[str]
    seat_count: int
    reset_interval_hours: int


class LLMStatusResponse(BaseModel):
    configured: bool
    model_count: int


class ExtendResponse(BaseModel):
    reset_at: str
    extended_by_hours: int


class ResetResponse(BaseModel):
    reset_at: str
    wiped_personas: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/status", response_model=StatusResponse)
async def get_status(request: Request):
    _require_try_sage_enabled()
    cfg = request.app.state.config
    reset_at = _ensure_reset_at(request)
    hours = max(0.0, (reset_at - _now_utc()).total_seconds() / 3600.0)

    # Tutorial steps come through as a JSON string so admins can edit
    # them via the config UI without restarting. Parse defensively.
    raw = cfg.TRY_SAGE_TUTORIAL_STEPS_JSON or ""
    try:
        steps = json.loads(raw) if raw else []
        if not isinstance(steps, list):
            steps = []
    except json.JSONDecodeError:
        log.warning("TRY_SAGE_TUTORIAL_STEPS_JSON failed to parse; serving empty list")
        steps = []

    return {
        "enabled": True,
        "reset_at": reset_at.isoformat(),
        "hours_until_reset": round(hours, 4),
        "banner_text": cfg.TRY_SAGE_BANNER_TEXT,
        "tutorial_steps": steps,
    }


@router.get("/personas", response_model=list[PersonaEntry])
async def get_personas(request: Request):
    _require_try_sage_enabled()
    # TTL only matters on the cold-start cache-miss path inside
    # `_get_persona_link`. Once seed has populated the cache, this value
    # is unused — links live as long as the JWT they were minted with.
    ttl_hours = int(request.app.state.config.TRY_SAGE_PERSONA_LINK_TTL_DAYS) * 24
    return [
        {
            "key": p["key"],
            "label": p["label"],
            "role": p["role"],
            "login_url": _get_persona_link(
                request, p["key"], p["email"], ttl_hours
            ),
        }
        for p in get_persona_definitions(request.app)
    ]


@router.get("/limits", response_model=LimitsResponse)
async def get_limits(request: Request):
    _require_try_sage_enabled()
    # The allowlist is the env-only TRY_SAGE_LLM_MODELS — already parsed
    # at import time. Surface it here for the frontend's "what models can
    # I use?" prompt without leaking the URL or key.
    from sage_is_ai.env import TRY_SAGE_LLM_MODELS

    cfg = request.app.state.config
    return {
        "allowed_models": list(TRY_SAGE_LLM_MODELS),
        "seat_count": cfg.TRY_SAGE_USER_SEAT_COUNT,
        "reset_interval_hours": cfg.TRY_SAGE_RESET_INTERVAL_HOURS,
    }


@router.get("/llm-status", response_model=LLMStatusResponse)
async def get_llm_status(request: Request, user=Depends(get_admin_user)):
    _require_try_sage_enabled()
    # Diagnostic-only. Never returns the URL or key — that contract is
    # enforced inside get_hidden_status itself.
    return get_hidden_status(request.app)


@router.post("/extend", response_model=ExtendResponse)
async def extend_reset(request: Request, user=Depends(get_admin_user)):
    _require_try_sage_enabled()
    cfg = request.app.state.config
    extend_by = int(cfg.TRY_SAGE_ADMIN_EXTEND_HOURS)
    interval = int(cfg.TRY_SAGE_RESET_INTERVAL_HOURS)
    current = _ensure_reset_at(request)

    # Cap: one extension at a time. If reset_at is already further out
    # than (now + interval), the deadline has been extended within this
    # window and another extension would stack — refuse.
    ceiling = _now_utc() + timedelta(hours=interval + extend_by)
    if current >= ceiling - timedelta(seconds=1):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Already extended this window. Wait for the current "
            "deadline to pass or call /reset to start over.",
        )

    new_deadline = current + timedelta(hours=extend_by)
    cfg.TRY_SAGE_RESET_AT = new_deadline.isoformat()

    log.info(
        "try_sage.admin.extend by=%dh actor=%s reset_at=%s",
        extend_by,
        getattr(user, "email", "<unknown>"),
        new_deadline.isoformat(),
    )
    return {"reset_at": new_deadline.isoformat(), "extended_by_hours": extend_by}


@router.post("/reset", response_model=ResetResponse)
async def force_reset(request: Request, user=Depends(get_admin_user)):
    _require_try_sage_enabled()
    cfg = request.app.state.config

    # Emit the audit line BEFORE the wipe so it lands in logs even if the
    # wipe explodes mid-flight.
    log.info(
        "try_sage.admin.reset actor=%s",
        getattr(user, "email", "<unknown>"),
    )

    await reset_persona_state(request.app)
    persona_count = len(get_persona_definitions(request.app))

    new_deadline = _now_utc() + timedelta(hours=cfg.TRY_SAGE_RESET_INTERVAL_HOURS)
    cfg.TRY_SAGE_RESET_AT = new_deadline.isoformat()

    return {"reset_at": new_deadline.isoformat(), "wiped_personas": persona_count}
