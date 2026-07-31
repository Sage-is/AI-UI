"""Sign-in providers: Google, GitHub, and an emailed magic link.

The last wizard panel, and the one the plan flagged as hardest. That reading was
wrong. `AuthStep.svelte` is 65 lines that mount `OAuthSettings.svelte` — 829 —
through `bind:this` and call an imperative `export const save`, and that pattern
has no server analogue. But the pattern is Svelte plumbing, not the data path.
Underneath it are two ordinary handlers, `update_oauth_config` and
`update_admin_config`, so what the panel actually needs is a form.

Only the compact half is here. `OAuthSettings` serves both this wizard and
Admin > Settings > Auth, and `compact` hides LDAP, API keys, JWT expiry and the
rest. Those belong to the admin page, which is not this surface, so migrating
them would be migrating something nobody asked for.

**Secrets are never rendered back.** `GET /api/v1/auths/admin/config/oauth`
returns `GOOGLE_CLIENT_SECRET`, `GITHUB_CLIENT_SECRET` and
`MAGIC_LINK_SMTP_PASSWORD` in the clear, and the Svelte panel binds all three
into inputs, so opening that step today ships every OAuth secret to the browser.
Here the fields render empty and say a secret is stored. Submitting one blank
keeps what is on disk, which is the same contract the connection panel's API key
uses.

Every checkbox renders every time, including the two the Svelte panel hides
behind `adminConfig.ENABLE_SIGNUP && anyOAuthConfigured`. An unchecked checkbox
posts nothing, and this form reads absence as False, so a control that is hidden
rather than unchecked would silently turn its setting off the next time anyone
pressed Save. Hiding a checkbox whose absence means False is a data-loss bug
waiting for a layout change. The conditional warnings still appear or not; the
inputs are constant.

The disclosure panels are `<details>`. So are the Svelte ones — that part was
already native HTML and needed no translation.
"""

from __future__ import annotations

from html import escape as e

from fastapi import Request

from sage_is_ai.pages.i18n import lang_query, translator

__all__ = ["render_auth", "save_auth", "PROVIDERS", "SECRETS", "TOGGLES"]

# id_key, secret_key, label, console URL, console link text, what to do there,
# callback path, id placeholder, secret placeholder.
PROVIDERS: tuple[tuple[str, ...], ...] = (
    (
        "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "Google",
        "https://console.cloud.google.com/apis/credentials",
        "Open Google Cloud Console",
        "create an OAuth 2.0 Client ID under Credentials, then Create "
        "Credentials, then OAuth client ID. Choose Web application as the type.",
        "/oauth/google/callback",
        "123456789.apps.googleusercontent.com", "GOCSPX-...",
    ),
    (
        "GITHUB_CLIENT_ID", "GITHUB_CLIENT_SECRET", "GitHub",
        "https://github.com/settings/developers",
        "Open GitHub Developer Settings",
        "click New OAuth App, then fill in your app name and homepage URL.",
        "/oauth/github/callback",
        "Iv1.abc123...", "the generated client secret",
    ),
)

# Fields whose stored value must never reach the browser.
SECRETS: tuple[str, ...] = (
    "GOOGLE_CLIENT_SECRET",
    "GITHUB_CLIENT_SECRET",
    "MAGIC_LINK_SMTP_PASSWORD",
)

# Every boolean on this panel, and where each one is stored. `ENABLE_SIGNUP`
# belongs to the admin config; the rest belong to the OAuth config. Two homes,
# two handlers, one form.
TOGGLES: tuple[tuple[str, str, str, str], ...] = (
    ("ENABLE_SIGNUP", "admin", "Enable new sign ups",
     "Anyone who can reach this instance can create an account."),
    ("ENABLE_OAUTH_SIGNUP", "oauth", "Allow OAuth sign up",
     "New people can create an account by signing in with a provider above. "
     "Turn this off and only existing accounts can use OAuth."),
    ("OAUTH_MERGE_ACCOUNTS_BY_EMAIL", "oauth", "Merge accounts by email",
     "Link an OAuth login to an existing account when the email matches. Turn "
     "this off to keep OAuth and password accounts separate."),
)

# The magic-link SMTP fields: name, label, input type, placeholder.
SMTP_FIELDS: tuple[tuple[str, str, str, str], ...] = (
    ("MAGIC_LINK_SMTP_HOST", "SMTP host", "text", "smtp.gmail.com"),
    ("MAGIC_LINK_SMTP_PORT", "Port", "number", "587"),
    ("MAGIC_LINK_SMTP_USER", "Username", "text", "you@example.com"),
    ("MAGIC_LINK_SMTP_PASSWORD", "Password", "password", "App or SMTP password"),
    ("MAGIC_LINK_SMTP_FROM", "From address", "email", "noreply@yourdomain.com"),
)

