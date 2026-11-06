# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""Optional Chromium tests for browser -> Flask -> theme preference flow.

pytest starts a loopback-only Werkzeug test server using temporary metadata.
Playwright drives local assets only; no real workout storage or external URLs.
"""

import os
import shutil
from threading import Thread
from urllib.parse import urlsplit

import pytest
from werkzeug.serving import make_server

from workout_tracker import create_app
from workout_tracker.storage import initialize_storage

playwright = pytest.importorskip("playwright.sync_api", reason="Install requirements-browser.txt for Chromium checks")


@pytest.fixture
def browser_page(tmp_path):
    """Serve a disposable application and reliably close its browser and server."""
    root = tmp_path / "browser-storage"
    initialize_storage(root)
    server = make_server("127.0.0.1", 0, create_app({"WORKOUT_DATA_ROOT": root}))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with playwright.sync_playwright() as manager:
            executable = os.environ.get("WORKOUT_CHROMIUM") or shutil.which("chromium")
            browser = manager.chromium.launch(headless=True, executable_path=executable)
            try:
                page = browser.new_page(viewport={"width": 320, "height": 740}, color_scheme="light")
                yield page, f"http://127.0.0.1:{server.server_port}"
            finally:
                browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_theme_persistence_auto_responsiveness_and_local_assets(browser_page):
    """Exercise real selection, reload, device changes, keyboard access and width."""
    page, address = browser_page
    requests = []
    errors = []
    page.on("request", lambda request: requests.append(request.url))
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(address)
    assert page.locator("#theme").input_value() == "auto"
    assert page.evaluate("getComputedStyle(document.body).backgroundColor") == "rgb(242, 245, 244)"
    page.emulate_media(color_scheme="dark")
    assert page.evaluate("getComputedStyle(document.body).backgroundColor") == "rgb(20, 32, 28)"
    page.select_option("#theme", "light")
    page.reload()
    assert page.locator("#theme").input_value() == "light"
    assert page.evaluate("getComputedStyle(document.body).backgroundColor") == "rgb(242, 245, 244)"
    page.select_option("#theme", "dark")
    page.reload()
    assert page.locator("#theme").input_value() == "dark"
    page.select_option("#theme", "auto")
    page.emulate_media(color_scheme="light")
    assert page.evaluate("getComputedStyle(document.body).backgroundColor") == "rgb(242, 245, 244)"
    page.keyboard.press("Tab")
    page.locator("#theme").focus()
    assert page.locator("#theme").evaluate("element => element === document.activeElement")
    assert page.locator('label[for="theme"]').inner_text() == "Theme for this browser"
    for width in (320, 768, 1280):
        page.set_viewport_size({"width": width, "height": 800})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert all(urlsplit(url).hostname == "127.0.0.1" for url in requests)
    assert errors == []


def test_storage_denied_and_invalid_saved_theme(browser_page):
    """Blocked browser storage remains usable; an unknown stored value uses Auto."""
    page, address = browser_page
    page.goto(address)
    page.evaluate("localStorage.setItem('workout-theme', 'invalid')")
    page.reload()
    assert page.locator("#theme").input_value() == "auto"
    page.add_init_script("Object.defineProperty(window, 'localStorage', {get() {throw new Error('blocked');}})")
    page.reload()
    assert "cannot be stored" in page.locator("#theme-status").inner_text()
    page.select_option("#theme", "dark")
    assert "could not save" in page.locator("#theme-status").inner_text()
    assert page.evaluate("document.documentElement.dataset.theme") == "dark"
