import sqlite3

from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS event (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    date TEXT NOT NULL,          -- YYYY-MM-DD
    time TEXT,                   -- HH:MM, or NULL for an all-day event
    category TEXT NOT NULL CHECK (category IN ('personal', 'professional')),
    location TEXT,               -- optional
    description TEXT             -- optional
);
"""

# Columns added after the first release; older database files get them on start.
ADDED_COLUMNS = {"location": "TEXT", "description": "TEXT"}


def get_db():
    """Return the SQLite connection for the current request."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_app(app):
    """Create the tables if needed and close the connection after each request."""
    with sqlite3.connect(app.config["DATABASE"]) as conn:
        conn.executescript(SCHEMA)
        existing = {row[1] for row in conn.execute("PRAGMA table_info(event)")}
        for name, kind in ADDED_COLUMNS.items():
            if name not in existing:
                conn.execute(f"ALTER TABLE event ADD COLUMN {name} {kind}")
    conn.close()
    app.teardown_appcontext(close_db)
