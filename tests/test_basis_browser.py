# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Touch Chromium exercises both save scopes, signed confirmation and error retention.

Synthetic schema 9 only. No browser operation deploys or touches a real database.
The app's normal CSRF, storage locks, forms and audit services remain active.
"""
import os
import shutil
from threading import Thread
import pytest
from werkzeug.serving import make_server
from workout_tracker import create_app,history as h,basis as b,catalog as c
from workout_tracker.storage import database_session
from test_basis import basis_data,phase11_root,phase9_root,weights,apply
from test_history import correction_payload
pw=pytest.importorskip('playwright.sync_api')


@pytest.fixture
def basis_page(basis_data):
    """Expose a disposable local server containing pre-migration shared exercise history."""
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


@pytest.mark.parametrize('width,height',[(320,844),(390,844),(844,390)])
@pytest.mark.parametrize('theme',['light','dark'])
def test_basis_radios_both_save_scopes_confirmation_and_effective_history(basis_page,width,height,theme):
    """First assignment preserves numbers; explicit subsequent transition halves only A."""
    page,base,x=basis_page;expect=pw.expect;root=x['root']
    page.set_viewport_size(dict(width=width,height=height))
    page.goto(base+f"/settings?person_id={x['a']}");page.select_option('#theme',theme)
    listing=base+f"/people/{x['a']}/exercises";editor=listing+f"/{x['e']}/defaults"
    page.goto(listing);expect(page.locator('.basis-status')).to_contain_text('0 of 1 exercises configured')
    page.goto(editor);expect(page.get_by_role('radio',name='Not Configured',exact=True)).to_be_checked()
    expect(page.get_by_label('Weight meaning (optional)',exact=True)).to_have_value('old free text')
    with database_session(root) as db:before=weights(db,x['a'],x['e']);foreign=weights(db,x['other'],x['e'])
    page.get_by_role('radio',name='Total Weight',exact=True).check()
    page.get_by_role('button',name='Save Defaults Only',exact=True).click()
    with database_session(root) as db:
        assert weights(db,x['a'],x['e'])==before and b.baseline(db,x['a'],x['e'])[0]=='not_configured'
    page.goto(editor);page.get_by_label('Number of sets',exact=True).fill('4');page.get_by_label('Exercise notes (optional)',exact=False).fill('My routine update')
    page.get_by_role('button',name='Save Defaults & Update My Routines',exact=True).click()
    expect(page.get_by_role('heading',name='Update your routines and history?',exact=True)).to_be_visible()
    expect(page.get_by_text('Divide by 2: 0 recorded measurements.',exact=True)).to_be_visible()
    page.get_by_role('button',name='Confirm Update My Routines',exact=True).click()
    with database_session(root) as db:assert b.baseline(db,x['a'],x['e'])[0]=='not_configured'
    page.get_by_role('checkbox').check();page.get_by_role('button',name='Confirm Update My Routines',exact=True).click()
    expect(page.locator('.basis-status')).to_contain_text('Your history: 1 of 1 exercises configured')
    with database_session(root) as db:assert weights(db,x['a'],x['e'])==before
    page.goto(editor);page.get_by_role('radio',name='Per Hand / Side',exact=True).check()
    page.get_by_role('button',name='Save Defaults & Update My Routines',exact=True).click()
    expect(page.get_by_text('Divide by 2: 5 recorded measurements.',exact=True)).to_be_visible()
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.get_by_role('checkbox').check();page.get_by_role('button',name='Confirm Update My Routines',exact=True).click()
    with database_session(root) as db:
        assert weights(db,x['a'],x['e'])=={k:None if v is None else v//2 for k,v in before.items()}
        assert weights(db,x['other'],x['e'])==foreign
        assert db.execute('SELECT target_sets FROM routine_exercises WHERE person_id=? AND exercise_id=?',(x['other'],x['e'])).fetchone()[0]==3
    page.goto(base+f"/people/{x['a']}/history/{x['first']}")
    expect(page.locator('.measurement').first).to_have_text('25.0 lb')
    assert 'Weight Basis transition' in page.content()
    page.goto(base+f"/people/{x['other']}/exercises/{x['e']}/defaults")
    expect(page.get_by_role('radio',name='Per Hand / Side',exact=True)).to_be_checked()
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    # Duration-only configuration has no active basis controls.
    page.get_by_role('radio',name='Time',exact=True).check()
    expect(page.get_by_role('radio',name='Per Hand / Side',exact=True)).to_be_hidden()


def test_precision_failure_keeps_typed_settings_and_no_defaults_or_routines_change(basis_page):
    """The preview refuses fractional tenths before showing any confirmable operation."""
    page,base,x=basis_page;expect=pw.expect
    with database_session(x['root'],write=True) as db:
        apply(db,x,'total');h.correct(db,x['a'],x['first'],correction_payload(db,x['a'],x['first'],weight_0='25.5'))
        before=[tuple(r) for r in db.execute('SELECT * FROM routine_exercises')]
    page.goto(base+f"/people/{x['a']}/exercises/{x['e']}/defaults")
    page.get_by_role('radio',name='Per Hand / Side',exact=True).check()
    page.get_by_label('Exercise name',exact=True).fill('Unsaved rename');page.get_by_label('Number of sets',exact=True).fill('7')
    page.get_by_label('Exercise notes (optional)',exact=False).fill('Retain these notes')
    page.get_by_role('button',name='Save Defaults & Update My Routines',exact=True).click()
    expect(page.get_by_role('alert')).to_contain_text('more than one decimal place')
    expect(page.get_by_label('Exercise name',exact=True)).to_have_value('Unsaved rename')
    expect(page.get_by_label('Number of sets',exact=True)).to_have_value('7')
    expect(page.get_by_label('Exercise notes (optional)',exact=False)).to_have_value('Retain these notes')
    with database_session(x['root']) as db:
        assert [tuple(r) for r in db.execute('SELECT * FROM routine_exercises')]==before
        assert c.definition(db,x['a'],x['e'])['name']=='Shared carry'
