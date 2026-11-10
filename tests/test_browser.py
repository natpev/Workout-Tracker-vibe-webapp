# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
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
def browser_page(phase2_root):
    """Serve a disposable application and reliably close its browser and server."""
    root = phase2_root
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
    page.goto(address + "/settings")
    assert page.locator("#theme").input_value() == "auto"
    assert page.evaluate("getComputedStyle(document.body).backgroundColor") == "rgb(243, 245, 250)"
    page.emulate_media(color_scheme="dark")
    assert page.evaluate("getComputedStyle(document.body).backgroundColor") == "rgb(17, 21, 31)"
    page.select_option("#theme", "light")
    page.reload()
    assert page.locator("#theme").input_value() == "light"
    assert page.evaluate("getComputedStyle(document.body).backgroundColor") == "rgb(243, 245, 250)"
    page.select_option("#theme", "dark")
    page.reload()
    assert page.locator("#theme").input_value() == "dark"
    page.select_option("#theme", "auto")
    page.emulate_media(color_scheme="light")
    assert page.evaluate("getComputedStyle(document.body).backgroundColor") == "rgb(243, 245, 250)"
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
    page.goto(address + "/settings")
    page.evaluate("localStorage.setItem('workout-theme', 'invalid')")
    page.reload()
    assert page.locator("#theme").input_value() == "auto"
    page.add_init_script("Object.defineProperty(window, 'localStorage', {get() {throw new Error('blocked');}})")
    page.reload()
    assert "cannot be stored" in page.locator("#theme-status").inner_text()
    page.select_option("#theme", "dark")
    assert "could not save" in page.locator("#theme-status").inner_text()
    assert page.evaluate("document.documentElement.dataset.theme") == "dark"


@pytest.fixture
def management_page(phase2_root):
    """Serve an actual schema-2 management app with its private fixture key."""
    server = make_server("127.0.0.1", 0, create_app({"WORKOUT_DATA_ROOT": phase2_root}))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with playwright.sync_playwright() as manager:
            browser = manager.chromium.launch(headless=True,
                executable_path=os.environ.get("WORKOUT_CHROMIUM") or shutil.which("chromium"))
            try:
                page = browser.new_page(viewport={"width": 320, "height": 800})
                yield page, f"http://127.0.0.1:{server.server_port}"
            finally:
                browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_management_workflow_modes_order_copy_and_phone_layout(management_page):
    """Drive routine creation/configuration/copy through real CSRF-protected forms."""
    page, address = management_page
    expect = playwright.expect
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(address + "/people")
    page.get_by_label("Name", exact=True).fill("Alex")
    page.get_by_role("button", name="Add person", exact=True).click()
    page.get_by_label("Routine name", exact=True).fill("Strength")
    page.get_by_role("button", name="Create routine", exact=True).click()
    source = page.url
    form = page.locator("[data-configuration]")
    form.get_by_label("New exercise name (when not reusing)").fill("Plank")
    # Native radios provide a segmented control with keyboard arrow navigation.
    form.get_by_role("radio", name="Weight", exact=True).focus()
    page.keyboard.press("ArrowRight")
    expect(form.get_by_role("radio", name="Time", exact=True)).to_be_checked()
    expect(form.locator('[data-fields="weight"]')).to_be_hidden()
    form.get_by_label("Minutes", exact=True).fill("1")
    form.get_by_label("Seconds", exact=True).fill("5")
    form.get_by_label("Exercise notes (optional)").fill("Keep steady")
    form.get_by_role("button", name="Add exercise", exact=True).click()
    expect(page.get_by_text("Time · 3 sets × 1 min 5 sec", exact=True)).to_be_visible()
    page.get_by_role("link", name="Plank", exact=True).click()
    expect(page.get_by_label("Seconds", exact=True)).to_have_value("5")
    page.get_by_role("radio", name="Weight", exact=True).check()
    page.get_by_label("Target repetitions per set").fill("12")
    page.get_by_role("button", name="Save exercise settings").click()
    expect(page.get_by_text("Weight · 3 sets × 12 reps · pounds", exact=True)).to_be_visible()
    form = page.locator("[data-configuration]")
    form.get_by_label("New exercise name (when not reusing)").fill("Bench")
    form.get_by_role("button", name="Add exercise", exact=True).click()
    page.get_by_role("button", name="Move Bench up", exact=True).click()
    expect(page.locator("h4")).to_have_text(["Bench", "Plank"])
    for width in (320, 768, 1280):
        page.set_viewport_size({"width": width, "height": 800})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    editor_url=page.url
    page.goto(address+'/settings')
    page.select_option("#theme", "dark")
    page.reload()
    expect(page.locator("#theme")).to_have_value("dark")
    page.goto(address+'/people')
    page.get_by_label("Name", exact=True).fill("Sam")
    page.get_by_role("button", name="Add person", exact=True).click()
    page.get_by_label("Source routine", exact=True).select_option(label="Alex / Strength")
    page.get_by_label("Name for the copy", exact=True).fill("Independent")
    page.get_by_role("button", name="Copy routine", exact=True).click()
    expect(page.get_by_role("heading", name="Independent", exact=True)).to_be_visible()
    expect(page.locator("h4")).to_have_text(["Bench", "Plank"])
    page.get_by_role("button",name="Open navigation",exact=True).click()
    page.get_by_role("link", name="Exercise Library", exact=True).click()
    page.locator('.library-exercise').filter(has=page.get_by_role('heading',name='Bench',exact=True)).get_by_role('link',name='Edit Defaults',exact=True).click()
    rename_form = page.locator('form[data-configuration]') if page.locator('form[data-configuration]').count() else page.locator('form')
    rename_form.get_by_label("Exercise name", exact=True).fill("Copy bench")
    rename_form.get_by_role("button", name="Save changes").click()
    page.goto(source)
    expect(page.locator("h4")).to_have_text(["Bench", "Plank"])
    assert errors == []