_CARD_S = "--b:1px solid var(--line); --br:.6rem; --m:0 0 .6rem; --p:0"
_SUMMARY_S = "--p:.7rem .8rem; --cur:pointer; --size:.85rem; --weight:500"
_INNER_S = "--p:0 .8rem .8rem"
_LABEL_S = "--size:.72rem; --weight:500; --d:block; --m:.5rem 0 .15rem"
_INPUT_S = ("--w:100%; --bxs:border-box; --p:.4rem .6rem; --size:.78rem; "
            "--br:.4rem; --b:1px solid var(--line); --bgc:transparent; --c:inherit")
_HELP_S = "--size:.7rem; --op:.7; --lh:1.5; --m:.35rem 0 0"
_CODE_S = "--size:.68rem; --p:.1rem .3rem; --br:.25rem; --b:1px solid var(--line); --wb:break-all"
_ROW_S = ("--d:flex; --ai:start; --g:.6rem; --p:.6rem; --br:.5rem; "
          "--b:1px solid var(--line); --m:0 0 .4rem; --cur:pointer")
_CAPTION_S = "--size:.7rem; --op:.7; --d:block"
_BADGE_S = ("--size:.6rem; --weight:600; --tt:uppercase; --ml:.4rem; --p:.1rem .3rem; "
            "--br:.25rem; --b:1px solid var(--line)")


def _hook(key: str) -> str:
    """A test hook derived from the config key, so the two cannot drift apart."""
    return "auth-" + key.lower().replace("_", "-")


def _text_input(name: str, kind: str, placeholder: str, value: str, _) -> str:
    """One input. Secret fields render empty and say why."""
    if name in SECRETS:
        stored = bool(value)
        hint = _("A secret is stored. Leave blank to keep it.") if stored else placeholder
        return (
            f'<input data-cy="{_hook(name)}" type="password" name="{e(name, quote=True)}" '
            f'value="" autocomplete="new-password" data-stored="{str(stored).lower()}" '
            f'placeholder="{e(hint, quote=True)}" style="{_INPUT_S}" />'
        )
    return (
        f'<input data-cy="{_hook(name)}" type="{kind}" name="{e(name, quote=True)}" '
        f'value="{e(value, quote=True)}" placeholder="{e(placeholder, quote=True)}" '
        f'style="{_INPUT_S}" />'
    )


def _provider(row: tuple[str, ...], cfg: dict, base_url: str, _) -> str:
    id_key, secret_key, label, url, link, how, path, id_ph, secret_ph = row
    client_id = str(cfg.get(id_key) or "")
    configured = bool(client_id and cfg.get(secret_key))
    badge = f'<small style="{_BADGE_S}">{e(_("configured"))}</small>' if configured else ""
    callback = (
        f"{e(_('Set the redirect URI to:'))} <code style=\"{_CODE_S}\">{e(base_url + path)}</code>"
        if base_url
        else ""
    )
    return f"""
<details data-cy="{_hook(id_key).removesuffix('-client-id')}-card" style="{_CARD_S}"{" open" if configured else ""}>
  <summary style="{_SUMMARY_S}">{e(_(label))}{badge}</summary>
  <div style="{_INNER_S}">
    <p style="{_HELP_S}">
      <a href="{e(url, quote=True)}" target="_blank" rel="noopener">{e(_(link))} &#8599;</a>
      &mdash; {e(_(how))} {callback}
    </p>
    <label style="{_LABEL_S}">{e(_("Client ID"))}</label>
    {_text_input(id_key, "text", id_ph, client_id, _)}
    <label style="{_LABEL_S}">{e(_("Client secret"))}</label>
    {_text_input(secret_key, "password", secret_ph, str(cfg.get(secret_key) or ""), _)}
  </div>
</details>
"""


def _toggle(key: str, label: str, caption: str, on: bool, _) -> str:
    """One checkbox, always rendered. See the module docstring on why always."""
    return (
        f'<label style="{_ROW_S}">'
        f'<input data-cy="{_hook(key)}" type="checkbox" name="{e(key, quote=True)}" '
        f'value="1"{" checked" if on else ""} />'
        f'<span><span style="--size:.82rem; --weight:500">{e(_(label))}</span>'
        f'<small style="{_CAPTION_S}">{e(_(caption))}</small></span>'
        f"</label>"
    )


