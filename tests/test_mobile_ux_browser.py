# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Rendered mobile UX/viewport evidence with disposable schema-4 households.

Real browser forms verify exit/resume, menus and persistent accents. Screenshots
are review artifacts, never synthetic mockups. Reduced-height keyboard tests are
simulations; no claim of an actual iOS Safari/hardware-keyboard run is made.
"""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from threading import Thread

import pytest
from werkzeug.serving import make_server
from workout_tracker import create_app,history as h,workouts as w,preferences as p
from workout_tracker.storage import database_session
from test_mobile_ux import seed

pw=pytest.importorskip('playwright.sync_api')
SHOTS=Path(os.environ.get('WORKOUT_UX_SCREENSHOTS',str(Path(tempfile.gettempdir())/'workout-ux-screenshots')))
BASELINE='2be4c740749f4d2923583321a40271859c13f79e'


@pytest.fixture
def ux_browser(phase4_root):
    """Serve synthetic corrected previous performance and two independent people."""
    root=phase4_root;a,b,routine=seed(root)
    with database_session(root,write=True) as db:
        form=h.prepare(db,a,routine,dict(workout_date='2020-01-01',workout_time=''),'UTC')
        prior=h.complete_historical(db,a,form,dict(weight_0='40.99',increase_0='1',minutes_1='0',seconds_1='45'))
        h.correct(db,a,prior,dict(confirm='yes',correction_revision='0',workout_date='2020-01-02',workout_time='',weight_0='42.56',increase_0='1',minutes_1='0',seconds_1='45'))
    server=make_server('127.0.0.1',0,create_app({'WORKOUT_DATA_ROOT':root,'WORKOUT_TIMEZONE':'UTC','TESTING':True}))
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with pw.sync_playwright() as manager:
            browser=manager.chromium.launch(headless=True,executable_path=os.environ.get('WORKOUT_CHROMIUM') or shutil.which('chromium'))
            context=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,device_scale_factor=1)
            page=context.new_page();page.on('dialog',lambda dialog:dialog.accept())
            try: yield page,browser,f'http://127.0.0.1:{server.server_port}',root,a,b,routine
            finally: browser.close()
    finally: server.shutdown();thread.join(5);server.server_close()


def choose_person_color(page,base,name,color):
    """Use the actual People disclosure and Settings form to persist one person's accent."""
    page.goto(base+'/people')
    page.get_by_role('button',name='Menu for '+name,exact=True).click()
    page.get_by_role('link',name='Person appearance',exact=True).click()
    page.get_by_role('radio',name='Soft '+color.title(),exact=True).check()
    page.get_by_role('button',name='Save accent color',exact=True).click()
    assert page.locator('body').get_attribute('data-accent')==color


