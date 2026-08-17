"""Calendar data for the home card and `/pages/calendar` — iCalendar, server-side.

A SCAFFOLD that reads public ICS feeds and lists what is coming up. It does not
write, does not authenticate, and knows nothing about Nextcloud beyond the fact
that Nextcloud publishes ICS like everything else does.

WHY SERVER-SIDE, and it is not a preference. The eventual home for this is a
ui-Sprig™, and a ui-Sprig fragment MAY NOT REACH AN EXTERNAL URL — the validator
refuses external references outright, because a fragment that can beacon out
breaks the zero-egress story (`sprigs/theme_dispatch.py`). So the obvious build,
a widget that calls the calendar, is structurally impossible under our own
contract. The data has to arrive server-side, which is what this does, and which
is why the eventual delivery is `service-endpoint` — a sidecar the operator runs
— with the feed URLs as wires on a Wired Sprig™.

OFF BY DEFAULT AND THAT IS THE POINT. With no URL configured nothing is fetched
and no request leaves the machine. Configuring one is an operator saying "reach
these hosts", once, deliberately.

SEVERAL FEEDS, FROM THE START (decided 2026-08-09). People keep work, personal
and shared calendars apart, so one URL is a limit you meet in week one — and
changing the shape of a setting after operators have set it is exactly the
rename the Sprig spec warns against. Each feed is fetched and cached
independently, so one dead feed costs its own events and nothing else.

WHAT IT REFUSES TO DO, each because the obvious version breaks a page:

* It never blocks the render for long. One short timeout per feed.
* It caches per feed, so a reload does not re-fetch.
* It never raises. Any failure yields no events from that feed, and the page
  renders without it.
* It refuses non-http(s) URLs, so a configured `file://` cannot turn an operator
  setting into a local file read.

WHAT THE PARSER DOES NOT DO, said plainly because a month grid makes gaps
visible in a way a four-item list does not:

* `EXDATE` — a cancelled instance of a repeating event still shows.
* `BYSETPOS` — "last Friday of the month" is not expanded.
* Named timezones — `TZID=Europe/Lisbon` is read as UTC. Wrong by an hour or
  two at the edges, and wrong about which DAY only near midnight.

Those belong in the sidecar, which can depend on a real iCalendar library. This
module is deliberately dependency-free.
"""

from __future__ import annotations

import logging
import re
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

log = logging.getLogger(__name__)

__all__ = [
    "upcoming",
    "forget",
    "WEEKDAY_NAMES",
    "WEEKDAY_SHORT",
    "sample_events",
    "feed_urls",
    "CALENDAR_TIMEOUT_S",
    "CALENDAR_CACHE_S",
]

# Short enough that a dead feed is a blip rather than a hang.
CALENDAR_TIMEOUT_S = 3.0
# Long enough that an open dashboard does not hammer a calendar server.
CALENDAR_CACHE_S = 300.0
# A calendar feed is text. Anything larger is not one, and we stop reading
# rather than pull an unbounded body from a host we do not control.
_MAX_BYTES = 2 * 1024 * 1024
# How far ahead a repeating event is expanded. A grid shows one month; this
# leaves room to page forward a little without expanding a daily standup to the
# heat death of the universe.
_HORIZON_DAYS = 120
_MAX_INSTANCES = 200

_WEEKDAYS = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}

_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}


def feed_urls(configured: str) -> list[str]:
    """Split the setting into feeds.

    Comma or newline separated, so an operator can paste a list either way and
    neither reads as a mistake.
    """
    raw = (configured or "").replace(",", "\n")
    return [u.strip() for u in raw.splitlines() if u.strip()]


# ── parsing ───────────────────────────────────────────────────────────────────


def _unfold(raw: str) -> list[str]:
    """iCalendar folds long lines with a leading space. Rejoin them."""
    lines: list[str] = []
    for line in raw.splitlines():
        if line[:1] in (" ", "\t") and lines:
            lines[-1] += line[1:]
        else:
            lines.append(line)
    return lines


def _parse_dt(value: str) -> tuple[datetime | None, bool]:
    """Return the moment and whether it was date-only (an all-day event)."""
    value = value.strip()
    for fmt, all_day in (
        ("%Y%m%dT%H%M%SZ", False),
        ("%Y%m%dT%H%M%S", False),
        ("%Y%m%d", True),
    ):
        try:
            parsed = datetime.strptime(value, fmt)
        except ValueError:
            continue
        return parsed.replace(tzinfo=timezone.utc), all_day
    return None, False


