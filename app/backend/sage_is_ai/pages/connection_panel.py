"""Model providers. Verify a connection, then keep it.

Two cards, OpenAI and Ollama, each with a URL and a button that verifies before
it saves. Verifying first is the whole point of the step: a saved-but-unreachable
provider is how an instance ends up looking configured and answering nothing.

The API key is never rendered back. This is a deliberate difference from the
Svelte panel, which reads `OPENAI_API_KEYS[0]` into a password field on mount,
so the live secret travels to the browser and sits in the DOM. A server-rendered
page would put it in the HTML source itself, where it reaches the disk cache and
the back button. So the field renders empty, its placeholder says whether a key
is already stored, and an empty submission means "keep the one you have". The
only way to see a stored key remains the API, which is where the authorisation
check lives.

Saving goes through the API handlers, which matters more here than usual.
`openai.update_config` refuses to persist a newly-added URL it cannot reach, and
that check is the reason this step exists at all. Writing `app.state.config`
directly would skip it and hand the operator exactly the broken instance the
verify button is meant to prevent.

Only the first URL in each list is edited. Both providers support several, and
the admin connections page is where that belongs; this is the setup wizard,
where the useful question is whether there is one working provider at all. The
rest of the list is read, preserved, and written back untouched.
"""

from __future__ import annotations

from html import escape as e

from fastapi import Request

from sage_is_ai.pages.i18n import lang_query, translator

__all__ = ["render_connection", "verify_and_save", "PROVIDERS"]

# key, label, url field, url placeholder, whether it takes an API key
PROVIDERS: tuple[tuple[str, str, str, str, bool], ...] = (
    ("openai", "OpenAI API", "url", "https://api.openai.com/v1", True),
    ("ollama", "Ollama", "url", "http://host.docker.internal:11434", False),
)

_CARD_S = ("--p:.85rem; --br:.6rem; --b:1px solid var(--line); --m:0 0 .75rem")
_NAME_S = "--size:.85rem; --weight:600"
_STATE_S = "--size:.6rem; --weight:500; --tt:uppercase; --ml:.4rem; --op:.75"
_LABEL_S = "--size:.7rem; --weight:500; --d:block; --m:.5rem 0 .15rem"
_INPUT_S = ("--w:100%; --bxs:border-box; --p:.4rem .6rem; --size:.78rem; "
            "--br:.4rem; --b:1px solid var(--line); --bgc:transparent; --c:inherit")
_BUTTON_S = ("--p:.35rem .8rem; --size:.75rem; --br:.4rem; "
             "--b:1px solid var(--line); --cur:pointer; --m:.6rem 0 0")


def _state(request: Request, provider: str) -> tuple[str, str]:
    """Current URL and whether this provider is switched on.

    Read through `app.state.config`, never the module-level PersistentConfig
    objects: they are the same objects today, but AppConfig checks Redis for a
    newer value, so a direct module read would be correct on one worker and
    stale on the next.
    """
    cfg = request.app.state.config
    if provider == "openai":
        urls = list(getattr(cfg, "OPENAI_API_BASE_URLS", []) or [])
        on = bool(getattr(cfg, "ENABLE_OPENAI_API", False))
    else:
        urls = list(getattr(cfg, "OLLAMA_BASE_URLS", []) or [])
        on = bool(getattr(cfg, "ENABLE_OLLAMA_API", False))
    return (urls[0] if urls else ""), ("configured" if on and urls and urls[0] else "")


def _has_key(request: Request) -> bool:
    keys = list(getattr(request.app.state.config, "OPENAI_API_KEYS", []) or [])
    return bool(keys and keys[0])


