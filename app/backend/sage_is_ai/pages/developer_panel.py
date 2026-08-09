"""Developer mode. Informational in production, a welcome in dev.

Two branches over one flag. In production it explains how to get a dev loop
running; under `DEV_MODE` it confirms the loop is already live. The Svelte
version writes both branches out longhand, including three numbered setup cards
and six links that differ only in href and text, which is the same repeated-row
shape `features_panel` collapses.

One value here outlives the page. "Sign me up for the mission" is stored in the
reader's own `ui` settings, the same blob the changelog read marker lives in.
"""

from __future__ import annotations

from fastapi import Request

from sage_is_ai.pages.i18n import lang_query, translator
from sage_is_ai.pages.templates import render

__all__ = ["render_developer", "save_developer"]

# number, title, command (or empty), hint
_STEPS: tuple[tuple[str, str, str, str], ...] = (
    ("1", "Install the CLI", "brew tap sage-is/apps && brew install ai-ui",
     "One tap, one install. Homebrew does the heavy lifting."),
    ("2", "Launch dev mode", "ai-ui dev",
     "Clones the repo, mounts source, fires up hot reload. Grab a coffee while "
     "it downloads ~1 GB of Node goodness the first time."),
    ("3", "Break things (then fix them)", "",
     "Edit code, save, watch it reload. That is the whole loop. Ship it when "
     "you are proud of it."),
)

_LINKS: tuple[tuple[str, str], ...] = (
    ("https://docs.sage.is/docs/contribute", "Contributing Guide"),
    ("https://docs.sage.is/docs/getting_started", "Getting Started Docs"),
    ("https://github.com/Sage-is/AI-UI", "GitHub Repository"),
)

_DEV_LINKS: tuple[tuple[str, str], ...] = (
    ("https://github.com/Sage-is/AI-UI", "GitHub Repository"),
    ("https://github.com/Sage-is/AI-UI/blob/master/docs/CONTRIBUTING.md",
     "Contributing Guide"),
)


def _signed_up(request: Request, user) -> bool:
    from sage_is_ai.models.users import Users

    current = Users.get_user_by_id(user.id)
    settings = (current.settings if current else None) or {}
    if hasattr(settings, "model_dump"):
        settings = settings.model_dump()
    return bool((settings.get("ui") or {}).get("devMissionSignup", False))


def render_developer(request: Request, user, saved: bool = False) -> str:
    """Build the context; `templates/developer.html` decides how it looks.

    Two shapes, chosen here rather than in the template only because DEV_MODE is
    the one fact the markup cannot look up for itself.
    """
    from sage_is_ai.env import DEV_MODE

    _ = translator(request)
    return render(
        "developer.html",
        lang=lang_query(request),
        dev_mode=bool(DEV_MODE),
        signed_up=_signed_up(request, user),
        note=_("Saved") if saved else "",
        save_label=_("Save"),
        live_source=_("Live source mounted. Changes reload automatically."),
        mounted=_("Source code mounted"),
        hot_reload=_("Hot reload active"),
        intro=_("Two commands and you are hacking on AI UI with hot reload. No PhD required."),
        signup_label=_("Sign me up for the mission"),
        signup_hint=_(
            "I solemnly swear I will open a terminal. Remind me next time I log in until I do."
        ),
        steps=[
            {"num": num, "title": _(title), "command": command, "hint": _(hint)}
            for num, title, command, hint in _STEPS
        ],
        links_=[{"href": href, "text": _(text)} for href, text in _LINKS],
        dev_links=[{"href": href, "text": _(text)} for href, text in _DEV_LINKS],
    )


async def save_developer(request: Request, user, form: dict) -> str:
    """Store the signup in the reader's own ui settings.

    Absence means False, for the same reason it does on the features panel: an
    unticked checkbox posts nothing, so reading only what arrived would make the
    box impossible to untick.
    """
    from sage_is_ai.models.users import Users, UserSettings
    from sage_is_ai.routers.users import update_user_settings_by_session_user

    current = Users.get_user_by_id(user.id)
    settings = (current.settings if current else None) or {}
    if hasattr(settings, "model_dump"):
        settings = settings.model_dump()
    ui = dict((settings or {}).get("ui") or {})
    ui["devMissionSignup"] = "devMissionSignup" in form

    await update_user_settings_by_session_user(
        request, UserSettings(**{**settings, "ui": ui}), user
    )
    return render_developer(request, user, saved=True)
