# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Real passwordless HTTP browser, restricted Unix controls and independent status.

Synthetic schema-6 data only. Remote Git/install work is simulated; actual HTTP,
CSRF, Unix sockets, peer UID, SQLite deletions and web interruption are exercised.
"""
import json
import os
import shutil
import socket
from threading import Thread
import time

import pytest
from werkzeug.serving import make_server
from workout_tracker import create_app,history as h,preferences
from workout_tracker.storage import database_session
from workout_tracker.migrations import migrate_storage
from workout_tracker.update_client import call
from workout_updater.engine import Engine,write_json
from workout_updater.service import status_app,UnixServer,Handler,Controller
from test_phase8_deletion import household,approval

pw=pytest.importorskip('playwright.sync_api')


@pytest.fixture
def lan_browser(phase4_root,tmp_path):
    """Start two independent loopback HTTP servers with no accounts or TLS setup."""
    data=phase4_root;migrate_storage(data,6)
    with database_session(data,write=True) as db:
        a,b,r,other,e=household(db)
        form=h.prepare(db,a,r,dict(workout_date='2020-01-01',workout_time=''),'UTC')
        saved=h.complete_historical(db,a,form,{'weight_0':'40','minutes_1':'0','seconds_1':'45'})
    preferences.set_color(data,a,'purple');preferences.set_color(data,b,'teal')
    root=tmp_path/'host';(root/'updater').mkdir(parents=True)
    engine=Engine(root);engine.data=data
    http=make_server('127.0.0.1',0,create_app({'WORKOUT_DATA_ROOT':data,'WORKOUT_TIMEZONE':'UTC'}),threaded=True)
    http_thread=Thread(target=http.serve_forever,daemon=True);http_thread.start()
    with socket.socket() as available:
        available.bind(('127.0.0.1',0));port=available.getsockname()[1]
    base=f'http://127.0.0.1:{http.server_port}';status_base=f'http://127.0.0.1:{port}'
    engine.config=dict(status_url=status_base+'/status',app_url=base)
    bridge=data/'config/updater-bridge';bridge.mkdir()
    write_json(bridge/'client.json',dict(status_url=status_base+'/status'))
    # Model the upgraded host's version-matched plain-note protocol. Older-host
    # fallback is separately checked in test_phase12; no raw Git notes render.
    release=dict(id='c'*40,version='0.9.0',schema=6,source='Synthetic approved main',notes='Approved fixture release',notes_version='0.9.0',notes_format=1)
    def check():
        """Simulate Git only; local protocol/status processing remain real."""
        engine.event('Available',release=release)
    def install(identity,**kwargs):
        """Simulate update commands, while actually stopping the separate web server."""
        engine.event('Building image');http.shutdown();http_thread.join(5)
        engine.event('Completed','Fixture update completed while web stopped.',last_success='fixture')
    engine.check=check;engine.install=install
    unix=UnixServer(str(bridge/'control.sock'),Handler);unix.controller=Controller(engine);unix.writer_uid=os.getuid()
    unix_thread=Thread(target=unix.serve_forever,daemon=True);unix_thread.start()
    status_http=make_server('127.0.0.1',port,status_app(engine),threaded=True)
    status_thread=Thread(target=status_http.serve_forever,daemon=True);status_thread.start()
    try:
        with pw.sync_playwright() as manager:
            browser=manager.chromium.launch(headless=True,executable_path=os.environ.get('WORKOUT_CHROMIUM') or shutil.which('chromium'))
            context=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
            page=context.new_page()
            try:yield page,base,status_base,data,a,b,r,other,e,saved,engine,http,unix
            finally:browser.close()
    finally:
        http.shutdown();http_thread.join(5);http.server_close()
        unix.shutdown();unix_thread.join(5);unix.server_close()
        status_http.shutdown();status_thread.join(5);status_http.server_close()


def test_passwordless_global_deletion_and_sticky_person_context(lan_browser):
    """LAN users delete with CSRF/typed confirmation; headers survive scrolling/back."""
    page,base,status_base,root,a,b,r,other,e,saved,engine,http,unix=lan_browser;expect=pw.expect
    paths=[f'/people/{a}',f'/people/{a}/routines/{r}',f'/people/{a}/exercises',f'/people/{a}/history',f'/people/{a}/progress',f'/settings?person_id={a}']
    for width in (320,390,768,1280):
        page.set_viewport_size({'width':width,'height':844})
        for theme in ('light','dark'):
            page.goto(base+f'/settings?person_id={a}');page.select_option('#theme',theme)
            for path in paths:
                page.goto(base+path)
                expect(page.locator('header .selected-person')).to_contain_text('A')
                assert page.locator('body').get_attribute('data-accent')=='purple'
                page.evaluate('scrollTo(0,document.body.scrollHeight)')
                box=page.locator('header').bounding_box();assert 0<=box['y']<5
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.goto(base+f'/people/{b}');expect(page.locator('header .selected-person')).to_contain_text('B')
    assert page.locator('body').get_attribute('data-accent')=='teal'
    page.goto(base+f'/people/{a}/routines/{r}');page.go_back();page.reload()
    expect(page.locator('header .selected-person')).to_contain_text('B')
    page.goto(base+f'/people/{a}/permanent-delete/exercise/{e}')
    expect(page.get_by_role('heading',name='Permanently Delete Bench?',exact=True)).to_be_visible()
    expect(page.get_by_text('This global exercise affects 2 people, 2 routines and 1 recorded workout entries.',exact=True)).to_be_visible()
    assert page.locator('input[type="password"]').count()==0
    page.get_by_label('Type DELETE or Bench',exact=True).fill('DELETE');page.get_by_role('checkbox').check()
    page.get_by_role('button',name='Permanently Delete Exercise',exact=True).click()
    with database_session(root) as db:
        assert db.execute('SELECT 1 FROM exercises WHERE id=?',(e,)).fetchone() is None
        assert h.effective(db,a,saved)[1][0]['name']=='Plank'
    page.goto(base+f'/people/{a}/permanent-delete/routine/{r}')
    page.get_by_label('Type DELETE or Mixed',exact=True).fill('DELETE');page.get_by_role('checkbox').check()
    page.get_by_role('button',name='Permanently Delete Routine',exact=True).click()
    page.goto(base+f'/people/{a}/history/{saved}')
    expect(page.get_by_text('Original routine was permanently deleted. This workout snapshot is retained.',exact=True)).to_be_visible()


def test_http_browser_updates_no_login_and_status_survives_web_stop(lan_browser):
    """Anyone reachable may confirm an approved update; status remains read-only/live."""
    page,base,status_base,root,a,b,r,other,e,saved,engine,http,unix=lan_browser;expect=pw.expect
    page.goto(base+f'/settings/updates?person_id={a}')
    expect(page.get_by_role('heading',name='Application Updates',exact=True)).to_be_visible()
    expect(page.locator('header .selected-person')).to_contain_text('A')
    assert page.locator('input[type="password"]').count()==0
    # Forged POST lacks CSRF and cannot trigger the worker.
    assert page.request.post(base+'/settings/updates',form={'action':'check'}).status==400
    # Wait for the actual POST/303 navigation before asking CDP to reload.
    # An immediate reload can race the newly attached page under heavy load.
    with page.expect_navigation(wait_until='load'):
        page.get_by_role('button',name='Check for Updates',exact=True).click()
    deadline=time.monotonic()+5
    while engine.state()['status']!='Available' and time.monotonic()<deadline:
        time.sleep(.05)
    assert engine.state()['status']=='Available'
    page.reload();expect(page.get_by_text('Latest approved version: 0.9.0 · Required database schema: 6',exact=True)).to_be_visible()
    expect(page.get_by_text('Approved fixture release',exact=True)).to_be_visible()
    status_page=page.context.new_page();status_page.goto(status_base+'/status')
    expect(status_page.get_by_role('heading',name='Independent Update Progress',exact=True)).to_be_visible()
    assert status_page.request.post(status_base+'/status',data='action=install').status==405
    # Without a confirmation checkbox, HTML validity refuses submission.
    page.get_by_role('button',name='Install Update',exact=True).click()
    assert engine.state()['status']=='Available'
    page.get_by_label('Install this approved release, with a verified backup.',exact=True).check()
    try:page.get_by_role('button',name='Install Update',exact=True).click()
    except pw.Error:pass  # Intentional app outage; the independent HTTP page survives.
    for _ in range(30):
        if engine.state()['status']=='Completed':break
        time.sleep(.1)
    assert engine.state()['status']=='Completed'
    status_page.reload()
    expect(status_page.get_by_text('Fixture update completed while web stopped.',exact=False)).to_be_visible()


def test_local_socket_peer_validation_and_unapproved_payloads(lan_browser):
    """Actual Unix server rejects wrong UID and arbitrary commands without passwords."""
    page,base,status_base,root,a,b,r,other,e,saved,engine,http,unix=lan_browser
    assert call(root,'status')['status']=='Not yet checked'
    from workout_tracker.storage import StorageError
    with pytest.raises(StorageError):call(root,'shell',command='id')
    with pytest.raises(StorageError):call(root,'check',repository='https://evil.example')
    if os.getuid()!=0:
        unix.writer_uid=os.getuid()+1
        with pytest.raises(StorageError):call(root,'status')
    unix.writer_uid=os.getuid()


@pytest.mark.parametrize('width',[320,1280])
def test_settings_context_survives_maintenance_navigation_and_workout_return(lan_browser,width):
    """Actual forms/redirects retain URL person and accent; restore refresh is read-only."""
    from workout_tracker import diagnostics,operations as o,workouts as w
    from workout_tracker.storage import storage_lock
    page,base,status_base,root,a,b,r,other,e,saved,engine,http,unix=lan_browser;expect=pw.expect
    page.set_viewport_size({'width':width,'height':844})
    def header(name,color):
        """Check exact person, accent, sticky bounds and phone-width overflow."""
        expect(page.locator('header .person-label')).to_contain_text(name)
        assert page.locator('body').get_attribute('data-accent')==color
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.evaluate('scrollTo(0,document.body.scrollHeight)')
        box=page.locator('header').bounding_box();assert 0<=box['y']<5 and box['height']<110
    for person,name,color in ((a,'A','purple'),(b,'B','teal')):
        page.goto(base+f'/settings?person_id={person}');header(name,color)
        for theme in ('auto','light','dark'):
            page.select_option('#theme',theme);page.reload();header(name,color)
        page.get_by_role('link',name='Open Administration',exact=True).click();header(name,color)
        page.get_by_role('button',name='Save settings',exact=True).click();header(name,color)
        assert f'person_id={person}' in page.url
        page.get_by_role('link',name='Application Updates',exact=True).click();header(name,color)
        with page.expect_navigation(wait_until='load'):
            page.get_by_role('button',name='Check for Updates',exact=True).click()
        page.reload();header(name,color)
        page.go_back();header(name,color)
        page.goto(base+f'/settings/administration?person_id={person}')
        page.get_by_role('button',name='Backup Now',exact=True).click();header(name,color)
        backup_url=page.url;assert f'person_id={person}' in backup_url
        page.reload();header(name,color)
        page.get_by_role('link',name='Back to Administration',exact=True).click();header(name,color)
        page.get_by_role('link',name='Inspect backup 1',exact=True).click();header(name,color)
        page.get_by_label('I understand this selects an earlier dataset and preserves the current database separately',exact=True).check()
        page.get_by_label('Type RESTORE to confirm',exact=True).fill('RESTORE')
        page.get_by_role('button',name='Restore Backup',exact=True).click()
        expect(page.get_by_role('heading',name='Restore result',exact=True)).to_be_visible();header(name,color)
        assert '/settings/restores/' in page.url and f'person_id={person}' in page.url
        with storage_lock(root) as storage:attempts=len(o.read_state(storage)['restores'])
        page.reload();header(name,color)
        with storage_lock(root) as storage:assert len(o.read_state(storage)['restores'])==attempts
        page.get_by_role('link',name='Back to Administration',exact=True).click();header(name,color)
        for i in range(55):diagnostics.emit(root,'INFO','Application','Context log fixture '+str(i))
        page.get_by_role('link',name='View logs',exact=True).click();header(name,color)
        page.get_by_label('Search log text',exact=True).fill('Context log fixture')
        page.get_by_role('button',name='Filter / Refresh logs',exact=True).click();header(name,color)
        page.get_by_role('link',name='Next page',exact=True).click();page.reload();header(name,color)
        page.get_by_role('link',name='Previous page',exact=True).click();header(name,color)
        page.get_by_role('link',name='Back to Administration',exact=True).click();header(name,color)
        page.goto(backup_url);page.get_by_label('I confirm deleting this backup file',exact=True).check()
        page.get_by_role('button',name='Delete backup permanently',exact=True).click();header(name,color)
    # The existing tab-scoped workout guard still prevents a direct Settings or
    # other-person navigation from switching context until explicit save/exit.
    with database_session(root,write=True) as db:draft,_=w.start(db,a,r,'UTC')
    page.goto(base+f'/people/{a}/workouts/{draft}');header('A','purple')
    workout_url=page.url
    page.goto(base+f'/settings?person_id={b}');page.wait_for_url(workout_url)
    page.wait_for_load_state('networkidle');header('A','purple')
    assert page.get_by_role('link',name='Switch person',exact=True).count()==0
    page.get_by_text('More',exact=True).click()
    with page.expect_navigation(wait_until='load'):
        page.get_by_role('button',name='Exit Workout',exact=True).click()
    page.wait_for_url('**/people/'+a+'?exited='+draft)
    page.wait_for_load_state('networkidle')
    page.goto(base+f'/settings?person_id={a}');header('A','purple')
    page.get_by_role('button',name='Open navigation',exact=True).click()
    page.get_by_role('link',name='Routines',exact=True).click()
    page.get_by_role('link',name='Resume or discard unfinished workout',exact=True).click();header('A','purple')
    page.reload();header('A','purple')
