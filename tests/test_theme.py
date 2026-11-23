import re

import pytest


def page(client, path="/"):
    response = client.get(path)
    assert response.status_code == 200
    return response.get_data(as_text=True)


def theme_of(html):
    match = re.search(r'<html[^>]*data-theme="([a-z]+)"', html)
    assert match, "the page has no data-theme on <html>"
    return match.group(1)


def theme_toggle(html):
    header = re.search(r"<header.*?</header>", html, re.S)
    assert header, "page has no header"
    form = re.search(r'<form[^>]*class="theme-toggle".*?</form>', header.group(0), re.S)
    assert form, "no light/dark toggle in the header"
    return form.group(0)


def switch_theme(client, theme, next_path="/"):
    return client.post("/theme", data={"theme": theme, "next": next_path})


def test_light_view_is_the_default(client):
    html = page(client)
    assert theme_of(html) == "light"
    toggle = theme_toggle(html)
    assert 'value="dark"' in toggle
    assert "Dark view" in toggle


def test_switching_to_dark_view(client):
    response = switch_theme(client, "dark")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")

    html = page(client)
    assert theme_of(html) == "dark"
    toggle = theme_toggle(html)
    assert 'value="light"' in toggle
    assert "Light view" in toggle


def test_switching_back_to_light_view(client):
    switch_theme(client, "dark")
    switch_theme(client, "light")
    assert theme_of(page(client)) == "light"


def test_chosen_view_is_remembered_on_every_page(client):
    switch_theme(client, "dark")
    for path in ("/", "/events/new", "/events/past"):
        assert theme_of(page(client, path)) == "dark", path


def test_switching_returns_to_the_page_you_were_on(client):
    response = switch_theme(client, "dark", "/events/new")
    assert response.headers["Location"].endswith("/events/new")


@pytest.mark.parametrize("next_path", ["//evil.example", "http://evil.example/", "", "events"])
def test_switching_never_redirects_off_site(client, next_path):
    response = switch_theme(client, "dark", next_path)
    assert response.status_code == 302
    assert response.headers["Location"] in ("/", "http://localhost/")


def test_unknown_theme_value_is_ignored(client):
    switch_theme(client, "purple")
    assert theme_of(page(client)) == "light"


def test_unknown_theme_cookie_falls_back_to_light(client):
    client.set_cookie("theme", "purple")
    assert theme_of(page(client)) == "light"


def test_stylesheet_has_dark_view_colours(client):
    css = client.get("/static/style.css").get_data(as_text=True)
    dark = re.search(r'\[data-theme="dark"\]\s*\{(.*?)\}', css, re.S)
    assert dark, "no dark view rules in the stylesheet"
    for variable in ("--bg", "--surface", "--text", "--border"):
        assert variable in dark.group(1), variable
