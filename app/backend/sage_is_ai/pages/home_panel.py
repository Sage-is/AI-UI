"""The home dashboard, server-rendered.

WHY THIS PAGE EXISTS, and it is not the payload argument.

A grafted ui-Sprig™ renders into `#sprig-ui-slot`, and `_ui_sprig_slot` in
`shell.py` emits that slot from `render_page`. Only two modules call
`render_page`, both under `pages/`. So the marketplace slot appears on
server-rendered surfaces and nowhere else — and the signed-in home screen is
`routes/(app)/home/+page.svelte`, which never calls it.

The consequence is that a grafted interface fragment cannot reach the screen a
person opens first. This page is the fix, and it is deliberately the SMALL fix:
a new surface beside the existing ones rather than a conversion of `/`.
`TODO.md:89` warns that the no-build migration is mid-Phase 2 with the wizard
still ahead, and that plan keeps the chat core for last. The signed-in `/` IS
the chat core. Taking it here would invert the sequencing on the hardest surface
in the product.

WHAT IT PORTS. The Svelte `/home` is a dashboard: a greeting, recent chats,
pinned chats, and three placeholder cards at 55% opacity. This carries the same
shape. The placeholders stay placeholders — the real fourth card arrives as a
grafted fragment in the slot, which is the whole point of the exercise.

THE GREETING IS CORRECTED CLIENT-SIDE, and the server still renders one. The
server has no idea what time it is where the reader is, so an instance in UTC
would greet someone in the Azores with the wrong half of the day. Six lines of
inline script in `home.html` re-read the hour from the browser and swap the word.

The server-rendered greeting is not a fallback nobody sees. It is what a reader
with script disabled gets, and it is what the parity gate and every spec read.
The script only ever replaces one word with another word from the same set, so
the page cannot end up empty or wrong if the script never runs.

Styling is IMPORTED from `_workshop.html`. This module adds no style strings of
its own and no lines to `pages.css`.
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import Request

from sage_is_ai.models.chats import Chats
from sage_is_ai.pages.calendar_card import (
    WEEKDAY_NAMES,
    rolling_grid,
    sample_events,
    shared_feeds,
    upcoming,
)
from sage_is_ai.pages.settings_calendar_panel import user_calendar
from sage_is_ai.pages.i18n import lang_query, translator
from sage_is_ai.pages.templates import render

__all__ = ["render_home"]

_RECENT_LIMIT = 5
_PINNED_LIMIT = 5
_CALENDAR_LIMIT = 4

# Mirrors `soonWidgets` in the Svelte page, minus Calendar — that one is real
# now when a feed is configured, and a card cannot be both live and "coming
# soon". The rest stay placeholders; the slot below them is where a grafted card
# lands.
_SOON = (
    (
        "📊",
        "Usage",
        "Track your activity, token usage, and model performance over time.",
    ),
    (
        "⚡",
        "Quick Actions",
        "One-tap shortcuts to your most-used prompts and workflows.",
    ),
)


def _greetings(_) -> dict[str, str]:
    """The three candidate words, translated, plus the server's own guess.

    All three go to the template so `home-greeting.js` can pick by the reader's
    clock without carrying a copy of the copy. The server's pick is what a
    reader with no script sees, and it is what every spec reads.
    """
    hour = time.localtime().tm_hour
    words = {
        "morning": _("Good morning"),
        "afternoon": _("Good afternoon"),
        "evening": _("Good evening"),
    }
    key = "morning" if hour < 12 else "afternoon" if hour < 17 else "evening"
    return {**words, "now": words[key]}


def _chat_rows(chats: list, lang: str) -> list[dict[str, Any]]:
    """Title, link and date per row.

    `updated_at` is stored in seconds. Formatted here rather than in the
    template so the template holds no logic, and rendered as an absolute date
    because a relative label ("2 hours ago") goes stale in a cached response and
    there is no script on this page to refresh it.
    """
    rows = []
    for chat in chats:
        rows.append(
            {
                "title": chat.title or "",
                "url": f"/c/{chat.id}{lang}",
                "date": time.strftime("%Y-%m-%d", time.localtime(chat.updated_at)),
            }
        )
    return rows


def render_home(request: Request, user) -> str:
    _ = translator(request)
    lang = lang_query(request)

    recent = Chats.get_chat_list_by_user_id(user.id, limit=_RECENT_LIMIT)
    pinned = Chats.get_pinned_chats_by_user_id(user.id)[:_PINNED_LIMIT]

    # First name only, matching the Svelte greeting's `split(' ')[0]`. The
    # parity gate compares hooks rather than text, but a page that greets the
    # same person two different ways is the kind of drift a reader notices
    # before a gate does.
    first_name = (user.name or "").split(" ")[0]

    # TWO LAYERS. `shared` is what an operator wired onto the Calendar Sprig™
    # and everyone on the instance sees; `mine` is this person's own feeds from
    # their settings. The rule that separates them: a wire is set once by an
    # admin, so anything two people would answer differently cannot be one.
    #
    # Nothing on either side previews from the .ics stub instead — real events
    # through the real parser, never mixed with anyone's actual calendar.
    shared = shared_feeds(request)
    mine = user_calendar(user)
    configured = bool(shared or mine["feeds"])
    events = (
        upcoming(
            shared,
            personal="\n".join(mine["feeds"]),
            hidden_shared=mine["hidden_shared"],
        )
        if configured
        else sample_events()
    )

    return render(
        "home.html",
        lang=lang,
        greetings=_greetings(_),
        greeted_name=first_name,
        starter_label=_("Start a conversation"),
        starter_placeholder=_("Ask anything…"),
        starter_submit=_("Send"),
        calendar_title=_("Calendar"),
        calendar_configured=configured,
        calendar_example=not configured,
        calendar_example_note=_("Nothing connected yet — this is an example."),
        calendar_events=[
            {
                "title": e["title"],
                "when": _("all day")
                if e["all_day"]
                else e["start"].strftime("%a %d %b, %H:%M"),
            }
            for e in events[:_CALENDAR_LIMIT]
        ],
        calendar_grid=rolling_grid(events),
        # First letter for the column, full name for anyone who cannot see
        # it. Taken from the TRANSLATED name, so a locale whose week does
        # not start with S still gets its own letters.
        calendar_weekdays=[{"letter": _(d)[:1], "name": _(d)} for d in WEEKDAY_NAMES],
        # The SPA route, not the bare server page: clicking through from
        # inside the app should keep the sidebar and the nav rather than
        # dropping the reader onto a chrome-less document. `/calendar` is
        # born hollow and hosts `/pages/calendar` inside that chrome.
        calendar_url=f"/calendar{lang}",
        calendar_all_label=_("View all"),
        calendar_empty=_("Nothing coming up."),
        calendar_unset=_(
            "No calendars yet. Add your own in settings, and nothing is fetched "
            "until you do."
        ),
        # The SPA route, for the same reason as `calendar_url` above. Until
        # 2026-08-09 this pointed at the bare server page, whose own "back" link
        # pointed at another bare server page — so clicking here left the app
        # and offered no way back into it.
        calendar_settings_url=f"/settings/calendar{lang}",
        calendar_settings_label=_("Add a calendar"),
        recent_title=_("Recent Chats"),
        recent=_chat_rows(recent, lang),
        recent_empty=_("No chats yet. Start a conversation!"),
        recent_all_label=_("View all"),
        recent_all_url=f"/{lang}",
        pinned_title=_("Pinned"),
        pinned=_chat_rows(pinned, lang),
        pinned_empty=_("Pin a chat from the sidebar to see it here."),
        notes_title=_("Notes"),
        notes_detail=_(
            "Quick-capture ideas, meeting notes, and thoughts. Always in reach."
        ),
        notes_url=f"/notes{lang}",
        soon_title=_("Coming soon"),
        soon=[
            {"icon": icon, "title": _(title), "detail": _(detail)}
            for icon, title, detail in _SOON
        ],
        vision_title=_("Your AI, Your Way"),
        # The Svelte page closes with three paragraphs promising "a widget-based
        # home where you choose what to see". On this page that promise is a
        # mechanism: the ui-Sprig™ slot renders after this body. The first two
        # paragraphs carry over; the third is replaced by the true sentence.
        vision_paragraphs=[
            _(
                "This is your dashboard — a personal space that adapts to how "
                "you work. Instead of jumping between pages to find what "
                "matters, everything lives here."
            ),
            _(
                "We're building toward a widget-based home where you choose "
                "what to see: recent conversations, pinned notes, calendar "
                "events, usage stats, quick-launch prompts — arranged your way."
            ),
            _(
                "Anything this instance grafts appears below, with no update "
                "and no rebuild."
            ),
        ],
    )
