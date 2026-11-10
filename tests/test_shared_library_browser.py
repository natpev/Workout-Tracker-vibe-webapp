# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Chromium drives shared library/copy/version forms against disposable schema 5.

Loopback-only Flask and synthetic households verify mobile layout and no remote
assets. Browser submissions use real CSRF/revision fields, not service shortcuts.
"""
import os
import shutil
from threading import Thread

import pytest
from werkzeug.serving import make_server
from workout_tracker import create_app, catalog as c
from workout_tracker.storage import database_session
from workout_tracker.migrations import migrate_storage
from test_catalog import weight

pw=pytest.importorskip('playwright.sync_api')


@pytest.fixture
def library_browser(phase4_root):
    """Serve an upgraded temporary household with one shared exercise identity."""
    root=phase4_root;migrate_storage(root,5)
    with database_session(root,write=True) as db:
        a,b=c.create_person(db,'Alex'),c.create_person(db,'Sam')
        r=c.create_routine(db,a,'Strength');c.add_entry(db,a,r,weight(name='Bench Press'))
        e=db.execute('SELECT exercise_id FROM routine_exercises WHERE routine_id=?',(r,)).fetchone()[0]
    server=make_server('127.0.0.1',0,create_app({'WORKOUT_DATA_ROOT':root,'TESTING':True}))
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with pw.sync_playwright() as manager:
            browser=manager.chromium.launch(headless=True,executable_path=os.environ.get('WORKOUT_CHROMIUM') or shutil.which('chromium'))
            page=browser.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
            try: yield page,f'http://127.0.0.1:{server.server_port}',root,a,b,r,e
            finally: browser.close()
    finally: server.shutdown();thread.join(5);server.server_close()


def test_global_library_named_cross_person_copy_and_versions(library_browser):
    """Real UI reuses IDs, validates name, edits independent targets and shows versions."""
    page,base,root,a,b,r,e=library_browser;expect=pw.expect;errors=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto(f'{base}/people/{b}/exercises')
    expect(page.get_by_role('heading',name='Exercise Library',exact=True)).to_be_visible()
    expect(page.get_by_text('Library ID: '+e,exact=True)).to_have_count(0)
    page.locator('.library-exercise').filter(has=page.get_by_role('heading',name='Bench Press',exact=True)).get_by_role('link',name='Edit Defaults',exact=True).click()
    expect(page.get_by_text('Library ID: '+e,exact=True)).to_be_visible()
    page.goto(f'{base}/people/{b}/exercises')
    add=page.locator('form').filter(has=page.get_by_role('button',name='Add exercise name',exact=True))
    add.get_by_label('Exercise name',exact=True).fill('Squat');add.get_by_role('button').click()
    page.goto(f'{base}/people/{a}/exercises')
    expect(page.get_by_role('heading',name='Squat',exact=True)).to_be_visible()
    page.goto(f'{base}/people/{b}?manage=1')
    page.get_by_label('Source routine',exact=True).select_option(f'{a}:{r}')
    page.get_by_role('button',name='Copy routine',exact=True).click()
    assert page.get_by_label('Name for the copy',exact=True).evaluate('element => !element.validity.valid')
    page.get_by_label('Name for the copy',exact=True).fill('Sam strength')
    page.get_by_role('button',name='Copy routine',exact=True).click()
    expect(page.get_by_role('heading',name='Sam strength',exact=True)).to_be_visible()
    copy=page.url.rsplit('/',1)[-1]
    page.get_by_role('link',name='Bench Press',exact=True).click()
    page.get_by_label('Target repetitions per set',exact=True).fill('8')
    page.get_by_role('button',name='Save exercise settings',exact=True).click()
    page.goto(f'{base}/people/{a}/routines/{r}')
    expect(page.get_by_text('Weight · 3 sets × 12 reps · pounds',exact=True)).to_be_visible()
    # Same-person duplicate also keeps the registered library identity.
    page.get_by_label('Copy name',exact=True).fill('Alex duplicate')
    page.get_by_role('button',name='Duplicate routine',exact=True).click()
    duplicate=page.url.rsplit('/',1)[-1]
    with database_session(root) as db:
        for routine in (r,copy,duplicate):
            assert db.execute('SELECT exercise_id FROM routine_exercises WHERE routine_id=?',(routine,)).fetchone()[0]==e
        assert db.execute('SELECT count(*) FROM exercises').fetchone()[0]==2
    # Registering/selecting is household-wide, and global rename is visible
    # in every current routine while archive refuses referenced definitions.
    page.goto(f'{base}/people/{b}?manage=1')
    page.get_by_label('Routine name',exact=True).fill('Selected from library')
    page.get_by_role('button',name='Create routine',exact=True).click()
    form=page.locator('[data-configuration]')
    form.get_by_label('Reuse an exercise name',exact=True).select_option(e)
    form.get_by_role('button',name='Add exercise',exact=True).click()
    expect(page.get_by_role('link',name='Bench Press',exact=True)).to_be_visible()
    page.goto(f'{base}/people/{b}/exercises')
    page.locator('.library-exercise').filter(has=page.get_by_role('heading',name='Bench Press',exact=True)).get_by_role('link',name='Edit Defaults',exact=True).click()
    rename=page.locator('form')
    rename.get_by_label('Exercise name',exact=True).fill('Household bench')
    rename.get_by_role('button',name='Save changes',exact=True).click()
    for width in (320,390,1280):
        page.set_viewport_size({'width':width,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    used=page.locator('.library-exercise').filter(has=page.get_by_role('heading',name='Household bench',exact=True))
    used.get_by_role('checkbox').check();used.get_by_role('button',name='Archive exercise',exact=True).click()
    expect(page.get_by_text('Remove this exercise from active routines before archiving it.',exact=True)).to_be_visible()
    page.goto(f'{base}/people/{a}/routines/{r}')
    expect(page.get_by_role('link',name='Household bench',exact=True)).to_be_visible()
    page.goto(f'{base}/people/{b}/exercises')
    unused=page.locator('.library-exercise').filter(has=page.get_by_role('heading',name='Squat',exact=True))
    unused.get_by_role('checkbox').check();unused.get_by_role('button',name='Archive exercise',exact=True).click()
    expect(page.get_by_role('heading',name='Squat',exact=True)).to_have_count(0)
    page.goto(f'{base}/settings/administration')
    expect(page.get_by_text('Application version: 0.12.0',exact=True)).to_be_visible()
    expect(page.get_by_text('Database schema: 5',exact=True)).to_be_visible()
    page.goto(f'{base}/settings')
    for theme in ('auto','light','dark'):
        page.select_option('#theme',theme)
        for width in (320,390,1280):
            page.set_viewport_size({'width':width,'height':844})
            expect(page.locator('footer')).to_contain_text('Workout Tracker v0.12.0 · Database v5')
            assert page.locator('footer').evaluate('element => getComputedStyle(element).position') not in ('fixed','sticky')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.goto(f'{base}/people/{b}/routines/{copy}')
    page.get_by_role('button',name='Start workout',exact=True).click()
    expect(page.locator('footer')).to_contain_text('Database v5')
    expect(page.get_by_label('Weight (lb)',exact=True)).to_have_value('')
    assert errors==[]
