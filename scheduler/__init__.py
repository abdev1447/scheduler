import os

from flask import Flask


def create_app(test_config=None):
    """Application factory: build and return the Flask app."""
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE=os.path.join(app.instance_path, "scheduler.sqlite"),
    )

    if test_config is not None:
        app.config.from_mapping(test_config)

    os.makedirs(app.instance_path, exist_ok=True)

    from . import db, events, theme

    db.init_app(app)
    app.register_blueprint(events.bp)
    app.register_blueprint(theme.bp)

    return app
