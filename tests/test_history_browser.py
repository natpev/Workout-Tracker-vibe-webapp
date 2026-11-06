# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""Chromium history workflow uses loopback Flask and disposable schema 4 only.

Browser forms exercise server validation, independent historical completion,
append-only corrections, local SVG charts, filters, themes and phone layout.
"""

import os
import shutil
from threading import Thread

import pytest
from werkzeug.serving import make_server

from workout_tracker import create_app, catalog as c, workouts as w
from workout_tracker.storage import database_session

pw=pytest.importorskip('playwright.sync_api')


@pytest.fixture
def history_page(phase4_root):
    """Serve one person's routine alongside an active draft to verify independence."""
    with database_session(phase4_root,write=True) as db:
        person=c.create_person(db,'History fixture');routine=c.create_routine(db,person,'Mixed')
        c.add_entry(db,person,routine,dict(name='Bench',measurement_type='weight',target_sets='3',target_reps='12',notes='Original note'))
        c.add_entry(db,person,routine,dict(name='Plank',measurement_type='time',target_sets='3',minutes='0',seconds='45'))
        draft,_=w.start(db,person,routine,'UTC')
    server=make_server('127.0.0.1',0,create_app({'WORKOUT_DATA_ROOT':phase4_root,'WORKOUT_TIMEZONE':'UTC'}))
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with pw.sync_playwright() as manager:
            browser=manager.chromium.launch(headless=True,executable_path=os.environ.get('WORKOUT_CHROMIUM') or shutil.which('chromium'))
            try:
                context=browser.new_context(viewport={'width':320,'height':800})
                page=context.new_page()
                address=f'http://127.0.0.1:{server.server_port}'
                page.goto(address+f'/people/{person}/history')
                yield page,address,person,draft,phase4_root
            finally: browser.close()
    finally:
        server.shutdown();thread.join(timeout=5);server.server_close()


def test_historical_entry_correction_charts_filters_themes_and_snapshot(history_page):
    """Use the actual phone UI to enter, correct, filter and graph a past workout."""
    page,address,person,draft,root=history_page;expect=pw.expect
    errors=[];requests=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.on('request',lambda request:requests.append(request.url))
    page.get_by_role('link',name='Enter historical workout',exact=True).click()
    page.get_by_label('Workout date',exact=True).fill('2020-01-02')
    page.get_by_role('button',name='Prepare historical workout',exact=True).click()
    expect(page.get_by_role('heading',name='Review historical workout',exact=True)).to_be_visible()
    page.get_by_label('Weight for Bench (lb)',exact=True).fill('40.99')
    page.get_by_label('Minutes for Plank',exact=True).fill('1')
    page.get_by_label('Seconds for Plank',exact=True).fill('5')
    page.get_by_role('button',name='Save historical workout',exact=True).click()
    expect(page.get_by_role('heading',name='Mixed — saved workout',exact=True)).to_be_visible()
    expect(page.locator('.measurement')).to_have_text(['40.9 lb','1:05'])
    detail=page.url
    page.get_by_role('link',name='Correct saved workout',exact=True).click()
    correction=page.url
    other=page.context.new_page();other.goto(correction)
    page.get_by_label('Weight for Bench (lb)',exact=True).fill('0')
    page.get_by_label('Workout date',exact=True).fill('2021-02-03')
    page.get_by_label('I confirm these corrections and understand original records are retained').check()
    page.get_by_role('button',name='Apply correction',exact=True).click()
    expect(page.locator('.measurement')).to_have_text(['0.0 lb','1:05'])
    expect(page.get_by_text('Correction 1',exact=False)).to_be_visible()
    other.get_by_label('Weight for Bench (lb)',exact=True).fill('99')
    other.get_by_label('I confirm these corrections and understand original records are retained').check()
    other.get_by_role('button',name='Apply correction',exact=True).click()
    expect(other.get_by_role('alert')).to_contain_text('corrected in another page')
    page.get_by_role('link',name='Progress charts',exact=True).click()
    expect(page.locator('.progress-series')).to_have_count(2)
    expect(page.locator('circle.chart-point')).to_have_count(2)
    expect(page.get_by_text('0.0 lb',exact=True).first).to_be_visible()
    expect(page.get_by_text('Longest logged duration',exact=False)).to_contain_text('1:05')
    chart_url=page.url
    page.goto(address+'/settings')
    for theme in ('light','dark','auto'):
        page.select_option('#theme',theme);page.reload();expect(page.locator('#theme')).to_have_value(theme)
    page.goto(chart_url)
    for width in (320,768,1280):
        page.set_viewport_size({'width':width,'height':800})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.get_by_label('From date',exact=True).fill('2022-01-01')
    page.get_by_role('button',name='Update progress',exact=True).click()
    expect(page.locator('.progress-series')).to_have_count(0)
    page.get_by_role('link',name='History',exact=True).click()
    page.get_by_label('From date',exact=True).fill('2021-01-01')
    page.get_by_label('To date',exact=True).fill('2021-12-31')
    page.get_by_role('button',name='Filter history',exact=True).click()
    expect(page.locator('.history-record')).to_have_count(1)
    with database_session(root) as db:
        assert w.active(db,person)['id']==draft
        assert db.execute('SELECT count(*) FROM historical_workouts').fetchone()[0]==1
        assert db.execute('SELECT count(*) FROM workout_corrections').fetchone()[0]==1
    assert errors==[]
    assert all(url.startswith(address) for url in requests)


def test_skipped_historical_confirmation_and_chart_exclusion(history_page):
    """Skipped rows stay visible in history but produce no numerical chart points."""
    page,_,_,_,_=history_page;expect=pw.expect
    page.get_by_role('link',name='Enter historical workout',exact=True).click()
    page.get_by_label('Workout date',exact=True).fill('2020-01-01')
    page.get_by_role('button',name='Prepare historical workout',exact=True).click()
    page.get_by_label('Confirm saving an entirely skipped workout, if all measurements are blank').check()
    page.get_by_role('button',name='Save historical workout',exact=True).click()
    expect(page.locator('.measurement')).to_have_text(['Skipped','Skipped'])
    page.get_by_role('link',name='Progress charts',exact=True).click()
    expect(page.locator('.progress-series')).to_have_count(2)
    expect(page.locator('circle.chart-point')).to_have_count(0)
    page.get_by_text('Chart data (including skipped entries)',exact=True).first.click()
    expect(page.get_by_text('Skipped',exact=False).first).to_be_visible()
