"""Diagnostics router — read-only operator visibility surface.

GET  /api/v1/diagnostics/health   — the 4-section diagnostic document
POST /api/v1/diagnostics/probe    — single-URL re-probe (SSRF-guarded)

==============================================================================
SECURITY INVARIANT — DO NOT REGRESS
==============================================================================

This router NEVER returns API keys, JWT secrets, or any secret material.

The endpoints section is built EXCLUSIVELY from
`endpoint_health.snapshot()` (see diagnostics/health_registry.py), which
stores URLs but never keys. We do NOT read
`app.state.config.OPENAI_API_KEYS`, `OLLAMA_API_KEYS`, or any
`*_API_KEY*` config. We do NOT return the value of WEBUI_SECRET_KEY —
only length, presence, and the filesystem type underneath data/.

If a future field needs to be added that touches secret material,
push it into a separate audited admin endpoint instead. The diagnostics
page is rendered as JSON in the operator's browser; assume the response
will end up in screenshots, support tickets, and chat logs.

==============================================================================
i18n CONTRACT — backend emits keys, not English
==============================================================================

Every row carries `summary_key` + `summary_params` instead of an English
sentence. The frontend resolves keys via the existing i18n catalog. The
key namespace is:

    diagnostics.summary.<capability_or_section>.<status>

Examples:
    diagnostics.summary.embedding.openai.unreachable
    diagnostics.summary.data_dir_writable.ok
    diagnostics.summary.alembic_head.degraded

For an endpoint with no recognised capability we fall back to
    diagnostics.summary.unknown.<status>

Notes (`observed_note` in browser_headers technicals) are also keys, not
English. The frontend resolves them.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from sage_is_ai.diagnostics.boot import boot_progress, collect_active_urls
from sage_is_ai.diagnostics.health_registry import endpoint_health
from sage_is_ai.diagnostics.probes import probe_http
from sage_is_ai.env import DATA_DIR, SRC_LOG_LEVELS, STATIC_DIR, WEBUI_SECRET_KEY
from sage_is_ai.utils.auth import get_admin_user
from sage_is_ai.utils.security_headers import (
    PERMISSIONS_POLICY_REJECTED_FEATURES,
    set_security_headers,
)

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


router = APIRouter()


# ---- canonical capability list (Phase 2b) -----------------------------------
#
# Listing these explicitly serves two purposes:
#   1. The frontend knows which `diagnostics.summary.<capability>.<status>`
#      keys to ship translations for.
#   2. Unknown capabilities (new Sprig™ transports, custom integrations)
#      fall through to `diagnostics.summary.unknown.<status>` without
#      crashing the page.
#
# The summary_key itself is derived by replacing "/" with "." — the dict
# below just records the canonical set. Do not gate emission on this set;
# rule R9 says capability discovery is open-ended.
CAPABILITY_SUMMARY_KEYS = {
    "openai/list_models",
    "openai/verify_connection",
    "ollama/list_models",
    "ollama/verify_connection",
    "rag/tika",
    "rag/docling",
    "rag/reranker",
    "embedding/openai",
    "embedding/ollama",
    "embedding/azure_openai",
    "audio/tts/openai",
    "audio/tts/elevenlabs",
    "audio/tts/azure",
    "pipelines/inlet_filter",
    "pipelines/outlet_filter",
}


# ---- per-URL probe locks (rule R6) ------------------------------------------
#
# POST /probe takes a per-URL asyncio.Lock so a second caller awaits the
# first probe's result rather than firing a duplicate. Locks are created
# lazily and never reaped — the active-URL set is small (single-digit
# count in normal operation), so the bookkeeping isn't worth it.
_probe_locks: dict[str, asyncio.Lock] = {}
_probe_locks_guard = asyncio.Lock()


async def _get_probe_lock(url: str) -> asyncio.Lock:
    async with _probe_locks_guard:
        lock = _probe_locks.get(url)
        if lock is None:
            lock = asyncio.Lock()
            _probe_locks[url] = lock
        return lock


# ---- row builder ------------------------------------------------------------


def _row(
    status: str,
    summary_key: str,
    summary_params: Optional[dict] = None,
    issue_type: Optional[str] = None,
    technical: Optional[dict] = None,
) -> dict:
    """Uniform row shape used in every section.

    All four rows in every section share this shape so the frontend
    can render them with one component.
    """
    return {
        "status": status,
        "summary_key": summary_key,
        "summary_params": summary_params or {},
        "issue_type": issue_type,
        "technical": technical or {},
    }


# ---- endpoint summarization -------------------------------------------------


_STATUS_RANK = {"unreachable": 0, "degraded": 1, "ok": 2, "unknown": 3}


def _summary_key_for(capability: Optional[str], status_str: str) -> str:
    """Map (capability, status) to a translation key.

    For canonical capabilities (see CAPABILITY_SUMMARY_KEYS), we emit
    `diagnostics.summary.<capability_dotted>.<status>`. For anything
    else (missing capability or a new Sprig™ capability we haven't
    translated yet) we fall back to `diagnostics.summary.unknown.<status>`.
    Rule R9: capabilities are open-ended; the frontend must handle
    fallbacks without surprise.
    """
    if capability and capability in CAPABILITY_SUMMARY_KEYS:
        return "diagnostics.summary." + capability.replace("/", ".") + "." + status_str
    return "diagnostics.summary.unknown." + status_str


def _summarize_endpoint(record: dict, in_config: bool) -> dict:
    """Render one EndpointRecord (dict form) as a section row.

    Returns the same dict shape `_row` produces but with extra
    `in_config` and `technical` fields; the endpoints section uses
    this so per-row ghost-marking works.
    """
    last_status = record.get("last_status")
    if last_status in ("ok", "degraded", "unreachable"):
        status_str = last_status
    else:
        status_str = "unknown"

    capability = record.get("capability")
    url = record.get("url", "")

    issue_type: Optional[str] = None
    if status_str == "unreachable":
        issue_type = "endpoint_unreachable"
    elif status_str == "degraded":
        issue_type = "endpoint_degraded"

    return {
        "status": status_str,
        "summary_key": _summary_key_for(capability, status_str),
        "summary_params": {
            "url": url,
            "latency_ms": record.get("last_latency_ms") or 0,
        },
        "issue_type": issue_type,
        "in_config": in_config,
        "technical": record,
    }


def _endpoints_section(app) -> dict:
    """Build the endpoints section sorted worst-first.

    Sort tuple (rule R3 — keep documented so it does not drift):
        (status_rank, -consecutive_failures, -last_probed_at, capability, url)
    where status_rank = {unreachable:0, degraded:1, ok:2, unknown:3}.
    Most-broken first; most-recently-broken-most first within status;
    capability + url as deterministic tiebreakers.

    Python dicts preserve insertion order in 3.7+, so building the
    output dict in sort order is enough — JSON serialisation carries
    the order through.
    """
    snapshot = endpoint_health.snapshot()
    try:
        active = {url for (url, _capability) in collect_active_urls(app)}
    except Exception as exc:
        # collect_active_urls touches app.state.config — defensively log
        # and treat all rows as out-of-config so the page still renders.
        log.warning("diagnostics: collect_active_urls failed: %s", exc)
        active = set()

    rows = []
    for url, record in snapshot.items():
        last_status = record.get("last_status") or "unknown"
        status_str = (
            last_status if last_status in _STATUS_RANK else "unknown"
        )
        sort_key = (
            _STATUS_RANK.get(status_str, 3),
            -(record.get("consecutive_failures") or 0),
            -(record.get("last_probed_at") or 0.0),
            record.get("capability") or "",
            url,
        )
        rows.append((sort_key, url, record))

    rows.sort(key=lambda r: r[0])

    out: dict = {}
    for _sort_key, url, record in rows:
        out[url] = _summarize_endpoint(record, in_config=(url in active))
    return out


# ---- boot_status checks -----------------------------------------------------


def _check_data_dir_writable() -> dict:
    """Probe DATA_DIR with os.access plus an actual write-test.

    os.access can lie under bind-mounted volumes whose mode bits look
    fine but whose underlying filesystem rejects writes (read-only
    mount, full disk). We add a tiny write to catch both.
    """
    data_dir = Path(DATA_DIR)
    technical = {"data_dir": str(data_dir)}

    if not data_dir.exists():
        technical["exists"] = False
        return _row(
            "degraded",
            "diagnostics.summary.data_dir_writable.degraded",
            {"data_dir": str(data_dir)},
            issue_type="data_not_writable",
            technical=technical,
        )

    technical["exists"] = True
    technical["os_access_w_ok"] = os.access(str(data_dir), os.W_OK)

    test_file = data_dir / ".diagnostics_write_test"
    try:
        test_file.write_text("ok")
        try:
            test_file.unlink()
        except OSError:
            pass
        technical["write_test"] = "ok"
        return _row(
            "ok",
            "diagnostics.summary.data_dir_writable.ok",
            {"data_dir": str(data_dir)},
            technical=technical,
        )
    except OSError as exc:
        technical["write_test"] = "failed"
        technical["error_class"] = type(exc).__name__
        technical["error_message"] = str(exc)
        return _row(
            "degraded",
            "diagnostics.summary.data_dir_writable.degraded",
            {"data_dir": str(data_dir)},
            issue_type="data_not_writable",
            technical=technical,
        )


_EPHEMERAL_FS_TYPES = {"tmpfs", "overlay", "overlayfs", "aufs", "ramfs"}


def _detect_fs_type(path: Path) -> str:
    """Best-effort filesystem-type detection for the `secret_key_persisted`
    check. Returns a lowercase fs name on Linux (via /proc/mounts), or
    a sentinel string elsewhere. Never raises.
    """
    try:
        # Linux: /proc/mounts has the authoritative answer
        mounts_path = Path("/proc/mounts")
        if not mounts_path.exists():
            return "unknown"
        target = str(path.resolve())
        best_match = ""
        best_fs = "unknown"
        for line in mounts_path.read_text().splitlines():
            parts = line.split()
            if len(parts) < 3:
                continue
            mount_point, fs_type = parts[1], parts[2]
            if target == mount_point or target.startswith(mount_point.rstrip("/") + "/"):
                if len(mount_point) > len(best_match):
                    best_match = mount_point
                    best_fs = fs_type
        return best_fs.lower()
    except OSError:
        return "unknown"


def _check_webui_secret_key() -> dict:
    """Verify WEBUI_SECRET_KEY is configured AND persistent.

    NEVER returns the key value. Reports length, presence, and the
    detected fs type underneath DATA_DIR — that's enough for the
    operator-fix flow without leaking the secret into a screenshot.

    Phase 1 already validates length 44 at boot; we re-check here so
    the diagnostics page is the single pane of glass.
    """
    key = WEBUI_SECRET_KEY or ""
    key_present = bool(key)
    key_len = len(key)
    expected_len = 44

    # The bootstrap key file persists the auto-generated key when the env
    # var is unset; presence here tells us "key will survive a restart".
    key_file = Path(DATA_DIR) / ".webui_secret_key"
    key_file_present = key_file.exists()

    fs_type = _detect_fs_type(Path(DATA_DIR))

    is_ephemeral = fs_type in _EPHEMERAL_FS_TYPES
    correct_length = key_len == expected_len
    persisted = key_file_present or (
        key_present and not is_ephemeral and correct_length
    )

    technical = {
        "key_present": key_present,
        "key_length": key_len,
        "expected_length": expected_len,
        "correct_length": correct_length,
        "key_file_present": key_file_present,
        "fs_type": fs_type,
        "is_ephemeral_fs": is_ephemeral,
    }

    # Degraded if anything in the persistence chain is missing or
    # ephemeral. Key length is reported but not the value (rule R1).
    healthy = (
        key_present
        and correct_length
        and key_file_present
        and not is_ephemeral
    )

    if healthy:
        return _row(
            "ok",
            "diagnostics.summary.secret_key_persisted.ok",
            {"fs_type": fs_type, "key_length": key_len},
            technical=technical,
        )

    return _row(
        "degraded",
        "diagnostics.summary.secret_key_persisted.degraded",
        {"fs_type": fs_type, "key_length": key_len},
        issue_type="secret_key_ephemeral",
        technical=technical,
    )


def _check_alembic_head() -> dict:
    """Compare code's expected Alembic head against the DB's recorded head.

    Wrapped end-to-end in try/except (rule R8): the diagnostics page MUST
    NEVER 500 even if Alembic config is broken. On any exception we
    return status `unknown` with the error class + message in technical
    so the operator can still see what happened.
    """
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        from sqlalchemy import text
        from sage_is_ai.env import SAGE_IS_AI_DIR
        from sage_is_ai.internal.db import engine

        alembic_cfg = Config(str(SAGE_IS_AI_DIR / "alembic.ini"))
        migrations_path = SAGE_IS_AI_DIR / "migrations"
        alembic_cfg.set_main_option("script_location", str(migrations_path))
        script = ScriptDirectory.from_config(alembic_cfg)
        code_head = script.get_current_head()

        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT version_num FROM alembic_version")
            ).fetchone()
            db_head = row[0] if row else None

        technical = {"code_head": code_head, "db_head": db_head}

        if code_head == db_head:
            return _row(
                "ok",
                "diagnostics.summary.alembic_head.ok",
                {"code_head": code_head or "", "db_head": db_head or ""},
                technical=technical,
            )

        # If db_head is None or differs, treat as pending upgrade.
        # Phase 6 will refuse-to-start on the inverse (db newer than code);
        # for now we flag both as `degraded` and rely on Phase 6 to harden.
        return _row(
            "degraded",
            "diagnostics.summary.alembic_head.degraded",
            {"code_head": code_head or "", "db_head": db_head or ""},
            issue_type="alembic_pending",
            technical=technical,
        )
    except Exception as exc:
        return _row(
            "unknown",
            "diagnostics.summary.alembic_head.unknown",
            {},
            technical={
                "error_class": type(exc).__name__,
                "error_message": str(exc),
            },
        )


def _boot_status_section() -> dict:
    return {
        "data_dir_writable": _check_data_dir_writable(),
        "secret_key_persisted": _check_webui_secret_key(),
        "alembic_head": _check_alembic_head(),
    }


# ---- static_assets section --------------------------------------------------


_STATIC_ASSET_PATHS = (
    "/assets/loader.js",
    "/assets/custom.css",
    "/manifest.json",
    "/favicon.ico",
)


def _check_static_asset(rel_path: str) -> dict:
    """Probe a single canonical SPA asset on disk.

    We deliberately use the filesystem (not HTTP) because the frontend
    SPA owns its own routing — the canonical assets are static-served
    by FastAPI from STATIC_DIR, so an HTTP probe would either need an
    in-process client or talk to itself over the network. Path.exists()
    is the cheapest fact.
    """
    relative = rel_path.lstrip("/")
    asset_path = Path(STATIC_DIR) / relative
    exists = asset_path.exists()
    technical = {"path": str(asset_path), "exists": exists}
    if exists:
        return _row(
            "ok",
            "diagnostics.summary.static_asset.ok",
            {"PATH": rel_path},
            technical=technical,
        )
    return _row(
        "degraded",
        "diagnostics.summary.static_asset.degraded",
        {"PATH": rel_path},
        issue_type="static_asset_missing",
        technical=technical,
    )


def _static_assets_section() -> dict:
    return {path: _check_static_asset(path) for path in _STATIC_ASSET_PATHS}


# ---- browser_headers section ------------------------------------------------


def _check_permissions_policy(headers: dict) -> dict:
    """Categorise the Permissions-Policy value into:
    - no env var configured → ok, browser defaults apply
    - configured, no rejected feature → ok
    - configured, contains rejected feature → degraded
    """
    raw_env = os.environ.get("PERMISSIONS_POLICY", "")
    header_value = headers.get("Permissions-Policy", "")

    technical = {
        "env_var_set": bool(raw_env),
        "header_value": header_value,
        "observed_note": "diagnostics.note.reverse_proxy_may_override",
    }

    if not raw_env:
        return _row(
            "ok",
            "diagnostics.summary.permissions_policy.ok",
            {},
            technical=technical,
        )

    lowered = header_value.lower()
    rejected_hits = [
        token for token in PERMISSIONS_POLICY_REJECTED_FEATURES if token in lowered
    ]
    technical["rejected_features_present"] = rejected_hits

    if rejected_hits:
        return _row(
            "degraded",
            "diagnostics.summary.permissions_policy.degraded",
            {"rejected_count": len(rejected_hits)},
            issue_type="permissions_policy_invalid",
            technical=technical,
        )

    return _row(
        "ok",
        "diagnostics.summary.permissions_policy.ok",
        {},
        technical=technical,
    )


def _check_content_security_policy(headers: dict) -> dict:
    header_value = headers.get("Content-Security-Policy", "")
    technical = {
        "configured": bool(header_value),
        "observed_note": "diagnostics.note.reverse_proxy_may_override",
    }
    if header_value:
        return _row(
            "ok",
            "diagnostics.summary.content_security_policy.ok",
            {},
            technical=technical,
        )
    return _row(
        "degraded",
        "diagnostics.summary.content_security_policy.degraded",
        {},
        issue_type="csp_missing",
        technical=technical,
    )


def _browser_headers_section() -> dict:
    headers = set_security_headers()
    return {
        "permissions_policy": _check_permissions_policy(headers),
        "content_security_policy": _check_content_security_policy(headers),
    }


# ---- deployment_shape -------------------------------------------------------


def _detect_deployment_shape() -> dict:
    """Best-effort detection used by the how-to-fix UI to pick the
    right runbook upfront. `confidence: low` triggers a "pick your
    deployment" radio in the modal.
    """
    caprover = os.environ.get("CAPROVER_APP_NAME")
    if caprover:
        return {
            "shape": "caprover",
            "confidence": "high",
            "signals": [{"env_var": "CAPROVER_APP_NAME", "value": caprover}],
        }

    compose = os.environ.get("COMPOSE_PROJECT_NAME")
    if compose:
        return {
            "shape": "docker_compose",
            "confidence": "low",
            "signals": [{"env_var": "COMPOSE_PROJECT_NAME", "value": compose}],
        }

    brew_prefix = os.environ.get("HOMEBREW_PREFIX")
    if brew_prefix and not Path("/.dockerenv").exists():
        return {
            "shape": "brew",
            "confidence": "low",
            "signals": [{"env_var": "HOMEBREW_PREFIX", "value": brew_prefix}],
        }

    return {"shape": "unknown", "confidence": "low", "signals": []}


# ---- routes -----------------------------------------------------------------


@router.get("/health")
async def get_diagnostics_health(request: Request, user=Depends(get_admin_user)):
    """Return the 4-section diagnostic document.

    Sections (rule R3 mandates worst-first sort within `endpoints`):
        - deployment_shape   — best-effort detection for fix-runbook routing
        - boot_probes        — progress so the UI suppresses alarms while running
        - endpoints          — every EndpointHealth row, sorted worst-first
        - boot_status        — data dir, secret key, alembic head
        - static_assets      — canonical SPA assets
        - browser_headers    — permissions-policy and CSP
    """
    app = request.app
    return {
        "deployment_shape": _detect_deployment_shape(),
        "boot_probes": boot_progress.to_dict_safe(),
        "endpoints": _endpoints_section(app),
        "boot_status": _boot_status_section(),
        "static_assets": _static_assets_section(),
        "browser_headers": _browser_headers_section(),
    }


class ProbeForm(BaseModel):
    url: str
    capability: Optional[str] = None


@router.post("/probe")
async def probe_endpoint(
    body: ProbeForm,
    request: Request,
    user=Depends(get_admin_user),
):
    """Re-probe a single URL on operator demand.

    SSRF defense (rule R6): we refuse any URL not in the current
    `collect_active_urls(app)` set. Re-probe is for URLs the operator
    already configured — never an arbitrary-URL primitive, even
    under admin auth.
    """
    app = request.app
    try:
        active = {url for (url, _capability) in collect_active_urls(app)}
    except Exception as exc:
        log.warning("diagnostics: collect_active_urls failed during probe: %s", exc)
        active = set()

    if body.url not in active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "detail": "URL not in active config",
                "url": body.url,
            },
        )

    lock = await _get_probe_lock(body.url)
    async with lock:
        # probe_http is blocking; run in default thread pool so we don't
        # stall the event loop if the URL is slow within the 5s budget.
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None, lambda: probe_http(body.url, timeout=5)
        )
        endpoint_health.record_probe(result, capability=body.capability)

    record = endpoint_health.snapshot().get(body.url) or {
        "url": body.url,
        "capability": body.capability,
        "last_status": "unknown",
    }
    return _summarize_endpoint(record, in_config=True)
