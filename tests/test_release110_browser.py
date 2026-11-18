# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Real Chromium mobile/desktop interactions with schema-14 disposable storage only."""
import pytest
from workout_tracker import catalog as c, ego_lifts as e, workouts as w
from workout_tracker.storage import database_session
from test_release110 import root110
from test_release_browser import release_page

pw = pytest.importorskip("playwright.sync_api")


@pytest.fixture
def unified_root(root110):
    """Reuse the existing app/browser fixture with the new candidate-migrated schema."""
    return root110


@pytest.mark.parametrize(
    "viewport", [(320, 800), (390, 844), (844, 390), (768, 1024), (1280, 900)]
)
@pytest.mark.parametrize("theme", ["light", "dark"])
def test_ego_mobile_create_edit_delete_idempotence_and_isolation(
    release_page, viewport, theme
):
    """Trophy entry, searchable shared IDs, signed Save, confirmed edits and responsive history."""
    page, base, x = release_page
    expect = pw.expect
    page.set_viewport_size(dict(zip(("width", "height"), viewport)))
    person = x["person"]
    exercise = x["exercises"][0]
    from workout_tracker import exercise_icons

    with database_session(x["root"], write=True) as db:
        exercise_icons.update(
            db,
            exercise,
            "start",
            b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><path d="M0 0L10 10"/></svg>',
        )
    page.goto(base + f"/settings?person_id={person}")
    page.select_option("#theme", theme)
    page.goto(base + f"/people/{person}")
    tile = page.locator(".ego-tile")
    routine_card = page.locator(".routine-card").first
    assert abs(tile.bounding_box()["width"] - routine_card.bounding_box()["width"]) < 1
    last = page.locator(".routine-card:not(.ego-tile)").last.bounding_box()
    assert tile.bounding_box()["y"] - last["y"] - last["height"] >= 24
    page.get_by_role("button", name="Start Ego Lift", exact=True).click()
    expect(
        page.get_by_role("heading", name="Select Exercise", exact=True)
    ).to_be_visible()
    expect(
        page.get_by_role("button", name="Select Exercise", exact=True)
    ).to_be_disabled()
    page.locator("#ego-exercise").select_option(exercise)
    expect(page.locator("#ego-preview .exercise-icon")).to_have_count(2)
    expect(page.locator('#ego-preview path[d="M0 0L10 10"]')).to_have_count(1)
    icons = page.locator("#ego-preview .exercise-icon").all()
    assert abs(icons[0].bounding_box()["y"] - icons[1].bounding_box()["y"]) < 1
    assert "/record/" not in page.url
    expect(
        page.get_by_role("button", name="Select Exercise", exact=True)
    ).to_be_enabled()
    page.get_by_role("button", name="Select Exercise", exact=True).click()
    expect(
        page.get_by_text("No previous Ego Lifts recorded.", exact=True)
    ).to_be_visible()
    expect(page.locator("input[name=weight]")).to_have_count(1)
    page.get_by_label("Weight (lb)", exact=True).fill("50.99")
    page.get_by_label("Repetitions", exact=True).fill("6")
    page.get_by_role("button", name="Save Lift", exact=True).click()
    expect(page.get_by_text("Ego Lift saved.", exact=True)).to_be_visible()
    expect(page.get_by_text("Estimated 1RM: 61.1 lb", exact=True)).to_be_visible()
    page.get_by_role("link", name="Back to selection", exact=True).click()
    page.get_by_role("link", name="Ego History", exact=True).click()
    expect(page.locator(".ego-history-row")).to_have_count(1)
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    page.get_by_role("link", name="Correct or delete lift", exact=True).click()
    page.get_by_label("Weight (lb)", exact=True).fill("60")
    page.get_by_label("Repetitions", exact=True).fill("1")
    page.get_by_label("I confirm this correction or deletion.", exact=True).check()
    page.get_by_role("button", name="Save correction", exact=True).click()
    expect(page.get_by_text("Estimated 1RM: 60.0 lb", exact=True)).to_be_visible()
    with database_session(x["root"]) as db:
        assert not e.history(db, x["other"], exercise)
        assert db.execute("SELECT count(*) FROM workout_sessions").fetchone()[0] == 0
    page.get_by_role("link", name="Correct or delete lift", exact=True).click()
    page.get_by_label("I confirm this correction or deletion.", exact=True).check()
    page.get_by_role("button", name="Delete lift", exact=True).click()
    expect(page.get_by_text("Ego Lift removed.", exact=True)).to_be_visible()
    expect(page.locator(".ego-history-row")).to_have_count(0)
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")


@pytest.mark.parametrize("viewport", [(390, 844), (844, 390)])
@pytest.mark.parametrize("theme", ["light", "dark"])
def test_automatic_sets_done_resume_inline_errors_and_finish(
    release_page, viewport, theme
):
    """All seven combinations use blank placeholders, durable Done and inferred statuses."""
    page, base, x = release_page
    expect = pw.expect
    page.set_viewport_size(dict(zip(("width", "height"), viewport)))
    page.goto(base + f'/settings?person_id={x["person"]}')
    page.select_option("#theme", theme)
    page.goto(base + f'/people/{x["person"]}')
    page.get_by_role("button", name="Start workout", exact=False).click()
    page.get_by_role("button", name="Skip", exact=True).click()
    expect(page.locator("select[data-set-status]")).to_have_count(0)
    assert (
        "One weight applies to every completed set. Zero is valid. Skip sets explicitly."
        not in page.content()
    )
    page.locator("[name=done_0]").check()
    expect(page.locator("#save-status")).to_have_text("✓ Saved")
    page.reload()
    expect(page.locator("[name=done_0]")).to_be_checked()
    page.get_by_role("link", name="Next", exact=True).click()
    expect(page.locator("[data-field-error=sets]")).to_contain_text(
        "every enabled measurement"
    )
    page.locator("[name=weight]").fill("0")
    page.get_by_role("link", name="Next", exact=True).click()
    for caps in range(2, 8):
        expect(
            page.get_by_role("heading", name=f"Exercise {caps}", exact=True)
        ).to_be_visible()
        for node in page.locator("#workout-form input[inputmode]").all():
            expect(node).to_have_attribute("placeholder", "—")
        if caps & 1:
            page.locator("[name=weight]").fill("40")
        if caps & 2:
            page.locator("[name=reps_0]").fill("0")
        if caps & 4:
            if caps == 4:
                page.locator("[name=seconds_0]").fill("0")
                expect(page.locator("[data-field-error=duration_0]")).to_contain_text(
                    "positive"
                )
            page.locator("[name=seconds_0]").fill("60")
        expect(page.locator("#save-status")).to_have_text("✓ Saved")
        if caps < 7:
            page.get_by_role("link", name="Next", exact=True).click()
    page.locator("[name=seconds_0]").fill("")
    expect(page.locator("#save-status")).to_have_text("✓ Saved")
    page.get_by_role("button", name="Finish & Save", exact=True).click()
    expect(page.locator("[data-field-error=reps_0]")).to_contain_text(
        "every enabled measurement"
    )
    page.locator("[name=seconds_0]").fill("60")
    page.get_by_role("button", name="Finish & Save", exact=True).click()
    expect(
        page.get_by_role("heading", name="Workout saved", exact=True)
    ).to_be_visible()
    with database_session(x["root"]) as db:
        assert (
            db.execute(
                "SELECT count(*) FROM workout_sets WHERE status='skipped' AND actual_reps IS NULL AND actual_duration_seconds IS NULL"
            ).fetchone()[0]
            == 14
        )
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
