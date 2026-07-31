"""Which steps to run. The wizard's opening choice.

Six checkboxes and a start button. The modal keeps the answer in a component
variable and hands it down to every later panel. A route cannot do that, so the
answer is written to the reader's own `ui` settings, alongside `workingAlone`
and the changelog read marker. That was the plan's decision and this is where it
becomes real: `selectedSteps` is now durable, which is what lets a panel at its
own URL know whether it was meant to be part of this run.

The defaults are answers, not guesses. On a re-run the modal pre-clears the
steps that are already done, so the admin is not asked to redo settled work:
connections when models exist, users when there is somebody besides the admin.
Whether a step is already done is read from the server here rather than from a
store the browser filled in, which is the same substitution the complete panel
makes and for the same reason. At a route there is no browser state to read.

Starting goes to the first selected step that has a route. Every step now has
one, so `_ROUTES` is a name map rather than a filter. It earns its place anyway:
the stored keys use the modal's vocabulary, `search_audio` with an underscore,
and the routes use hyphens.
"""

from __future__ import annotations

from html import escape as e

from fastapi import Request

from sage_is_ai.pages.i18n import lang_query, translator

__all__ = ["render_welcome", "start_wizard", "STEPS", "selected_steps"]

# form field, label, caption. The field name is the value stored in
# `ui.selectedSteps`, and it matches the modal's own vocabulary, including the
# underscore in `search_audio`, so a value written by one is read by the other.
STEPS: tuple[tuple[str, str, str], ...] = (
    ("auth", "Authentication",
     "Configure Google, GitHub, or email link sign-in for your users"),
    ("connection", "Model Connections",
     "Add or update API connections to model providers"),
    ("users", "Users", "Invite your team or choose to work alone"),
    ("features", "Features",
     "Enable or disable platform features like sharing, notes, and spaces"),
    ("search_audio", "AI Engine",
     "Install local AI processing for document search and audio transcription"),
    ("developer", "Developer Mode", "Set up a local development environment"),
)

# Stored key to route segment. The two differ only where the modal's vocabulary
# uses an underscore, so this exists to translate `search_audio` and to keep the
# mapping in one place rather than in a string operation at the call site.
_ROUTES: dict[str, str] = {
    "auth": "auth",
    "connection": "connection",
    "users": "users",
    "features": "features",
    "search_audio": "search-audio",
    "developer": "developer",
}

_ROW_S = ("--d:flex; --ai:center; --g:.75rem; --p:.7rem; --br:.6rem; "
          "--b:1px solid var(--line); --m:0 0 .5rem; --cur:pointer")
_NAME_S = "--size:.85rem; --weight:500"
_CAPTION_S = "--size:.7rem; --op:.7; --d:block"
_DONE_S = "--size:.6rem; --weight:500; --tt:uppercase; --ml:.35rem; --op:.75"


def _has_models(request: Request) -> bool:
    cfg = request.app.state.config
    return bool(
        (getattr(cfg, "ENABLE_OPENAI_API", False) and getattr(cfg, "OPENAI_API_BASE_URLS", []))
        or (getattr(cfg, "ENABLE_OLLAMA_API", False) and getattr(cfg, "OLLAMA_BASE_URLS", []))
    )


def _has_other_users() -> bool:
    from sage_is_ai.models.users import Users

    users = Users.get_users()
    rows = users["users"] if isinstance(users, dict) else users
    return any(getattr(u, "role", "") != "admin" for u in rows)


def selected_steps(user) -> list[str]:
    """What this reader chose last time, if anything."""
    from sage_is_ai.models.users import Users

    current = Users.get_user_by_id(user.id) if user else None
    settings = (current.settings if current else None) or {}
    if hasattr(settings, "model_dump"):
        settings = settings.model_dump()
    stored = (settings.get("ui") or {}).get("selectedSteps")
    return [s for s in stored if isinstance(s, str)] if isinstance(stored, list) else []


def _defaults(request: Request, user) -> dict[str, bool]:
    """Which boxes start ticked.

    A stored choice wins — the reader already answered. Otherwise everything
    except developer mode, minus whatever the instance has plainly already got.
    """
    stored = selected_steps(user)
    if stored:
        return {key: key in stored for key, _, _ in STEPS}
    done_models, done_users = _has_models(request), _has_other_users()
    return {
        "auth": True,
        "connection": not done_models,
        "users": not done_users,
        "features": True,
        "search_audio": True,
        # Off by default. Setting up a dev environment is not part of getting an
        # instance working, and the modal agrees.
        "developer": False,
    }


def _row(key: str, label: str, caption: str, on: bool, done: bool, _) -> str:
    badge = (
        f'<small style="{_DONE_S}">{e(_("already configured"))}</small>' if done else ""
    )
    return (
        f'<label style="{_ROW_S}">'
        f'<input data-cy="welcome-{e(key.replace("_", "-"), quote=True)}" type="checkbox" '
        f'name="{e(key, quote=True)}" value="1"{" checked" if on else ""} />'
        f'<span><span style="{_NAME_S}">{e(_(label))}</span>{badge}'
        f'<small style="{_CAPTION_S}">{e(_(caption))}</small></span></label>'
    )


def render_welcome(request: Request, user) -> str:
    _ = translator(request)
    lang = lang_query(request)
    on = _defaults(request, user)
    done = {"connection": _has_models(request), "users": _has_other_users()}
    rows = "".join(
        _row(k, lb, cp, on[k], done.get(k, False), _) for k, lb, cp in STEPS
    )
    return f"""
<section data-cy="welcome-panel">
  <form method="post" action="/pages/admin/setup/welcome/start{lang}">
    <fieldset style="--b:0; --p:0; --m:0">
      <legend style="--size:.85rem; --weight:600; --p:0">
        {e(_("Choose what to set up. You can change any of it later in Admin settings."))}
      </legend>
      {rows}
    </fieldset>
    <button data-cy="welcome-start" type="submit"
            style="--p:.45rem 1rem; --br:999px; --b:1px solid var(--line); --cur:pointer">
      {e(_("Get Started"))}
    </button>
  </form>
</section>
"""


async def start_wizard(request: Request, user, form: dict) -> str:
    """Store the choice and report where to go next.

    Returns the destination path. Absence means False, as everywhere else here:
    an unticked checkbox posts nothing, so reading only what arrived is what
    makes a box impossible to untick.
    """
    from sage_is_ai.models.users import Users, UserSettings
    from sage_is_ai.routers.users import update_user_settings_by_session_user

    chosen = [key for key, _, _ in STEPS if key in form]

    current = Users.get_user_by_id(user.id)
    settings = (current.settings if current else None) or {}
    if hasattr(settings, "model_dump"):
        settings = settings.model_dump()
    ui = dict((settings or {}).get("ui") or {})
    ui["selectedSteps"] = chosen

    await update_user_settings_by_session_user(
        request, UserSettings(**{**settings, "ui": ui}), user
    )

    # First chosen step, in STEPS order. Choosing nothing is a real answer, so it
    # lands on the summary rather than nowhere.
    for key in (k for k, _, _ in STEPS):
        if key in chosen and key in _ROUTES:
            return f"/pages/admin/setup/{_ROUTES[key]}{lang_query(request)}"
    return f"/pages/admin/setup/complete{lang_query(request)}"
