import calendar
import re
from datetime import MAXYEAR, MINYEAR, date, datetime, time

from flask import Blueprint, redirect, render_template, request, url_for

from .db import get_db

bp = Blueprint("events", __name__)

CATEGORIES = ("personal", "professional")


def load_events():
    """Return all events as dicts, sorted by date and time (all-day events first)."""
    rows = get_db().execute(
        "SELECT id, title, date, time, category FROM event"
        " ORDER BY date, time IS NOT NULL, time, id"
    ).fetchall()
    events = []
    for row in rows:
        day = date.fromisoformat(row["date"])
        at = time.fromisoformat(row["time"]) if row["time"] else None
        events.append({**dict(row), "day": day, "at": at})
    return events


def is_past(event, now):
    """An event with a time is past once that time has gone by; an all-day
    event stays upcoming until the end of its day."""
    if event["at"] is None:
        return event["day"] < now.date()
    return datetime.combine(event["day"], event["at"]) < now


def split_events(events, now):
    upcoming = [e for e in events if not is_past(e, now)]
    past = [e for e in events if is_past(e, now)]
    return upcoming, past


def parse_month(value):
    """Turn a "YYYY-MM" query value into (year, month), or None if invalid."""
    match = re.fullmatch(r"(\d{4})-(\d{2})", value or "")
    if not match:
        return None
    year, month = int(match.group(1)), int(match.group(2))
    if not (MINYEAR <= year <= MAXYEAR and 1 <= month <= 12):
        return None
    return year, month


def shift_month(year, month, delta):
    """The (year, month) `delta` months away, or None if outside the date range."""
    index = year * 12 + month - 1 + delta
    year, month = divmod(index, 12)
    if not MINYEAR <= year <= MAXYEAR:
        return None
    return year, month + 1


def month_param(year_month):
    return f"{year_month[0]:04d}-{year_month[1]:02d}" if year_month else None


def calendar_dates(year, month):
    """Full weeks (Monday first) covering the month. The stdlib helper fails at
    the very first and last supported months, so pad those weeks by hand."""
    first = date(year, month, 1)
    start = first.toordinal() - first.weekday()
    last = date(year, month, calendar.monthrange(year, month)[1])
    end = last.toordinal() + 6 - last.weekday()
    days = [
        date.fromordinal(n) if date.min.toordinal() <= n <= date.max.toordinal() else None
        for n in range(start, end + 1)
    ]
    return [days[i:i + 7] for i in range(0, len(days), 7)]


def month_calendar(today, event_days, shown=None):
    """Weeks of the shown month (default: today's month) for the calendar widget."""
    year, month = shown or (today.year, today.month)
    weeks = []
    for week in calendar_dates(year, month):
        weeks.append([
            None if day is None else {
                "date": day,
                "in_month": day.month == month,
                "today": day == today,
                "has_event": day in event_days,
            }
            for day in week
        ])
    is_current = (year, month) == (today.year, today.month)
    return {
        "title": f"{calendar.month_name[month]} {year}",
        "weekdays": [calendar.day_abbr[i][:2] for i in range(7)],
        "weeks": weeks,
        "prev": month_param(shift_month(year, month, -1)),
        "next": month_param(shift_month(year, month, 1)),
        "is_current": is_current,
    }


@bp.route("/")
def dashboard():
    now = datetime.now()
    events = load_events()
    upcoming, past = split_events(events, now)
    shown = parse_month(request.args.get("month"))
    cal = month_calendar(now.date(), {e["day"] for e in events}, shown)
    return render_template(
        "dashboard.html", upcoming=upcoming, has_past=bool(past), calendar=cal
    )


@bp.route("/events/past")
def past_events():
    _, past = split_events(load_events(), datetime.now())
    past.reverse()  # most recent first
    return render_template("past_events.html", events=past)


def validate(form):
    errors = []
    title = form.get("title", "").strip()
    if not title:
        errors.append("Title is required.")
    try:
        date.fromisoformat(form.get("date", ""))
    except ValueError:
        errors.append("Enter a valid date.")
    raw_time = form.get("time", "").strip()
    if raw_time:
        try:
            datetime.strptime(raw_time, "%H:%M")
        except ValueError:
            errors.append("Enter a valid time.")
    if form.get("category") not in CATEGORIES:
        errors.append("Choose personal or professional.")
    return errors


@bp.route("/events/new", methods=("GET", "POST"))
def new_event():
    if request.method == "POST":
        errors = validate(request.form)
        if errors:
            return render_template("event_form.html", errors=errors, form=request.form), 400
        db = get_db()
        db.execute(
            "INSERT INTO event (title, date, time, category) VALUES (?, ?, ?, ?)",
            (
                request.form["title"].strip(),
                date.fromisoformat(request.form["date"]).isoformat(),
                request.form.get("time", "").strip() or None,
                request.form["category"],
            ),
        )
        db.commit()
        return redirect(url_for("events.dashboard"))
    return render_template("event_form.html", errors=[], form={})
