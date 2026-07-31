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

from html import escape as e

from fastapi import Request

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


_ROW_S = ("--d:flex; --ai:center; --g:.75rem; --p:.7rem; --br:.6rem; "
          "--b:1px solid var(--line); --m:0 0 .5rem; --cur:pointer")
_NAME_S = "--size:.85rem; --weight:500"
_CAPTION_S = "--size:.7rem; --op:.7; --d:block"
_BETA_S = ("--size:.55rem; --weight:600; --tt:uppercase; --p:.1rem .3rem; "
           "--br:.25rem; --b:1px solid var(--line); --ml:.35rem")


def _row(key: str, label: str, caption: str, beta: bool, on: bool) -> str:
    """One toggle.

    A `<label>` wrapping its own `<input>` needs no `for`/`id` pair and no ARIA:
    the association is the nesting, and the whole row is already the click
    target that the Svelte version reproduces with a cursor prop.
    """
    badge = f'<small style="{_BETA_S}">Beta</small>' if beta else ""
    return (
        f'<label style="{_ROW_S}">'
        f'<input data-cy="{_hook(key)}" type="checkbox" name="{e(key, quote=True)}" '
        f'value="1"{" checked" if on else ""} />'
        f"<span><span style=\"{_NAME_S}\">{e(label)}</span>{badge}"
        f'<small style="{_CAPTION_S}">{e(caption)}</small></span>'
        f"</label>"
    )


def _current(request: Request) -> dict:
    cfg = request.app.state.config
    return {key: bool(getattr(cfg, key, False)) for key, _, _, _ in FIELDS}


def render_features(request: Request, saved: bool = False) -> str:
    on = _current(request)
    rows = "".join(_row(k, lb, cp, bt, on[k]) for k, lb, cp, bt in FIELDS)
    # `<output>` carries an implicit status role, so the save confirmation
    # announces itself with no ARIA attribute written by hand.
    note = (
        '<output data-cy="features-saved" style="--size:.8rem; --op:.75">Features saved.</output>'
        if saved
        else ""
    )
    return f"""
<section data-cy="features-panel">
  <form method="post" action="/pages/admin/setup/features/save">
    <fieldset style="--b:0; --p:0; --m:0">
      <legend style="--size:.85rem; --weight:600; --p:0">
        Enable or disable platform features for your users.
      </legend>
      {rows}
    </fieldset>
    <button data-cy="features-save" type="submit"
            style="--p:.45rem 1rem; --br:999px; --b:1px solid var(--line); --cur:pointer">
      Save
    </button>
    {note}
  </form>
</section>
"""


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
