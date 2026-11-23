import re
from datetime import date, datetime, timedelta

import pytest

TODAY = date.today()
FUTURE = (TODAY + timedelta(days=10)).isoformat()
LATER = (TODAY + timedelta(days=20)).isoformat()
PAST = (TODAY - timedelta(days=10)).isoformat()


def add_event(client, title, day, category="personal", time=""):
    return client.post(
        "/events/new",
        data={"title": title, "date": day, "time": time, "category": category},
    )


def dashboard(client):
    response = client.get("/")
    assert response.status_code == 200
    return response.get_data(as_text=True)


def upcoming_section(html):
    """Return only the HTML of the upcoming events section."""
    match = re.search(r'<section[^>]*id="upcoming".*?</section>', html, re.S)
    assert match, "upcoming events section not found"
    return match.group(0)


# --- Layout: logo and calendar -------------------------------------------


def test_logo_scheduler_is_shown_at_the_top(client):
    html = dashboard(client)
    header = re.search(r"<header.*?</header>", html, re.S)
    assert header, "page has no header"
    assert 'class="logo"' in header.group(0)
    assert "Scheduler" in header.group(0)
    # The header comes before the main content.
    assert html.index("<header") < html.index("<main")


def test_calendar_is_shown_on_the_right(client):
    html = dashboard(client)
    side = re.search(r'<aside class="dashboard__side".*?</aside>', html, re.S)
    assert side, "no right-hand side column"
    assert 'id="calendar"' in side.group(0)
    # The calendar shows the current month and marks today.
    assert TODAY.strftime("%B %Y") in side.group(0)
    assert 'class="calendar__day calendar__day--today' in side.group(0)
    # The side column comes after the events column.
    assert html.index('id="upcoming"') < html.index('class="dashboard__side"')


def test_calendar_marks_days_with_upcoming_events(client):
    day = TODAY + timedelta(days=1)
    if day.month != TODAY.month:
        pytest.skip("tomorrow is in another month; not visible in this month's calendar")
    add_event(client, "Dentist", day.isoformat())
    html = dashboard(client)
    assert f'data-date="{day.isoformat()}"' in html
    marked = re.search(rf'<td[^>]*class="[^"]*calendar__day--event[^"]*"[^>]*data-date="{day.isoformat()}"', html)
    assert marked, "day with an event is not marked in the calendar"


# --- Upcoming list ---------------------------------------------------------


def test_personal_and_professional_events_look_different(client):
    add_event(client, "Birthday party", FUTURE, "personal")
    add_event(client, "Board meeting", LATER, "professional")
    section = upcoming_section(dashboard(client))

    personal = re.search(r'<li class="event event--personal".*?</li>', section, re.S)
    professional = re.search(r'<li class="event event--professional".*?</li>', section, re.S)
    assert personal and "Birthday party" in personal.group(0)
    assert professional and "Board meeting" in professional.group(0)
    assert "Personal" in personal.group(0)
    assert "Professional" in professional.group(0)


def test_styles_distinguish_the_two_event_types(client):
    css = client.get("/static/style.css").get_data(as_text=True)
    assert ".event--personal" in css
    assert ".event--professional" in css


def test_past_events_are_not_in_the_upcoming_list(client):
    add_event(client, "Old conference", PAST, "professional")
    add_event(client, "Future trip", FUTURE, "personal")
    section = upcoming_section(dashboard(client))
    assert "Future trip" in section
    assert "Old conference" not in section


def test_event_earlier_today_is_past_but_later_today_is_upcoming(client):
    now = datetime.now()
    if now.hour == 0 or now.hour == 23:
        pytest.skip("too close to midnight to build same-day times")
    earlier = (now - timedelta(hours=1)).strftime("%H:%M")
    later = (now + timedelta(hours=1)).strftime("%H:%M")
    add_event(client, "Morning call", TODAY.isoformat(), time=earlier)
    add_event(client, "Evening call", TODAY.isoformat(), time=later)
    add_event(client, "All-day task", TODAY.isoformat())
    section = upcoming_section(dashboard(client))
    assert "Evening call" in section
    assert "All-day task" in section
    assert "Morning call" not in section


