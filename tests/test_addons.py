"""Tests for M4 add-on features: query history, export/copy, loading animation."""

import pathlib

STATIC = pathlib.Path(__file__).resolve().parent.parent / "static"


def _read(name):
    return (STATIC / name).read_text()


# --- Query History ---


def test_html_has_query_history_section():
    html = _read("index.html")
    assert 'id="query-history-section"' in html
    assert 'id="query-history"' in html


def test_html_has_clear_history_button():
    html = _read("index.html")
    assert 'id="clear-history-btn"' in html
    assert "Clear History" in html


def test_app_js_uses_localstorage():
    js = _read("app.js")
    assert "localStorage.getItem" in js
    assert "localStorage.setItem" in js
    assert "localStorage.removeItem" in js


def test_app_js_limits_history_to_10():
    js = _read("app.js")
    assert "MAX_HISTORY" in js


# --- Export/Copy ---


def test_html_has_copy_button():
    html = _read("index.html")
    assert 'id="copy-result-btn"' in html
    assert "Copy to Clipboard" in html


def test_html_has_download_button():
    html = _read("index.html")
    assert 'id="download-result-btn"' in html
    assert "Download as .txt" in html


def test_app_js_uses_clipboard_api():
    js = _read("app.js")
    assert "navigator.clipboard.writeText" in js


def test_app_js_creates_blob_download():
    js = _read("app.js")
    assert "new Blob" in js
    assert "URL.createObjectURL" in js


# --- Loading Animation ---


def test_html_has_loading_spinner():
    html = _read("index.html")
    assert 'id="loading-spinner"' in html
    assert "spinner" in html


def test_css_has_spinner_animation():
    css = _read("style.css")
    assert ".spinner-circle" in css
    assert "@keyframes spin" in css
    assert "animation:" in css


def test_css_has_spinner_styles():
    css = _read("style.css")
    assert "border-radius: 50%" in css
    assert "border-top-color" in css


def test_app_js_toggles_spinner():
    js = _read("app.js")
    assert "showSpinner" in js
    assert "hideSpinner" in js
