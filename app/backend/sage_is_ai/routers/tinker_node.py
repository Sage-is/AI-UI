"""
AI-UI as web Tinker's node: GET /v1/model-login (2026-11-17).

Web Tinker (upstream `tenkts-server` with TENKTS_WEB=1) asks its node for a
model once at start: GET {TENKTS_WEB_NODE}/v1/model-login with
`Authorization: Bearer <TENKTS_WEB_NODE_TOKEN>` and a 20 s timeout. It reads
200 as a login, 204 as none and 401 as refused.

AI-UI answers provider `custom`, its own /api as the base URL and the caller's
own key, so every build comes back through /api/chat/completions as that user
and the privacy filter sees it.

The path is upstream's, so the router sits at the root, outside /api. The SPA
mount answers any unknown non-api path with the shell and a 200 (main.py,
SPAStaticFiles), so the router is always registered and raises its own 404
while ENABLE_TINKER_NODE is off.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials

from sage_is_ai.env import (
    ENABLE_TINKER_NODE,
    TINKER_NODE_BASE_URL,
    TINKER_NODE_MODEL,
)
from sage_is_ai.utils.auth import bearer_security, get_verified_user

router = APIRouter()


def _require_tinker_node_enabled() -> None:
    """404, not 401: while off, the route looks never installed. Listed first
    in the handler so it fires before any auth answer."""
    if not ENABLE_TINKER_NODE:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


def _bearer_key(
    auth: HTTPAuthorizationCredentials = Depends(bearer_security),
) -> str:
    """The key the reply hands back. Without a bearer, get_current_user answers
    403 or falls back to the session cookie; Tinker expects 401, and a cookie
    leaves no key to hand back."""
    if auth is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    return auth.credentials


@router.get("/v1/model-login")
def model_login(
    request: Request,
    _enabled: None = Depends(_require_tinker_node_enabled),
    key: str = Depends(_bearer_key),
    user=Depends(get_verified_user),
):
    base_url = TINKER_NODE_BASE_URL or f"{str(request.base_url).rstrip('/')}/api"
    return {
        "name": "Sage.is AI-UI",
        "provider": "custom",
        "base_url": base_url.rstrip("/"),
        "api_key": key,
        "model": TINKER_NODE_MODEL,
    }
