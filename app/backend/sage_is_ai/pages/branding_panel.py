"""Theme & branding as a server-rendered fragment — the third surface.

The first form-only surface to go through this. Sprigs and diagnostics are both
lists of things with buttons; this is seven fields and a save, which is the
shape the plan claimed htmx deletes the most code on. That claim is now
measurable rather than asserted.

Two decisions worth reading before editing.

**The preview reflects SAVED branding, not what is being typed.** The Svelte
page updates it on every keystroke because the values are bound to a client-side
model. Reproducing that here would mean either a round-trip per keystroke or a
client-side copy of the form state — the second being exactly the duplication
this migration exists to delete. So the preview re-renders when the save
returns. That is a real behaviour difference and it is written into the
guard-rail spec and the UX-review item rather than left for someone to discover.

**The hex field is the authority; the colour picker is a convenience.**
`<input type="color">` cannot express "unset" — it submits `#000000` when
untouched — and unset is a meaningful value here, since empty means "use the
theme's own colours". So the text field carries the value and a ten-line island
keeps the picker in step with it. That island is the only script these pages
ship beyond htmx, and it is why the pair cannot be done with inline handlers:
an operator who follows the diagnostics page's advice and sets a
Content-Security-Policy would break them.
"""

from __future__ import annotations


from fastapi import Request

from sage_is_ai.pages.templates import render

__all__ = ["render_branding", "save_branding", "FIELDS"]

# name, label, placeholder, help. The order is the order they render, and the
# grouping below reads off it, so adding a field is one row here plus one entry
# in _GROUPS.
FIELDS: tuple[tuple[str, str, str, str], ...] = (
    ("logo_url", "Logo URL (Light Mode)", "https://example.com/logo.png",
     "URL to your logo image for light mode"),
    ("logo_dark_url", "Logo URL (Dark Mode)", "https://example.com/logo-dark.png",
     "Falls back to the light-mode logo when empty"),
    ("favicon_url", "Favicon URL", "https://example.com/favicon.ico",
     "URL to your favicon (browser tab icon)"),
    ("title", "Application Title", "Sage.is AI",
     "Main title displayed in your application"),
    ("subtitle", "Application Subtitle", "Powered by Sage.is AI UI",
     "Subtitle or tagline for your application"),
)

_COLORS: tuple[tuple[str, str, str, str], ...] = (
    ("primary_color", "Primary Color", "#3B82F6", "Main brand colour (buttons, links)"),
    ("accent_color", "Accent Color", "#10B981", "Secondary accent colour for highlights"),
)

_GROUPS = (
    ("Logo Settings", FIELDS[:3]),
    ("Text Settings", FIELDS[3:]),
)


# startr.style props, written once here and repeated by the generator rather
# than by a human. This is the whole reason the props cost so little: a rule
# that appears on five fields is one string in this file, and editing it is
# editing one line — no stylesheet to open, no class name to invent, no round
# trip between two files to see what a field looks like.
#
# Mobile-first, per the framework's own contract: base values are the phone
# case and a suffix appears only where the layout genuinely changes going up.
# Nothing here changes going up, so nothing carries a suffix.
# A fieldset IS a group of related form controls and a legend IS its caption,
# so the browser gives us the grouping and the accessible name for free — no
# section/h2 pair, no class, nothing to keep in step. The three props only undo
# the UA's default chrome; the semantics are what we came for.


def _current(request: Request) -> dict:
    """Branding as the config holds it.

    Read through `app.state.config`, never the module-level PersistentConfig —
    `AppConfig.__getattr__` checks Redis for a newer value when Redis is
    configured, so a direct module read would be correct on one worker and stale
    on the next.

    Config writes a plain dict (`config.py` stores `branding.model_dump()`), but
    `routers/configs.get_branding` defends against a model instance too, so this
    does the same. The difference matters: falling back to `{}` for an
    unrecognised shape would render a perfectly normal-looking EMPTY form, and
    an operator who then pressed Save would wipe their branding. An empty form
    is not a safe default when the form overwrites what it failed to read.
    """
    data = request.app.state.config.BRANDING
    if isinstance(data, dict):
        return dict(data)
    if hasattr(data, "model_dump"):
        return dict(data.model_dump())
    return {}


def render_branding(request: Request, *, message: str = "", kind: str = "info") -> str:
    """Build the context; `templates/branding.html` decides how it looks.

    The whole panel is also the whole htmx swap target, so what comes back from
    a save is the same shape as what came back from the GET.
    """
    b = _current(request)

    def field(name: str, label: str, placeholder: str, help_text: str) -> dict:
        value = str(b.get(name) or "")
        return {
            "name": name,
            "hook": name.replace("_", "-"),
            "label": label,
            "placeholder": placeholder,
            "help": help_text,
            "value": value,
            # The picker cannot express "unset", so it falls back to black while
            # the text field beside it stays genuinely empty.
            "picker_value": value or "#000000",
        }

    return render(
        "branding.html",
        message=message,
        kind=kind,
        groups=[
            {"name": name, "fields": [field(*f) for f in fields]}
            for name, fields in _GROUPS
        ],
        colors=[field(*f) for f in _COLORS],
        preview={
            "logo_url": b.get("logo_url") or "",
            "title": b.get("title") or "",
            "subtitle": b.get("subtitle") or "",
            "primary_color": b.get("primary_color") or "",
            "swatches": [
                {"kind": kind_, "color": b[key]}
                for kind_, key in (("primary", "primary_color"), ("accent", "accent_color"))
                if b.get(key)
            ],
        },
    )

async def save_branding(request: Request, user, form: dict) -> str:
    """Persist through the API handler, then re-render.

    `routers/configs.set_branding` owns the model and the admin check, so this
    does not restate either. The fields come from FIELDS rather than from
    whatever the browser posted, so an extra form value cannot reach the config.
    """
    from sage_is_ai.routers.configs import BrandingModel, set_branding

    names = [f[0] for f in FIELDS] + [c[0] for c in _COLORS]
    payload = {n: str(form.get(n) or "").strip() for n in names}

    try:
        await set_branding(request, BrandingModel(**payload), user)
    except Exception as exc:  # noqa: BLE001 — the operator gets the reason
        return render_branding(request, message=f"Could not save branding: {exc}", kind="error")

    return render_branding(request, message="Branding saved.", kind="success")
