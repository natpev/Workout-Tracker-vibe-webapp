# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""Chromium verifies server-sorted cards retain existing controls and phone layout.

Reuse the disposable schema-7 HTTP fixture, never a production installation.
Only fixture completion data changes; no browser sorting script is introduced.
"""
import pytest
from workout_tracker.storage import database_session
from test_phase9 import phase9_root
from test_phase10_browser import phase10_page
from test_routine_listing import routine, historical

pw = pytest.importorskip('playwright.sync_api')


@pytest.mark.parametrize('width', [320, 1280])
def test_sorted_cards_controls_refresh_and_all_themes(phase10_page, width):
    """Read server order before/after completion while preserving cards and actions."""
    page, base, root, person, other, mixed, exercise, saved, draft = phase10_page
    expect = pw.expect
    with database_session(root, write=True) as db:
        never_z = routine(db, person, 'Zulu')
        older = routine(db, person, 'Older')
        routine(db, person, 'alpha')
        historical(db, person, older, '2021-01-01')
    page.set_viewport_size({'width': width, 'height': 844})
    for theme in ('light', 'dark', 'auto'):
        page.goto(base + f'/settings?person_id={person}')
        page.select_option('#theme', theme)
        page.goto(base + '/people/' + person)
        page.reload()
        expect(page.locator('.routine-card h2')).to_have_text(['Mixed', 'Older', 'alpha', 'Zulu'])
        expect(page.locator('.routine-card button')).to_have_count(4)
        expect(page.locator('.routine-card .edit-link')).to_have_count(4)
        assert page.locator('.routine-card form').first.get_attribute('action') == f'/people/{person}/routines/{mixed}/start'
        assert page.evaluate('document.documentElement.scrollWidth <= document.documentElement.clientWidth')
    with database_session(root, write=True) as db:
        historical(db, person, never_z, '2026-11-07')
    page.reload()
    expect(page.locator('.routine-card h2')).to_have_text(['Zulu', 'Mixed', 'Older', 'alpha'])
    expect(page.locator('footer')).to_contain_text('v0.11.0 · Database v7')
