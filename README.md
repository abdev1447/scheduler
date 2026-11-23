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

Events are stored in an SQLite file at `instance/scheduler.sqlite`, created
automatically on first start. Delete that file to start again with no events.

## Running the tests

```sh
.venv/bin/python -m pytest
```
