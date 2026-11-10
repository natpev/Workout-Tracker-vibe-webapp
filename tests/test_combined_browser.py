# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Real Chromium combined forms, acknowledgments, history, graphs and download.

Loopback HTTP and disposable schema 8 exercise the complete browser-to-SQL path.
No production source, host updater deployment or real workout data is involved.
"""
import csv
from io import StringIO
import os
import shutil
from threading import Thread
import pytest
from werkzeug.serving import make_server
from workout_tracker import create_app, catalog as c, history as h
from workout_tracker.storage import database_session
from test_combined import phase11_root, phase9_root, seed
from test_phase8_deletion import manual
pw=pytest.importorskip('playwright.sync_api')


@pytest.fixture
def combined_page(phase11_root):
    """Open a local app with prior paired performance and one later skipped row."""
    root=phase11_root
    with database_session(root,write=True) as db:
        a,b,r,e,item=seed(db)
        c.add_entry(db,a,r,dict(name='Plank',measurement_type='time',target_sets='1',seconds='45'))
        saved,_=manual(db,a,r,'2020-01-01',weight_0='20',seconds_0='360',increase_0='1')
    server=make_server('127.0.0.1',0,create_app({'WORKOUT_DATA_ROOT':root,'WORKOUT_TIMEZONE':'UTC'}),threaded=True)
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with pw.sync_playwright() as manager:
            browser=manager.chromium.launch(headless=True,executable_path=os.environ.get('WORKOUT_CHROMIUM') or shutil.which('chromium'))
            try:
                page=browser.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
                page.on('dialog',lambda dialog:dialog.accept())
                yield page,f'http://127.0.0.1:{server.server_port}',root,a,b,r,e,item,saved
            finally:browser.close()
    finally:server.shutdown();thread.join(5);server.server_close()


@pytest.mark.parametrize('width',[320,390,1280])
def test_combined_config_autosave_navigation_history_charts_and_csv(combined_page,tmp_path,width):
    """Both inputs share the screen; partial pairs fail inline and never raise progress."""
    page,base,root,a,b,r,e,item,saved=combined_page;expect=pw.expect
    page.set_viewport_size({'width':width,'height':844});errors=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto(base+f'/people/{a}/exercises/{e}/defaults')
    expect(page.get_by_role('radio',name='Weight + Duration',exact=True)).to_be_checked()
    expect(page.get_by_label('Target repetitions per set')).to_be_disabled()
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.get_by_label('Minutes',exact=True).fill('7')
    page.get_by_role('button',name='Save changes',exact=True).click()
    with database_session(root) as db:assert c.entry(db,a,r,item)['target_duration_seconds']==360
    page.goto(base+f'/people/{a}/routines/{r}/items/{item}')
    expect(page.get_by_label('Minutes',exact=True)).to_have_value('6')
    page.get_by_label('Number of sets',exact=True).fill('2')
    page.get_by_role('button',name='Save exercise settings',exact=True).click()
    page.get_by_role('button',name='Start workout',exact=True).click()
    path=page.url
    expect(page.get_by_label('Weight (lb)',exact=True)).to_have_value('')
    expect(page.get_by_label('Minutes',exact=True)).to_have_value('')
    expect(page.locator('.previous-line')).to_contain_text('20.0 lb per hand · 6:00')
    expect(page.get_by_text('Increase ↑',exact=True)).to_be_visible()
    expect(page.get_by_label('Increase duration next time',exact=True)).to_have_count(0)
    page.get_by_label('Weight (lb)',exact=True).fill('0')
    expect(page.locator('#minutes-error')).to_contain_text('both weight')
    expect(page.get_by_label('Minutes',exact=True)).to_have_attribute('aria-invalid','true')
    expect(page.locator('#workout-progress')).to_have_attribute('value','0')
    page.get_by_label('Seconds',exact=True).fill('90')
    expect(page.locator('#save-status')).to_have_text('✓ Saved')
    expect(page.get_by_label('Minutes',exact=True)).to_have_value('1')
    expect(page.get_by_label('Seconds',exact=True)).to_have_value('30')
    page.get_by_label('Increase weight next time',exact=True).check()
    expect(page.locator('#save-status')).to_have_text('✓ Saved')
    expect(page.locator('#workout-progress')).to_have_attribute('value','0')
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.reload();expect(page.get_by_label('Weight (lb)',exact=True)).to_have_value('0.0')
    page.get_by_role('link',name='Next',exact=True).click()
    expect(page.get_by_role('heading',name='Plank',exact=True)).to_be_visible()
    expect(page.locator('#workout-progress')).to_have_attribute('value','1')
    page.get_by_role('link',name='Back',exact=True).click()
    expect(page.get_by_label('Weight (lb)',exact=True)).to_have_value('0.0')
    expect(page.locator('#workout-progress')).to_have_attribute('value','1')
    page.get_by_role('button',name='Finish & Save',exact=True).click()
    expect(page.get_by_role('heading',name='Workout saved',exact=True)).to_be_visible()
    assert '0.0 lb per hand · 1:30' in page.locator('body').inner_text()
    for theme in ('light','dark','auto'):
        page.goto(base+f'/settings?person_id={a}');page.select_option('#theme',theme)
        page.goto(base+f'/people/{a}/progress?range=all&exercise={e}')
        expect(page.locator('.combined-progress')).to_have_count(1)
        expect(page.locator('.combined-progress .progress-chart')).to_have_count(2)
        expect(page.locator('.chart-target')).to_have_count(1)
        for point in page.locator('.chart-point').all():
            point.scroll_into_view_if_needed();point.tap()
            tip=point.locator('xpath=ancestor::section[1]').locator('[data-chart-tooltip]')
            expect(tip).to_be_visible();assert point.get_attribute('data-tooltip') in tip.inner_text()
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.get_by_text('CSV export — choose exercises',exact=True).click()
    page.locator(f'[name=export_exercise][value="{e}"]').check()
    with page.expect_download() as download:page.get_by_role('button',name='Export CSV',exact=True).click()
    file=tmp_path/'combined.csv';download.value.save_as(file)
    data=list(csv.reader(StringIO(file.read_text(encoding='utf-8-sig'))))
    assert len(data[0])==7 and data[-1][4:]==['0','1:30','2 × 6:00']
    assert not errors


@pytest.mark.parametrize('width',[320,1280])
def test_historical_partial_pair_errors_correction_and_originals(combined_page,width):
    """Paired historical values and corrections keep raw input and immutable originals."""
    page,base,root,a,b,r,e,item,saved=combined_page;expect=pw.expect
    page.set_viewport_size({'width':width,'height':844})
    page.goto(base+f'/people/{a}/historical')
    page.get_by_label('Workout date',exact=True).fill('2020-01-02')
    page.get_by_role('button',name='Prepare historical workout',exact=True).click()
    group=page.get_by_role('group',name='Weighted carry',exact=True)
    group.get_by_label('Weight (lb)',exact=True).fill('25.99')
    page.get_by_role('button',name='Save historical workout',exact=True).click()
    expect(group.locator('#minutes_0')).to_have_attribute('aria-invalid','true')
    expect(group.get_by_label('Weight (lb)',exact=True)).to_have_value('25.99')
    group.locator('#seconds_0').fill('285')
    page.get_by_role('button',name='Save historical workout',exact=True).click()
    expect(page.locator('.measurement').first).to_have_text('25.9 lb per hand · 4:45')
    page.get_by_role('link',name='Correct saved workout',exact=True).click()
    group=page.get_by_role('group',name='Weighted carry',exact=True)
    group.get_by_label('Weight (lb)',exact=True).fill('30.99')
    group.locator('#minutes_0').fill('6');group.locator('#seconds_0').fill('0')
    page.get_by_label('I confirm these corrections and understand original records are retained').check()
    page.get_by_role('button',name='Apply correction',exact=True).click()
    expect(page.locator('.measurement').first).to_have_text('30.9 lb per hand · 6:00')
    page.get_by_text('Original saved values',exact=True).click()
    expect(page.get_by_text('Weighted carry — 25.9 lb per hand · 4:45',exact=True)).to_be_visible()
    expect(page.locator('.audit-record')).to_have_count(1)
    with database_session(root) as db:
        audits=db.execute('SELECT after_json FROM workout_corrections').fetchall()
        assert len(audits)==1 and '309' in audits[0][0] and '360' in audits[0][0]


def test_create_library_combined_and_copy_defaults_via_forms(combined_page):
    """Library creation and Add Library exercise copy the selected mode/targets once."""
    page,base,root,a,b,r,e,item,saved=combined_page;expect=pw.expect
    page.goto(base+f'/people/{a}/exercises')
    form=page.locator('form[data-configuration]')
    form.get_by_label('Exercise name',exact=True).fill('Weighted dead hang')
    form.get_by_role('radio',name='Weight + Duration',exact=True).check()
    form.get_by_label('Number of sets',exact=True).fill('2')
    form.get_by_label('Minutes',exact=True).fill('0');form.get_by_label('Seconds',exact=True).fill('90')
    form.get_by_label('Weight meaning (optional)',exact=True).fill('total weight')
    form.get_by_role('button').last.click()
    with database_session(root) as db:
        definition=db.execute("SELECT id FROM exercises WHERE name='Weighted dead hang'").fetchone()[0]
    page.goto(base+f'/people/{a}/routines/{r}')
    page.locator('#exercise-identity').select_option(definition)
    page.get_by_role('button',name='Add library exercise',exact=True).click()
    with database_session(root) as db:
        row=db.execute('SELECT * FROM routine_exercises WHERE exercise_id=? AND routine_id=?',(definition,r)).fetchone()
        assert (row['measurement_type'],row['target_sets'],row['target_duration_seconds'],row['weight_meaning'])==('weight_duration',2,90,'total weight')
