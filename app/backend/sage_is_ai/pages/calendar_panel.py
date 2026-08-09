"""The Calendar page — an agenda and a month grid, from the same events.

The home card shows four things and a dot grid; this is where you go when four
is not enough. Both read `calendar_card`, so there is one parser, one cache and
one idea of which day a week starts on.

NO SCRIPT, and month navigation is the reason it can stay that way. The month
lives in the URL as `?month=YYYY-MM`, so previous and next are ordinary links:
shareable, back-button-correct, and cacheable per month. Holding it in component
state would have bought nothing and cost a runtime.

WHAT THE PAGE SHOWS ABOUT ITS OWN LIMITS. The parser expands the repeats people
actually keep — daily, weekly on set days, monthly — and does not expand
`EXDATE`, `BYSETPOS`, or named timezones. A calendar that is quietly wrong is
worse than one that says where it stops, so the page carries that note when a
feed is configured rather than burying it in a docstring nobody opens.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import Request

from sage_is_ai.pages.calendar_card import (
    feed_urls,
    group_by_day,
    month_grid,
    sample_events,
    shared_feeds,
    WEEKDAY_SHORT,
    upcoming,
)
from sage_is_ai.pages.settings_calendar_panel import user_calendar
from sage_is_ai.pages.i18n import lang_query, translator
from sage_is_ai.pages.templates import render

__all__ = ["render_calendar"]

# Enough to fill a page without turning a daily standup into a wall.
_AGENDA_LIMIT = 40


def _month_from(value: str) -> tuple[int, int]:
    """`?month=2026-09` → (2026, 9). Anything else → this month.

    Deliberately forgiving rather than a 422: a stale bookmark or a hand-typed
    URL should land on the current month, not an error page. The value is only
    ever used to build dates, so a bad one costs nothing.
    """
    today = datetime.now(timezone.utc).date()
    try:
        year_s, month_s = value.split("-", 1)
        year, month = int(year_s), int(month_s)
        if 1 <= month <= 12 and 1970 <= year <= 2999:
            return year, month
    except (ValueError, AttributeError):
        pass
    return today.year, today.month


def _shift(year: int, month: int, delta: int) -> str:
    index = (year * 12 + month - 1) + delta
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def render_calendar(request: Request, user, month: str = "") -> str:
    _ = translator(request)
    lang = lang_query(request)

    # Both layers, same rule as the home card: operator wires the shared feeds,
    # each person keeps their own. Preview from the .ics stub when neither has
    # anything — never mixed with real events, so nobody has to work out which
    # rows are theirs.
    shared = shared_feeds(request)
    mine = user_calendar(user)
    configured = bool(shared or mine["feeds"])
    events = (
        upcoming(shared, personal="\n".join(mine["feeds"]), hidden_shared=mine["hidden_shared"])
        if configured
        else sample_events()
    )

    year, month_num = _month_from(month)
    shown = date(year, month_num, 1)
    base = f"/pages/calendar{lang or '?'}" + ("&" if lang else "")

    return render(
        "calendar.html",
        configured=bool(configured),
        example=not configured,
        example_note=_(
            "Nothing connected yet. This is an example, so you can see what a "
            "connected calendar looks like."
        ),
        feed_count=len(feed_urls(shared)) + len(mine["feeds"]),
        # The SPA route, not the bare server page — leaving this surface should
        # keep the sidebar. The month links below are the opposite case: they
        # stay on `/pages/calendar` so Startr Swap can swap them in place.
        settings_url=f"/settings/calendar{lang}",
        settings_label=_("Your calendars"),
        unset=_(
            "No calendars yet. Add your own in settings, or ask an "
            "administrator to share one with everyone."
        ),
        month_label=shown.strftime("%B %Y"),
        weekday_names=[_(d) for d in WEEKDAY_SHORT],
        grid=month_grid(events, year, month_num),
        prev_url=f"{base}month={_shift(year, month_num, -1)}",
        next_url=f"{base}month={_shift(year, month_num, 1)}",
        today_url=f"/pages/calendar{lang}",
        prev_label=_("Previous"),
        next_label=_("Next"),
        today_label=_("Today"),
        agenda_title=_("Coming up"),
        agenda=group_by_day(events[:_AGENDA_LIMIT]),
        agenda_empty=_("Nothing coming up."),
        limits_note=_(
            "Repeating events are expanded for daily, weekly and monthly rules. "
            "Cancelled instances, rules like “last Friday of the month”, and "
            "named time zones are not handled yet."
        ),
    )
