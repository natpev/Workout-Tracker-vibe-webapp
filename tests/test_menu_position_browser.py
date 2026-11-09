# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""Real Chromium menu bounds, navigation, themes and sticky-header regression.

Use disposable schema-7 data and existing local HTTP/Chromium fixtures. Check
actual hit targets, not merely CSS visibility; no production server is contacted.
"""
import os
from pathlib import Path

import pytest
from workout_tracker import catalog as c, preferences
from workout_tracker.storage import database_session
from test_phase9 import phase9_root
from test_phase10_browser import phase10_page

pw = pytest.importorskip('playwright.sync_api')
SHOTS = Path(os.environ.get('WORKOUT_MENU_SCREENSHOTS', '/tmp/workout-menu-screenshots'))
SHOTS.mkdir(parents=True, exist_ok=True)
VIEWPORTS = [(390, 844), (320, 568), (844, 390), (768, 1024), (1280, 900)]
LINKS = ['Routines', 'Exercise Library', 'History & Progress', 'Settings']


def assert_usable_menu(page, width, height):
    """Check viewport containment, unclipped links and real frontmost hit targets."""
    panel = page.locator('#main-menu')
    pw.expect(panel).to_be_visible()
    box = panel.bounding_box()
    header = page.locator('.app-header').bounding_box()
    button = page.get_by_role('button', name='Open navigation', exact=True).bounding_box()
    padding = page.locator('.app-header').evaluate('(n)=>parseFloat(getComputedStyle(n).paddingRight)')
    assert abs(button['x'] + button['width'] - (header['x'] + header['width'] - padding)) < 1
    assert header['height'] <= 65 and button['y'] >= header['y']
    assert button['y'] + button['height'] <= header['y'] + header['height']
    selected = page.locator('.selected-person')
    if selected.count():
        info = selected.bounding_box()
        assert info['width'] > 20 and info['x'] >= page.locator('header .brand').bounding_box()['x'] + page.locator('header .brand').bounding_box()['width']
        assert info['x'] + info['width'] <= button['x'] - 8
        pw.expect(selected).to_be_visible()
    assert 8 <= box['x'] and box['x'] + box['width'] <= width - 8
    assert box['y'] >= page.locator('.app-header').bounding_box()['y'] + page.locator('.app-header').bounding_box()['height']
    assert box['y'] + box['height'] <= height - 8
    pw.expect(panel.get_by_role('link')).to_have_text(LINKS)
    for link in panel.get_by_role('link').all():
        pw.expect(link).to_be_visible()
        point = link.bounding_box()
        assert point['x'] >= box['x'] and point['x'] + point['width'] <= box['x'] + box['width']
        assert point['y'] >= box['y'] and point['y'] + point['height'] <= box['y'] + box['height']
        # A card or sticky element covering a link fails this check even when
        # Playwright's visibility definition would still consider the link visible.
        assert link.evaluate('(n)=>{const r=n.getBoundingClientRect();return !!document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)?.closest("#main-menu");}')
    assert page.evaluate('document.documentElement.scrollWidth <= document.documentElement.clientWidth')


@pytest.mark.parametrize('width,height', VIEWPORTS)
@pytest.mark.parametrize('theme', ['light', 'dark'])
def test_menu_bounds_links_context_keyboard_and_orientation(phase10_page, width, height, theme):
    """Exercise both anchor positions, long names, every link and unchanged closing."""
    page, base, root, person, other, routine, exercise, saved, draft = phase10_page
    expect = pw.expect
    with database_session(root, write=True) as db:
        long_person = c.create_person(db, 'A long household person name for viewport checks')
        for owner in (person, long_person):
            for index in range(9):
                c.create_routine(db, owner, 'Menu fixture ' + str(index))
    preferences.set_color(root, person, 'purple')
    preferences.set_color(root, long_person, 'teal')
    page.set_viewport_size({'width': width, 'height': height})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    for selected, name, accent in ((person, 'A', 'purple'), (long_person, 'A long household person name for viewport checks', 'teal'), (None, None, 'blue')):
        settings = '/settings' + ('?person_id=' + selected if selected else '')
        destination = '/people/' + selected if selected else '/people'
        page.goto(base + settings)
        page.select_option('#theme', theme)
        page.goto(base + destination)
        button = page.get_by_role('button', name='Open navigation', exact=True)
        panel = page.locator('#main-menu')
        button.click()
        expect(button).to_have_attribute('aria-expanded', 'true')
        assert_usable_menu(page, width, height)
        assert page.locator('body').get_attribute('data-accent') == accent
        if selected:
            expect(page.locator('.selected-person')).to_contain_text(name)
        if width in (390, 844) and selected == person:
            page.screenshot(path=str(SHOTS / f'menu-{width}-{theme}.png'))
        # Toggle, outside click, ArrowDown/focus and Escape retain old behavior.
        button.click();expect(panel).to_be_hidden()
        expect(button).to_have_attribute('aria-expanded', 'false')
        button.click();page.mouse.click(width - 2, height - 2)
        expect(panel).to_be_hidden();expect(button).to_have_attribute('aria-expanded', 'false')
        button.press('ArrowDown')
        expect(panel.get_by_role('link').first).to_be_focused()
        page.keyboard.press('Escape')
        expect(panel).to_be_hidden();expect(button).to_be_focused()
        expect(button).to_have_attribute('aria-expanded', 'false')
        button.click();page.locator('header .brand').focus();expect(panel).to_be_hidden()
        # Each actual click navigates to its original URL with person context.
        for label in LINKS:
            page.goto(base + destination)
            button.click()
            assert_usable_menu(page, width, height)
            link = panel.get_by_role('link', name=label, exact=True)
            href = link.get_attribute('href')
            link.click()
            expect(page).to_have_url(base + href)
            expect(panel).to_be_hidden()
            expect(button).to_have_attribute('aria-expanded', 'false')
            if selected:
                expect(page.locator('.selected-person')).to_contain_text(name)
                assert page.locator('body').get_attribute('data-accent') == accent
        page.goto(base + destination)
        if selected:
            page.evaluate('scrollTo(0,400)')
            assert abs(page.locator('.app-header').bounding_box()['y']) < 1
        button.click();assert_usable_menu(page, width, height)
        # Existing safe-area CSS variables allow a deterministic notch-boundary
        # rehearsal without pretending Chromium is physical iPhone Safari.
        panel.evaluate('(n)=>{n.style.setProperty("--menu-safe-left","44px");n.style.setProperty("--menu-safe-right","44px");}')
        assert_usable_menu(page, width, height)
        safe = panel.bounding_box()
        assert safe['x'] >= 44 and safe['x'] + safe['width'] <= width - 44
        panel.evaluate('(n)=>{n.style.removeProperty("--menu-safe-left");n.style.removeProperty("--menu-safe-right");}')
        # Reflow an already-open menu across portrait/landscape without new JS.
        rotated_width, rotated_height = (844, 390) if width < 768 else (390, 844)
        page.set_viewport_size({'width': rotated_width, 'height': rotated_height})
        assert_usable_menu(page, rotated_width, rotated_height)
        expect(button).to_have_attribute('aria-expanded', 'true')
        page.set_viewport_size({'width': width, 'height': height})
        button.click();expect(panel).to_be_hidden()
    assert errors == []
