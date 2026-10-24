import logging
import uuid
import jwt
import base64
import hmac
import hashlib
import requests
import os
import time


from datetime import datetime, timedelta
from pytz import UTC
from typing import Optional, Union

from opentelemetry import trace

from sage_is_ai.models.users import Users

from sage_is_ai.constants import ERROR_MESSAGES
from sage_is_ai.env import (
    WEBUI_SECRET_KEY,
    TRUSTED_SIGNATURE_KEY,
    STATIC_DIR,
    SRC_LOG_LEVELS,
    WEBUI_AUTH_TRUSTED_EMAIL_HEADER,
)

from fastapi import BackgroundTasks, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Re-exported: routers import both from here. See utils/passwords.py.
from sage_is_ai.utils.passwords import get_password_hash, verify_password  # noqa: F401

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["OAUTH"])

SESSION_SECRET = WEBUI_SECRET_KEY
ALGORITHM = "HS256"

##############
# Auth Utils
##############


def verify_signature(payload: str, signature: str) -> bool:
    """
    Verifies the HMAC signature of the received payload.
    """
    try:
        expected_signature = base64.b64encode(
            hmac.new(TRUSTED_SIGNATURE_KEY, payload.encode(), hashlib.sha256).digest()
        ).decode()

        # Compare securely to prevent timing attacks
        return hmac.compare_digest(expected_signature, signature)

    except Exception:
        return False


def override_static(path: str, content: str):
    # Ensure path is safe
    if "/" in path or ".." in path:
        log.error(f"Invalid path: {path}")
        return

    file_path = os.path.join(STATIC_DIR, path)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, "wb") as f:
        f.write(base64.b64decode(content))  # Convert Base64 back to raw binary


def get_license_data(app, key):
    def handler(u):
        res = requests.post(
            f"{u}/api/v1/license/",
            json={"key": key, "version": "1"},
            timeout=5,
        )

        if getattr(res, "ok", False):
            payload = getattr(res, "json", lambda: {})()
            for k, v in payload.items():
                if k == "resources":
                    for p, c in v.items():
                        globals().get("override_static", lambda a, b: None)(p, c)
                elif k == "count":
                    setattr(app.state, "USER_COUNT", v)
                elif k == "name":
                    setattr(app.state, "WEBUI_NAME", v)
                elif k == "metadata":
                    setattr(app.state, "LICENSE_METADATA", v)
            return True
        else:
            log.error(
                f"License: retrieval issue: {getattr(res, 'text', 'unknown error')}"
            )

    if key:
        us = ["https://api.sage.is", "https://licenses.api.sage.is"]
        try:
            for u in us:
                if handler(u):
                    return True
        except Exception as ex:
            log.exception(f"License: Uncaught Exception: {ex}")
    return False


bearer_security = HTTPBearer(auto_error=False)


def create_token(data: dict, expires_delta: Union[timedelta, None] = None) -> str:
    payload = data.copy()
    # Every token says when it was minted, whichever caller minted it, so
    # is_live_session can measure it (2026-10-23).
    payload.setdefault("iat", int(time.time()))

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
        payload.update({"exp": expire})

    encoded_jwt = jwt.encode(payload, SESSION_SECRET, algorithm=ALGORITHM)
    return encoded_jwt


def create_session_token(user_id: str, expires_delta: Union[timedelta, None] = None):
    """Mint the token a browser or API client holds as its session.

    Every session carries `iat`, which is_live_session reads, and `exp` when
    JWT_EXPIRES_IN sets one (an admin's "-1" means no expiry). Returns the
    token and its expiry as a Unix timestamp, None without one (2026-10-23).
    """
    issued_at = int(time.time())
    expires_at = (
        issued_at + int(expires_delta.total_seconds()) if expires_delta else None
    )
    claims = {"id": user_id, "iat": issued_at}
    if expires_at:
        claims["exp"] = expires_at
    return create_token(claims), expires_at


def is_live_session(data: dict, cutoff=0) -> bool:
    """Whether decoded session claims still stand; the API and the socket share it.

    A session token carries `iat`. Every mint since 3.3.0 stamps it, so a token
    without it was minted before then, or by hand, and is refused, which signs
    those sessions out once. `cutoff` is the try.sage reset: when a facilitator
    presses "Reset now", every session minted before that moment is invalid. A
    magic-link token is not a session and keeps its own check in
    /magic-link/verify (2026-10-23).
    """
    if data.get("type") == "magic_link":
        return True
    try:
        issued_at = int(data.get("iat") or 0)
    except (TypeError, ValueError):
        return False
    try:
        cutoff = int(cutoff or 0)
    except (TypeError, ValueError):
        cutoff = 0
    return issued_at > 0 and issued_at >= cutoff


