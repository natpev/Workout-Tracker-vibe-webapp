# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Real Chromium forms, touch SVG and independent host output on disposable data.

Loopback servers exercise CSRF/transactions and actual streaming subprocesses.
No real Git updates, production data, identities or remote server are involved.
"""
from datetime import datetime,timezone
import os
from pathlib import Path
import shutil
import sys
from threading import Thread
import time
from unittest.mock import patch
from uuid import uuid4

import pytest
from werkzeug.serving import make_server
from workout_tracker import create_app,history as h,workouts as w
from workout_tracker.storage import database_session
from workout_updater.console import Console,safe_line
from workout_updater.process_output import stream_run
from test_phase9 import phase9_root
from test_phase8_deletion import household,manual
from test_phase8_lan_browser import lan_browser

pw=pytest.importorskip('playwright.sync_api')
SHOTS=Path(os.environ.get('WORKOUT_PHASE10_SCREENSHOTS','/tmp/phase10-screenshots'))
SHOTS.mkdir(parents=True,exist_ok=True)


@pytest.fixture
def phase10_page(phase9_root):
    """Freeze only the current clock, retaining actual SQLite/HTTP browser flows."""
    root=phase9_root
    with database_session(root,write=True) as db:
        a,b,r,other,e=household(db)
        old,_=manual(db,a,r,'2020-01-01',weight_0='99')
        saved,_=manual(db,a,r,'2026-11-01',weight_0='0',seconds_1='45')
        manual(db,a,r,'2026-11-02',weight_0='40.99')
        draft,_=w.start(db,a,r,'America/Indiana/Indianapolis')
    server=make_server('127.0.0.1',0,create_app({'WORKOUT_DATA_ROOT':root,'WORKOUT_TIMEZONE':'America/Indiana/Indianapolis'}),threaded=True)
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with patch.object(w,'now',return_value=datetime(2026,11,8,17,tzinfo=timezone.utc)),pw.sync_playwright() as manager:
            browser=manager.chromium.launch(headless=True,executable_path=os.environ.get('WORKOUT_CHROMIUM') or shutil.which('chromium'))
            context=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
            page=context.new_page()
            try:yield page,f'http://127.0.0.1:{server.server_port}',root,a,b,r,e,saved,draft
            finally:browser.close()
    finally:server.shutdown();thread.join(5);server.server_close()


@pytest.mark.parametrize('width',[320,1280])
def test_historical_inline_errors_picker_resubmission_and_conflict(phase10_page,width):
    """Raw fields/error links survive invalid POSTs; a stale correction never wins."""
    page,base,root,a,b,r,e,saved,draft=phase10_page;expect=pw.expect
    page.set_viewport_size({'width':width,'height':844})
    page.goto(base+f'/people/{a}/historical')
    page.get_by_label('Workout date',exact=True).fill('2020-11-01')
    clock=page.get_by_label('Workout time (optional)',exact=True)
    clock.fill('0960');page.get_by_role('button',name='Prepare historical workout',exact=True).click()
    expect(page.locator('.error-summary')).to_be_focused()
    expect(clock).to_have_value('09:60');expect(clock).to_have_attribute('aria-invalid','true')
    # Typing is stable until blur. The explicit picker is always 00..23, not AM/PM.
    clock.fill('0930');expect(clock).to_have_value('0930');clock.press('Tab');expect(clock).to_have_value('09:30')
    page.get_by_role('button',name='Choose time',exact=True).click()
    expect(page.locator('[data-clock-hour] option')).to_have_count(25)
    expect(page.locator('[data-clock-minute] option')).to_have_count(61)
    assert page.evaluate('document.documentElement.scrollWidth<=document.documentElement.clientWidth')
    if width==320:page.screenshot(path=str(SHOTS/'time-picker-320.png'),full_page=True)
    page.get_by_label('Hour',exact=True).select_option('14');page.get_by_label('Minute',exact=True).select_option('45')
    page.get_by_role('button',name='Use time',exact=True).click();expect(clock).to_have_value('14:45')
    page.get_by_role('button',name='Prepare historical workout',exact=True).click()
    path=page.url
    page.locator('#weight_0').fill('bad');page.locator('#minutes_1').fill('1');page.locator('#seconds_1').fill('-1')
    page.locator('#increase_0').check();page.locator('#increase_1').check()
    page.get_by_role('button',name='Save historical workout',exact=True).click()
    assert page.url==path
    expect(page.locator('.error-summary')).to_be_visible();expect(page.locator('.error-summary li')).to_have_count(2)
    for selector,value in (('#weight_0','bad'),('#minutes_1','1'),('#seconds_1','-1')):
        expect(page.locator(selector)).to_have_value(value);expect(page.locator(selector)).to_have_attribute('aria-invalid','true')
        assert page.locator(selector).get_attribute('aria-describedby')
    expect(page.locator('#increase_0')).to_be_checked();expect(page.locator('#increase_1')).to_be_checked()
    page.locator('.error-summary a').first.click();expect(page.locator('#weight_0')).to_be_focused()
    if width==320:page.screenshot(path=str(SHOTS/'historical-inline-320.png'),full_page=True)
    # Summary appears immediately before Save in document order, even on a phone.
    assert page.locator('.error-summary').evaluate('(n)=>n.nextElementSibling.tagName')=='BUTTON'
    page.locator('#weight_0').fill('42.56');page.locator('#seconds_1').fill('0')
    page.get_by_role('button',name='Save historical workout',exact=True).click()
    expect(page.locator('.measurement')).to_have_text(['42.5 lb','01:00'])
    page.get_by_role('link',name='Correct saved workout',exact=True).click()
    expect(page.get_by_label('Workout time (optional)',exact=True)).to_have_value('14:45')
    correction=page.url;other=page.context.new_page();other.goto(correction)
    page.locator('#weight_0').fill('0');page.locator('#seconds_1').fill('0');page.locator('#minutes_1').fill('')
    page.get_by_role('button',name='Apply correction',exact=True).click()
    expect(page.locator('#weight_0')).to_have_value('0');expect(page.locator('#error-confirm')).to_be_visible()
    expect(page.locator('#error-seconds_1')).to_be_visible()
    page.locator('#seconds_1').fill('45');page.locator('#confirm').check()
    page.get_by_role('button',name='Apply correction',exact=True).click()
    expect(page.locator('.measurement')).to_have_text(['0.0 lb','00:45'])
    other.locator('#weight_0').fill('99');other.locator('#confirm').check()
    with other.expect_response(lambda response:response.request.method=='POST') as response:
        other.get_by_role('button',name='Apply correction',exact=True).click()
    assert response.value.status==409
    expect(other.locator('.error-summary')).to_contain_text('Your inputs are retained')
    expect(other.locator('#weight_0')).to_have_value('99');expect(other.locator('#correction_revision')).to_have_count(0)
    assert other.locator('[name=correction_revision]').input_value()=='0'
    with database_session(root) as db:
        assert w.active(db,a)['id']==draft
        assert db.execute('SELECT count(*) FROM workout_corrections').fetchone()[0]==1
    assert page.evaluate('document.documentElement.scrollWidth<=document.documentElement.clientWidth')


@pytest.mark.parametrize('width',[320,1280])
def test_progress_range_state_tooltips_and_themes(phase10_page,width):
    """Preset/custom URL state and zero/NULL chart points work on touch and keyboard."""
    page,base,root,a,b,r,e,saved,draft=phase10_page;expect=pw.expect
    page.set_viewport_size({'width':width,'height':844})
    page.goto(base+f'/people/{a}/progress')
    expect(page.get_by_role('button',name='3 Months',exact=True)).to_have_attribute('aria-pressed','true')
    expect(page.locator('[name=from]')).to_have_count(0)
    expect(page.locator('.chart-point')).to_have_count(3) # Two weights including zero, one duration; skips unplotted.
    page.get_by_role('button',name='Custom Range',exact=True).click()
    expect(page.locator('.chart-point')).to_have_count(3)
    expect(page.get_by_label('From date',exact=True)).to_have_value('2026-08-09')
    for label in ('6 Months','12 Months','24 Months','All Time'):
        page.get_by_role('button',name=label,exact=True).click()
        expect(page.get_by_role('button',name=label,exact=True)).to_have_attribute('aria-pressed','true')
    expect(page.locator('.chart-point')).to_have_count(4)
    page.get_by_label('Exercise',exact=True).select_option(e);page.get_by_role('button',name='Update progress',exact=True).click()
    expect(page.locator('.chart-point')).to_have_count(3)
    # Explicitly finish document swaps before reload/Back; these checks should
    # test persisted filters rather than race Chromium's navigation protocol.
    with page.expect_navigation(wait_until='load'):
        page.get_by_role('link',name='History',exact=True).click()
    page.reload()
    page.get_by_role('link',name='Progress',exact=True).click()
    expect(page.get_by_role('button',name='All Time',exact=True)).to_have_attribute('aria-pressed','true')
    expect(page.get_by_label('Exercise',exact=True)).to_have_value(e)
    page.get_by_role('button',name='Custom Range',exact=True).click()
    page.get_by_label('From date',exact=True).fill('2026-11-02');page.get_by_label('To date',exact=True).fill('2026-11-01')
    page.get_by_role('button',name='Update progress',exact=True).click()
    expect(page.get_by_role('alert')).to_contain_text('after')
    expect(page.get_by_label('From date',exact=True)).to_have_value('2026-11-02')
    expect(page.get_by_label('Exercise',exact=True)).to_have_value(e)
    expect(page.locator('.chart-point')).to_have_count(3)
    page.get_by_label('From date',exact=True).fill('2026-11-01');page.get_by_label('To date',exact=True).fill('2026-11-01')
    with page.expect_navigation(wait_until='load'):
        page.get_by_role('button',name='Update progress',exact=True).click()
    page.reload()
    expect(page.locator('.chart-point')).to_have_count(1)
    single=page.url
    with page.expect_navigation(wait_until='load'):
        page.get_by_role('button',name='All Time',exact=True).click()
    page.go_back()
    expect(page.locator('.chart-point')).to_have_count(1)
    assert 'range=custom' in page.url
    for theme in ('light','dark','auto'):
        page.goto(base+f'/settings?person_id={a}');page.select_option('#theme',theme)
        page.goto(single)
        point=page.locator('.chart-point').first;tip=page.locator('[data-chart-tooltip]').first
        point.scroll_into_view_if_needed();point.hover();expect(tip).to_be_visible()
        expect(tip).to_contain_text('2026-11-01');expect(tip).to_contain_text('0.0 lb')
        if width==320:page.screenshot(path=str(SHOTS/('progress-'+theme+'-320.png')))
        box=tip.bounding_box();assert box['x']>=0 and box['x']+box['width']<=width
        page.mouse.move(0,0);expect(tip).to_be_hidden()
        point.focus();expect(tip).to_be_visible();point.press('Escape');expect(tip).to_be_hidden()
        point.tap();expect(tip).to_be_visible()
        # Browser focus may queue a scroll event after touch activation. The
        # visible point must keep its label through that delayed notification.
        page.evaluate("window.dispatchEvent(new Event('scroll'))")
        point.dispatch_event('mouseleave')
        expect(tip).to_be_visible()
        page.locator('h1').tap();expect(tip).to_be_hidden()
        assert page.evaluate('document.documentElement.scrollWidth<=document.documentElement.clientWidth')
    page.goto(base+f'/people/{a}/progress?range=all')
    for point in page.locator('.chart-point').all():
        point.scroll_into_view_if_needed();point.hover()
        tip=point.locator('xpath=ancestor::section').locator('[data-chart-tooltip]')
        expect(tip).to_be_visible();assert point.get_attribute('data-tooltip') in tip.inner_text()
    page.goto(base+f'/people/{b}/progress?range=all');expect(page.locator('.chart-point')).to_have_count(0)


@pytest.mark.parametrize('width,blocked,failed',[(320,False,False),(1280,False,True),(320,True,False),(1280,True,False)])
def test_install_tab_safe_live_output_refresh_and_web_offline(lan_browser,width,blocked,failed):
    """Actual HTTP/Unix controls stream a child process after the web server stops."""
    page,base,status_base,root,a,b,r,other,e,saved,engine,http,unix=lan_browser;expect=pw.expect
    page.set_viewport_size({'width':width,'height':844});errors=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    def install(identity,**kwargs):
        """Replace only deployment commands with a streaming real synthetic child."""
        op=uuid4().hex;engine.console=Console(engine.state_dir,op)
        engine.event('Building image',operation=op)
        http.shutdown()
        script='import time\n'
        script+='for i in range(80): print(f"#{i} DONE 0.1s",flush=True)\n'
        script+='print("SECRET_SESSION_KEY=NEVER_VISIBLE",flush=True)\ntime.sleep(4)\nprint("#100 DONE 0.5s",flush=True)\ntime.sleep(2)\n'
        try:
            stream_run([sys.executable,'-u','-c',script],env=os.environ.copy(),on_line=lambda line:engine.console_line(safe_line('build',line)) if safe_line('build',line) else None)
            engine.event('Failed' if failed else 'Completed',last_failure='fixture' if failed else None)
        finally:engine.console=None
    engine.install=install
    page.goto(base+f'/settings/updates?person_id={a}')
    # Let the POST/redirect finish before issuing an explicit reload. Starting
    # reload during a document swap can detach Chromium's automation target.
    with page.expect_navigation(wait_until='load'):
        page.get_by_role('button',name='Check for Updates',exact=True).click()
    page.reload()
    assert len(page.context.pages)==1
    page.get_by_role('button',name='Install Update',exact=True).click()
    assert len(page.context.pages)==1 and engine.state()['status']=='Available'
    page.get_by_label('Install this approved release, with a verified backup.',exact=True).check()
    original=page.url
    if blocked:
        page.evaluate('window.open=()=>null')
        page.get_by_role('button',name='Install Update',exact=True).click()
        expect(page.locator('#popup-fallback')).to_be_visible()
        assert len(page.context.pages)==1
        status=page.context.new_page();status.goto(status_base+'/status')
    else:
        with page.context.expect_page() as opened:page.get_by_role('button',name='Install Update',exact=True).click()
        status=opened.value;status.wait_for_url(status_base+'/status')
        assert len(page.context.pages)==2 and status.evaluate('window.opener===null')
    status.set_viewport_size({'width':width,'height':844})
    assert page.url==original
    expect(page.get_by_role('button',name='Install Update',exact=True)).to_be_disabled()
    expect(status.locator('#console')).to_contain_text('Build step 0',timeout=10000)
    assert engine.state()['status']=='Building image'
    assert 'NEVER_VISIBLE' not in status.locator('body').inner_text()
    op=engine.state()['operation'];expect(status.locator('#operation-id')).to_have_text(op)
    box=status.locator('#console');box.evaluate('(n)=>n.scrollTop=0')
    expect(box).to_contain_text('Build step 100',timeout=10000)
    assert box.evaluate('(n)=>n.scrollTop')==0
    status.get_by_role('button',name='Scroll to Latest',exact=True).click()
    assert box.evaluate('(n)=>n.scrollHeight-n.scrollTop-n.clientHeight')<24
    status.reload();expect(box).to_contain_text('Build step 100')
    expect(status.locator('#current-status')).to_have_text('Failed' if failed else 'Completed',timeout=10000)
    status.reload();expect(box).to_contain_text('Build step 0')
    if width==320 and not blocked:status.screenshot(path=str(SHOTS/'live-console-320.png'),full_page=True)
    assert not status.request.get(status_base+'/console.json?path=/etc/passwd').ok
    assert status.request.post(status_base+'/console.json').status==405
    assert status.evaluate('document.documentElement.scrollWidth<=document.documentElement.clientWidth')
    assert errors==[]