def test_complete_person_routine_workout_exit_switch_resume_and_history(ux_browser):
    """Full one-handed workflow keeps draft data, corrected previous values and ownership."""
    page,browser,base,root,a,b,routine=ux_browser;expect=pw.expect;errors=[]
    page.on('pageerror',lambda error:errors.append(str(error)));SHOTS.mkdir(parents=True,exist_ok=True)
    page.goto(base+'/');expect(page.get_by_role('heading',name='Who’s working out?',exact=True)).to_be_visible()
    assert 'SHAMELESSLY VIBE-CODED' not in page.locator('body').inner_text()
    expect(page.locator('#theme')).to_have_count(0)
    assert page.locator('.person-card').first.bounding_box()['y']<page.locator('.add-person').bounding_box()['y']
    menu=page.get_by_role('button',name='Menu for Alex',exact=True);original=page.url;menu.click()
    expect(menu).to_have_attribute('aria-expanded','true');assert page.url==original
    page.keyboard.press('Escape');expect(menu).to_have_attribute('aria-expanded','false');expect(menu).to_be_focused()
    menu.press('ArrowDown');expect(page.get_by_role('link',name='Manage routines',exact=True)).to_be_focused()
    page.keyboard.press('Escape');menu.click();page.get_by_role('heading',name='Who’s working out?',exact=True).click()
    expect(menu).to_have_attribute('aria-expanded','false')
    choose_person_color(page,base,'Alex','purple');choose_person_color(page,base,'Sam','teal')
    page.goto(base+'/people');page.screenshot(path=str(SHOTS/'people-390x844-light.png'),full_page=True)
    page.get_by_role('link',name='Alex',exact=True).click()
    expect(page.locator('body')).to_have_attribute('data-accent','purple')
    page.get_by_role('button',name='Start workout',exact=True).click()
    path=page.url
    expect(page.get_by_label('Weight (lb)')).to_have_value('')
    expect(page.get_by_text('Previous session:',exact=False)).to_contain_text('42.5 lb')
    expect(page.get_by_text('Increase ↑',exact=True)).to_be_visible()
    expect(page.get_by_role('button',name='Open navigation')).to_have_count(0)
    page.get_by_label('Weight (lb)').fill('40.99')
    page.get_by_role('link',name='Next',exact=True).click()
    page.get_by_label('Minutes').fill('0');page.get_by_label('Seconds').fill('55')
    page.get_by_role('link',name='Back',exact=True).click()
    expect(page.get_by_label('Weight (lb)')).to_have_value('40.9')
    page.get_by_role('button',name='Save draft',exact=True).click();page.reload()
    expect(page.get_by_label('Weight (lb)')).to_have_value('40.9')
    # Attempting browser Back to routine selection cannot offer person switching
    # while this tab remains in its active workout flow.
    page.go_back();expect(page.get_by_label('Weight (lb)')).to_be_visible()
    separate=browser.new_context();other=separate.new_page();other.goto(base+'/people')
    other.get_by_role('link',name='Sam',exact=True).click();expect(other.locator('body')).to_have_attribute('data-accent','teal')
    separate.close()
    page.get_by_label('Weight (lb)').fill('42.56')
    page.get_by_text('More',exact=True).click();page.get_by_role('button',name='Exit Workout',exact=True).click()
    expect(page.get_by_role('heading',name='Ready for a workout?',exact=True)).to_be_visible()
    page.get_by_role('button',name='Open navigation',exact=True).click();page.locator('a.brand').click()
    page.get_by_role('link',name='Sam',exact=True).click();expect(page.locator('body')).to_have_attribute('data-accent','teal')
    page.goto(base+'/people');page.get_by_role('link',name='Alex',exact=True).click()
    page.get_by_role('link',name='Resume or discard unfinished workout',exact=True).click()
    page.get_by_role('link',name='Resume workout',exact=True).click()
    # Resume uses the persisted Next checkpoint, even after revisiting Bench.
    # Verify both saved actuals, and that Back cannot create extra progress.
    expect(page.locator('#workout-progress')).to_have_attribute('value','1')
    expect(page.get_by_label('Seconds')).to_have_value('55')
    page.get_by_role('link',name='Back',exact=True).click()
    expect(page.get_by_label('Weight (lb)')).to_have_value('42.5')
    expect(page.locator('#workout-progress')).to_have_attribute('value','1')
    page.get_by_role('link',name='Next',exact=True).click()
    expect(page.get_by_label('Seconds')).to_have_value('55')
    page.get_by_role('button',name='Finish & Save',exact=True).click()
    expect(page.get_by_role('heading',name='Workout saved',exact=True)).to_be_visible()
    page.get_by_role('button',name='Open navigation',exact=True).click()
    page.get_by_role('link',name='History & Progress',exact=True).click();expect(page.locator('.history-record')).to_have_count(2)
    page.screenshot(path=str(SHOTS/'history-390x844-light.png'),full_page=True)
    page.get_by_role('link',name='Progress',exact=True).click()
    page.get_by_role('button',name='All Time',exact=True).click();expect(page.locator('.progress-series')).to_have_count(2)
    page.screenshot(path=str(SHOTS/'progress-390x844-light.png'),full_page=True)
    with database_session(root) as db:
        assert w.active(db,a) is None
        assert db.execute('SELECT actual_weight_tenths_lb FROM workout_entries WHERE measurement_type="weight"').fetchone()[0]==425
        assert db.execute('SELECT count(*) FROM workout_corrections').fetchone()[0]==1
    assert not errors


def test_failed_exit_remains_on_input_and_native_back_retains_confirmed_draft(ux_browser):
    """Failed acknowledgment cannot navigate away or label unsaved text as persisted."""
    page,_,base,root,a,_,_=ux_browser;expect=pw.expect
    page.goto(base+'/people/'+a);page.get_by_role('button',name='Start workout',exact=True).click()
    path=page.url;page.get_by_label('Weight (lb)').fill('0');expect(page.locator('#save-status')).to_have_text('✓ Saved')
    page.route('**/draft',lambda route:route.abort())
    page.get_by_label('Weight (lb)').fill('99');expect(page.locator('#save-status')).to_have_text('Save failed')
    page.get_by_text('More',exact=True).click();page.get_by_role('button',name='Exit Workout',exact=True).click()
    assert page.url==path;expect(page.get_by_label('Weight (lb)')).to_have_value('99')
    expect(page.locator('#save-error')).to_contain_text('Stay here')
    with database_session(root) as db: assert db.execute('SELECT actual_weight_tenths_lb FROM workout_entries WHERE measurement_type="weight"').fetchone()[0]==0
    page.unroute('**/draft');page.get_by_label('Weight (lb)').fill('42')
    expect(page.locator('#save-status')).to_have_text('✓ Saved');page.go_back()
    expect(page.get_by_label('Weight (lb)')).to_have_value('42.0')


