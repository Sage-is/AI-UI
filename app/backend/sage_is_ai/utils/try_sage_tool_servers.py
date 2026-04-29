"""Idempotent registration of try.sage trial tool servers.

The trial environment ships with two tool servers wired in by default:

1. The real markdown-search OpenAPI server
   (``TRY_SAGE_TOOL_SERVER_URL``) — used for live retrieval demos.
2. The in-process placeholder server defined in
   ``routers/sage_dummy_tools.py`` — exposes "preview / not available in
   trial" endpoints so an LLM can see the tool surface without any
   capability actually firing.

This helper ensures both entries land in ``app.state.config.TOOL_SERVER_CONNECTIONS``
on every boot and after every trial reset, deduped by URL so we never
duplicate on restart. Persisting the mutated list back through
``app.state.config`` triggers the existing ``PersistentConfig`` save path.
"""

import logging

from sage_is_ai.env import ENABLE_TRY_SAGE, SRC_LOG_LEVELS, TRY_SAGE_TOOL_SERVER_API_KEY

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


# Mirrors the ``ToolServerConnection`` Pydantic shape in ``routers/configs.py``
# (url / path / auth_type / key / config). Anything else would silently drop
# when the model coerces the list on the next admin save.
def _build_entry(url: str, key: str = "") -> dict:
    return {
        "url": url,
        "path": "openapi.json",
        # Bearer auth flips on whenever a key is supplied. Empty key keeps
        # the historical "none" auth_type so the dummy in-process server
        # (no key) still registers cleanly.
        "auth_type": "bearer" if key else "none",
        "key": key,
        "config": {"enable": True},
    }


async def register_try_sage_tool_servers(app) -> None:
    # Trial gating is checked here (not at import time) so flipping the env
    # var requires only a restart, not a rebuild.
    if not ENABLE_TRY_SAGE:
        return

    config = app.state.config
    existing = list(config.TOOL_SERVER_CONNECTIONS or [])
    existing_urls = {entry.get("url") for entry in existing if isinstance(entry, dict)}

    registered: list[str] = []
    skipped: list[str] = []

    # Real markdown-search tool server. The bearer key comes from
    # TRY_SAGE_TOOL_SERVER_API_KEY (env-only) — when set, every boot
    # writes it into the entry so admins never have to populate it
    # manually. When unset, we fall back to the historical "none" auth
    # and let an admin add the key by hand.
    real_key = (TRY_SAGE_TOOL_SERVER_API_KEY or "").strip()
    real_url = (config.TRY_SAGE_TOOL_SERVER_URL or "").strip()
    if real_url:
        existing_entry = next(
            (e for e in existing if isinstance(e, dict) and e.get("url") == real_url),
            None,
        )
        if existing_entry is not None:
            # Honor an env-supplied key as the source of truth: refresh
            # the entry's auth_type/key in place. Skip the rewrite when
            # the env key is empty so we don't clobber an admin-managed
            # key set via the UI.
            if real_key and (
                existing_entry.get("key") != real_key
                or existing_entry.get("auth_type") != "bearer"
            ):
                existing_entry["auth_type"] = "bearer"
                existing_entry["key"] = real_key
                registered.append(real_url)
            else:
                skipped.append(real_url)
        else:
            existing.append(_build_entry(real_url, real_key))
            existing_urls.add(real_url)
            registered.append(real_url)
    else:
        log.info(
            "try.sage tool server URL is empty; skipping markdown-search registration."
        )

    # Auto-derive the dummy URL from WEBUI_URL when the operator has not
    # pinned an explicit override. WEBUI_URL is the only public origin we
    # know maps to this process, so the in-process router is reachable
    # there.
    dummy_url = (config.TRY_SAGE_DUMMY_TOOL_SERVER_URL or "").strip()
    if not dummy_url:
        webui_url = (getattr(config, "WEBUI_URL", "") or "").strip().rstrip("/")
        if webui_url:
            dummy_url = f"{webui_url}/api/v1/sage/dummy-tools"

    if dummy_url:
        if dummy_url in existing_urls:
            skipped.append(dummy_url)
        else:
            existing.append(_build_entry(dummy_url))
            existing_urls.add(dummy_url)
            registered.append(dummy_url)
    else:
        log.info(
            "try.sage dummy tool server URL could not be derived (WEBUI_URL unset); skipping."
        )

    # Reassign through the PersistentConfig descriptor so the value is
    # persisted to the DB-backed config table — not just held in memory.
    config.TOOL_SERVER_CONNECTIONS = existing

    if registered:
        log.info("try.sage registered tool servers: %s", registered)
    if skipped:
        log.info("try.sage skipped already-registered tool servers: %s", skipped)
