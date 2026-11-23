import calendar
from datetime import date, datetime, time

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


def month_calendar(today, event_days):
    """Weeks of the current month for the calendar widget."""
    weeks = []
    for week in calendar.Calendar(firstweekday=0).monthdatescalendar(today.year, today.month):
        weeks.append([
            {
                "date": day,
                "in_month": day.month == today.month,
                "today": day == today,
                "has_event": day in event_days,
            }
            for day in week
        ])
    return {
        "title": today.strftime("%B %Y"),
        "weekdays": [calendar.day_abbr[i][:2] for i in range(7)],
        "weeks": weeks,
    }


@bp.route("/")
def dashboard():
    now = datetime.now()
    events = load_events()
    upcoming, past = split_events(events, now)
    cal = month_calendar(now.date(), {e["day"] for e in events})
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