def _card(request: Request, key: str, label: str, _f: str, placeholder: str,
          takes_key: bool, _, lang: str) -> str:
    url, state = _state(request, key)
    badge = (
        f'<small data-state="{e(state, quote=True)}" style="{_STATE_S}">{e(state)}</small>'
        if state
        else ""
    )
    # The key field is empty by design. Its placeholder is the only thing that
    # reports whether one is stored, and it reports existence, never the value.
    key_field = (
        f'<label style="{_LABEL_S}">{e(_("API Key"))}</label>'
        f'<input data-cy="connection-openai-key" type="password" name="api_key" '
        f'autocomplete="off" placeholder="'
        f'{_("a key is stored, leave blank to keep it") if _has_key(request) else "sk-..."}" '
        f'style="{_INPUT_S}" />'
        if takes_key
        else ""
    )
    return f"""
<article data-cy="connection-{e(key, quote=True)}" data-provider-state="{e(state or 'unset', quote=True)}"
         style="{_CARD_S}">
  <form method="post" action="/pages/admin/setup/connection/{e(key, quote=True)}{lang}">
    <strong style="{_NAME_S}">{e(_(label))}</strong>{badge}
    <label style="{_LABEL_S}">{e(_("API Base URL"))}</label>
    <input data-cy="connection-{e(key, quote=True)}-url" type="text" name="url"
           value="{e(url, quote=True)}" placeholder="{e(placeholder, quote=True)}"
           style="{_INPUT_S}" />
    {key_field}
    <button data-cy="connection-{e(key, quote=True)}-verify" type="submit"
            style="{_BUTTON_S}">{e(_("Verify & Save"))}</button>
  </form>
</article>
"""


def render_connection(request: Request, message: str = "") -> str:
    _ = translator(request)
    lang = lang_query(request)
    cards = "".join(_card(request, *p, _, lang) for p in PROVIDERS)
    note = (
        f'<output data-cy="connection-result" style="--size:.8rem; --op:.8">{e(message)}</output>'
        if message
        else ""
    )
    return f"""
<section data-cy="connection-panel">
  <p style="--size:.85rem">{e(_("Add at least one connection to start chatting with AI models."))}</p>
  {cards}
  {note}
</section>
"""


async def verify_and_save(request: Request, user, provider: str, form: dict) -> str:
    """Verify the URL, then persist it. Never one without the other.

    The backend's own failure text is what reaches the operator, because it says
    which host refused and why. "Connection failed" says neither, and this is the
    step where a wrong answer costs the most: everything downstream assumes a
    model provider answers.
    """
    from fastapi import HTTPException

    url = str(form.get("url", "")).strip()
    if not url:
        return render_connection(request, "Enter a URL first.")

    if provider == "openai":
        from sage_is_ai.routers.openai import (
            ConnectionVerificationForm,
            OpenAIConfigForm,
            update_config,
            verify_connection,
        )

        cfg = request.app.state.config
        keys = list(getattr(cfg, "OPENAI_API_KEYS", []) or [])
        posted = str(form.get("api_key", "")).strip()
        # Empty means keep. That is what lets the field render blank without
        # making every save wipe the stored key.
        api_key = posted or (keys[0] if keys else "")

        try:
            await verify_connection(
                ConnectionVerificationForm(url=url, key=api_key), user
            )
        except HTTPException as exc:
            return render_connection(request, f"OpenAI did not verify: {exc.detail}")
        except Exception as exc:  # noqa: BLE001 — the reason is the message
            return render_connection(request, f"OpenAI did not verify: {exc}")

        urls = list(getattr(cfg, "OPENAI_API_BASE_URLS", []) or [])
        urls = [url] + urls[1:] if urls else [url]
        keys = [api_key] + keys[1:] if keys else [api_key]
        await update_config(
            request,
            OpenAIConfigForm(
                ENABLE_OPENAI_API=True,
                OPENAI_API_BASE_URLS=urls,
                OPENAI_API_KEYS=keys,
                OPENAI_API_CONFIGS=dict(getattr(cfg, "OPENAI_API_CONFIGS", {}) or {}),
            ),
            user,
        )
        return render_connection(request, "OpenAI verified and saved.")

    from sage_is_ai.routers.ollama import (
        ConnectionVerificationForm,
        OllamaConfigForm,
        update_config,
        verify_connection,
    )

    cfg = request.app.state.config
    try:
        await verify_connection(ConnectionVerificationForm(url=url), user)
    except HTTPException as exc:
        return render_connection(request, f"Ollama did not verify: {exc.detail}")
    except Exception as exc:  # noqa: BLE001
        return render_connection(request, f"Ollama did not verify: {exc}")

    urls = list(getattr(cfg, "OLLAMA_BASE_URLS", []) or [])
    urls = [url] + urls[1:] if urls else [url]
    await update_config(
        request,
        OllamaConfigForm(
            ENABLE_OLLAMA_API=True,
            OLLAMA_BASE_URLS=urls,
            OLLAMA_API_CONFIGS=dict(getattr(cfg, "OLLAMA_API_CONFIGS", {}) or {}),
        ),
        user,
    )
    return render_connection(request, "Ollama verified and saved.")
