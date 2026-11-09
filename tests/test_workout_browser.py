# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""Chromium exercises browser -> autosave -> Flask -> disposable SQLite flows.

A loopback-only test server uses a temporary schema-3 fixture. Network faults and
held responses check acknowledgments, conflicts and typing during pending saves.
"""

import os
import shutil
from threading import Thread

import pytest
from werkzeug.serving import make_server

from workout_tracker import create_app, catalog as c
from workout_tracker.storage import database_session

pw=pytest.importorskip('playwright.sync_api')


@pytest.fixture
def workout_page(phase3_root):
    """Serve one synthetic person's mixed routine and open a new blank workout."""
    with database_session(phase3_root,write=True) as db:
        person=c.create_person(db,'Browser fixture')
        routine=c.create_routine(db,person,'Mixed workout')
        c.add_entry(db,person,routine,dict(name='Bench',measurement_type='weight',target_sets='3',target_reps='12'))
        c.add_entry(db,person,routine,dict(name='Plank',measurement_type='time',target_sets='3',minutes='0',seconds='45'))
    server=make_server('127.0.0.1',0,create_app({'WORKOUT_DATA_ROOT':phase3_root,'WORKOUT_TIMEZONE':'America/Indiana/Indianapolis'}))
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with pw.sync_playwright() as manager:
            browser=manager.chromium.launch(headless=True,executable_path=os.environ.get('WORKOUT_CHROMIUM') or shutil.which('chromium'))
            try:
                context=browser.new_context(viewport={'width':320,'height':800})
                page=context.new_page()
                page.on('dialog',lambda dialog:dialog.accept())
                address=f'http://127.0.0.1:{server.server_port}'
                routine_path=f'/people/{person}/routines/{routine}'
                page.goto(address+routine_path)
                page.get_by_role('button',name='Start workout',exact=True).click()
                yield page,address+routine_path,phase3_root
            finally:
                browser.close()
    finally:
        server.shutdown();thread.join(timeout=5);server.server_close()


def test_workout_autosave_navigation_recovery_finish_and_themes(workout_page):
    """Real input truncates, saves, resumes, navigates and finishes with pending data."""
    page,routine_path,root=workout_page;expect=pw.expect
    expect(page.get_by_label('Weight (lb)')).to_have_value('')
    expect(page.locator('#workout-progress')).to_have_attribute('value','0')
    page.get_by_label('Weight (lb)').fill('40.99')
    page.get_by_label('Increase weight next time',exact=True).check()
    expect(page.get_by_label('Weight (lb)')).to_have_value('40.9')
    expect(page.locator('#save-status')).to_have_text('✓ Saved')
    expect(page.locator('#workout-progress')).to_have_attribute('value','0')
    page.get_by_text('More',exact=True).click()
    page.get_by_text('Workout overview',exact=True).click()
    expect(page.locator('[data-entry-state]').first).to_have_text('40.9 lb')
    page.reload()
    expect(page.get_by_label('Weight (lb)')).to_have_value('40.9')
    page.get_by_role('link',name='Next',exact=True).click()
    expect(page.get_by_role('heading',name='Plank',exact=True)).to_be_visible()
    expect(page.get_by_label('Minutes')).to_have_value('')
    expect(page.locator('#workout-progress')).to_have_attribute('value','1')
    page.get_by_label('Minutes').fill('1')
    expect(page.get_by_label('Seconds')).to_have_value('0')
    page.get_by_label('Seconds').fill('-1')
    expect(page.locator('#save-error')).to_contain_text('Not saved:')
    page.get_by_label('Seconds').fill('5')
    expect(page.locator('#save-status')).to_have_text('✓ Saved')
    expect(page.locator('#workout-progress')).to_have_attribute('value','1')
    page.get_by_text('More',exact=True).click()
    page.select_option('#exercise-jump','0')
    expect(page.get_by_role('heading',name='Bench',exact=True)).to_be_visible()
    page.get_by_text('More',exact=True).click()
    page.select_option('#exercise-jump','1')
    expect(page.get_by_role('heading',name='Plank',exact=True)).to_be_visible()
    # Appearance now lives in Settings; no selector competes with workout controls.
    expect(page.locator('#theme')).to_have_count(0)
    for width in (320,768,1280):
        page.set_viewport_size({'width':width,'height':800})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.get_by_label('Seconds').focus()
    assert page.get_by_label('Seconds').evaluate('element=>element===document.activeElement')
    # Immediate Finish must flush the most recent edit before atomic completion.
    page.get_by_label('Seconds').fill('6')
    page.get_by_role('button',name='Finish & Save',exact=True).click()
    expect(page.get_by_role('heading',name='Workout saved',exact=True)).to_be_visible()
    expect(page.get_by_text('Plank — 01:06',exact=True)).to_be_visible()
    with database_session(root) as db:
        assert db.execute("SELECT status FROM workout_sessions").fetchone()[0]=='completed'
        assert db.execute("SELECT actual_duration_seconds FROM workout_entries WHERE measurement_type='time'").fetchone()[0]==66
    page.goto(routine_path)
    page.get_by_role('button',name='Start workout',exact=True).click()
    expect(page.get_by_label('Weight (lb)')).to_have_value('')
    expect(page.get_by_text('Increase ↑',exact=True)).to_be_visible()
    expect(page.get_by_text('Previous session:',exact=False)).to_contain_text('40.9 lb')


