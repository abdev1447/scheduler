import re
import sqlite3
from datetime import date, timedelta

from scheduler import create_app

TODAY = date.today()
FUTURE = TODAY + timedelta(days=10)
PAST = TODAY - timedelta(days=10)


def add_event(client, title, day, category="personal", time="", location="", description=""):
    return client.post(
        "/events/new",
        data={
            "title": title,
            "date": day.isoformat(),
            "time": time,
            "category": category,
            "location": location,
            "description": description,
        },
    )


def page(client, path):
    response = client.get(path)
    assert response.status_code == 200
    return response.get_data(as_text=True)


def event_link(html, title):
    """The href of the list item link that contains the given event title."""
    match = re.search(rf'<a class="event__link" href="([^"]+)"[^>]*>(?:(?!</a>).)*{re.escape(title)}', html, re.S)
    assert match, f"no clickable link for event {title!r}"
    return match.group(1)


def details(html):
    match = re.search(r'<section[^>]*id="event-details".*?</section>', html, re.S)
    assert match, "event details section not found"
    return match.group(0)


def field(section, name):
    """Text of the <dd> that follows the <dt> with the given label."""
    match = re.search(rf"<dt>{name}</dt>\s*<dd[^>]*>(.*?)</dd>", section, re.S)
    assert match, f"field {name!r} not shown"
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", match.group(1))).strip()


# --- The form takes the extra details ------------------------------------------


def test_add_event_form_has_location_and_description(client):
    html = page(client, "/events/new")
    assert 'name="location"' in html
    assert '<textarea id="description" name="description"' in html


def test_location_and_description_are_optional(client):
    response = add_event(client, "Gym", FUTURE)
    assert response.status_code == 302
    section = details(page(client, event_link(page(client, "/"), "Gym")))
    assert field(section, "Location") == "Not given"
    assert field(section, "Description") == "No description"


# --- Clicking an upcoming event --------------------------------------------------


def test_clicking_an_upcoming_event_shows_all_its_information(client):
    add_event(
        client, "Board meeting", FUTURE, "professional", time="14:30",
        location="Room 4B, Head office", description="Quarterly results.\nBring the slides.",
    )
    href = event_link(page(client, "/"), "Board meeting")
    section = details(page(client, href))

    assert "<h1" in section and "Board meeting" in section
    assert field(section, "Status") == "Upcoming"
    assert field(section, "Type") == "Professional"
    assert field(section, "Date") == FUTURE.strftime("%A, %d %B %Y")
    assert field(section, "Time") == "14:30"
    assert field(section, "Location") == "Room 4B, Head office"
    assert "Quarterly results." in field(section, "Description")
    assert "Bring the slides." in field(section, "Description")
    # The details page keeps the colour of the event type.
    assert "event-details--professional" in section


def test_all_day_event_details_say_all_day(client):
    add_event(client, "Holiday", FUTURE, "personal")
    section = details(page(client, event_link(page(client, "/"), "Holiday")))
    assert field(section, "Time") == "All day"
    assert field(section, "Type") == "Personal"
    assert "event-details--personal" in section


def test_upcoming_event_details_link_back_to_dashboard(client):
    add_event(client, "Holiday", FUTURE)
    section = details(page(client, event_link(page(client, "/"), "Holiday")))
    assert re.search(r'<a[^>]*id="back"[^>]*href="/"', section)


# --- Clicking a past event -------------------------------------------------------


def test_clicking_a_past_event_shows_all_its_information(client):
    add_event(
        client, "Old conference", PAST, "professional", time="09:00",
        location="Berlin", description="Talk about scheduling.",
    )
    href = event_link(page(client, "/events/past"), "Old conference")
    section = details(page(client, href))

    assert "Old conference" in section
    assert field(section, "Status") == "Past"
    assert field(section, "Type") == "Professional"
    assert field(section, "Date") == PAST.strftime("%A, %d %B %Y")
    assert field(section, "Time") == "09:00"
    assert field(section, "Location") == "Berlin"
    assert field(section, "Description") == "Talk about scheduling."
    assert re.search(r'<a[^>]*id="back"[^>]*href="/events/past"', section)


# --- Safety and edge cases -------------------------------------------------------


def test_unknown_event_gives_not_found(client):
    assert client.get("/events/999").status_code == 404


def test_details_are_escaped(client):
    add_event(client, "Party", FUTURE, description="<script>alert(1)</script>")
    section = details(page(client, event_link(page(client, "/"), "Party")))
    assert "<script>" not in section
    assert "&lt;script&gt;" in section


def test_existing_database_without_new_columns_still_works(tmp_path):
    path = tmp_path / "old.sqlite"
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE event (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,"
            " date TEXT NOT NULL, time TEXT,"
            " category TEXT NOT NULL CHECK (category IN ('personal', 'professional')))"
        )
        conn.execute(
            "INSERT INTO event (title, date, time, category) VALUES (?, ?, NULL, 'personal')",
            ("Old row", FUTURE.isoformat()),
        )
    conn.close()

    client = create_app({"TESTING": True, "DATABASE": str(path)}).test_client()
    section = details(page(client, event_link(page(client, "/"), "Old row")))
    assert field(section, "Location") == "Not given"


# --- How we know it works: one past and one future event --------------------------


def test_one_past_and_one_future_event_can_both_be_opened(client):
    add_event(client, "Last week's review", PAST, "professional", location="Office")
    add_event(client, "Next week's dinner", FUTURE, "personal", time="19:00", location="Luigi's")

    future = details(page(client, event_link(page(client, "/"), "Next week&#39;s dinner")))
    assert field(future, "Status") == "Upcoming"
    assert field(future, "Location") == "Luigi&#39;s"

    past = details(page(client, event_link(page(client, "/events/past"), "Last week&#39;s review")))
    assert field(past, "Status") == "Past"
    assert field(past, "Location") == "Office"
