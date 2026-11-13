# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Real Chromium release workflows with temporary SQLite and mocked official Garmin.

These are application regressions, not claims of physical iPhone/Safari testing.
"""
import os
import shutil
from threading import Thread
from unittest.mock import patch
import pytest
from werkzeug.serving import make_server
from workout_tracker import create_app, catalog as c, workouts as w
from workout_tracker.storage import database_session
from test_unified_measurements import unified_root
from test_garmin import response as garmin_response

pw = pytest.importorskip("playwright.sync_api")


@pytest.fixture
def release_page(unified_root):
    """Serve the actual app on loopback; no real API, production mount or deployment."""
    with database_session(unified_root, write=True) as db:
        person = c.create_person(db, "Alex")
        other = c.create_person(db, "Blair")
        routine = c.create_routine(db, person, "All combinations")
        exercises = []
        for caps in range(1, 8):
            item = c.add_entry(
                db,
                person,
                routine,
                dict(
                    name=f"Exercise {caps}",
                    measurement_type="flex",
                    capabilities=caps,
                    target_sets="3",
                    target_reps="12",
                    seconds="45",
                    weight_basis="total",
                ),
            )
            exercises.append(c.entry(db, person, routine, item)["exercise_id"])
    app = create_app(
        {"TESTING": True, "WORKOUT_DATA_ROOT": unified_root, "WORKOUT_TIMEZONE": "UTC"}
    )
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with patch(
            "workout_tracker.garmin.request", side_effect=garmin_response
        ), pw.sync_playwright() as manager:
            browser = manager.chromium.launch(
                headless=True,
                executable_path=os.environ.get("WORKOUT_CHROMIUM")
                or shutil.which("chromium"),
            )
            try:
                yield browser.new_page(), f"http://127.0.0.1:{server.server_port}", dict(
                    root=unified_root,
                    person=person,
                    other=other,
                    routine=routine,
                    exercises=exercises,
                )
            finally:
                browser.close()
    finally:
        server.shutdown()
        thread.join(5)
        server.server_close()


@pytest.mark.parametrize("viewport", [(390, 844), (844, 390)])
@pytest.mark.parametrize("theme", ["light", "dark"])
def test_seven_combinations_autosave_skip_resume_and_complete(
    release_page, viewport, theme
):
    """One weight input; set NULLs/status survive refresh and navigation to completion."""
    page, base, x = release_page
    expect = pw.expect
    page.set_viewport_size(dict(zip(("width", "height"), viewport)))
    page.goto(base + f"/settings?person_id={x['person']}")
    page.select_option("#theme", theme)
    page.goto(base + f"/people/{x['person']}")
    expect(
        page.get_by_role("heading", name="Training Consistency", exact=True)
    ).to_be_visible()
    page.get_by_role("button", name="Start workout", exact=False).click()
    expect(page.get_by_role("heading", name="Today’s Body Weight")).to_be_visible()
    page.get_by_role("button", name="Skip", exact=True).click()
    for caps in range(1, 8):
        expect(
            page.get_by_role("heading", name=f"Exercise {caps}", exact=True)
        ).to_be_visible()
        expect(page.locator("#workout-form [name=weight]")).to_have_count(
            1 if caps & 1 else 0
        )
        assert page.locator("#progress-text").count() == 0
        if caps & 1:
            page.locator("#workout-form [name=weight]").fill("40")
        if caps & 2:
            page.locator("[name=reps_0]").fill("0")
        if caps & 4:
            page.locator("[name=seconds_0]").fill("90")
        page.locator("[name=status_0]").select_option("completed")
        page.locator("[name=status_1]").select_option("skipped")
        page.locator("[name=status_2]").select_option("skipped")
        expect(page.locator("#save-status")).to_have_text("✓ Saved")
        page.reload()
        expect(page.locator("[name=status_1]")).to_have_value("skipped")
        if caps & 2:
            expect(page.locator("[name=reps_0]")).to_have_value("0")
        if caps & 4:
            expect(page.locator("[name=seconds_0]")).to_have_value("30")
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
        if caps < 7:
            page.get_by_role("link", name="Next", exact=True).click()
    page.get_by_role("button", name="Finish & Save", exact=True).click()
    expect(
        page.get_by_role("heading", name="Workout saved", exact=True)
    ).to_be_visible()
    day = w.now().date().isoformat()
    page.goto(base + f"/people/{x['person']}/reports?from={day}&to={day}")
    with page.expect_download() as csv_download:
        page.get_by_role("button", name="Download detailed CSV", exact=True).click()
    assert b"set_status" in open(csv_download.value.path(), "rb").read()
    with page.expect_download() as pdf_download:
        page.get_by_role("button", name="Download PDF", exact=True).click()
    assert open(pdf_download.value.path(), "rb").read(4) == b"%PDF"
    page.goto(
        base + f"/people/{x['person']}/progress?range=all&exercise={x['exercises'][-1]}"
    )
    expect(page.locator(".progress-series")).to_have_count(3)
    assert page.locator(".progress-series[data-kind=reps]").count() == 1
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    with database_session(x["root"]) as db:
        assert (
            db.execute(
                "SELECT count(*) FROM workout_sessions WHERE status='completed'"
            ).fetchone()[0]
            == 1
        )
        assert (
            db.execute(
                "SELECT count(*) FROM workout_sets WHERE status='skipped' AND actual_reps IS NULL AND actual_duration_seconds IS NULL"
            ).fetchone()[0]
            == 14
        )
        assert db.execute("SELECT count(*) FROM body_weights").fetchone()[0] == 0


@pytest.mark.parametrize('viewport',[(320,800),(768,1024),(1280,900)])
@pytest.mark.parametrize('theme',['light','dark'])
def test_body_weights_garmin_reports_details_and_database_download(release_page,viewport,theme):
    """Read-only details, multiple local readings, real file downloads and secret-free pages."""
    page, base, x = release_page
    expect = pw.expect
    person = x["person"]
    page.set_viewport_size(dict(zip(('width','height'),viewport)))
    page.goto(base+f'/settings?person_id={person}');page.select_option('#theme',theme)
    page.get_by_role('radio',name='Soft Purple',exact=True).check()
    page.get_by_role('button',name='Save accent color',exact=True).click()
    page.goto(base + f"/people/{person}/exercises/{x['exercises'][0]}")
    expect(page.get_by_role("heading", name="Exercise 1", exact=True)).to_be_visible()
    assert page.locator("input").count() == 0
    page.get_by_role("link", name="Edit Exercise", exact=True).click()
    expect(page.get_by_role("checkbox", name="Weight", exact=True)).to_be_checked()
    page.goto(base + f"/people/{person}/weight")
    for weight, clock in [("220.5", "08:00"), ("219.5", "18:00")]:
        page.get_by_role("textbox", name="Weight (lb)", exact=True).fill(weight)
        page.locator("[name=date]").fill("2020-01-01")
        page.locator("[name=time]").fill(clock)
        page.get_by_role("button", name="Save body weight", exact=True).click()
    expect(page.get_by_role("link", name="Edit weigh-in")).to_have_count(2)
    page.get_by_role('link',name='Edit weigh-in').first.click()
    page.locator('[name=weight]').fill('218.125')
    page.get_by_role('button',name='Save changes',exact=True).click()
    page.get_by_role('link',name='Edit weigh-in').first.click()
    page.get_by_label('I confirm removing this manual measurement',exact=True).check()
    page.get_by_role('button',name='Remove measurement',exact=True).click()
    expect(page.get_by_role('link',name='Edit weigh-in')).to_have_count(1)
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    expect(page.locator('body')).to_have_attribute('data-accent','purple')
    page.goto(base + f"/people/{person}/garmin")
    page.locator("[name=api_key]").fill("synthetic-a")
    page.get_by_role("button", name="Connect and verify", exact=True).click()
    expect(page.get_by_text("Connected", exact=True)).to_be_visible()
    assert "synthetic-a" not in page.content()
    page.get_by_role("button", name="Sync Now", exact=True).click()
    expect(
        page.get_by_text(
            "Garmin synchronization complete: 2 new or updated measurements.",
            exact=True,
        )
    ).to_be_visible()
    # Download the real SQLite snapshot through the CSRF-protected browser form.
    page.goto(base + f"/settings/administration?person_id={person}")
    with page.expect_download() as download:
        page.get_by_role("button", name="Download Database", exact=True).click()
    data = open(download.value.path(), "rb").read()
    assert data.startswith(b"SQLite format 3") and b"synthetic-a" not in data
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")


def test_new_historical_corrections_reports_and_full_restore_workflow(release_page):
    """Real forms correct per-set history, preserve a draft and restore body/icon data."""
    from workout_tracker import history as h, body_weight as b

    page, base, x = release_page
    expect = pw.expect
    person = x["person"]
    page.set_viewport_size(dict(width=320, height=800))
    with database_session(x["root"], write=True) as db:
        draft, _ = w.start(db, person, x["routine"], "UTC")
        b.manual(db, person, dict(date="2020-01-01", time="08:00", weight="220"), "UTC")
        from workout_tracker.exercise_icons import update

        update(
            db,
            x["exercises"][0],
            "start",
            '<svg><circle r="10" fill="var(--accent)"/></svg>',
        )
    page.goto(base + f"/people/{person}/history")
    page.get_by_role("link", name="Enter historical workout", exact=True).click()
    page.get_by_label("Workout date", exact=True).fill("2020-01-02")
    page.get_by_role("button", name="Prepare historical workout", exact=True).click()
    for index, caps in enumerate(range(1, 8)):
        if caps & 1:
            page.locator(f"[name=weight_{index}]").fill("40")
        if caps & 2:
            page.locator(f"[name=reps_{index}_0]").fill("10")
        if caps & 4:
            page.locator(f"[name=seconds_{index}_0]").fill("45")
        for set_index in range(3):
            page.locator(f"[name=status_{index}_{set_index}]").select_option(
                "completed" if set_index == 0 else "skipped"
            )
    page.get_by_role("button", name="Save historical workout", exact=True).click()
    expect(
        page.get_by_role("link", name="Correct saved workout", exact=True)
    ).to_be_visible()
    identity = page.url.rsplit("/", 1)[-1]
    page.get_by_role("link", name="Correct saved workout", exact=True).click()
    page.locator("[name=weight_6]").fill("0")
    page.locator("[name=reps_6_0]").fill("9")
    page.locator("[name=seconds_6_0]").fill("90")
    page.get_by_label(
        "I confirm these corrections and understand original records are retained"
    ).check()
    page.get_by_role("button", name="Apply correction", exact=True).click()
    expect(page.get_by_text("Correction 1", exact=False)).to_be_visible()
    page.goto(
        base + f"/people/{person}/progress?range=all&exercise={x['exercises'][6]}"
    )
    expect(page.locator(".progress-series")).to_have_count(3)
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    page.goto(base + f"/people/{person}/reports?from=2020-01-01&to=2020-01-31")
    with page.expect_download() as pdf:
        page.get_by_role("button", name="Download PDF", exact=True).click()
    assert open(pdf.value.path(), "rb").read(4) == b"%PDF"
    page.goto(base + f"/settings/administration?person_id={person}")
    page.get_by_role("button", name="Backup Now", exact=True).click()
    expect(page.locator("#backup-status")).to_have_text("verified")
    backup_url = page.url
    with database_session(x["root"], write=True) as db:
        row = db.execute("SELECT id FROM body_weights").fetchone()[0]
        b.remove(db, person, row, dict(confirm="yes", revision="0"))
    page.get_by_label(
        "I understand this selects an earlier dataset and preserves the current database separately",
        exact=True,
    ).check()
    page.get_by_label("Type RESTORE to confirm", exact=True).fill("RESTORE")
    page.get_by_role("button", name="Restore Backup", exact=True).click()
    expect(
        page.get_by_role("heading", name="Restore result", exact=True)
    ).to_be_visible()
    expect(page.locator('[role="status"]:not(#theme-status)')).to_have_text("succeeded")
    with database_session(x["root"]) as db:
        assert w.active(db, person)["id"] == draft
        row = h.effective(db, person, identity)[1][-1]
        assert (
            row["actual_weight_tenths_lb"] == 0
            and row["sets"][0]["actual_duration_seconds"] == 90
        )
        assert db.execute("SELECT count(*) FROM body_weights").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM exercise_icons").fetchone()[0] == 1
