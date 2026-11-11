# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Real Chromium final basis, save scopes, per-set reps and mobile regressions.

All browser routes use a disposable synthetic schema-10 household and loopback.
"""
import os
import shutil
from threading import Thread
import pytest
from werkzeug.serving import make_server
from workout_tracker import create_app,history as h,workouts as w,catalog as c
from workout_tracker.storage import database_session
from test_basis import basis_data,weights
pw=pytest.importorskip('playwright.sync_api')


@pytest.fixture
def basis_page(basis_data):
    x=basis_data;server=make_server('127.0.0.1',0,create_app({'WORKOUT_DATA_ROOT':x['root']}),threaded=True)
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with pw.sync_playwright() as manager:
            browser=manager.chromium.launch(headless=True,executable_path=os.environ.get('WORKOUT_CHROMIUM') or shutil.which('chromium'))
            try:
                page=browser.new_page(is_mobile=True,has_touch=True)
                yield page,f'http://127.0.0.1:{server.server_port}',x
            finally:browser.close()
    finally:server.shutdown();thread.join(5);server.server_close()


@pytest.mark.parametrize('width,height',[(320,568),(390,844),(844,390),(1280,900)])
@pytest.mark.parametrize('theme',['light','dark'])
def test_permanent_basis_save_scopes_and_repetition_navigation(basis_page,width,height,theme):
    page,base,x=basis_page;expect=pw.expect;root=x['root']
    page.set_viewport_size(dict(width=width,height=height))
    page.goto(base+f"/settings?person_id={x['a']}");page.select_option('#theme',theme)
    listing=base+f"/people/{x['a']}/exercises";editor=listing+f"/{x['e']}/defaults"
    page.goto(listing);expect(page.locator('.basis-status')).to_have_count(0)
    page.goto(editor);expect(page.locator('[name=weight_basis]')).to_have_count(0)
    expect(page.locator('[name=weight_meaning]')).to_have_count(0)
    expect(page.get_by_text('This setting cannot be changed after creating the exercise.',exact=True)).to_be_visible()
    with database_session(root) as db:before=weights(db,x['a'],x['e'])
    page.get_by_label('Exercise notes (optional)').fill('Shared new default')
    page.get_by_role('button',name='Save Defaults Only',exact=True).click()
    page.goto(editor);page.get_by_label('Exercise notes (optional)').fill('My routine settings')
    page.get_by_role('button',name='Save Defaults & Update My Routines',exact=True).click()
    expect(page.get_by_role('heading',name='Update your routine settings?',exact=True)).to_be_visible()
    page.get_by_role('checkbox').check();page.get_by_role('button',name='Confirm Update My Routines',exact=True).click()
    with database_session(root) as db:
        assert weights(db,x['a'],x['e'])==before
        draft=w.active(db,x['a'])['id']
        assert db.execute('SELECT notes FROM routine_exercises WHERE routine_id=? ORDER BY position',(x['r'],)).fetchone()[0]=='My routine settings'
        assert db.execute('SELECT notes FROM routine_exercises WHERE routine_id=? ORDER BY position',(x['rb'],)).fetchone()[0]!='My routine settings'
    page.goto(base+f"/people/{x['a']}/workouts/{draft}")
    expect(page.locator('[name=weight]')).to_have_count(1)
    expect(page.locator('[data-actual-reps]')).to_have_count(3)
    expect(page.locator('[name=reps_0]')).to_have_value('12')
    expect(page.locator('[name=weight]')).to_have_value('41.0')
    page.locator('[name=reps_2]').fill('10');expect(page.locator('#save-status')).to_have_text('✓ Saved')
    page.get_by_role('link',name='Next',exact=True).click()
    expect(page.locator('[data-actual-reps]')).to_have_count(0)
    page.get_by_role('link',name='Back',exact=True).click()
    expect(page.locator('[name=reps_2]')).to_have_value('10')
    page.reload();expect(page.locator('[name=reps_2]')).to_have_value('10')
    page.locator('[name=reps_2]').fill('0');expect(page.locator('#save-status')).to_have_text('✓ Saved')
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.get_by_role('button',name='Finish & Save',exact=True).click()
    expect(page.get_by_role('heading',name='Weight Lifted This Workout',exact=True)).to_be_visible()
    expect(page.get_by_text('Set 3: 0',exact=True)).to_be_visible()
    page.goto(base+f"/people/{x['a']}")
    expect(page.get_by_role('heading',name='Estimated Total Weight Lifted',exact=True)).to_be_visible()
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')


@pytest.mark.parametrize('sets',[1,2,4,5,1000])
def test_dynamic_set_counts_and_new_creation_basis_unselected(basis_page,sets):
    page,base,x=basis_page;expect=pw.expect
    with database_session(x['root'],write=True) as db:
        draft=w.active(db,x['a']);w.discard(db,x['a'],draft['id'],dict(revision=str(draft['revision']),confirm='yes'))
        row=db.execute('SELECT id FROM routine_exercises WHERE routine_id=? ORDER BY position',(x['r'],)).fetchone()[0]
        values=c.default_values(c.exercise_defaults(db,x['a'],x['e']));values['target_sets']=str(sets)
        c.update_entry(db,x['a'],x['r'],row,values)
        draft,_=w.start(db,x['a'],x['r'],'UTC')
    page.goto(base+f"/people/{x['a']}/workouts/{draft}")
    expect(page.locator('[name=weight]')).to_have_count(1)
    expect(page.locator('[data-actual-reps]')).to_have_count(sets)
    page.goto(base+f"/people/{x['a']}/exercises")
    assert page.locator('[name=weight_basis]:checked').count()==0
    assert page.locator('[name=weight_basis][value=not_configured]').count()==0


def test_slow_autosave_never_replaces_newer_reps_and_invalid_inputs(basis_page):
    page,base,x=basis_page;expect=pw.expect
    with database_session(x['root']) as db:draft=w.active(db,x['a'])['id']
    page.goto(base+f"/people/{x['a']}/workouts/{draft}")
    page.route('**/draft',lambda route: (page.wait_for_timeout(400),route.continue_()))
    page.locator('[name=reps_2]').fill('1');page.wait_for_timeout(350)
    page.locator('[name=reps_2]').fill('15');expect(page.locator('#save-status')).to_have_text('✓ Saved')
    expect(page.locator('[name=reps_2]')).to_have_value('15')
    page.locator('[name=reps_2]').fill('1.5');expect(page.locator('#save-status')).to_have_text('Save failed')
    expect(page.locator('[name=reps_2]')).to_have_value('1.5')
    page.locator('[name=reps_2]').fill('');expect(page.locator('#save-status')).to_have_text('Save failed')
    expect(page.locator('[name=reps_2]')).to_have_value('')
    page.locator('[name=reps_2]').fill('10');expect(page.locator('#save-status')).to_have_text('✓ Saved')
    page.reload();expect(page.locator('[name=reps_2]')).to_have_value('10')


def test_manual_history_actual_reps_corrections_and_legacy_display(basis_page):
    page,base,x=basis_page;expect=pw.expect
    page.goto(base+f"/people/{x['other']}/historical")
    page.get_by_label('Workout date',exact=True).fill('2020-03-01')
    page.get_by_role('button',name='Prepare historical workout',exact=True).click()
    expect(page.locator('[name=reps_0_0]')).to_have_value('12')
    page.locator('[name=weight_0]').fill('40')
    page.locator('[name=reps_0_2]').fill('10')
    page.get_by_role('button',name='Save historical workout',exact=True).click()
    expect(page.get_by_text('Set 3: 10',exact=True).first).to_be_visible()
    expect(page.get_by_role('heading',name='Weight Lifted This Workout',exact=True)).to_be_visible()
    page.get_by_role('link',name='Correct saved workout',exact=True).click()
    expect(page.locator('[name=reps_0_2]')).to_have_value('10')
    page.locator('[name=reps_0_2]').fill('0')
    page.get_by_label('I confirm these corrections and understand original records are retained').check()
    page.get_by_role('button',name='Apply correction',exact=True).click()
    expect(page.get_by_text('Set 3: 0',exact=True).first).to_be_visible()
    expect(page.locator('.audit-record')).to_have_count(1)
    page.goto(base+f"/people/{x['a']}/history/{x['first']}")
    expect(page.get_by_text('Actual repetitions were not recorded. Estimates use the prescribed targets.',exact=True).first).to_be_visible()
    page.get_by_role('link',name='Correct saved workout',exact=True).click()
    expect(page.locator('[name=reps_0_0]')).to_have_value('')
    for index,value in enumerate(('12','10','0')):page.locator(f'[name=reps_0_{index}]').fill(value)
    page.get_by_label('I confirm these corrections and understand original records are retained').check()
    page.get_by_role('button',name='Apply correction',exact=True).click()
    expect(page.get_by_text('Set 3: 0',exact=True).first).to_be_visible()
    expect(page.locator('.audit-record')).to_have_count(4)


def test_new_exercise_native_required_basis_and_permanent_saved_value(basis_page):
    page,base,x=basis_page;expect=pw.expect
    page.goto(base+f"/people/{x['a']}/exercises")
    page.locator('.add-exercise summary').click()
    form=page.locator('form[data-configuration]')
    form.get_by_label('Exercise name',exact=True).fill('Explicit new basis')
    assert form.locator('[name=weight_basis]:checked').count()==0
    assert form.evaluate('(form)=>form.checkValidity()') is False
    form.get_by_role('radio',name='Total Weight',exact=True).check()
    assert form.evaluate('(form)=>form.checkValidity()') is True
    form.get_by_role('button',name='Add exercise name',exact=True).click()
    with database_session(x['root']) as db:
        e=db.execute("SELECT id FROM exercises WHERE name='Explicit new basis'").fetchone()[0]
        assert c.exercise_defaults(db,x['a'],e)['weight_basis']=='total'
    page.goto(base+f"/people/{x['a']}/exercises/{e}/defaults")
    expect(page.locator('[name=weight_basis]')).to_have_count(0)
    expect(page.get_by_text('Total Weight',exact=True)).to_be_visible()
