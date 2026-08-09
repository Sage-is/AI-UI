"""A person's own calendar feeds — the first per-user no-build settings page.

WHY THIS EXISTS. `HOME_CALENDAR_ICS_URL` was an instance-wide `PersistentConfig`,
so every person on the instance saw the same calendar. On a personal dashboard
that is simply wrong, and on a school instance one teacher's feed would have
appeared on every student's home page. This is the other half of the fix.

THE RULE THAT DECIDES WHICH SIDE A SETTING FALLS ON: a **wire** is what the
operator must decide; a **setting** is what a person must decide. A wire is set
once by an admin, so anything two people would answer differently cannot be one.
Shared feeds — term dates, company holidays — are wires on the Calendar Sprig™.
These are not.

NO NEW STORAGE. `users.settings` is a JSON column that allows extra keys
(`models/users.py:41`), and `update_user_settings_by_id` merges rather than
replaces (`:359`), so a person's calendar settings do not disturb their UI ones.

NO PER-USER SECRETS, DELIBERATELY. Feeds here are public ICS URLs only.
`users.settings` is plain JSON in the database, so a personal CalDAV password
would be a credential stored in the clear. Authenticated CalDAV waits for
somewhere to keep a secret, and the page says so rather than offering a field
that quietly does the wrong thing.

This is also the first per-user surface on the no-build stack — every other
`/pages/*` page is admin-gated or read-only. Keep it small; it is the pattern
every settings tab will need eventually.
"""

from __future__ import annotations

from typing import Any

from fastapi import Request

from sage_is_ai.models.users import Users
from sage_is_ai.pages.calendar_card import feed_urls, forget
from sage_is_ai.pages.i18n import lang_query, translator
from sage_is_ai.pages.templates import render

__all__ = ["render_settings_calendar", "save_settings_calendar", "user_calendar"]

_SETTINGS_KEY = "calendar"


def user_calendar(user) -> dict[str, Any]:
    """One person's calendar settings, with defaults. Never raises.

    Read by the home card and the calendar page as well as this one, so the
    shape has a single definition rather than three that agree by luck.
    """
    settings = getattr(user, "settings", None) or {}
    if hasattr(settings, "model_dump"):
        settings = settings.model_dump()
    block = (settings or {}).get(_SETTINGS_KEY) or {}
    return {
        "feeds": list(block.get("feeds") or []),
        "hidden_shared": list(block.get("hidden_shared") or []),
    }


def render_settings_calendar(request: Request, user, *, message: str = "") -> str:
    _ = translator(request)
    lang = lang_query(request)
    mine = user_calendar(user)

    return render(
        "settings-calendar.html",
        message=message,
        heading=_("Your calendars"),
        intro=_(
            "Calendar feeds only you see. Paste an iCalendar (.ics) address, one "
            "per line. A shared Nextcloud calendar publishes a read-only link "
            "that needs no password."
        ),
        feeds_label=_("Your calendar feeds"),
        feeds="\n".join(mine["feeds"]),
        save_label=_("Save"),
        back_label=_("Back to the calendar"),
        # The SPA route. This link was the far end of a one-way door: reached
        # from the dashboard, it sent the reader to another chrome-less page
        # rather than back into the app.
        back_url=f"/calendar{lang}",
        action=f"/pages/settings/calendar{lang}",
        privacy_note=_(
            "These are yours alone. Anyone else on this instance sees only their "
            "own feeds, plus any calendars an administrator has shared with "
            "everyone."
        ),
        secret_note=_(
            "Public feeds only for now. Calendars that need a username and "
            "password are not supported yet, because there is nowhere to keep "
            "your password safely."
        ),
    )


async def save_settings_calendar(request: Request, user, form: dict) -> str:
    """Store the feeds, then re-render.

    Validated the same way a `url` wire is, so an operator and a person meet the
    same rule: http(s) only, because a `file://` here would ask the server to
    read a local path on somebody's behalf.
    """
    _ = translator(request)
    submitted = feed_urls(form.get("feeds", ""))

    bad = [u for u in submitted if not u.lower().startswith(("http://", "https://"))]
    if bad:
        return render_settings_calendar(
            request, user, message=_("Feeds must start with http:// or https://.")
        )

    # A MERGE at the top level — `update_user_settings_by_id` merges keys, so
    # writing `calendar` leaves `ui` and everything else alone.
    existing = user_calendar(user)
    Users.update_user_settings_by_id(
        user.id, {_SETTINGS_KEY: {**existing, "feeds": submitted}}
    )

    # Forget what was cached for the feeds that changed, so a corrected URL
    # takes effect now rather than after the five-minute cache expires.
    forget(list(set(existing["feeds"]) ^ set(submitted)))

    # Re-read rather than trusting what was sent: the page must show what is
    # stored, so a save that silently dropped something is visible immediately.
    fresh = Users.get_user_by_id(user.id) or user
    return render_settings_calendar(request, fresh, message=_("Saved."))
