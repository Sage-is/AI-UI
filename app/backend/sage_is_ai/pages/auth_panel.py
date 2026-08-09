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


from fastapi import Request

from sage_is_ai.pages.i18n import lang_query, translator
from sage_is_ai.pages.templates import render

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



def _hook(key: str) -> str:
    """A test hook derived from the config key, so the two cannot drift apart."""
    return "auth-" + key.lower().replace("_", "-")


async def _config(request: Request, user) -> tuple[dict, dict]:
    """Both halves of this panel's state, read through the API handlers."""
    from sage_is_ai.routers.auths import get_admin_config, get_oauth_config

    return dict(await get_oauth_config(request, user)), dict(
        await get_admin_config(request, user)
    )


async def render_auth(request: Request, user, saved: bool = False) -> str:
    """Build the context; `templates/auth.html` decides how it looks."""
    _ = translator(request)
    oauth, admin = await _config(request, user)
    base_url = str(admin.get("WEBUI_URL") or "").rstrip("/")
    merged = {**oauth, **admin}

    def field(name: str, kind: str, placeholder: str, value: str) -> dict:
        """One input as data. Secret fields carry existence, never the value."""
        secret = name in SECRETS
        stored = secret and bool(value)
        return {
            "hook": _hook(name),
            "name": name,
            "kind": kind,
            "secret": secret,
            "stored": stored,
            "value": "" if secret else value,
            "placeholder": (
                _("A secret is stored. Leave blank to keep it.")
                if stored
                else placeholder
            ),
        }

    providers = []
    for id_key, secret_key, label, url, link, how, path, id_ph, secret_ph in PROVIDERS:
        client_id = str(oauth.get(id_key) or "")
        providers.append(
            {
                "hook": _hook(id_key).removesuffix("-client-id") + "-card",
                "label": _(label),
                "configured": bool(client_id and oauth.get(secret_key)),
                "url": url,
                "link": _(link),
                "how": _(how),
                "callback": (base_url + path) if base_url else "",
                "id_field": field(id_key, "text", id_ph, client_id),
                "secret_field": field(
                    secret_key, "password", secret_ph, str(oauth.get(secret_key) or "")
                ),
            }
        )

    magic_on = bool(oauth.get("ENABLE_MAGIC_LINK_LOGIN"))
    return render(
        "auth.html",
        lang=lang_query(request),
        providers=providers,
        magic={
            "on": magic_on,
            "configured": magic_on and bool(oauth.get("MAGIC_LINK_SMTP_HOST")),
            "hook": _hook("ENABLE_MAGIC_LINK_LOGIN"),
            "title": _("Email Magic Link"),
            "enable_label": _("Enable Email Magic Link Login"),
            "help": _(
                "Users with existing accounts can sign in by clicking a link sent to "
                "their email. No password needed. Requires SMTP."
            ),
            "fields": [
                {**field(name, kind, placeholder, str(oauth.get(name) or "")), "label": _(label)}
                for name, label, kind, placeholder in SMTP_FIELDS
            ],
        },
        # `home` rather than `_` for the discarded column. `_` is the translator
        # here, and unpacking over it would shadow it for the rest of the loop.
        toggles=[
            {
                "hook": _hook(key),
                "key": key,
                "label": _(label),
                "caption": _(caption),
                "on": bool(merged.get(key)),
            }
            for key, home, label, caption in TOGGLES
        ],
        legend=_("Authentication"),
        configured_label=_("configured"),
        beta_label=_("Beta"),
        callback_label=_("Set the redirect URI to:"),
        client_id_label=_("Client ID"),
        client_secret_label=_("Client secret"),
        save_label=_("Save"),
        note=_("Auth settings saved") if saved else "",
    )

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
