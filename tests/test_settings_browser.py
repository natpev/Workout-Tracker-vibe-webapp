# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""Chromium recovery controls run on loopback against disposable household storage.

Actual forms exercise explicit confirmation, persistent settings, safe logs and
phone/desktop themes. No external services or production data are contacted.
"""
import os
import shutil
from threading import Thread

import pytest
from werkzeug.serving import make_server
from workout_tracker import create_app,diagnostics as d

pw=pytest.importorskip('playwright.sync_api')


@pytest.fixture
def settings_page(phase4_root):
    """Serve a synthetic schema-4 instance and launch local headless Chromium."""
    app=create_app({'WORKOUT_DATA_ROOT':phase4_root,'WORKOUT_TIMEZONE':'UTC','TESTING':True})
    server=make_server('127.0.0.1',0,app);thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with pw.sync_playwright() as manager:
            browser=manager.chromium.launch(headless=True,executable_path=os.environ.get('WORKOUT_CHROMIUM') or shutil.which('chromium'))
            try:
                page=browser.new_page(viewport={'width':320,'height':800});base=f'http://127.0.0.1:{server.server_port}'
                page.goto(base+'/settings');yield page,base,phase4_root
            finally: browser.close()
    finally: server.shutdown();thread.join(5);server.server_close()


def test_backup_restore_confirmation_delete_themes_and_responsive(settings_page):
    """Complete a verified backup/restore/delete through touch-sized local forms."""
    page,base,root=settings_page;expect=pw.expect;errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
    expect(page.get_by_label('Enable automatic backups',exact=True)).not_to_be_checked()
    page.get_by_role('button',name='Backup Now',exact=True).click()
    expect(page.locator('#backup-status')).to_have_text('verified')
    backup_url=page.url
    for theme in ('light','dark','auto'):
        page.select_option('#theme',theme);page.reload();expect(page.locator('#theme')).to_have_value(theme)
    for width in (320,768,1280):
        page.set_viewport_size({'width':width,'height':800});assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.get_by_label('I understand this selects an earlier dataset and preserves the current database separately',exact=True).check()
    page.get_by_label('Type RESTORE to confirm',exact=True).fill('RESTORE')
    page.get_by_role('button',name='Restore Backup',exact=True).click()
    expect(page.get_by_role('heading',name='Restore result',exact=True)).to_be_visible()
    expect(page.locator('[role="status"]:not(#theme-status)')).to_have_text('succeeded')
    page.goto(backup_url)
    page.get_by_label('I confirm deleting this backup file',exact=True).check()
    page.get_by_role('button',name='Delete backup permanently',exact=True).click()
    expect(page.get_by_role('heading',name='Settings',exact=True)).to_be_visible()
    expect(page.get_by_text('deleted',exact=True)).to_be_visible()
    assert not errors


def test_schedule_persistence_log_filters_and_error_details(settings_page):
    """Configure scheduling through UI, then filter/expand safe persistent diagnostics."""
    page,base,root=settings_page;expect=pw.expect
    page.get_by_label('Enable automatic backups',exact=True).check()
    page.get_by_label('Frequency in whole days',exact=True).fill('3')
    page.get_by_label('Backup time',exact=True).fill('14:35')
    page.get_by_label('IANA timezone',exact=True).fill('America/New_York')
    page.get_by_label('Log retention in whole days',exact=True).fill('45')
    page.get_by_role('button',name='Save settings',exact=True).click();page.reload()
    expect(page.get_by_label('Enable automatic backups',exact=True)).to_be_checked()
    expect(page.get_by_label('Frequency in whole days',exact=True)).to_have_value('3')
    try: raise RuntimeError('private csrf_token=hidden /secret/database')
    except RuntimeError as error: d.emit(root,'ERROR','Backup','Synthetic backup error',error=error)
    page.get_by_role('link',name='View logs',exact=True).click()
    page.get_by_label('Severity',exact=True).select_option('ERROR')
    page.get_by_label('Category',exact=True).select_option('Backup')
    page.get_by_label('Search log text',exact=True).fill('Synthetic')
    page.get_by_role('button',name='Filter / Refresh logs',exact=True).click()
    expect(page.locator('.log-entry')).to_have_count(1)
    page.get_by_text('Error details',exact=True).click()
    expect(page.get_by_text('Operation failed. Inspect protected server logs for technical frames.',exact=True)).to_be_visible()
    assert 'hidden' not in page.content() and str(root) not in page.content()