def _rrule(value: str) -> dict[str, str]:
    parts = {}
    for chunk in value.split(";"):
        key, _, val = chunk.partition("=")
        if key:
            parts[key.strip().upper()] = val.strip()
    return parts


def _expand(event: dict[str, Any], horizon: datetime) -> list[datetime]:
    """Every start this event has between its first and the horizon.

    Handles the repeats people actually keep in a calendar: a daily standup, a
    weekly meeting on set days, a monthly review. Anything more elaborate falls
    back to the single first occurrence rather than guessing, because a wrong
    repeat is worse than a missing one.
    """
    start: datetime = event["start"]
    rule = event.get("rrule")
    if not rule:
        return [start]

    freq = rule.get("FREQ", "").upper()
    if freq not in ("DAILY", "WEEKLY", "MONTHLY"):
        return [start]

    try:
        interval = max(1, int(rule.get("INTERVAL", "1")))
    except ValueError:
        interval = 1

    count = None
    if rule.get("COUNT"):
        try:
            count = max(1, int(rule["COUNT"]))
        except ValueError:
            count = None

    until = None
    if rule.get("UNTIL"):
        until, _ = _parse_dt(rule["UNTIL"])

    # BYDAY on a weekly rule means "these weekdays each week".
    bydays = [
        _WEEKDAYS[d.strip()[-2:].upper()]
        for d in rule.get("BYDAY", "").split(",")
        if d.strip()[-2:].upper() in _WEEKDAYS
    ]

    out: list[datetime] = []
    cursor = start
    guard = 0
    while cursor <= horizon and guard < _MAX_INSTANCES:
        guard += 1
        if until and cursor > until:
            break

        if freq == "WEEKLY" and bydays:
            # Emit each named weekday within the cursor's week.
            week_start = cursor - timedelta(days=cursor.weekday())
            for day in sorted(bydays):
                moment = week_start + timedelta(days=day)
                if (
                    moment >= start
                    and moment <= horizon
                    and (not until or moment <= until)
                ):
                    out.append(moment)
            cursor = cursor + timedelta(weeks=interval)
        elif freq == "DAILY":
            out.append(cursor)
            cursor = cursor + timedelta(days=interval)
        elif freq == "WEEKLY":
            out.append(cursor)
            cursor = cursor + timedelta(weeks=interval)
        else:  # MONTHLY — same day number, skipping months that lack it
            out.append(cursor)
            month = cursor.month - 1 + interval
            year = cursor.year + month // 12
            month = month % 12 + 1
            try:
                cursor = cursor.replace(year=year, month=month)
            except ValueError:
                break

        if count and len(out) >= count:
            out = out[:count]
            break

    return sorted(set(out))


def _parse(raw: str, source: str) -> list[dict[str, Any]]:
    """Every occurrence from one feed, between now and the horizon."""
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(days=_HORIZON_DAYS)
    parsed: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for line in _unfold(raw):
        if line.startswith("BEGIN:VEVENT"):
            current = {}
            continue
        if line.startswith("END:VEVENT"):
            if current and current.get("start"):
                parsed.append(current)
            current = None
            continue
        if current is None or ":" not in line:
            continue

        # `DTSTART;TZID=Europe/Lisbon:20260809T140000` — the property name is
        # everything before the first `;` or `:`.
        name, _, value = line.partition(":")
        key = name.split(";", 1)[0].upper()
        if key == "SUMMARY":
            current["title"] = value.replace("\\,", ",").replace("\\n", " ").strip()
        elif key == "DTSTART":
            current["start"], current["all_day"] = _parse_dt(value)
        elif key == "DTEND":
            current["end"], _ = _parse_dt(value)
        elif key == "RRULE":
            current["rrule"] = _rrule(value)

    out: list[dict[str, Any]] = []
    for event in parsed:
        # A span is carried on each occurrence so a three-day conference marks
        # three days rather than one.
        span = 0
        if event.get("end") and event["end"] > event["start"]:
            span = (event["end"].date() - event["start"].date()).days
            # An all-day event's DTEND is EXCLUSIVE — a one-day event ends the
            # next morning. Without this every all-day event would be a day long
            # on the grid when it is not.
            if event.get("all_day") and span > 0:
                span -= 1

        for moment in _expand(event, horizon):
            if moment + timedelta(days=span) < now:
                continue  # wholly in the past
            out.append(
                {
                    "title": event.get("title") or "(untitled)",
                    "start": moment,
                    "span_days": span,
                    "all_day": bool(event.get("all_day")),
                    "source": source,
                }
            )
    return out


# ── fetching ──────────────────────────────────────────────────────────────────


