# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Actual mobile/desktop library, calendar controls and independent scroll boxes.

Both loopback servers use synthetic data. Host status remains available after
Flask stops, with persisted escaped notes and the original safe-console polling.
"""
import os
import shutil
from threading import Thread
from uuid import uuid4
import pytest
from werkzeug.serving import make_server
from workout_tracker import create_app,catalog as c
from workout_tracker.storage import database_session
from workout_updater.engine import Engine,write_json
from workout_updater.console import Console
from workout_updater.service import status_app
from test_phase12 import phase12_data,phase11_root,phase9_root
pw=pytest.importorskip('playwright.sync_api')


@pytest.fixture
def phase12_page(phase12_data,tmp_path):
    """Serve application and independent host state without real updates or data."""
    root,client,a,b,r,e,item,saved,other=phase12_data
    app=create_app({'WORKOUT_DATA_ROOT':root,'WORKOUT_TIMEZONE':'America/Indiana/Indianapolis'})
    server=make_server('127.0.0.1',0,app,threaded=True);thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_port}'
    host=tmp_path/'host';(host/'updater').mkdir(parents=True)
    write_json(host/'updater/config.json',dict(status_url='http://127.0.0.1:8001/status',app_url=base))
    engine=Engine(host);operation=uuid4().hex
    notes='• A short readable improvement.\n• '+'LongToken'*55+' <script>window.noteInjected=true</script>'
    state=dict(status='Available',operation=operation,events=[dict(time='2026-11-10T12:00:00+00:00',status='Building image',message='Build step '+str(i)+' '+('long-console-token-'*24)) for i in range(70)],
               release=dict(id='a'*40,version='0.12.0',schema=8,source='Approved fixture',notes=notes,notes_version='0.12.0',notes_format=1))
    write_json(engine.state_path,state);console=Console(engine.state_dir,operation)
    for i in range(80):console.append('Build step '+str(i)+': '+('0123456789 '*35))
    independent=make_server('127.0.0.1',0,status_app(engine),threaded=True);worker=Thread(target=independent.serve_forever,daemon=True);worker.start()
    host_url=f'http://127.0.0.1:{independent.server_port}'
    bridge=root/'config/updater-bridge';bridge.mkdir();write_json(bridge/'client.json',dict(status_url=host_url+'/status'))
    from unittest.mock import patch
    try:
        with patch('workout_tracker.update_client.call',return_value=state),pw.sync_playwright() as manager:
            browser=manager.chromium.launch(headless=True,executable_path=os.environ.get('WORKOUT_CHROMIUM') or shutil.which('chromium'))
            try:
                page=browser.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
                yield page,base,host_url,root,a,b,r,e,item,server,console
            finally:browser.close()
    finally:
        server.shutdown();thread.join(5);server.server_close()
        independent.shutdown();worker.join(5);independent.server_close()


@pytest.mark.parametrize('width,height',[(320,740),(390,844),(844,390),(1280,900)])
def test_library_name_editing_ids_choices_and_month_ranges(phase12_page,width,height):
    """Visible names replace raw IDs while forms still submit permanent identities."""
    page,base,host_url,root,a,b,r,e,item,server,console=phase12_page;expect=pw.expect
    page.set_viewport_size(dict(width=width,height=height))
    page.goto(base+f'/people/{a}/exercises')
    listing=page.locator('.library-exercise').filter(has=page.get_by_role('heading',name='Weighted carry',exact=True))
    expect(listing.get_by_role('link',name='Edit Defaults',exact=True)).to_be_hidden()
    listing.get_by_role('button',name='Actions for Weighted carry',exact=True).click()
    expect(listing.get_by_role('link',name='Edit Defaults',exact=True)).to_be_visible()
    assert e not in page.locator('body').inner_text()
    expect(page.get_by_role('button',name='Rename exercise',exact=True)).to_have_count(0)
    listing.get_by_role('link',name='Edit Defaults',exact=True).click()
    expect(page.get_by_text('Library ID: '+e,exact=True)).to_be_visible()
    expect(page.get_by_text('Renaming changes this exercise’s name',exact=False)).to_be_visible()
    page.get_by_label('Exercise name',exact=True).fill('Household carry')
    page.get_by_label('Number of sets',exact=True).fill('3')
    page.get_by_role('button',name='Save changes',exact=True).click()
    expect(page.get_by_role('heading',name='Household carry',exact=True)).to_be_visible()
    page.goto(base+f'/people/{a}/routines/{r}')
    option=page.locator(f'#exercise-identity option[value="{e}"]')
    expect(option).to_have_text('Household carry')
    with database_session(root) as db:assert c.entry(db,a,r,item)['target_sets']==1
    page.goto(base+f'/people/{a}/progress?range=all&exercise={e}')
    expect(page.locator('.combined-progress .progress-chart')).to_have_count(2)
    for label in ('3 Months','6 Months','12 Months','24 Months','All Time'):
        page.get_by_role('button',name=label,exact=True).click()
        expect(page.get_by_role('button',name=label,exact=True)).to_have_attribute('aria-pressed','true')
        expect(page.get_by_label('Exercise',exact=True)).to_have_value(e)
        expect(page.locator('[name=from]')).to_have_count(0)
    page.reload();expect(page.get_by_role('button',name='All Time',exact=True)).to_have_attribute('aria-pressed','true')
    page.get_by_role('button',name='Custom Range',exact=True).click()
    page.get_by_label('From date',exact=True).fill('2020-01-01');page.get_by_label('To date',exact=True).fill('2020-01-01')
    with page.expect_navigation(wait_until='load'):page.get_by_role('button',name='Update progress',exact=True).click()
    page.reload();expect(page.locator('.progress-chart')).to_have_count(2)
    assert e not in page.locator('body').inner_text()
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')


@pytest.mark.parametrize('width,height',[(320,740),(390,844),(844,390),(1280,900)])
@pytest.mark.parametrize('theme',['light','dark'])
def test_notes_and_logs_scroll_inside_boxes_even_when_web_stops(phase12_page,width,height,theme):
    """Long text never enlarges the page; live console keeps original nonwrapped lines."""
    page,base,host_url,root,a,b,r,e,item,server,console=phase12_page;expect=pw.expect
    page.set_viewport_size(dict(width=width,height=height));page.emulate_media(color_scheme=theme)
    page.goto(base+f'/settings?person_id={a}');page.select_option('#theme',theme)
    page.goto(base+'/settings/updates')
    notes=page.get_by_role('region',name='Release notes',exact=True)
    log=page.get_by_role('log',name='Update status log',exact=True)
    for box in (notes,log):
        assert box.evaluate('(n)=>n.scrollWidth>n.clientWidth')
        box.evaluate('(n)=>n.scrollLeft=200');assert box.evaluate('(n)=>n.scrollLeft')>0
        bounds=box.bounding_box();assert bounds['x']>=0 and bounds['x']+bounds['width']<=width
    assert log.evaluate('(n)=>getComputedStyle(n).whiteSpace')=='pre'
    assert log.evaluate('(n)=>n.scrollHeight>n.clientHeight')
    assert page.evaluate('window.noteInjected') is None
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.goto(host_url+'/status')
    box=page.locator('#console');expect(box).to_contain_text('Build step 79')
    assert box.evaluate('(n)=>getComputedStyle(n).whiteSpace')=='pre'
    assert box.evaluate('(n)=>getComputedStyle(n).fontFamily').endswith('monospace')
    assert box.evaluate('(n)=>n.scrollWidth>n.clientWidth && n.scrollHeight>n.clientHeight')
    box.evaluate('(n)=>{n.scrollLeft=150;n.scrollTop=0}');assert box.evaluate('(n)=>n.scrollLeft')>0
    assert len(box.inner_text().splitlines())==80
    assert page.evaluate('window.noteInjected') is None
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    # Stop only this disposable Flask server. Host notes and live polling survive.
    server.shutdown();console.append('Build step 100: DONE 0.1s')
    expect(box).to_contain_text('Build step 100',timeout=6000)
    page.reload();expect(page.get_by_role('region',name='Release notes')).to_contain_text('short readable')
    expect(box).to_contain_text('Build step 100')
