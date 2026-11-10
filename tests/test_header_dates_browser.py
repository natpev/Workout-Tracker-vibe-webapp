# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Real phone/desktop cards show the date from their existing completion rank.

Read semantic time elements and theme contrast, retain original actions, and
compare with hidden date text to bound the extra card height. Disposable data only.
"""
from pathlib import Path
import pytest
from workout_tracker.storage import database_session
from test_phase9 import phase9_root
from test_phase10_browser import phase10_page
from test_routine_listing import routine, historical

pw = pytest.importorskip('playwright.sync_api')


@pytest.mark.parametrize('width', [320, 390, 1280])
def test_card_dates_compact_controls_and_themes(phase10_page, width):
    """Dates stay readable and compact with working actions and a rightmost header."""
    page, base, root, person, other, mixed, exercise, saved, draft = phase10_page
    expect = pw.expect
    with database_session(root, write=True) as db:
        recent = routine(db, person, 'Recently done')
        routine(db, person, 'Never done')
        historical(db, person, recent, '2026-11-06')
    page.set_viewport_size({'width': width, 'height': 844})
    for theme in ('light', 'dark', 'auto'):
        page.goto(base + f'/settings?person_id={person}')
        page.select_option('#theme', theme)
        page.goto(base + '/people/' + person)
        expect(page.locator('.routine-card h2')).to_have_text(['Recently done', 'Mixed', 'Never done'])
        expect(page.locator('.routine-activity')).to_have_text(['Last completed: November 6, 2026', 'Last completed: November 2, 2026', 'Never completed'])
        expect(page.locator('.routine-card time').first).to_have_attribute('datetime', '2026-11-06')
        expect(page.locator('.routine-card button')).to_have_count(3)
        expect(page.locator('.routine-card .edit-link')).to_have_count(3)
        for card in page.locator('.routine-card').all():
            # Check actual rendered height, including the existing mobile wrap,
            # rather than assuming a desktop line-height budget fits every phone.
            with_date = card.bounding_box()['height']
            label = card.locator('.routine-activity')
            label.evaluate('(n)=>n.style.display="none"')
            without_date = card.bounding_box()['height']
            label.evaluate('(n)=>n.style.removeProperty("display")')
            assert with_date - without_date <= 25
            assert label.evaluate('(n)=>getComputedStyle(n).color') == page.locator('footer').evaluate('(n)=>getComputedStyle(n).color')
        assert page.evaluate('document.documentElement.scrollWidth <= document.documentElement.clientWidth')
        if width == 390:
            shots = Path('/tmp/header-dates-screenshots');shots.mkdir(exist_ok=True)
            page.screenshot(path=str(shots / ('cards-' + theme + '.png')))
    # Preserve the existing real navigation target for the named routine.
    card = page.locator('.routine-card').first
    assert card.locator('form').get_attribute('action') == f'/people/{person}/routines/{recent}/start'
    card.locator('.edit-link').click()
    expect(page.get_by_role('heading', name='Recently done', exact=True)).to_be_visible()
