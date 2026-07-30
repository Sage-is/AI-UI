"""Developer mode — informational in production, a welcome in dev.

Two branches over one flag. In production it explains how to get a dev loop
running; under `DEV_MODE` it confirms the loop is already live. The Svelte
version writes both branches out longhand, including three numbered setup cards
and six links that differ only in href and text, which is the same repeated-row
shape `features_panel` collapses.

The only thing here that outlives the page is one checkbox: "sign me up for the
mission" is stored in the reader's own `ui` settings, the same blob the
changelog read marker lives in.
"""

from __future__ import annotations

from html import escape as e

from fastapi import Request

__all__ = ["render_developer", "save_developer"]

_CARD_S = ("--d:flex; --g:.75rem; --p:.7rem; --br:.6rem; "
           "--b:1px solid var(--line); --m:0 0 .6rem")
_NUM_S = "--size:1.1rem; --weight:600; --op:.45; --w:1.5rem; --ta:center; --fs:0"
_STEP_S = "--size:.85rem; --weight:500"
_HINT_S = "--size:.68rem; --op:.7; --d:block; --m:.2rem 0 0"
_LINK_S = "--size:.75rem; --d:block; --m:0 0 .3rem"
_CODE_S = "--size:.7rem; --p:.2rem .4rem; --br:.25rem; --b:1px solid var(--line)"

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


def _links(items: tuple[tuple[str, str], ...]) -> str:
    # rel="noopener" on every target=_blank link, same as the Svelte original.
    return "".join(
        f'<a href="{e(href, quote=True)}" target="_blank" rel="noopener" '
        f'style="{_LINK_S}">{e(text)}</a>'
        for href, text in items
    )


def _step(num: str, title: str, command: str, hint: str) -> str:
    cmd = f'<code style="{_CODE_S}">{e(command)}</code>' if command else ""
    return (
        f'<li style="{_CARD_S}"><span style="{_NUM_S}">{e(num)}</span>'
        f'<span><span style="{_STEP_S}">{e(title)}</span> {cmd}'
        f'<small style="{_HINT_S}">{e(hint)}</small></span></li>'
    )


def _signed_up(request: Request, user) -> bool:
    from sage_is_ai.models.users import Users

    current = Users.get_user_by_id(user.id)
    settings = (current.settings if current else None) or {}
    if hasattr(settings, "model_dump"):
        settings = settings.model_dump()
    return bool((settings.get("ui") or {}).get("devMissionSignup", False))


def render_developer(request: Request, user, saved: bool = False) -> str:
    from sage_is_ai.env import DEV_MODE

    if DEV_MODE:
        # An <ul> of facts, not cards. Nothing here is a step to follow.
        body = (
            '<p style="--size:.9rem">Live source mounted. Changes reload automatically.</p>'
            '<ul style="--size:.8rem"><li>Source code mounted</li>'
            "<li>Hot reload active</li></ul>" + _links(_DEV_LINKS)
        )
    else:
        checked = " checked" if _signed_up(request, user) else ""
        note = (
            '<output data-cy="developer-saved" style="--size:.8rem; --op:.75">Saved.</output>'
            if saved
            else ""
        )
        # An ordered list, because these are numbered steps in sequence — which
        # is what <ol> means, and it renders the numbers without the three
        # hand-written digits the Svelte version carries.
        body = (
            "<p>Two commands and you are hacking on AI UI with hot reload. "
            "No PhD required.</p>"
            f'<ol style="--p:0; --list-style:none">'
            f"{''.join(_step(*s) for s in _STEPS)}</ol>"
            '<form method="post" action="/pages/admin/setup/developer/save">'
            f'<label style="{_CARD_S}; --cur:pointer">'
            f'<input data-cy="developer-mission-signup" type="checkbox" '
            f'name="devMissionSignup" value="1"{checked} />'
            '<span><span style="--size:.85rem; --weight:500">'
            "Sign me up for the mission</span>"
            f'<small style="{_HINT_S}">I solemnly swear I will open a terminal. '
            "Remind me next time I log in until I do.</small></span></label>"
            '<button data-cy="developer-save" type="submit" '
            'style="--p:.45rem 1rem; --br:999px; --b:1px solid var(--line); --cur:pointer">'
            f"Save</button>{note}</form>" + _links(_LINKS)
        )

    return f'<section data-cy="developer-panel" data-dev-mode="{str(bool(DEV_MODE)).lower()}">{body}</section>'


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
