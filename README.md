# scheduler

A personal schedule management website, built in Python with the Flask web framework.

## Setup

```sh
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

## Running the website

```sh
.venv/bin/flask --app scheduler run --debug
```

Then open http://127.0.0.1:5000 in a browser. The dashboard lists upcoming
events (personal and professional are colour-coded), shows this month's
calendar on the right, and has "Add event" and (when there are past events)
"Past events" buttons.

Click any event, upcoming or past, to open its details page (`/events/<id>`):
title, type, whether it is upcoming or past, date, time, location and
description. Location and description are optional fields in the "Add event"
form. Databases created before these fields existed are upgraded automatically
on start; their old events show "Not given" / "No description".

Use the ‹ and › buttons above the calendar to move to the previous or next
month; days with events are marked in every month. When you are away from the
current month, a "Today" button takes you back. The shown month is part of the
address (for example `/?month=2027-03`), so it can be bookmarked; an invalid
value shows the current month.

The "Dark view" / "Light view" button in the top right switches the colour
theme. The choice is kept in a browser cookie, so it stays the same on every
page and the next time you visit. Light view is the default.

Events are stored in an SQLite file at `instance/scheduler.sqlite`, created
automatically on first start. Delete that file to start again with no events.

## Running the tests

```sh
.venv/bin/python -m pytest
```
