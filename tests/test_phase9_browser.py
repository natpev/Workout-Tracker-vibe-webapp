# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Real Chromium Phase 9 navigation, defaults, normalized entry and palette review.

Fixtures use disposable schema 7 and loopback HTTP. No host updates or production
storage are touched. Browser requests retain the real CSRF/transaction workflow.
"""
import os
import shutil
from threading import Thread

import pytest
from werkzeug.serving import make_server
from workout_tracker import create_app,catalog as c,preferences
from workout_tracker.storage import database_session
from test_phase9 import phase9_root

pw=pytest.importorskip('playwright.sync_api')


@pytest.fixture
def phase9_browser(phase9_root):
    """Serve a real schema-7 instance with two people and a shared timed preset."""
    root=phase9_root
    with database_session(root,write=True) as db:
        a=c.create_person(db,'Alex');b=c.create_person(db,'Sam')
        r=c.create_routine(db,a,'Morning');other=c.create_routine(db,b,'Other')
        e=c.create_definition(db,a,'Plank',dict(measurement_type='time',target_sets='3',seconds='120'))
    app=create_app({'WORKOUT_DATA_ROOT':root,'WORKOUT_TIMEZONE':'America/Indiana/Indianapolis','TESTING':True})
    server=make_server('127.0.0.1',0,app,threaded=True);thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with pw.sync_playwright() as p:
            browser=p.chromium.launch(headless=True,executable_path=shutil.which('chromium'))
            page=browser.new_page(viewport={'width':390,'height':844})
            try:yield page,f'http://127.0.0.1:{server.server_port}',root,a,b,r,other,e
            finally:browser.close()
    finally:server.shutdown();thread.join(5);server.server_close()


def test_library_defaults_navigation_and_deletion_destinations(phase9_browser):
    """Shared defaults copy into independent routines; menu/tabs/deletion follow context."""
    page,base,root,a,b,r,other,e=phase9_browser;expect=pw.expect
    page.goto(base+f'/people/{a}/exercises')
    assert page.locator('.history-tabs').count()==0
    page.locator('.library-exercise').filter(has=page.get_by_role('heading',name='Plank',exact=True)).get_by_role('button').click()
    page.locator('.library-exercise').filter(has=page.get_by_role('heading',name='Plank',exact=True)).get_by_role('link',name='Edit Defaults',exact=True).click()
    page.get_by_label('Seconds',exact=True).fill('150');page.get_by_label('Minutes',exact=True).fill('3')
    page.get_by_role('button',name='Save changes',exact=True).click()
    for person,routine in ((a,r),(b,other)):
        page.goto(base+f'/people/{person}/routines/{routine}')
        page.select_option('#exercise-identity',e)
        page.get_by_role('button',name='Add library exercise',exact=True).click()
        expect(page.get_by_text('Time · 3 sets × 5 min 30 sec',exact=True)).to_be_visible()
    page.goto(base+f'/people/{a}/exercises')
    page.locator('.library-exercise').filter(has=page.get_by_role('heading',name='Plank',exact=True)).get_by_role('button').click()
    page.locator('.library-exercise').filter(has=page.get_by_role('heading',name='Plank',exact=True)).get_by_role('link',name='Edit Defaults',exact=True).click()
    page.get_by_label('Number of sets',exact=True).fill('5')
    page.get_by_role('button',name='Save changes',exact=True).click()
    with database_session(root) as db:
        assert [x[0] for x in db.execute('SELECT target_sets FROM routine_exercises')]==[3,3]
    page.get_by_role('button',name='Open navigation',exact=True).click()
    assert page.locator('#main-menu a').all_text_contents()==['Routines','Exercise Library','History & Progress','Settings']
    page.get_by_role('link',name='History & Progress',exact=True).click()
    expect(page.locator('.history-tabs a')).to_have_text(['History','Progress'])
    page.get_by_role('link',name='Progress',exact=True).click();page.go_back()
    expect(page.locator('header .selected-person')).to_contain_text('Alex')
    page.goto(base+f'/people/{a}/exercises')
    page.get_by_role('button',name='Actions for Plank',exact=True).click()
    page.get_by_role('link',name='Delete Exercise',exact=True).click()
    page.get_by_role('link',name='Cancel',exact=True).click()
    expect(page.get_by_role('heading',name='Exercise Library',exact=True)).to_be_visible()
    page.get_by_role('button',name='Actions for Plank',exact=True).click()
    page.get_by_role('link',name='Delete Exercise',exact=True).click()
    page.get_by_label('Type DELETE or Plank',exact=True).fill('DELETE');page.get_by_role('checkbox').check()
    page.get_by_role('button',name='Permanently Delete Exercise',exact=True).click()
    expect(page.get_by_role('heading',name='Exercise Library',exact=True)).to_be_visible()
    expect(page.get_by_role('status')).to_contain_text('Exercise permanently deleted')
    page.locator('.add-exercise summary').click()
    page.get_by_label('Exercise name',exact=True).fill('Plank')
    page.get_by_role('button',name='Add exercise name',exact=True).click()
    with database_session(root) as db:assert db.execute('SELECT id FROM exercises WHERE name=?',('Plank',)).fetchone()[0]!=e
    page.goto(base+f'/people/{a}/routines/{r}')
    page.get_by_role('link',name='Permanently Delete Routine',exact=True).click()
    page.get_by_label('Type DELETE or Morning',exact=True).fill('DELETE');page.get_by_role('checkbox').check()
    page.get_by_role('button',name='Permanently Delete Routine',exact=True).click()
    expect(page.get_by_role('heading',name='Ready for a workout?',exact=True)).to_be_visible()


def test_normalized_autosave_historical_labels_and_administration(phase9_browser):
    """Seconds-only autosave, manual entry and corrections all save normalized seconds."""
    page,base,root,a,b,r,other,e=phase9_browser;expect=pw.expect
    with database_session(root,write=True) as db:c.add_entry(db,a,r,dict(exercise_id=e,use_library_defaults='yes'))
    page.goto(base+f'/people/{a}/routines/{r}')
    page.get_by_role('button',name='Start workout',exact=True).click()
    page.get_by_label('Seconds',exact=True).fill('120')
    expect(page.locator('#save-status')).to_contain_text('Saved')
    expect(page.get_by_label('Minutes',exact=True)).to_have_value('2')
    expect(page.get_by_label('Seconds',exact=True)).to_have_value('0')
    page.get_by_role('button',name='Finish & Save',exact=True).click()
    expect(page.get_by_text('Plank — 02:00',exact=True)).to_be_visible()
    page.get_by_role('button',name='Open navigation',exact=True).click()
    page.get_by_role('link',name='History & Progress',exact=True).click()
    page.get_by_role('link',name='Plank',exact=True).count()  # Names remain in saved snapshots.
    page.get_by_role('link',name='Morning',exact=True).first.click()
    page.get_by_role('link',name='Correct saved workout',exact=True).click()
    assert page.get_by_label('Workout time (optional)',exact=True).get_attribute('type')=='text'
    page.get_by_label('Minutes',exact=True).fill('1');page.get_by_label('Seconds',exact=True).fill('90')
    page.get_by_label('I confirm these corrections and understand original records are retained',exact=True).check()
    page.get_by_role('button',name='Apply correction',exact=True).click()
    expect(page.locator('.measurement')).to_have_text('02:30')
    page.goto(base+f'/settings?person_id={a}')
    assert page.get_by_role('button',name='Backup Now',exact=True).count()==0
    page.get_by_role('link',name='Open Administration',exact=True).click()
    expect(page.get_by_role('heading',name='Administration',exact=True)).to_be_visible()
    expect(page.locator('header .selected-person')).to_contain_text('Alex')
    assert page.locator('input[type=password]').count()==0
    page.get_by_role('button',name='Backup Now',exact=True).click()
    expect(page.locator('#backup-status')).to_have_text('verified')


def test_twelve_preserved_colors_contrast_and_compact_layout(phase9_browser):
    """Actual rendered palettes maintain readable button contrast on phone and desktop."""
    page,base,root,a,b,r,other,e=phase9_browser
    for width in (320,1280):
        page.set_viewport_size({'width':width,'height':844})
        for theme in ('light','dark','auto'):
            page.goto(base+f'/settings?person_id={a}');page.select_option('#theme',theme)
            assert page.locator('[name=accent]').count()==12
            for color in preferences.PALETTE:
                preferences.set_color(root,a,color);page.reload()
                assert page.locator('body').get_attribute('data-accent')==color
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                contrast=page.get_by_role('button',name='Save accent color',exact=True).evaluate('''el=>{
                  const s=getComputedStyle(el),lum=c=>c.match(/[0-9.]+/g).slice(0,3).map(Number).map(x=>x/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4).reduce((s,x,i)=>s+x*[.2126,.7152,.0722][i],0);
                  const a=lum(s.color),b=lum(s.backgroundColor);return (Math.max(a,b)+.05)/(Math.min(a,b)+.05);
                }''')
                assert contrast>=4.5,(color,theme,contrast)
