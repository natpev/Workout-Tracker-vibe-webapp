# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Real Chromium checks schema-11 draft entry, SVG coloring and mobile layouts."""
import os
import shutil
from threading import Thread
import pytest
from werkzeug.serving import make_server
from workout_tracker import create_app,workouts as w,exercise_icons as icons
from workout_tracker.storage import database_session
from test_phase15 import ui_root,ui_data,SVG
pw=pytest.importorskip('playwright.sync_api')

@pytest.fixture
def ui_page(ui_data):
    x=ui_data
    with database_session(x['root'],write=True) as db:
        draft,_=w.start(db,x['a'],x['r'],'UTC');x['draft']=draft
        icons.update(db,x['e'],'start',SVG)
    server=make_server('127.0.0.1',0,create_app({'WORKOUT_DATA_ROOT':x['root']}),threaded=True)
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with pw.sync_playwright() as manager:
            browser=manager.chromium.launch(headless=True,executable_path=os.environ.get('WORKOUT_CHROMIUM') or shutil.which('chromium'))
            try:yield browser.new_page(),f'http://127.0.0.1:{server.server_port}',x
            finally:browser.close()
    finally:server.shutdown();thread.join(5);server.server_close()

@pytest.mark.parametrize('viewport',[(390,844),(844,390),(1280,900)])
@pytest.mark.parametrize('theme',['light','dark'])
def test_blank_partial_resume_focus_and_recorded_zero(ui_page,viewport,theme):
    page,base,x=ui_page;expect=pw.expect
    page.set_viewport_size(dict(zip(('width','height'),viewport)))
    page.goto(base+f"/settings?person_id={x['a']}");page.select_option('#theme',theme)
    url=base+f"/people/{x['a']}/workouts/{x['draft']}";page.goto(url)
    if viewport==(390,844) and theme=='light':page.screenshot(path='/tmp/phase15-workout.png',full_page=True)
    expect(page.locator('[name=weight]')).to_be_focused()
    expect(page.locator('[data-actual-reps]')).to_have_count(3)
    for field in page.locator('[data-actual-reps]').all():expect(field).to_have_value('')
    page.locator('[name=weight]').fill('40');page.locator('[name=weight]').press('Enter')
    expect(page.locator('[name=reps_0]')).to_be_focused()
    page.locator('[name=reps_0]').fill('0');expect(page.locator('#save-status')).to_have_text('✓ Saved')
    expect(page.locator('[name=reps_0]')).to_be_focused()
    expect(page.locator('[name=reps_0]').locator('..')).to_contain_text('Recorded')
    page.reload();expect(page.locator('[name=reps_0]')).to_have_value('0');expect(page.locator('[name=reps_1]')).to_have_value('')
    page.get_by_role('link',name='Next',exact=True).click()
    expect(page.locator('#save-error')).to_be_visible()
    expect(page.locator('[name=reps_0]')).to_have_value('0')
    page.locator('[name=reps_1]').fill('10');page.locator('[name=reps_2]').fill('12')
    expect(page.locator('#save-status')).to_have_text('✓ Saved')
    page.get_by_role('link',name='Next',exact=True).click();page.get_by_role('link',name='Back',exact=True).click()
    expect(page.locator('[name=reps_1]')).to_have_value('10')
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')


@pytest.mark.parametrize('theme',['light','dark'])
def test_collapsed_creation_and_actual_inline_accent_recolor(ui_page,theme):
    page,base,x=ui_page;expect=pw.expect;colors=[]
    for person,color in ((x['a'],'red'),(x['b'],'blue')):
        # Theme preferences use the same browser and selected-person context.
        page.goto(base+f'/settings?person_id={person}')
        page.select_option('#theme',theme)
        page.locator(f'[name=accent][value={color}]').check()
        page.get_by_role('button',name='Save accent color',exact=True).click()
        page.goto(base+f'/people/{person}/exercises')
        expect(page.locator('.add-exercise')).not_to_have_attribute('open','')
        page.locator('.add-exercise summary').click();expect(page.locator('.add-exercise [name=name]')).to_be_visible()
        page.locator('.add-exercise summary').click()
        svg=page.locator('.exercise-icons svg').first
        colors.append(svg.locator('[fill="var(--accent)"]').first.evaluate('el=>getComputedStyle(el).fill'))
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert colors[0]!=colors[1]


def test_confirmed_plank_correction_and_independent_icon_management(ui_page):
    page,base,x=ui_page;expect=pw.expect
    editor=base+f"/people/{x['a']}/exercises/{x['e']}/defaults"
    page.goto(editor)
    expect(page.locator('[data-icon-preview=start] svg')).to_have_count(1)
    page.locator('input[type=file]').nth(1).set_input_files(dict(name='end.svg',mimeType='image/svg+xml',buffer=SVG.encode()))
    page.get_by_role('button',name='Upload End Position SVG',exact=True).click()
    expect(page.get_by_role('button',name='Remove custom End Position SVG',exact=True)).to_be_visible()
    page.get_by_role('button',name='Remove custom Start Position SVG',exact=True).click()
    expect(page.get_by_role('button',name='Upload Start Position SVG',exact=True)).to_be_visible()
    expect(page.get_by_role('button',name='Remove custom End Position SVG',exact=True)).to_be_visible()
    page.get_by_role('radio',name='Time',exact=True).check()
    page.get_by_role('button',name='Save Defaults Only',exact=True).click()
    expect(page.get_by_role('heading',name='Change Plank from Weight to Duration?',exact=True)).to_be_visible()
    page.get_by_role('checkbox').check()
    page.get_by_role('button',name='Confirm measurement-type correction',exact=True).click()
    with database_session(x['root']) as db:
        assert db.execute('SELECT measurement_type FROM exercise_defaults WHERE exercise_id=?',(x['e'],)).fetchone()[0]=='time'
        assert w.entries(db,x['a'],x['draft'])[0]['measurement_type']=='weight'
