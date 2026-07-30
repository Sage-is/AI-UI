"""The wizard's closing summary — what got configured, and one button.

Nothing here is new information. It is five things the server already knows,
which the Svelte panel gathers with four API calls after boot and then keeps
re-asking: it polls `/api/v1/retrieval/models/status` every five seconds while a
model is downloading. On this side all five are read in the same request that
renders them.

**One real behaviour difference, and it is not hidden.** The Svelte panel
updates the AI-engine line while a download runs; a server-rendered page cannot,
because nothing is listening. So this panel renders the status at the moment you
asked and offers a refresh, and the guard-rail spec asserts only the contract
both can honour — that the line reflects the server's status when the page was
produced. Losing the live count is the cost of not shipping a poller, and it is
recorded rather than discovered.

That difference is also the fix for a leak: the Svelte timer has no `onDestroy`,
so closing the wizard mid-download leaves it running for the session. Filed in
TODO.md against the original. A page that does not poll cannot leak a poller.

**The feature count is imported, not restated.** `features_panel.FIELDS` is the
one list of what a feature flag is, so this counts through it — otherwise the
two would drift the first time a flag is added and the summary would quietly
undercount.

**Three lines are derived differently here than in the modal, on purpose.**
The Svelte panel decides "model connection configured" from `$models.length`,
which is the list the browser has finished loading; this reads whether a
provider is enabled with a URL, which is the configuration itself. It decides
"working alone" from a prop the modal sets during this run of the wizard; this
reads the stored setting, which is the only thing a standalone page could know.
Either can be right, but they are not the same question, so the guard-rail spec
asserts only the counts both derive identically — users and features — and
leaves those three to the human review pass. Asserting agreement we did not
build would be a spec that quietly stopped checking.
"""

from __future__ import annotations

from html import escape as e

from fastapi import Request

__all__ = ["render_complete", "finish_setup"]

_LINE_S = "--d:flex; --ai:center; --g:.5rem; --size:.85rem; --m:0 0 .35rem"
_MARK_S = "--fs:0"


def _line(key: str, text: str, ok: bool = True) -> str:
    return (
        f'<li data-check="{e(key, quote=True)}" style="{_LINE_S}">'
        f'<span style="{_MARK_S}" aria-hidden="true">{"&check;" if ok else "&circlearrowright;"}</span>'
        f"<span>{e(text)}</span></li>"
    )


def _facts(request: Request, user) -> tuple[list[str], dict[str, int]]:
    """Everything the summary reports, gathered once.

    Returns the rendered lines and the counts, so the counts can also go on the
    root element as data attributes. A spec asserting "2 users" through the
    attribute cannot be fooled by a pluralisation change.
    """
    from sage_is_ai.env import DEV_MODE
    from sage_is_ai.models.users import Users
    from sage_is_ai.pages.features_panel import FIELDS

    cfg = request.app.state.config
    lines: list[str] = []

    # Auth methods, same three the Svelte panel checks and in the same order.
    methods = []
    if getattr(cfg, "GOOGLE_CLIENT_ID", "") and getattr(cfg, "GOOGLE_CLIENT_SECRET", ""):
        methods.append("Google")
    if getattr(cfg, "GITHUB_CLIENT_ID", "") and getattr(cfg, "GITHUB_CLIENT_SECRET", ""):
        methods.append("GitHub")
    if getattr(cfg, "ENABLE_MAGIC_LINK_LOGIN", False):
        methods.append("Email Link")
    if methods:
        lines.append(_line("auth", f"Auth configured: {', '.join(methods)}"))

    # A model connection exists if either provider is switched on with a URL.
    connected = bool(
        (getattr(cfg, "ENABLE_OPENAI_API", False) and getattr(cfg, "OPENAI_API_BASE_URLS", []))
        or (getattr(cfg, "ENABLE_OLLAMA_API", False) and getattr(cfg, "OLLAMA_BASE_URLS", []))
    )
    if connected:
        lines.append(_line("connection", "Model connection configured"))

    users = Users.get_users()
    rows = users["users"] if isinstance(users, dict) else users
    others = len([u for u in rows if getattr(u, "role", "") != "admin"])
    if others:
        lines.append(_line("users", f"{others} user{'' if others == 1 else 's'} configured"))

    settings = (Users.get_user_by_id(user.id).settings if user else None) or {}
    if hasattr(settings, "model_dump"):
        settings = settings.model_dump()
    if (settings.get("ui") or {}).get("workingAlone"):
        lines.append(_line("working-alone", "Working alone mode enabled"))

    status = getattr(request.app.state, "MODEL_DOWNLOAD_STATUS", {}) or {}
    parts = [status.get("embedding", "pending"), status.get("whisper", "pending")]
    ready = len([s for s in parts if s == "ready"])
    downloading = len([s for s in parts if s == "downloading"])
    if ready == len(parts):
        lines.append(_line("ai-engine", "AI engine components installed"))
    elif downloading:
        lines.append(
            _line("ai-engine", f"{ready} of {len(parts)} AI engine components ready...", ok=False)
        )
    elif ready:
        lines.append(_line("ai-engine", f"{ready} of {len(parts)} AI engine components installed"))

    if DEV_MODE:
        lines.append(_line("dev-mode", "Developer mode active"))

    enabled = len([k for k, _, _, _ in FIELDS if getattr(cfg, k, False)])
    lines.append(
        _line("features", f"{enabled} feature{'' if enabled == 1 else 's'} enabled")
    )

    return lines, {"users": others, "features": enabled, "ready": ready}


def render_complete(request: Request, user) -> str:
    lines, counts = _facts(request, user)
    # A <ul> of what is done, not a stack of divs. The list is the meaning.
    return f"""
<section data-cy="complete-panel" data-users="{counts['users']}"
         data-features="{counts['features']}" data-ready="{counts['ready']}">
  <p style="--size:.9rem">This instance is ready to use.</p>
  <ul style="--p:0; --list-style:none; --m:1rem 0">{''.join(lines)}</ul>
  <form method="post" action="/pages/admin/setup/complete/finish">
    <button data-cy="complete-finish" type="submit"
            style="--p:.5rem 1.2rem; --br:999px; --b:1px solid var(--line); --cur:pointer">
      Let&rsquo;s Go
    </button>
    <a data-cy="complete-refresh" href="/pages/admin/setup/complete"
       style="--size:.75rem; --ml:.75rem">Refresh</a>
  </form>
</section>
"""


async def finish_setup(request: Request, user) -> None:
    """Mark setup complete — the half of "Let's Go" that outlives the click.

    In the modal it also closes the modal. At a route there is nothing to close,
    so what is asserted on both sides is this: the server records that setup is
    done, which is what stops the wizard opening itself on the next page load.
    """
    from sage_is_ai.env import VERSION
    from sage_is_ai.models.users import Users, UserSettings
    from sage_is_ai.routers.users import update_user_settings_by_session_user

    current = Users.get_user_by_id(user.id)
    settings = (current.settings if current else None) or {}
    if hasattr(settings, "model_dump"):
        settings = settings.model_dump()
    ui = dict((settings or {}).get("ui") or {})
    ui["setupCompleted"] = True
    ui["version"] = VERSION

    await update_user_settings_by_session_user(
        request, UserSettings(**{**settings, "ui": ui}), user
    )
