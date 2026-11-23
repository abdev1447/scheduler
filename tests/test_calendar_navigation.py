import re
from datetime import date, timedelta

TODAY = date.today()
THIS_MONTH = TODAY.strftime("%Y-%m")


def add_event(client, title, day, category="personal"):
    return client.post(
        "/events/new",
        data={"title": title, "date": day, "time": "", "category": category},
    )


def calendar_html(client, query=""):
    response = client.get("/" + query)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    match = re.search(r'<div class="card calendar" id="calendar">.*?</aside>', html, re.S)
    assert match, "calendar not found"
    return match.group(0)


def link(html, element_id):
    match = re.search(rf'<a[^>]*id="{element_id}"[^>]*href="([^"]*)"', html)
    assert match, f"link #{element_id} not found"
    return match.group(1).replace("&amp;", "&")


def shift_month(day, delta):
    index = day.year * 12 + day.month - 1 + delta
    return date(index // 12, index % 12 + 1, 1)


# --- Previous / next buttons ------------------------------------------------


def test_calendar_has_previous_and_next_month_buttons(client):
    html = calendar_html(client)
    previous = shift_month(TODAY, -1)
    following = shift_month(TODAY, 1)
    assert link(html, "calendar-prev") == f"/?month={previous:%Y-%m}"
    assert link(html, "calendar-next") == f"/?month={following:%Y-%m}"
    assert 'aria-label="Previous month"' in html
    assert 'aria-label="Next month"' in html


def test_next_button_moves_to_the_next_month(client):
    following = shift_month(TODAY, 1)
    html = calendar_html(client, "?" + link(calendar_html(client), "calendar-next").split("?")[1])
    assert following.strftime("%B %Y") in html
    assert TODAY.strftime("%B %Y") not in html


def test_previous_button_moves_to_the_previous_month(client):
    previous = shift_month(TODAY, -1)
    html = calendar_html(client, "?" + link(calendar_html(client), "calendar-prev").split("?")[1])
    assert previous.strftime("%B %Y") in html
    assert TODAY.strftime("%B %Y") not in html


def test_chosen_month_shows_its_days_and_neighbour_links(client):
    html = calendar_html(client, "?month=2026-03")
    assert "March 2026" in html
    assert 'data-date="2026-03-01"' in html
    assert 'data-date="2026-03-31"' in html
    assert link(html, "calendar-prev") == "/?month=2026-02"
    assert link(html, "calendar-next") == "/?month=2026-04"


def test_navigation_wraps_around_the_year(client):
    january = calendar_html(client, "?month=2027-01")
    assert "January 2027" in january
    assert link(january, "calendar-prev") == "/?month=2026-12"

    december = calendar_html(client, "?month=2026-12")
    assert "December 2026" in december
    assert link(december, "calendar-next") == "/?month=2027-01"


def test_buttons_can_be_clicked_several_times(client):
    query = "?month=2026-03"
    for expected in ("April 2026", "May 2026", "June 2026"):
        query = "?" + link(calendar_html(client, query), "calendar-next").split("?")[1]
        assert expected in calendar_html(client, query)
    for expected in ("May 2026", "April 2026"):
        query = "?" + link(calendar_html(client, query), "calendar-prev").split("?")[1]
        assert expected in calendar_html(client, query)


# --- What is shown in another month -----------------------------------------


def test_events_are_marked_in_other_months(client):
    day = shift_month(TODAY, 2) + timedelta(days=14)
    add_event(client, "Conference", day.isoformat(), "professional")
    html = calendar_html(client, f"?month={day:%Y-%m}")
    marked = re.search(
        rf'<td[^>]*class="[^"]*calendar__day--event[^"]*"[^>]*data-date="{day.isoformat()}"', html
    )
    assert marked, "event day not marked after moving to its month"


def test_today_is_only_highlighted_in_the_current_month(client):
    other = shift_month(TODAY, 3)
    assert "calendar__day--today" in calendar_html(client)
    assert "calendar__day--today" not in calendar_html(client, f"?month={other:%Y-%m}")


def test_today_button_returns_to_the_current_month(client):
    # On the current month there is nothing to go back to.
    assert 'id="calendar-today"' not in calendar_html(client)

    other = shift_month(TODAY, -5)
    html = calendar_html(client, f"?month={other:%Y-%m}")
    assert link(html, "calendar-today") == "/"
    assert TODAY.strftime("%B %Y") in calendar_html(client, "")


def test_upcoming_list_is_the_same_in_any_month(client):
    future = (TODAY + timedelta(days=3)).isoformat()
    past = (TODAY - timedelta(days=3)).isoformat()
    add_event(client, "Coming soon", future)
    add_event(client, "Long gone", past)
    other = shift_month(TODAY, -4)
    html = client.get(f"/?month={other:%Y-%m}").get_data(as_text=True)
    section = re.search(r'<section[^>]*id="upcoming".*?</section>', html, re.S).group(0)
    assert "Coming soon" in section
    assert "Long gone" not in section
    assert 'id="past-events"' in section


def test_invalid_month_falls_back_to_the_current_month(client):
    for bad in ("nonsense", "2026-13", "2026-00", "0000-05", "99999-01", "2026-1x", ""):
        html = calendar_html(client, f"?month={bad}")
        assert TODAY.strftime("%B %Y") in html, bad
        assert "calendar__day--today" in html, bad


def test_no_links_beyond_the_first_and_last_possible_month(client):
    first = calendar_html(client, "?month=0001-01")
    assert "January 0001" in first or "January 1" in first
    assert 'id="calendar-prev"' not in first
    assert link(first, "calendar-next") == "/?month=0001-02"

    last = calendar_html(client, "?month=9999-12")
    assert "December 9999" in last
    assert 'id="calendar-next"' not in last
    assert link(last, "calendar-prev") == "/?month=9999-11"


def test_theme_toggle_keeps_the_chosen_month(client):
    html = client.get("/?month=2026-03").get_data(as_text=True)
    assert 'name="next" value="/?month=2026-03"' in html
    response = client.post("/theme", data={"theme": "dark", "next": "/?month=2026-03"})
    assert response.status_code == 302
    assert response.headers["Location"] == "/?month=2026-03"


def test_navigation_buttons_are_styled(client):
    css = client.get("/static/style.css").get_data(as_text=True)
    assert ".calendar__nav" in css
