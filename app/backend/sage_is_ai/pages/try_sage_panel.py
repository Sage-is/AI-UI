"""The try.sage welcome page, server-rendered.

The replacement for `TrySageWelcome.svelte`, which painted a `position:fixed`
100vh layer and flex-centered its content — on a phone the layer sat behind the
browser chrome and the centered overflow was cut off the top and bottom with no
way to scroll to it (Reviewer T's bottom-of-page cutoff, reported on 2.3.2 and
reproduced on 3.0.0). The template renders a normal document that scrolls,
which is the whole fix.

Anonymous by design: this is what a visitor WITHOUT an invite sees. The magic
link a facilitator shares lands on `/auth` and is processed by the SPA before
this page is ever relevant, so there is nothing here to gate — no sign-in form,
no signup, no escape hatch, per the trial's invite-only contract.

Copy uses the English sentences as i18n keys, the same keys the Svelte version
registered, so existing locale catalogs translate this page for free.
"""

from fastapi import Request

from sage_is_ai.pages.i18n import locale_for, translator
from sage_is_ai.pages.shell import asset_url
from sage_is_ai.pages.templates import render

__all__ = ["render_try_sage"]

# Mirrors the seed in routers/sage_runtime.py + utils/try_sage_seed.py. The
# copy reads accurately whatever TRY_SAGE_USER_SEAT_COUNT is, because no user
# is listed individually.
_ROLES = (
    (
        "Admin",
        "Full control of this trial environment. Resets the workspace, extends "
        "the deadline, helps Facilitators and Users when something looks off.",
    ),
    (
        "Facilitator",
        "Guide and helper. Sees what Users see. In schools, this is the teacher "
        "role. In offices, this is a project manager, team lead, or workshop host.",
    ),
    (
        "Users",
        "Workshop attendees. Try the agents, explore models, build something "
        "small you can take with you. The trial resets cleanly each day so the "
        "next cohort starts fresh.",
    ),
)


def render_try_sage(request: Request) -> str:
    _ = translator(request)
    cfg = request.app.state.config

    # Same precedence as the Svelte version: custom branding logo wins, then
    # the favicon pair. The dark variant rides a <picture> source instead of
    # the DOM-swapping script the component needed.
    branding = cfg.BRANDING or {}
    logo = branding.get("logo_url") or "/static/icons/favicon.png"
    logo_dark = branding.get("logo_dark_url") or (
        "" if branding.get("logo_url") else "/static/icons/favicon-dark.png"
    )

    from sage_is_ai.env import PAGES_RELOAD_DIRS

    return render(
        "try-sage.html",
        lang=locale_for(request),
        title=_("Welcome to try.sage.is AI"),
        tagline=_(
            "This trial is by invitation only. Your Sage.is AI workshop "
            "facilitator will share the link you need to sign in."
        ),
        logo=logo,
        logo_dark=logo_dark,
        roles_heading=_("Roles in this trial"),
        roles=[{"title": _(t), "detail": _(d)} for t, d in _ROLES],
        signin_heading=_("How to sign in"),
        in_person_title=_("At an in-person workshop"),
        in_person_detail=_(
            "Scan the QR code your facilitator shared, or open the link they "
            "passed around."
        ),
        remote_title=_("Joining remotely"),
        remote_detail=_(
            "Check the email your workshop organizer sent. Open the magic link "
            "there to sign in."
        ),
        lost_link=_(
            "Lost your link? Reach out to whoever invited you and they'll "
            "resend it."
        ),
        banner_text=str(cfg.TRY_SAGE_BANNER_TEXT or ""),
        # SlideShow.svelte's image list, same order. Its cycler skipped the
        # last image (`% (length - 1)`); this one cycles all four on purpose.
        slides=[
            "/static/assets/images/library.webp",
            "/static/assets/images/galaxy.jpg",
            "/static/assets/images/earth.jpg",
            "/static/assets/images/space.jpg",
        ],
        slideshow_src=asset_url("try-sage-slideshow.js"),
        dev_reload_src=asset_url("dev-reload.js") if PAGES_RELOAD_DIRS else "",
    )