def test_discard_cancel_ok_and_all_skipped_confirmation(workout_page):
    """Skipped Next advances navigation; Cancel retains draft; OK needs acknowledgment."""
    page,routine_path,root=workout_page;expect=pw.expect
    page.get_by_role('link',name='Next',exact=True).click()
    expect(page.locator('#workout-progress')).to_have_attribute('value','1')
    page.get_by_text('More',exact=True).click()
    page.get_by_role('link',name='Discard Workout',exact=True).click()
    expect(page.get_by_role('dialog')).to_be_visible()
    expect(page.get_by_role('heading',name='Are you sure?',exact=True)).to_be_visible()
    expect(page.get_by_role('button',name='OK',exact=True)).to_be_disabled()
    page.keyboard.press('Escape')
    expect(page.get_by_role('heading',name='Plank',exact=True)).to_be_visible()
    page.get_by_text('More',exact=True).click()
    page.get_by_role('link',name='Discard Workout',exact=True).click()
    page.get_by_role('link',name='Cancel',exact=True).click()
    expect(page.get_by_role('heading',name='Plank',exact=True)).to_be_visible()
    page.get_by_text('More',exact=True).click()
    page.get_by_role('link',name='Discard Workout',exact=True).click()
    page.get_by_role('checkbox').check()
    expect(page.get_by_role('button',name='OK',exact=True)).to_be_enabled()
    page.get_by_role('button',name='OK',exact=True).click()
    expect(page.get_by_role('heading',name='Workout discarded',exact=True)).to_be_visible()
    page.goto(routine_path);page.get_by_role('button',name='Start workout',exact=True).click()
    page.get_by_role('button',name='Finish & Save',exact=True).click()
    expect(page.get_by_role('alert')).to_contain_text('Confirm that you want')
    page.get_by_label('Confirm saving an entirely skipped workout').check()
    page.get_by_role('button',name='Finish & Save',exact=True).click()
    expect(page.get_by_role('heading',name='Workout saved',exact=True)).to_be_visible()
    with database_session(root) as db:
        assert db.execute('SELECT count(*) FROM workout_entries WHERE actual_weight_tenths_lb IS NULL AND actual_duration_seconds IS NULL').fetchone()[0]==4


def test_offline_failure_and_concurrent_tab_conflict(workout_page):
    """Failures keep local input visible and cannot overwrite an acknowledged save."""
    page,_,root=workout_page;expect=pw.expect
    page.get_by_label('Weight (lb)').fill('40')
    expect(page.get_by_label('Weight (lb)')).to_have_value('40.0')
    other=page.context.new_page();other.on('dialog',lambda dialog:dialog.accept());other.goto(page.url)
    page.route('**/draft',lambda route:route.abort())
    page.get_by_label('Weight (lb)').fill('41')
    expect(page.locator('#save-error')).to_contain_text('Not saved:')
    expect(page.get_by_label('Weight (lb)')).to_have_value('41')
    with database_session(root) as db:
        assert db.execute("SELECT actual_weight_tenths_lb FROM workout_entries WHERE measurement_type='weight'").fetchone()[0]==400
    page.unroute('**/draft')
    page.get_by_label('Weight (lb)').fill('42.56')
    expect(page.get_by_label('Weight (lb)')).to_have_value('42.5')
    other.get_by_label('Weight (lb)').fill('99')
    expect(other.locator('#save-error')).to_contain_text('changed in another tab')
    expect(other.get_by_label('Weight (lb)')).to_have_value('99')
    other.reload()
    expect(other.get_by_label('Weight (lb)')).to_have_value('42.5')


def test_typing_during_held_acknowledgment_serializes_saves(workout_page):
    """A delayed response must not replace newer input or self-conflict revisions."""
    page,_,root=workout_page;expect=pw.expect
    held=[]

    def hold_first(route):
        """Let SQLite commit but hold its first acknowledgment in the browser."""
        if not held:
            response=route.fetch()
            held.append((route,response))
        else:
            route.continue_()

    page.route('**/draft',hold_first)
    page.get_by_label('Weight (lb)').fill('40.99')
    expect(page.locator('#save-status')).to_contain_text('Saving')
    # Wait until the request handler holds a committed response, not a timer guess.
    page.wait_for_function("() => document.getElementById('save-status').textContent.includes('Saving')")
    for _ in range(20):
        if held: break
        page.wait_for_timeout(50)
    assert held
    page.get_by_label('Weight (lb)').fill('42.56')
    page.wait_for_timeout(400)
    expect(page.get_by_label('Weight (lb)')).to_have_value('42.56')
    route,response=held[0];route.fulfill(response=response)
    expect(page.get_by_label('Weight (lb)')).to_have_value('42.5')
    expect(page.locator('#save-status')).to_have_text('✓ Saved')
    with database_session(root) as db:
        assert db.execute("SELECT actual_weight_tenths_lb FROM workout_entries WHERE measurement_type='weight'").fetchone()[0]==425
        assert db.execute('SELECT revision FROM workout_sessions').fetchone()[0]==2