def _magic_link(cfg: dict, _) -> str:
    on = bool(cfg.get("ENABLE_MAGIC_LINK_LOGIN"))
    configured = on and bool(cfg.get("MAGIC_LINK_SMTP_HOST"))
    badge = f'<small style="{_BADGE_S}">{e(_("configured"))}</small>' if configured else ""
    fields = "".join(
        f'<label style="{_LABEL_S}">{e(_(label))}</label>'
        + _text_input(name, kind, placeholder, str(cfg.get(name) or ""), _)
        for name, label, kind, placeholder in SMTP_FIELDS
    )
    return f"""
<details data-cy="auth-magic-link-card" style="{_CARD_S}"{" open" if on else ""}>
  <summary style="{_SUMMARY_S}">{e(_("Email Magic Link"))}<small style="{_BADGE_S}">{e(_("Beta"))}</small>{badge}</summary>
  <div style="{_INNER_S}">
    <p style="{_HELP_S}">
      {e(_("Users with existing accounts can sign in by clicking a link sent to their email. No password needed. Requires SMTP."))}
    </p>
    <label style="{_ROW_S}">
      <input data-cy="{_hook('ENABLE_MAGIC_LINK_LOGIN')}" type="checkbox"
             name="ENABLE_MAGIC_LINK_LOGIN" value="1"{" checked" if on else ""} />
      <span><span style="--size:.82rem; --weight:500">{e(_("Enable Email Magic Link Login"))}</span></span>
    </label>
    {fields}
  </div>
</details>
"""


async def _config(request: Request, user) -> tuple[dict, dict]:
    """Both halves of this panel's state, read through the API handlers."""
    from sage_is_ai.routers.auths import get_admin_config, get_oauth_config

    return dict(await get_oauth_config(request, user)), dict(
        await get_admin_config(request, user)
    )


async def render_auth(request: Request, user, saved: bool = False) -> str:
    _ = translator(request)
    lang = lang_query(request)
    oauth, admin = await _config(request, user)
    base_url = str(admin.get("WEBUI_URL") or "").rstrip("/")
    merged = {**oauth, **admin}

    cards = "".join(_provider(row, oauth, base_url, _) for row in PROVIDERS)
    # `home` rather than `_` for the discarded column. `_` is the translator here,
    # and unpacking over it would shadow it for the rest of the comprehension.
    toggles = "".join(
        _toggle(key, label, caption, bool(merged.get(key)), _)
        for key, home, label, caption in TOGGLES
    )
    note = (
        f'<output data-cy="auth-saved" style="--size:.8rem; --op:.75">'
        f'{e(_("Auth settings saved"))}</output>'
        if saved
        else ""
    )
    return f"""
<section data-cy="auth-panel">
  <form method="post" action="/pages/admin/setup/auth/save{lang}">
    {cards}
    {_magic_link(oauth, _)}
    <fieldset style="--b:0; --p:0; --m:1rem 0 0">
      <legend style="--size:.85rem; --weight:600; --p:0">{e(_("Authentication"))}</legend>
      {toggles}
    </fieldset>
    <button data-cy="auth-save" type="submit"
            style="--p:.45rem 1rem; --br:999px; --b:1px solid var(--line); --cur:pointer">
      {e(_("Save"))}
    </button>
    {note}
  </form>
</section>
"""


def _port(raw: object, fallback: int) -> int:
    """A port the model will accept. `MAGIC_LINK_SMTP_PORT` is typed `int`, and
    an empty or mistyped box would otherwise fail validation for the whole
    form — losing every other field the admin just filled in."""
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return fallback


async def save_auth(request: Request, user, form: dict) -> str:
    """Write both halves, preserving everything neither half of this form owns.

    Read, merge, write. `OAuthConfig` and `AdminConfig` are both whole-object
    models, so posting only what this panel shows would reset every field it does
    not show to the model's defaults. `AdminConfig` alone carries sixteen.
    """
    from sage_is_ai.routers.auths import (
        AdminConfig,
        OAuthConfig,
        update_admin_config,
        update_oauth_config,
    )

    oauth, admin = await _config(request, user)

    for name, _, _, _ in SMTP_FIELDS:
        if name in SECRETS:
            continue
        oauth[name] = str(form.get(name, "")).strip()
    oauth["MAGIC_LINK_SMTP_PORT"] = _port(
        form.get("MAGIC_LINK_SMTP_PORT"), int(oauth.get("MAGIC_LINK_SMTP_PORT") or 587)
    )
    for id_key, _, _, _, _, _, _, _, _ in PROVIDERS:
        oauth[id_key] = str(form.get(id_key, "")).strip()

    # Blank keeps what is stored. This is the only reason an admin can open the
    # panel, change one client ID, and press Save without wiping three secrets
    # the form never showed them.
    for name in SECRETS:
        submitted = str(form.get(name, ""))
        if submitted:
            oauth[name] = submitted

    # Absence means False, which is what makes a checkbox able to turn something
    # off. Every box on this panel is always rendered, so absence really does
    # mean the admin cleared it.
    oauth["ENABLE_MAGIC_LINK_LOGIN"] = "ENABLE_MAGIC_LINK_LOGIN" in form
    for key, home, _, _ in TOGGLES:
        (admin if home == "admin" else oauth)[key] = key in form

    await update_oauth_config(request, OAuthConfig(**oauth), user)
    await update_admin_config(request, AdminConfig(**admin), user)
    return await render_auth(request, user, saved=True)
