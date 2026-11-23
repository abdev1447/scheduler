from flask import Blueprint, redirect, request, url_for

bp = Blueprint("theme", __name__)

THEMES = ("light", "dark")
DEFAULT_THEME = "light"
COOKIE = "theme"
ONE_YEAR = 60 * 60 * 24 * 365


def current_theme():
    theme = request.cookies.get(COOKIE)
    return theme if theme in THEMES else DEFAULT_THEME


@bp.app_context_processor
def inject_theme():
    return {"theme": current_theme()}


def safe_next(target):
    """Only allow redirects to a path on this site."""
    if target and target.startswith("/") and not target.startswith("//") and "\\" not in target:
        return target
    return url_for("events.dashboard")


@bp.post("/theme")
def set_theme():
    response = redirect(safe_next(request.form.get("next", "")))
    theme = request.form.get("theme")
    if theme in THEMES:
        response.set_cookie(COOKIE, theme, max_age=ONE_YEAR, samesite="Lax", httponly=True)
    return response
