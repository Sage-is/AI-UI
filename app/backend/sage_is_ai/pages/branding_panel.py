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

from html import escape as e

from fastapi import Request

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
_LABEL_S = "--size:0.8rem; --weight:500"
_HELP_S = "--size:0.7rem; --c:var(--muted)"
_FIELD_S = "--d:grid; --g:0.25rem; --m:0 0 0.85rem"
_INPUT_S = (
    "--w:100%; --bxs:border-box; --p:0.5rem 0.75rem; --size:0.85rem; "
    "--br:0.5rem; --b:1px solid var(--line); --bgc:transparent; --c:inherit"
)
# A fieldset IS a group of related form controls and a legend IS its caption,
# so the browser gives us the grouping and the accessible name for free — no
# section/h2 pair, no class, nothing to keep in step. The three props only undo
# the UA's default chrome; the semantics are what we came for.
_GROUP_S = "--b:0; --p:0; --m:1.25rem 0"
_LEGEND_S = "--size:0.85rem; --weight:600; --p:0"


def _text_field(name: str, label: str, placeholder: str, help_text: str, value: str) -> str:
    """One form row: caption, control, fine print.

    `<p>` is the element the HTML spec itself uses to wrap a form row, and
    `<small>` is fine print rather than a div pretending to be some. Both come
    with sensible defaults, so the props here are adjustments and not a
    reimplementation.
    """
    n = e(name, quote=True)
    return f"""<p style="{_FIELD_S}">
  <label for="{n}" style="{_LABEL_S}">{e(label)}</label>
  <input id="{n}" name="{n}" type="text" data-cy="branding-{n.replace('_', '-')}"
         style="{_INPUT_S}"
         placeholder="{e(placeholder, quote=True)}" value="{e(value, quote=True)}" />
  <small style="{_HELP_S}">{e(help_text)}</small>
</p>"""


def _color_field(name: str, label: str, placeholder: str, help_text: str, value: str) -> str:
    """A hex field with a picker beside it.

    The picker carries no `name`, so it never submits: it exists to set the text
    field, which is the one the server reads. That is what keeps "empty" a
    reachable value.
    """
    n = e(name, quote=True)
    cy = n.replace("_", "-")
    return f"""<p style="{_FIELD_S}">
  <label for="{n}" style="{_LABEL_S}">{e(label)}</label>
  <span style="--d:flex; --ai:center; --g:0.5rem">
    <input type="color" data-cy="branding-{cy}" data-syncs="{n}"
           style="--fx:0 0 auto; --w:3rem; --h:2.25rem; --p:0; --br:0.35rem;
                  --b:1px solid var(--line); --bgc:transparent; --cur:pointer"
           value="{e(value or '#000000', quote=True)}" aria-label="{e(label)} picker" />
    <input id="{n}" name="{n}" type="text" data-cy="branding-{cy}-text"
           style="--fx:1 1 auto; {_INPUT_S}"
           placeholder="{e(placeholder, quote=True)}" value="{e(value, quote=True)}" />
  </span>
  <small style="{_HELP_S}">{e(help_text)}</small>
</p>"""


def _preview(b: dict) -> str:
    """What the saved branding looks like.

    Every part is conditional on its value, matching the Svelte page: an empty
    accent renders no accent swatch. The parity gate compares both pages against
    the same server state, so these conditions have to agree — a page that
    always renders every swatch would pass a "swatch exists" assertion while
    being wrong.
    """
    logo = (f'<img src="{e(b.get("logo_url") or "", quote=True)}" alt="Logo" '
            f'style="--h:2rem; --w:auto" />' if b.get("logo_url") else "")
    # Spans, not divs: the preview is an <output>, whose content model is
    # phrase content. `--d:block` gets the line break without the invalid
    # nesting a div would produce.
    title = (f'<span style="--d:block; --weight:600; '
             f'--c:{e(b.get("primary_color") or "inherit", quote=True)}">'
             f'{e(b.get("title") or "")}</span>' if b.get("title") else "")
    subtitle = (f'<span style="--d:block; --size:0.75rem; --c:var(--muted)">'
                f'{e(b.get("subtitle") or "")}</span>' if b.get("subtitle") else "")
    # The operator picks these colours, so a swatch can land at any contrast
    # against white. The text shadow keeps a pale one legible without
    # second-guessing their choice.
    swatches = "".join(
        f'<span data-cy="branding-swatch-{kind}" '
        f'style="--p:0.4rem 0.6rem; --br:0.25rem; --size:0.7rem; --c:#fff; '
        f'--bgc:{e(b[key], quote=True)}; --ts:0 1px 2px rgba(0,0,0,0.55)">{kind.title()}</span>'
        for kind, key in (("primary", "primary_color"), ("accent", "accent_color"))
        if b.get(key)
    )
    # <output> is the element for "result derived from the form", which is
    # exactly what this is, and it carries an implicit status role — so the
    # preview announces itself after a save without a single aria attribute.
    return f"""<output data-cy="branding-preview"
     style="--d:grid; --g:0.6rem; --p:1rem; --br:0.5rem; --b:1px solid var(--line)">
  <span style="--d:flex; --ai:center; --g:0.6rem">{logo}<span>{title}{subtitle}</span></span>
  {f'<span style="--d:flex; --fw:wrap; --g:0.5rem">{swatches}</span>' if swatches else ""}
</output>"""


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
    """The whole panel, which is also the whole swap target."""
    b = _current(request)
    groups = "".join(
        f'<fieldset style="{_GROUP_S}"><legend style="{_LEGEND_S}">{e(name)}</legend>'
        + "".join(_text_field(f, l, p, h, str(b.get(f) or "")) for f, l, p, h in fields)
        + "</fieldset>"
        for name, fields in _GROUPS
    )
    colors = "".join(_color_field(f, l, p, h, str(b.get(f) or "")) for f, l, p, h in _COLORS)
    # The one class left on this surface, and the reason is structural rather
    # than habit: the toast fades itself out with @keyframes, and a keyframe is
    # not something the prop vocabulary can express. It is also shared with the
    # Sprigs panel, so it is a real shared rule and not a private one.
    note = (f'<p class="toast toast-float toast-{e(kind, quote=True)}" role="status" '
            f'data-cy="panel-message">{e(message)}</p>' if message else "")

    return f"""<div id="branding-panel">{note}
  <form hx-post="/pages/admin/branding/save" hx-target="#branding-panel" hx-swap="outerHTML">
    {groups}
    <fieldset style="{_GROUP_S}">
      <legend style="{_LEGEND_S}">Color Settings</legend>
      <p style="{_HELP_S}">Overrides the theme colours. Leave empty to use the defaults.</p>
      {colors}
    </fieldset>
    <fieldset style="{_GROUP_S}">
      <legend style="{_LEGEND_S}">Preview</legend>
      {_preview(b)}
    </fieldset>
    <div style="--d:flex; --jc:flex-end; --pt:0.5rem">
      <button type="submit" data-cy="branding-save"
              style="--p:0.45rem 1.1rem; --size:0.85rem; --weight:500; --br:999px;
                     --b:1px solid var(--line); --cur:pointer">Save</button>
    </div>
  </form>
</div>"""


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