def test_upcoming_events_are_sorted_by_date(client):
    add_event(client, "Second", LATER)
    add_event(client, "First", FUTURE)
    section = upcoming_section(dashboard(client))
    assert section.index("First") < section.index("Second")


def test_events_are_shown_with_add_event_button_below(client):
    add_event(client, "Team lunch", FUTURE, "professional")
    html = dashboard(client)
    section = upcoming_section(html)
    assert '<ul class="event-list"' in section
    assert "Team lunch" in section
    assert 'id="add-event"' in section
    assert section.index("Team lunch") < section.index('id="add-event"')


def test_without_events_only_add_event_button_is_shown(client):
    section = upcoming_section(dashboard(client))
    assert 'id="add-event"' in section
    assert 'class="event-list"' not in section
    assert 'id="past-events"' not in section


def test_with_only_past_events_upcoming_list_is_hidden(client):
    add_event(client, "Old conference", PAST)
    section = upcoming_section(dashboard(client))
    assert 'class="event-list"' not in section
    assert 'id="add-event"' in section


# --- Past events button ----------------------------------------------------


def test_past_events_button_shown_below_add_event_when_past_events_exist(client):
    add_event(client, "Old conference", PAST)
    section = upcoming_section(dashboard(client))
    assert 'id="past-events"' in section
    assert section.index('id="add-event"') < section.index('id="past-events"')


def test_past_events_button_hidden_when_no_past_events(client):
    add_event(client, "Future trip", FUTURE)
    html = dashboard(client)
    assert 'id="past-events"' not in html


def test_past_events_page_lists_only_past_events(client):
    add_event(client, "Old conference", PAST, "professional")
    add_event(client, "Future trip", FUTURE)
    html = client.get("/events/past").get_data(as_text=True)
    assert "Old conference" in html
    assert "Future trip" not in html
    assert "event--professional" in html


# --- Add event form ---------------------------------------------------------


def test_add_event_button_opens_the_form(client):
    html = dashboard(client)
    assert 'href="/events/new"' in html
    form = client.get("/events/new")
    assert form.status_code == 200
    text = form.get_data(as_text=True)
    for field in ('name="title"', 'name="date"', 'name="time"', 'name="category"'):
        assert field in text


def test_adding_an_event_redirects_to_dashboard(client):
    response = add_event(client, "Gym", FUTURE)
    assert response.status_code == 302
    assert response.headers["Location"] == "/"


@pytest.mark.parametrize(
    "data, message",
    [
        ({"title": "", "date": FUTURE, "category": "personal"}, "Title is required."),
        ({"title": "X", "date": "not-a-date", "category": "personal"}, "Enter a valid date."),
        ({"title": "X", "date": FUTURE, "time": "25:99", "category": "personal"}, "Enter a valid time."),
        ({"title": "X", "date": FUTURE, "category": "other"}, "Choose personal or professional."),
    ],
)
def test_invalid_event_is_rejected(client, data, message):
    response = client.post("/events/new", data=data)
    assert response.status_code == 400
    assert message in response.get_data(as_text=True)
    assert 'class="event-list"' not in dashboard(client)


# --- How we know it works: one past and one future event ----------------------


def test_one_past_and_one_future_event(client):
    add_event(client, "Last week's review", PAST, "professional")
    add_event(client, "Next week's dinner", FUTURE, "personal")

    html = dashboard(client)
    section = upcoming_section(html)

    # Future event is listed, past one is not.
    assert "Next week&#39;s dinner" in section
    assert "Last week&#39;s review" not in section
    # Buttons: Add event below the list, Past events below Add event.
    assert section.index("Next week&#39;s dinner") < section.index('id="add-event"')
    assert section.index('id="add-event"') < section.index('id="past-events"')

    # The past event can be found behind the Past events button.
    past = client.get("/events/past").get_data(as_text=True)
    assert "Last week&#39;s review" in past
    assert "Next week&#39;s dinner" not in past