def decode_token(token: str) -> Optional[dict]:
    try:
        # PyJWT 2.10+ refuses an `iat` in the future. A clock that steps back,
        # as a VM's does when its host corrects it, then rejects a session
        # minted a moment ago for a second or two (seen 2026-10-24 as
        # intermittent 401s on fresh sign-ins). A minute of leeway covers it
        # without loosening `exp` in any way that matters.
        decoded = jwt.decode(token, SESSION_SECRET, algorithms=[ALGORITHM], leeway=60)
        return decoded
    except Exception:
        return None


def extract_token_from_auth_header(auth_header: str):
    return auth_header[len("Bearer ") :]


def create_api_key():
    key = str(uuid.uuid4()).replace("-", "")
    return f"sk-{key}"


def get_http_authorization_cred(auth_header: Optional[str]):
    if not auth_header:
        return None
    try:
        scheme, credentials = auth_header.split(" ")
        return HTTPAuthorizationCredentials(scheme=scheme, credentials=credentials)
    except Exception:
        return None


def get_current_user(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    auth_token: HTTPAuthorizationCredentials = Depends(bearer_security),
):
    token = None

    if auth_token is not None:
        token = auth_token.credentials

    if token is None and "token" in request.cookies:
        token = request.cookies.get("token")

    if token is None:
        raise HTTPException(status_code=403, detail="Not authenticated")

    # auth by api key
    if token.startswith("sk-"):
        if not request.state.enable_api_key:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.API_KEY_NOT_ALLOWED
            )

        if request.app.state.config.ENABLE_API_KEY_ENDPOINT_RESTRICTIONS:
            # Blank entries are dropped: "" + "/" would match every path, so
            # an empty list or a trailing comma opened everything. An empty
            # allowlist admits nothing (2026-10-23).
            allowed_paths = [
                path.strip()
                for path in str(
                    request.app.state.config.API_KEY_ALLOWED_ENDPOINTS
                ).split(",")
                if path.strip()
            ]

            # Check if the request path matches any allowed endpoint.
            if not any(
                request.url.path == allowed
                or request.url.path.startswith(allowed + "/")
                for allowed in allowed_paths
            ):
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.API_KEY_NOT_ALLOWED
                )

        user = get_current_user_by_api_key(token)

        # Add user info to current span
        current_span = trace.get_current_span()
        if current_span:
            current_span.set_attribute("client.user.id", user.id)
            current_span.set_attribute("client.user.email", user.email)
            current_span.set_attribute("client.user.role", user.role)
            current_span.set_attribute("client.auth.type", "api_key")

        return user

    # auth by jwt token
    try:
        data = decode_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    if data is not None and "id" in data:
        # The session rules, shared with the socket: see is_live_session.
        cutoff = getattr(
            request.app.state.config, "TRY_SAGE_SESSIONS_INVALIDATED_AT", 0
        )
        if not is_live_session(data, cutoff):
            response.delete_cookie("token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session reset — please sign in again.",
            )

        user = Users.get_user_by_id(data["id"])
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ERROR_MESSAGES.INVALID_TOKEN,
            )
        else:
            if WEBUI_AUTH_TRUSTED_EMAIL_HEADER:
                trusted_email = request.headers.get(
                    WEBUI_AUTH_TRUSTED_EMAIL_HEADER, ""
                ).lower()
                if trusted_email and user.email != trusted_email:
                    # Delete the token cookie
                    response.delete_cookie("token")
                    # Delete OAuth token if present
                    if request.cookies.get("oauth_id_token"):
                        response.delete_cookie("oauth_id_token")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="User mismatch. Please sign in again.",
                    )

            # Add user info to current span
            current_span = trace.get_current_span()
            if current_span:
                current_span.set_attribute("client.user.id", user.id)
                current_span.set_attribute("client.user.email", user.email)
                current_span.set_attribute("client.user.role", user.role)
                current_span.set_attribute("client.auth.type", "jwt")

            # Refresh the user's last active timestamp asynchronously
            # to prevent blocking the request
            if background_tasks:
                background_tasks.add_task(Users.update_user_last_active_by_id, user.id)
        return user
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )


def get_current_user_by_api_key(api_key: str):
    user = Users.get_user_by_api_key(api_key)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.INVALID_TOKEN,
        )
    else:
        # Add user info to current span
        current_span = trace.get_current_span()
        if current_span:
            current_span.set_attribute("client.user.id", user.id)
            current_span.set_attribute("client.user.email", user.email)
            current_span.set_attribute("client.user.role", user.role)
            current_span.set_attribute("client.auth.type", "api_key")

        Users.update_user_last_active_by_id(user.id)

    return user


def get_verified_user(user=Depends(get_current_user)):
    if user.role not in {"user", "admin", "facilitator", "temporary"}:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    # Check temporary account expiry
    if user.role == "temporary":
        import time

        if user.info and isinstance(user.info, dict):
            temp_info = user.info.get("temporary", {})
            expires_at = temp_info.get("expires_at")
            if expires_at and int(expires_at) < int(time.time()):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Temporary account has expired.",
                )

    return user


def get_admin_user(user=Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )
    return user


def get_admin_or_facilitator_user(user=Depends(get_current_user)):
    if user.role not in {"admin", "facilitator"}:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )
    return user