def _fetch(url: str) -> list[dict[str, Any]]:
    """One feed's events, or an empty list for any reason at all. Never raises."""
    hit = _cache.get(url)
    if hit and (time.monotonic() - hit[0]) < CALENDAR_CACHE_S:
        return hit[1]

    try:
        # http/https only. A configured `file://` would turn an operator setting
        # into a local file read, which is not what "calendar feed" means.
        if not url.lower().startswith(("http://", "https://")):
            raise ValueError("calendar feed must be http(s)")
        # Two suppressions because two tools flag the same line and neither
        # reads the other's: `noqa` is ruff, `nosec` is bandit. Both are
        # answered by the check three lines above — the scheme is http(s)
        # or this never runs — plus a 3s timeout and a byte cap below.
        with urlopen(url, timeout=CALENDAR_TIMEOUT_S) as response:  # noqa: S310 # nosec B310
            raw = response.read(_MAX_BYTES).decode("utf-8", "replace")
        events = _parse(raw, source=url)
    except (URLError, ValueError, OSError, UnicodeError) as exc:
        log.warning("calendar feed unavailable (%s); its events are omitted", exc)
        events = []

    _cache[url] = (time.monotonic(), events)
    return events


# ── the example calendar ──────────────────────────────────────────────────────
#
# A REAL .ics FILE, parsed by the real parser (Alexander, 2026-08-09: "we should
# use an ical stub file for it so it uses the same language internally, just not
# grabbing from a server"). That is the good part of the idea: sample data that
# goes through the shipping code path cannot drift from what the parser actually
# supports. If recurrence breaks, the example breaks, visibly, on the home page.
#
# The file is anchored to a known Monday and every date is shifted forward to
# THIS week on load. So it stays a valid iCalendar file you could open in any
# calendar app, while the preview is never stale — a sample calendar showing
# January 2026 in August teaches nobody anything.
#
# The titles are deliberately not plausible meetings. A preview that reads like
# a real schedule is one somebody eventually acts on, and "Team standup" in a
# glance is indistinguishable from a commitment. These say what they are.
_SAMPLE_PATH = Path(__file__).parent / "samples" / "example-calendar.ics"
_SAMPLE_ANCHOR = date(2026, 1, 5)  # a Monday
_DATE_IN_ICS = re.compile(r"(?<=[:;])(\d{8})(T\d{6}Z?)?(?=\r?$)")


def _shift_sample(raw: str, today: date) -> str:
    """Move every date in the stub forward so the sample lands on this week."""
    delta = (today - timedelta(days=today.weekday())) - _SAMPLE_ANCHOR

    def move(match: re.Match) -> str:
        moved = datetime.strptime(match.group(1), "%Y%m%d").date() + delta
        return moved.strftime("%Y%m%d") + (match.group(2) or "")

    return "\n".join(_DATE_IN_ICS.sub(move, line) for line in raw.splitlines())


def sample_events(today: date | None = None) -> list[dict[str, Any]]:
    """The example calendar, shifted to this week. Never raises."""
    today = today or datetime.now(timezone.utc).date()
    try:
        raw = _SAMPLE_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        log.warning("example calendar unreadable (%s); the preview is empty", exc)
        return []
    events = _parse(_shift_sample(raw, today), source="example")
    for event in events:
        event["example"] = True
    return events


