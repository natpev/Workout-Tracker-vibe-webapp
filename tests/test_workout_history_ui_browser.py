# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Real focused typing, responsive History filters and compact workout emphasis.

Loopback HTTP and disposable schema 8 cover touch-capable Chromium. This validates
inputmode hints, not the physical iPhone operating system's keyboard rendering.
"""
import os
import shutil
from threading import Thread
import pytest
from werkzeug.serving import make_server
from workout_tracker import create_app,workouts as w
from workout_tracker.storage import database_session
from test_workout_history_ui import ui_data,phase11_root,phase9_root,ZONE
pw=pytest.importorskip('playwright.sync_api')


@pytest.fixture
def ui_page(ui_data):
    """Serve all three exercise modes with previous performance and a DST record."""
    root,a,b,r,saved,review=ui_data
    server=make_server('127.0.0.1',0,create_app({'WORKOUT_DATA_ROOT':root,'WORKOUT_TIMEZONE':ZONE}),threaded=True)
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with pw.sync_playwright() as manager:
            browser=manager.chromium.launch(headless=True,executable_path=os.environ.get('WORKOUT_CHROMIUM') or shutil.which('chromium'))
            try:
                page=browser.new_page(is_mobile=True,has_touch=True)
                page.on('dialog',lambda dialog:dialog.accept())
                yield page,f'http://127.0.0.1:{server.server_port}',root,a,b,r,saved,review
            finally:browser.close()
    finally:server.shutdown();thread.join(5);server.server_close()


@pytest.mark.parametrize('width,height',[(320,844),(390,844),(844,390),(768,1024),(1280,900)])
@pytest.mark.parametrize('theme',['light','dark'])
def test_readable_workouts_zone_free_history_and_responsive_filters(ui_page,width,height,theme):
    """Scoped date fields stack only when narrow; all modes retain prominent references."""
    page,base,root,a,b,r,saved,review=ui_page;expect=pw.expect
    page.set_viewport_size(dict(width=width,height=height))
    page.goto(base+f'/settings?person_id={a}');page.select_option('#theme',theme)
    page.goto(base+f'/people/{a}/history')
    assert ZONE not in page.locator('body').inner_text()
    start=page.get_by_label('From date',exact=True);end=page.get_by_label('To date',exact=True)
    x=start.bounding_box();y=end.bounding_box()
    if width<=390:assert y['y']>=x['y']+x['height'] and abs(x['x']-y['x'])<1
    else:assert abs(x['y']-y['y'])<1 and y['x']>=x['x']+x['width']
    assert x['width']>=200 and y['width']>=200
    start.fill('2020-11-01');end.fill('2020-11-01');page.get_by_role('button',name='Filter history',exact=True).click()
    expect(start).to_have_value('2020-11-01');expect(end).to_have_value('2020-11-01')
    expect(page.locator('.history-record')).to_have_count(1)
    start.fill('2020-11-02');end.fill('2020-11-02');page.get_by_role('button',name='Filter history',exact=True).click()
    expect(page.locator('.history-record')).to_have_count(0)
    for path in (f'/people/{a}/history/{saved}',f'/people/{a}/history/{saved}/correct',f'/people/{a}/historical/{review}',f'/people/{a}/historical'):
        page.goto(base+path);assert ZONE not in page.locator('body').inner_text()
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.goto(base+f'/people/{a}/history/{saved}');page.get_by_text('Timing diagnostics',exact=True).click()
    expect(page.get_by_text('Stored time zone: '+ZONE,exact=True)).to_be_visible()
    with database_session(root,write=True) as db:draft,_=w.start(db,a,r,ZONE)
    for position,previous in enumerate(('40.9 lb','00:45','20.0 lb total weight · 6:00')):
        page.goto(base+f'/people/{a}/workouts/{draft}?position={position}')
        target=page.locator('.target');measurement=page.locator('.previous-line strong')
        expect(measurement).to_contain_text(previous)
        if position==0:expect(target).to_contain_text('per hand')
        if position==2:expect(target).to_contain_text('total weight')
        assert target.evaluate('(n)=>parseFloat(getComputedStyle(n).fontSize)')>=16
        assert target.evaluate('(n)=>parseInt(getComputedStyle(n).fontWeight)')>=650
        assert measurement.evaluate('(n)=>parseFloat(getComputedStyle(n).fontSize)')>=18
        assert measurement.evaluate('(n)=>parseInt(getComputedStyle(n).fontWeight)')>=700
        assert target.evaluate('(n)=>parseFloat(getComputedStyle(n).marginBottom)')<=12
        assert target.evaluate('(n)=>getComputedStyle(n).color')==page.locator('.exercise-card').evaluate('(n)=>getComputedStyle(n).color')
        expect(page.get_by_text('Increase ↑',exact=True)).to_be_visible()
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')


@pytest.mark.parametrize('position',[0,2])
@pytest.mark.parametrize('width',[320,390])
def test_weight_typing_keeps_text_cursor_node_and_validated_normalization(ui_page,position,width):
    """Slow/fast typing and acknowledged saves never rewrite a focused weight field."""
    page,base,root,a,b,r,saved,review=ui_page;expect=pw.expect
    page.set_viewport_size(dict(width=width,height=844))
    with database_session(root,write=True) as db:draft,_=w.start(db,a,r,ZONE)
    page.goto(base+f'/people/{a}/workouts/{draft}?position={position}')
    weight=page.get_by_label('Weight (lb)',exact=True);status=page.locator('#save-status')
    if position==2:page.get_by_label('Seconds',exact=True).fill('60')
    expect(weight).to_have_attribute('inputmode','decimal');expect(weight).to_have_attribute('type','text')
    weight.focus();page.evaluate('window.originalWeight=document.querySelector("[name=weight]")')
    weight.press_sequentially('40',delay=450)
    expect(status).to_have_text('✓ Saved');expect(weight).to_have_value('40')
    assert weight.evaluate('(n)=>n===window.originalWeight && n.selectionStart===2 && document.activeElement===n')
    weight.blur();expect(weight).to_have_value('40.0')
    for raw,normal in [('42.5','42.5'),('100','100.0'),('0','0.0'),('0.5','0.5'),('40.99','40.9')]:
        weight.focus();weight.press('ControlOrMeta+A');weight.press_sequentially(raw,delay=10)
        expect(status).to_have_text('✓ Saved');expect(weight).to_have_value(raw)
        assert weight.evaluate('(n)=>n.selectionStart')==len(raw)
        weight.blur();expect(weight).to_have_value(normal)
    weight.fill('42.5');expect(status).to_have_text('✓ Saved')
    weight.press('End');weight.press('Backspace');expect(weight).to_have_value('42.')
    weight.press('Backspace');weight.press('Backspace');expect(status).to_have_text('✓ Saved');expect(weight).to_have_value('4')
    weight.press('ControlOrMeta+A');weight.press_sequentially('100');expect(status).to_have_text('✓ Saved')
    weight.evaluate('(n)=>n.setSelectionRange(1,1)');weight.press_sequentially('.')
    expect(status).to_have_text('✓ Saved');expect(weight).to_have_value('1.00')
    assert weight.evaluate('(n)=>n.selectionStart')==2
    for invalid in ('.','1e2','-2'):
        weight.fill(invalid);expect(status).to_have_text('Save failed');expect(weight).to_have_value(invalid)
        weight.blur();expect(weight).to_have_value(invalid)
    with database_session(root) as db:assert w.entries(db,a,draft)[position]['actual_weight_tenths_lb']==10
    weight.fill('')
    if position==2:
        expect(status).to_have_text('Save failed')
        page.get_by_label('Minutes',exact=True).fill('');page.get_by_label('Seconds',exact=True).fill('')
    expect(status).to_have_text('✓ Saved')
    with database_session(root) as db:
        entry=w.entries(db,a,draft)[position]
        assert entry['actual_weight_tenths_lb'] is None and entry['actual_duration_seconds'] is None
    if position==2:page.get_by_label('Seconds',exact=True).fill('60')
    weight.fill('42.56');expect(status).to_have_text('✓ Saved');expect(weight).to_have_value('42.56')
    page.get_by_role('link',name='Next',exact=True).click()
    expect(page.locator('#workout-progress')).to_have_attribute('value',str(position+1))
    page.get_by_role('link',name='Back',exact=True).click();expect(weight).to_have_value('42.5')
    page.reload();expect(weight).to_have_value('42.5')
    page.get_by_text('More',exact=True).click();page.get_by_role('button',name='Exit Workout',exact=True).click()
    page.get_by_role('link',name='Resume or discard unfinished workout',exact=True).click()
    page.get_by_role('link',name='Resume workout',exact=True).click()
    # Resume uses the furthest Next checkpoint. Back returns to the saved value.
    page.get_by_role('link',name='Back',exact=True).click();expect(weight).to_have_value('42.5')
    page.get_by_role('button',name='Finish & Save',exact=True).click()
    expect(page.get_by_role('heading',name='Workout saved',exact=True)).to_be_visible()
    with database_session(root) as db:assert w.session(db,a,draft)['status']=='completed'
