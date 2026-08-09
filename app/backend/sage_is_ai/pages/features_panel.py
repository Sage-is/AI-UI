"""Platform feature toggles. The wizard's first real form.

Five checkboxes over `/api/v1/auths/admin/config`. The Svelte panel writes each
row out longhand: five near-identical seventeen-line blocks differing only in a
label, a caption, a tooltip and a beta badge. Here that is one table and one
loop, which is the whole argument for generated markup over hand-written rows.

Unchecked boxes do not post. An HTML checkbox sends nothing when it is off, so a
form that only reads what arrived would silently treat "turned it off" as "did
not mention it". `FIELDS` is the authority on what exists, and every name in it
is resolved to True or False from the submitted form, so switching a feature off
is a value in its own right. Getting this wrong is the classic way a settings
form quietly refuses to turn anything off.

The current config is read, merged, and written back whole. `AdminConfig`
carries far more than these five values, and posting only the five would reset
everything else to the model's defaults. So the handler is called with the
existing config plus the five changes.
"""

from __future__ import annotations

from fastapi import Request

from sage_is_ai.pages.i18n import lang_query, translator
from sage_is_ai.pages.templates import render

__all__ = ["render_features", "save_features", "FIELDS"]

# key, label, caption, beta. Order is render order; adding a feature is one row.
FIELDS: tuple[tuple[str, str, str, bool], ...] = (
    ("ENABLE_COMMUNITY_SHARING", "Community Sharing",
     "Allow users to share conversations with the community", False),
    ("ENABLE_MESSAGE_RATING", "Message Rating",
     "Allow users to rate AI responses", False),
    ("ENABLE_NOTES", "Notes", "Enable note-taking features", True),
    ("ENABLE_SPACES", "Spaces",
     "Enable workspace and collaboration spaces", True),
    ("ENABLE_USER_WEBHOOKS", "User Webhooks",
     "Allow users to configure webhook integrations", False),
)


# The hook is derived from the key so the two cannot drift: a renamed field
# renames its test hook, and the parity gate says so.
def _hook(key: str) -> str:
    return "features-" + key.removeprefix("ENABLE_").lower().replace("_", "-")


def _current(request: Request) -> dict:
    cfg = request.app.state.config
    return {key: bool(getattr(cfg, key, False)) for key, _, _, _ in FIELDS}


def render_features(request: Request, saved: bool = False) -> str:
    """Build the context; `templates/features.html` decides how it looks.

    Translate where the table is READ, not where it is declared. `FIELDS` keeps
    holding plain English, which is also the catalog key, so the table needs no
    second column and no edit when a language lands.

    `lang` rides on the form action. One that dropped it would answer a Spanish
    reader in English the moment they pressed Save.
    """
    _ = translator(request)
    on = _current(request)
    return render(
        "features.html",
        lang=lang_query(request),
        legend=_("Enable or disable platform features for your users."),
        save_label=_("Save"),
        note=_("Features saved.") if saved else "",
        rows=[
            {
                "key": key,
                "hook": _hook(key),
                "label": _(label),
                "caption": _(caption),
                "on": on[key],
                "badge": _("Beta") if beta else "",
                "badge_style": (
                    "--size:.55rem; --weight:600; --tt:uppercase; --p:.1rem .3rem; "
                    "--br:.25rem; --b:1px solid var(--line); --ml:.35rem"
                ),
            }
            for key, label, caption, beta in FIELDS
        ],
    )


async def save_features(request: Request, user, form: dict) -> str:
    """Write the five values, preserving everything else in the admin config.

    Calls the API handler rather than assigning to `app.state.config` here. That
    handler is where the side effects of each flag live, and reproducing them
    would be a second copy of the rules that drift apart on the first change.
    """
    from sage_is_ai.routers.auths import AdminConfig, get_admin_config, update_admin_config

    current = await get_admin_config(request, user)
    merged = dict(current)
    # Absence means False. See the module docstring: reading only what was
    # posted is how a checkbox form loses the ability to turn anything off.
    for key, _, _, _ in FIELDS:
        merged[key] = key in form

    await update_admin_config(request, AdminConfig(**merged), user)
    return render_features(request, saved=True)