def upcoming(
    configured: str,
    *,
    personal: str = "",
    hidden_shared: list[str] | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Merged, sorted occurrences across both layers.

    TWO LAYERS, and the rule that separates them: `configured` holds the SHARED
    feeds an operator wired onto the Calendar Sprig™ — term dates, company
    holidays, the things it makes no sense to answer twice. `personal` holds one
    person's own feeds from their settings. A wire is set once by an admin, so
    anything two people would answer differently cannot be one.

    Each event carries `shared`, so a surface can tell a person which rows came
    from the instance and let them hide one.

    `start` stays an aware datetime rather than a formatted string, because the
    home card wants one line and the page wants day groupings, and neither
    should re-parse what the other formatted.
    """
    hidden = set(hidden_shared or [])
    events: list[dict[str, Any]] = []

    for url in feed_urls(configured):
        if url in hidden:
            continue
        for event in _fetch(url):
            events.append({**event, "shared": True})

    for url in feed_urls(personal):
        for event in _fetch(url):
            events.append({**event, "shared": False})

    events.sort(key=lambda e: e["start"])
    return events[:limit] if limit else events


def forget(urls: list[str] | None = None) -> None:
    """Drop cached feeds so the next render fetches fresh.

    Called when a wire or a person's feeds change. Without it, correcting a
    mistyped URL leaves the page empty for the rest of the five-minute cache —
    the operator fixes the setting, sees no change, and reasonably concludes the
    feature is broken. Found exactly that way.
    """
    if urls is None:
        _cache.clear()
        return
    for url in urls:
        _cache.pop(url, None)


def shared_feeds(request: Any) -> str:
    """The operator's feeds: the Calendar Sprig™'s wire, or the old setting.

    `HOME_CALENDAR_ICS_URL` came first and some instances already have it set.
    It stays as the fallback so nothing an operator configured stops working —
    renaming a setting under people is the exact failure the Sprig spec warns
    about. The wire wins when both exist, and the env var can be retired on a
    later tag.
    """
    config = request.app.state.config
    try:
        from sage_is_ai.sprigs.wiring import read_wires

        wired = str(read_wires(config, "calendar").get("shared_feeds") or "").strip()
        if wired:
            return wired
    except Exception:  # noqa: BLE001 — a calendar must never take a page down
        log.warning("could not read calendar wires; falling back to the setting")
    return str(getattr(config, "HOME_CALENDAR_ICS_URL", "") or "").strip()


def days_with_events(events: list[dict[str, Any]]) -> set[date]:
    """Every date any event touches, spans included.

    What the dot grid reads. A three-day conference marks three days, which is
    the whole reason `span_days` is carried.
    """
    marked: set[date] = set()
    for event in events:
        first = event["start"].date()
        for offset in range(event.get("span_days", 0) + 1):
            marked.add(first + timedelta(days=offset))
    return marked


# ── grids ─────────────────────────────────────────────────────────────────────
#
# Both views are the same date arithmetic: a run of weeks, seven cells each,
# SUNDAY first. The home card shows a rolling five weeks from this week; the
# page shows one calendar month. One builder, so they cannot drift apart on
# which day starts a week.
#
# THIS IS A DISPLAY DECISION AND NOTHING ELSE. `_expand` above computes a weekly
# rule's week from `cursor.weekday()`, which is Monday-based, and that is
# correct: RFC 5545 defaults WKST to Monday, so a `BYDAY=MO,WE` rule means the
# same dates whatever a reader's calendar looks like. Moving THAT would move
# events rather than relabel columns. Keep the two apart.


# The one list of day names, Sunday first, so the card's letters and the page's
# headers cannot disagree about the order. Full names because a reader needs
# them: the home card shows only first letters, and "S M T W T F S" has two S
# and two T in it — the full name rides along for anyone who cannot see the
# column.
WEEKDAY_NAMES = (
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
)
WEEKDAY_SHORT = ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")


def _week_start(day: date) -> date:
    """The Sunday on or before `day`.

    `weekday()` is Monday-based (Mon=0 … Sun=6), so `+1 % 7` shifts the origin:
    a Monday goes back one day, a Sunday goes back none.
    """
    return day - timedelta(days=(day.weekday() + 1) % 7)


def _grid(
    first_cell: date, weeks: int, marked: set[date], month: int | None
) -> list[list[dict]]:
    rows = []
    day = first_cell
    for _ in range(weeks):
        row = []
        for _ in range(7):
            row.append(
                {
                    "date": day,
                    "iso": day.isoformat(),
                    "num": day.day,
                    "marked": day in marked,
                    # Greyed on the month grid, where the run spills either side.
                    "outside": month is not None and day.month != month,
                }
            )
            day += timedelta(days=1)
        rows.append(row)
    return rows


def rolling_grid(
    events: list[dict[str, Any]], *, weeks: int = 5, today: date | None = None
):
    """Five weeks from the Sunday of this week — the home card's dot grid."""
    today = today or datetime.now(timezone.utc).date()
    return _grid(_week_start(today), weeks, days_with_events(events), None)


def month_grid(events: list[dict[str, Any]], year: int, month: int):
    """One calendar month, padded to whole weeks — the page's grid."""
    first = date(year, month, 1)
    # Six rows covers every month, including a 31-day month starting Saturday —
    # the worst case once the week begins on Sunday.
    return _grid(_week_start(first), 6, days_with_events(events), month)


def group_by_day(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Events under one heading per day — the agenda view."""
    days: dict[date, list[dict[str, Any]]] = {}
    for event in events:
        days.setdefault(event["start"].date(), []).append(event)
    return [
        {
            "date": day,
            "iso": day.isoformat(),
            "heading": day.strftime("%A %d %B"),
            "events": [
                {
                    "title": e["title"],
                    "when": "all day" if e["all_day"] else e["start"].strftime("%H:%M"),
                }
                for e in items
            ],
        }
        for day, items in sorted(days.items())
    ]
