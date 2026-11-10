# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Real touch/keyboard Library menus and CSS-only name truncation on synthetic data.

Loopback Flask serves disposable schema 8. Navigation must retain permanent IDs;
opening menus or editor/review pages must never write exercise/history records.
"""
import os
import shutil
from threading import Thread
import pytest
from werkzeug.serving import make_server
from workout_tracker import create_app,catalog as c
from workout_tracker.storage import database_session
from test_phase12 import phase12_data,phase11_root,phase9_root
pw=pytest.importorskip('playwright.sync_api')


@pytest.fixture
def library_page(phase12_data):
    """Supply short, spaced/punctuated and maximum-length names without real data."""
    root,client,a,b,r,e,item,saved,other=phase12_data
    names=['Bench','Single Arm Dumbbell Press — Left / Right','Weighted Carry: '+('W'*84)]
    with database_session(root,write=True) as db:
        identities=[c.create_definition(db,a,name) for name in names]
    server=make_server('127.0.0.1',0,create_app({'WORKOUT_DATA_ROOT':root}),threaded=True)
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with pw.sync_playwright() as manager:
            browser=manager.chromium.launch(headless=True,executable_path=os.environ.get('WORKOUT_CHROMIUM') or shutil.which('chromium'))
            try:
                page=browser.new_page(is_mobile=True,has_touch=True)
                yield page,f'http://127.0.0.1:{server.server_port}',root,a,dict(zip(names,identities))
            finally:browser.close()
    finally:server.shutdown();thread.join(5);server.server_close()


@pytest.mark.parametrize('width,height',[(320,740),(390,844),(844,390),(768,1024),(1280,900)])
@pytest.mark.parametrize('theme',['light','dark'])
def test_library_menu_geometry_accessibility_navigation_and_full_names(library_page,width,height,theme):
    """Every viewport keeps actions frontmost, keyboard accessible and identity-bound."""
    page,base,root,person,identities=library_page;expect=pw.expect
    page.set_viewport_size(dict(width=width,height=height))
    page.goto(base+f'/settings?person_id={person}');page.select_option('#theme',theme)
    path=base+f'/people/{person}/exercises'
    with database_session(root) as db:before='\n'.join(db.iterdump())
    for name,identity in identities.items():
        page.goto(path)
        card=page.locator('.library-exercise').filter(has=page.get_by_role('heading',name=name,exact=True))
        heading=card.get_by_role('heading',name=name,exact=True)
        trigger=card.get_by_role('button',name='Actions for '+name,exact=True)
        edit=card.get_by_role('link',name='Edit Defaults',exact=True)
        delete=card.get_by_role('link',name='Delete Exercise',exact=True)
        expect(edit).to_be_hidden();expect(delete).to_be_hidden()
        expect(trigger).to_have_attribute('aria-expanded','false')
        expect(heading).to_have_attribute('title',name)
        trigger.scroll_into_view_if_needed();h=heading.bounding_box();t=trigger.bounding_box()
        assert h['x']<t['x'] and h['x']+h['width']<=t['x']
        assert abs(h['y']+h['height']/2-t['y']-t['height']/2)<2
        assert t['width']>=44 and t['height']>=44 and t['x']+t['width']<=width
        assert heading.evaluate('(n)=>getComputedStyle(n).whiteSpace')=='nowrap'
        assert heading.evaluate('(n)=>getComputedStyle(n).textOverflow')=='ellipsis'
        if name.startswith('Weighted Carry:'):
            assert heading.evaluate('(n)=>n.scrollWidth>n.clientWidth')
        trigger.click();expect(trigger).to_have_attribute('aria-expanded','true')
        panel=card.locator('.library-menu');box=panel.bounding_box()
        assert 0<=box['x'] and box['x']+box['width']<=width
        assert 0<=box['y'] and box['y']+box['height']<=height
        for link in (edit,delete):
            expect(link).to_be_visible()
            assert link.evaluate('(n)=>{const r=n.getBoundingClientRect();return n.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2))}')
        assert delete.get_attribute('href').endswith('/permanent-delete/exercise/'+identity)
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        # Toggle, outside click and Escape all close the same disclosure.
        trigger.click();expect(edit).to_be_hidden();trigger.click()
        page.get_by_role('heading',name='Exercise Library',exact=True).click();expect(edit).to_be_hidden()
        trigger.focus();page.keyboard.press('ArrowDown');expect(edit).to_be_focused()
        page.keyboard.press('Escape');expect(trigger).to_be_focused();expect(edit).to_be_hidden()
        trigger.press('Enter');page.keyboard.press('Tab');expect(edit).to_be_focused()
        page.keyboard.press('Tab');expect(delete).to_be_focused()
        page.keyboard.press('Escape');expect(trigger).to_have_attribute('aria-expanded','false')
        trigger.click();edit.click()
        expect(page.get_by_label('Exercise name',exact=True)).to_have_value(name)
        assert page.url.endswith('/exercises/'+identity+'/defaults')
        page.goto(path);card.get_by_role('button',name='Actions for '+name,exact=True).click()
        card.get_by_role('link',name='Delete Exercise',exact=True).click()
        expect(page.get_by_role('heading',name='Permanently Delete '+name+'?',exact=True)).to_be_visible()
        page.get_by_role('link',name='Cancel',exact=True).click()
    # Opening another row closes the old one, including its aria state.
    first=page.get_by_role('button',name='Actions for Bench',exact=True)
    second=page.get_by_role('button',name='Actions for '+list(identities)[1],exact=True)
    first.click();second.click();expect(first).to_have_attribute('aria-expanded','false')
    expect(second).to_have_attribute('aria-expanded','true')
    expect(page.locator('.library-menu:visible')).to_have_count(1)
    page.keyboard.press('Escape');expect(second).to_be_focused()
    with database_session(root) as db:assert '\n'.join(db.iterdump())==before
