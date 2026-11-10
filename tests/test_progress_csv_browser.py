# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Actual navigation autosaves, setting-scope notes and CSV download on fixtures."""
import csv
from io import StringIO
import pytest
from workout_tracker import catalog as c
from workout_tracker.storage import database_session
from test_workout_browser import workout_page
from test_phase10_browser import phase10_page
from test_phase9 import phase9_root

pw=pytest.importorskip('playwright.sync_api')
ROUTINE_NOTE='These settings apply only to this routine. Changes will not affect Exercise Library defaults or other routines.'
LIBRARY_NOTE='These are the default settings for this exercise. Changes will apply to newly added routine exercises. Existing routines will not change.'


@pytest.mark.parametrize('width',[320,1280])
def test_navigation_bar_ignores_measurements_and_counts_skipped_next(workout_page,width):
    """Real acknowledged saves never move the bar; Next checkpoint survives revisits."""
    page,path,root=workout_page;expect=pw.expect
    page.set_viewport_size({'width':width,'height':844})
    progress=page.locator('#workout-progress')
    page.get_by_label('Weight (lb)').fill('40.99')
    expect(page.locator('#save-status')).to_have_text('✓ Saved')
    expect(progress).to_have_attribute('value','0')
    page.get_by_label('Increase weight next time',exact=True).check()
    expect(page.locator('#save-status')).to_have_text('✓ Saved');expect(progress).to_have_attribute('value','0')
    page.get_by_label('Weight (lb)').fill('')
    expect(page.locator('#save-status')).to_have_text('✓ Saved')
    page.get_by_role('link',name='Next',exact=True).click()
    expect(progress).to_have_attribute('value','1')
    page.get_by_label('Seconds',exact=True).fill('45')
    expect(page.locator('#save-status')).to_have_text('✓ Saved');expect(progress).to_have_attribute('value','1')
    page.get_by_label('Increase duration next time',exact=True).check()
    expect(page.locator('#save-status')).to_have_text('✓ Saved');expect(progress).to_have_attribute('value','1')
    page.get_by_role('link',name='Back',exact=True).click()
    expect(page.get_by_role('heading',name='Bench',exact=True)).to_be_visible()
    expect(progress).to_have_attribute('value','1')
    page.reload();expect(progress).to_have_attribute('value','1')
    page.get_by_role('link',name='Next',exact=True).click()
    expect(page.get_by_role('heading',name='Plank',exact=True)).to_be_visible()
    expect(progress).to_have_attribute('value','1')
    page.get_by_text('More',exact=True).click();page.select_option('#exercise-jump','0')
    expect(page.get_by_role('heading',name='Bench',exact=True)).to_be_visible()
    expect(progress).to_have_attribute('value','1')
    with page.expect_navigation(wait_until='load'):
        page.get_by_role('button',name='Save draft',exact=True).click()
    expect(page.get_by_role('heading',name='Bench',exact=True)).to_be_visible()
    expect(progress).to_have_attribute('value','1')
    page.get_by_role('link',name='Next',exact=True).click()
    expect(page.get_by_role('heading',name='Plank',exact=True)).to_be_visible()
    page.get_by_role('button',name='Finish & Save',exact=True).click()
    expect(page.get_by_role('heading',name='Workout saved',exact=True)).to_be_visible()
    with database_session(root) as db:
        assert db.execute("SELECT status FROM workout_sessions").fetchone()[0]=='completed'
        rows=db.execute('SELECT actual_weight_tenths_lb,actual_duration_seconds FROM workout_entries ORDER BY position').fetchall()
        assert rows[0][0] is None and rows[1][1]==45


@pytest.mark.parametrize('width',[320,1280])
def test_export_selection_ranges_download_and_scope_notes(phase10_page,tmp_path,width):
    """Export is a real attachment; range/selection and correct scope notes survive."""
    page,base,root,a,b,r,e,saved,draft=phase10_page;expect=pw.expect
    page.set_viewport_size({'width':width,'height':844})
    with database_session(root) as db:
        item=db.execute('SELECT id FROM routine_exercises WHERE routine_id=? ORDER BY position',(r,)).fetchone()[0]
        before=[tuple(row) for row in db.execute('SELECT * FROM routine_exercises ORDER BY id')]
    page.goto(base+f'/people/{a}/routines/{r}/items/{item}')
    expect(page.get_by_text(ROUTINE_NOTE,exact=True)).to_be_visible()
    page.goto(base+f'/people/{a}/routines/{r}')
    expect(page.get_by_text(ROUTINE_NOTE,exact=True)).to_be_visible()
    page.goto(base+f'/people/{a}/exercises/{e}/defaults')
    expect(page.get_by_text(LIBRARY_NOTE,exact=True)).to_be_visible()
    page.get_by_label('Number of sets',exact=True).fill('8')
    page.get_by_role('button',name='Save changes',exact=True).click()
    with database_session(root) as db:
        assert [tuple(row) for row in db.execute('SELECT * FROM routine_exercises ORDER BY id')]==before
    page.goto(base+f'/people/{a}/exercises')
    expect(page.get_by_text(LIBRARY_NOTE,exact=True)).to_be_visible()
    page.goto(base+f'/people/{a}/progress')
    page.get_by_text('CSV export — choose exercises',exact=True).click()
    page.get_by_role('button',name='Export CSV',exact=True).click()
    expect(page.get_by_role('alert')).to_contain_text('Select at least one')
    page.get_by_role('button',name='Select All',exact=True).click()
    assert page.locator('[name=export_exercise]:checked').count()==2
    page.get_by_role('button',name='All Time',exact=True).click()
    expect(page.get_by_role('button',name='All Time',exact=True)).to_have_attribute('aria-pressed','true')
    page.get_by_text('CSV export — choose exercises',exact=True).click()
    assert page.locator('[name=export_exercise]:checked').count()==2
    with page.expect_download() as download:
        page.get_by_role('button',name='Export CSV',exact=True).click()
    target=tmp_path/'export.csv';download.value.save_as(target)
    data=list(csv.reader(StringIO(target.read_text(encoding='utf-8-sig'))))
    assert data[0][:4]==['Date','Time','Routine','Workout ID'] and len(data)==4
    assert any('Weight (lb)' in field for field in data[0]) and any('Duration' in field for field in data[0])
    assert download.value.suggested_filename.startswith('workout-progress-')
    page.get_by_role('button',name='Clear Selection',exact=True).click()
    assert page.locator('[name=export_exercise]:checked').count()==0
    expect(page.get_by_role('button',name='All Time',exact=True)).to_have_attribute('aria-pressed','true')
    assert page.evaluate('document.documentElement.scrollWidth<=document.documentElement.clientWidth')