def test_viewport_theme_accent_matrix_and_keyboard_reachability(ux_browser):
    """Capture actual rendered phones/tablet/desktop and check essential bounds/contrast."""
    page,_,base,root,a,_,_=ux_browser;expect=pw.expect;SHOTS.mkdir(parents=True,exist_ok=True)
    page.goto(base+'/people/'+a);page.get_by_role('button',name='Start workout',exact=True).click()
    viewports=[(320,568),(375,667),(390,844),(430,932),(768,1024),(1280,900)]
    for index,(width,height) in enumerate(viewports):
        color=p.PALETTE[index];p.set_color(root,a,color)
        for theme in ('light','dark'):
            page.evaluate('(choice)=>localStorage.setItem("workout-theme",choice)',theme)
            page.set_viewport_size({'width':width,'height':height});page.reload()
            expect(page.locator('body')).to_have_attribute('data-accent',color)
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            assert page.locator('#theme').count()==0
            for label in ('Next','Save draft','Finish & Save'):
                control=page.get_by_role('link' if label=='Next' else 'button',name=label,exact=True)
                bounds=control.bounding_box();assert bounds['height']>=44 and bounds['x']>=0 and bounds['x']+bounds['width']<=width
                if (width,height)==(390,844): assert bounds['y']+bounds['height']<=height
            if theme=='dark':
                rgb=page.evaluate('getComputedStyle(document.body).backgroundColor')
                assert rgb=='rgb(17, 21, 31)'
            # Derive WCAG contrast from the actual rendered primary button colors.
            contrast=page.get_by_role('button',name='Finish & Save',exact=True).evaluate('''el=>{
              const style=getComputedStyle(el);
              const lum=c=>c.match(/[0-9.]+/g).slice(0,3).map(Number).map(x=>x/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4).reduce((sum,x,i)=>sum+x*[.2126,.7152,.0722][i],0);
              const a=lum(style.color),b=lum(style.backgroundColor);return (Math.max(a,b)+.05)/(Math.min(a,b)+.05);
            }''')
            assert contrast>=4.5,(theme,color,contrast)
            page.screenshot(path=str(SHOTS/f'workout-{width}x{height}-{theme}-{color}.png'),full_page=True)
    p.set_color(root,a,'purple')
    page.set_viewport_size({'width':390,'height':844});page.reload()
    page.get_by_role('link',name='Next',exact=True).click()
    expect(page.get_by_label('Minutes')).to_have_value('')
    assert page.get_by_role('button',name='Finish & Save',exact=True).bounding_box()['y']<844
    page.screenshot(path=str(SHOTS/'time-390x844-dark-purple.png'),full_page=True)
    page.get_by_role('link',name='Back',exact=True).click()
    page.set_viewport_size({'width':390,'height':420})
    page.get_by_label('Weight (lb)').focus()
    page.get_by_role('link',name='Next',exact=True).scroll_into_view_if_needed()
    assert page.get_by_role('link',name='Next',exact=True).bounding_box()['y']<420
    page.get_by_role('button',name='Finish & Save',exact=True).scroll_into_view_if_needed()
    assert page.get_by_role('button',name='Finish & Save',exact=True).bounding_box()['y']<420
    page.screenshot(path=str(SHOTS/'workout-390x420-keyboard-simulation.png'))
    page.evaluate('document.documentElement.style.fontSize="20px"')
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.get_by_role('button',name='Finish & Save',exact=True).scroll_into_view_if_needed()
    assert page.get_by_role('button',name='Finish & Save',exact=True).is_visible()


def test_baseline_and_settings_screenshot_evidence(ux_browser,tmp_path):
    """Render main's old assets as a visual baseline; inspect new Settings on real browser."""
    page,_,base,root,a,_,routine=ux_browser;SHOTS.mkdir(parents=True,exist_ok=True)
    with database_session(root,write=True) as db: identity,_=w.start(db,a,routine,'UTC')
    original=tmp_path/'baseline';(original/'templates').mkdir(parents=True);(original/'static').mkdir()
    repo=Path(__file__).resolve().parents[1]
    files=subprocess.run(['git','ls-tree','-r','--name-only',BASELINE,'workout_tracker/templates','workout_tracker/static'],cwd=repo,capture_output=True,text=True,check=True).stdout.splitlines()
    for source in files:
        if source.endswith(('.html','.js','.css')):
            relative=Path(source).relative_to('workout_tracker');target=original/relative;target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(subprocess.run(['git','show',BASELINE+':'+source],cwd=repo,capture_output=True,check=True).stdout)
    app=create_app({'WORKOUT_DATA_ROOT':root,'WORKOUT_TIMEZONE':'UTC','TESTING':True})
    app.template_folder=str(original/'templates');app.static_folder=str(original/'static')
    server=make_server('127.0.0.1',0,app);thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        page.goto(f'http://127.0.0.1:{server.server_port}/people/{a}/workouts/{identity}')
        page.select_option('#theme','dark');page.screenshot(path=str(SHOTS/'before-390x844-dark.png'),full_page=True)
    finally: server.shutdown();thread.join(5);server.server_close()
    page.goto(base+f'/settings?person_id={a}')
    page.select_option('#theme','dark');page.screenshot(path=str(SHOTS/'settings-390x844-dark.png'),full_page=True)
