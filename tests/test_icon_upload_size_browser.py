# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Chromium multipart uploads and accent rendering on disposable mobile pages.

Reuses the established loopback fixture. No server installation or live storage
is accessed; each test explicitly upgrades only its own temporary database.
"""
import pytest
from workout_tracker.migrations import migrate_storage
from workout_tracker.storage import database_session
from test_phase15 import ui_root, ui_data
from test_phase15_browser import ui_page, pw
from test_icon_upload_size import sized_svg


@pytest.mark.parametrize('viewport', [(320,844), (390,844), (844,390)])
@pytest.mark.parametrize('theme', ['light','dark'])
def test_large_independent_icons_upload_replace_reject_and_accent(ui_page, viewport, theme):
    """Touch-size forms accept both limits and retain artwork after rejected uploads."""
    page, base, x = ui_page
    migrate_storage(x['root'], 12)
    page.set_viewport_size(dict(zip(('width','height'), viewport)))
    page.goto(base + f"/settings?person_id={x['a']}")
    page.select_option('#theme', theme)
    page.locator('[name=accent][value=red]').check()
    page.get_by_role('button', name='Save accent color', exact=True).click()
    editor = base + f"/people/{x['a']}/exercises/{x['e']}/defaults"
    page.goto(editor)
    pw.expect(page.locator('.icon-manager')).to_contain_text('SVG only, up to 300 KiB per image.')
    for index, label in enumerate(('Start','End')):
        page.locator('input[type=file]').nth(index).set_input_files(dict(name='large.svg', mimeType='image/svg+xml', buffer=sized_svg(307200)))
        page.get_by_role('button', name=f'{"Replace" if index == 0 else "Upload"} {label} Position SVG', exact=True).click()
        pw.expect(page.get_by_role('button', name=f'Remove custom {label} Position SVG', exact=True)).to_be_visible()
        colored = page.locator(f'[data-icon-preview={label.lower()}] [fill="var(--accent)"]').first
        assert colored.evaluate('el=>getComputedStyle(el).fill').startswith('rgb(')
    page.locator('input[type=file]').first.set_input_files(dict(name='replacement.svg', mimeType='image/svg+xml', buffer=sized_svg(150 * 1024)))
    page.get_by_role('button', name='Replace Start Position SVG', exact=True).click()
    with database_session(x['root']) as db:
        before = [tuple(r) for r in db.execute('SELECT * FROM exercise_icons ORDER BY position')]
        assert sorted(len(r[2].encode()) for r in before) == [150 * 1024, 307200]
    page.locator('input[type=file]').first.set_input_files(dict(name='oversize.svg', mimeType='image/svg+xml', buffer=sized_svg(307201)))
    page.get_by_role('button', name='Replace Start Position SVG', exact=True).click()
    pw.expect(page.get_by_text('Icon unchanged: SVG must be at most 300 KiB per image.', exact=True)).to_be_visible()
    page.reload()
    with database_session(x['root']) as db:
        assert [tuple(r) for r in db.execute('SELECT * FROM exercise_icons ORDER BY position')] == before
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    # The same shared artwork inherits another person's independently chosen color.
    first_color = page.locator('[data-icon-preview=start] path').first.evaluate('el=>getComputedStyle(el).fill')
    page.goto(base + f"/people/{x['b']}/exercises/{x['e']}/defaults")
    second_color = page.locator('[data-icon-preview=start] path').first.evaluate('el=>getComputedStyle(el).fill')
    assert first_color != second_color
