# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Phase 12 UI contracts, rename transactions, calendar ranges and release metadata.

All reads/writes use synthetic households and disposable storage. Release tests
use approved-SHA-shaped fixtures, never external GitHub or production services.
"""
from datetime import date,datetime,timezone
import json
import os
from pathlib import Path
import re
import subprocess
from unittest.mock import patch
import pytest
from workout_tracker import create_app,catalog as c,history as h,workouts as w,progress_ranges as ranges
from workout_tracker.storage import database_session
from workout_updater.release_notes import read_notes
from workout_updater.engine import Engine,UpdateError
from test_combined import phase11_root,phase9_root,seed
from test_phase8_deletion import manual,token
from test_phase8_updater import fixture,REPO


@pytest.fixture
def phase12_data(phase11_root):
    """One completed paired workout freezes names/settings before Library edits."""
    root=phase11_root
    with database_session(root,write=True) as db:
        a,b,r,e,item=seed(db)
        saved,_=manual(db,a,r,'2020-01-01',weight_0='20',seconds_0='360')
        other=c.create_definition(db,a,'Existing name')
    client=create_app({'TESTING':True,'WORKOUT_DATA_ROOT':root,'WORKOUT_TIMEZONE':'America/Indiana/Indianapolis'}).test_client()
    return root,client,a,b,r,e,item,saved,other


def form_values(page,**changes):
    """Submit a valid combined preset with server-issued CSRF/revision tokens."""
    revision=re.search(r'name="revision" value="([^"]+)"',page.get_data(as_text=True))[1]
    values=dict(csrf_token=token(page),revision=revision,name='Renamed carry',measurement_type='weight_duration',target_sets='2',minutes='1',seconds='30',unit='lb',weight_meaning='total weight',notes='New default')
    values.update(changes);return values


def test_library_listing_detail_rename_snapshots_and_independent_settings(phase12_data):
    """The combined form renames the same identity without rewriting any snapshots."""
    root,client,a,b,r,e,item,saved,other=phase12_data
    path=f'/people/{a}/exercises';listing=client.get(path)
    visible=re.sub('<[^>]+>','',listing.get_data(as_text=True))
    assert 'Edit Defaults' in visible and e not in visible and 'Rename exercise' not in visible
    detail=client.get(path+f'/{e}/defaults');assert ('Library ID: '+e).encode() in detail.data
    with database_session(root) as db:
        before=[tuple(row) for row in db.execute('SELECT * FROM routine_exercises')]
        original=h.original(db,a,saved)
    result=client.post(path+f'/{e}/defaults',data=form_values(detail))
    assert result.status_code==303
    with database_session(root) as db:
        assert c.definition(db,b,e)['name']=='Renamed carry'
        assert [tuple(row) for row in db.execute('SELECT * FROM routine_exercises')]==before
        assert h.original(db,a,saved)==original
        assert c.exercise_defaults(db,a,e)['target_duration_seconds']==90
        assert c.entry(db,a,r,item)['exercise_id']==e
    routine=client.get(f'/people/{a}/routines/{r}').get_data(as_text=True)
    option=re.search(r'<option value="'+e+r'">([^<]+)</option>',routine)[1]
    assert option=='Renamed carry' and e not in option


def test_duplicate_invalid_and_stale_library_edits_roll_back(phase12_data):
    """Failed names/targets retain raw input and cannot commit a partial defaults edit."""
    root,client,a,b,r,e,item,saved,other=phase12_data;path=f'/people/{a}/exercises/{e}/defaults'
    page=client.get(path)
    with database_session(root) as db:before='\n'.join(db.iterdump())
    result=client.post(path,data=form_values(page,name='Existing NAME'))
    assert result.status_code==400 and b'already registered' in result.data and b'Existing NAME' in result.data
    with database_session(root) as db:assert '\n'.join(db.iterdump())==before
    result=client.post(path,data=form_values(page,name='Typed name',minutes='bad'))
    assert result.status_code==400 and b'Typed name' in result.data and b'value="bad"' in result.data
    assert client.post(path,data=form_values(page)).status_code==303
    stale=client.post(path,data=form_values(page,name='Stale name'))
    assert stale.status_code==400 and b'changed; reload' in stale.data
    with database_session(root) as db:assert c.definition(db,a,e)['name']=='Renamed carry'


def test_same_name_choices_remain_distinct_without_visible_ids():
    """Synthetic matching names get option numbers, not identity merging or repair."""
    rows=[dict(id='a'*32,name='Bench'),dict(id='b'*32,name='Bench'),dict(id='c'*32,name='Plank')]
    labels=c.exercise_labels(rows)
    assert labels[rows[0]['id']]=='Bench (option 1)' and labels[rows[1]['id']]=='Bench (option 2)'
    assert labels[rows[2]['id']]=='Plank' and all(identity not in label for identity,label in labels.items())
    assert c.exercise_labels(reversed(rows))==labels


@pytest.mark.parametrize('today,months,start',[
    (date(2024,3,31),3,'2024-01-01'),(date(2024,3,31),6,'2023-10-01'),
    (date(2024,3,31),12,'2023-04-01'),(date(2024,3,31),24,'2022-04-01'),
    (date(2024,5,31),3,'2024-03-01'),(date(2024,2,29),12,'2023-03-01'),
])
def test_calendar_month_ranges_and_clamping(today,months,start):
    """Each range is inclusive through local today, using clamped calendar months."""
    filters,selected,_=ranges.selection(dict(range=f'{months}m',exercise='owned'),today)
    assert filters['from']==start and filters['to']==today.isoformat() and selected==f'{months}m'
    assert filters['exercise']=='owned'


def test_default_iana_date_legacy_links_and_combined_filtering(phase12_data):
    """Default local date, old day bookmarks, both axes and ownership remain correct."""
    root,client,a,b,r,e,item,saved,other=phase12_data
    with patch.object(w,'now',return_value=datetime(2024,4,1,2,tzinfo=timezone.utc)):
        response=client.get(f'/people/{a}/progress')
        assert b'2024-01-01 through 2024-03-31' in response.data
        assert b'value="3m"' in response.data and b'30 Days' not in response.data
        legacy=client.get(f'/people/{a}/progress?range=30')
        assert legacy.status_code==200 and b'2024-03-02' in legacy.data and b'value="custom"' in legacy.data
    all_time=client.get(f'/people/{a}/progress?range=all&exercise={e}')
    assert all_time.data.count(b'class="progress-chart"')==2
    assert b'class="progress-chart"' not in client.get(f'/people/{b}/progress?range=all').data


def test_release_notes_version_fallback_validation_and_untrusted_text():
    """Only version-matched bounded text is accepted; no raw Git summaries are made."""
    notes=json.loads((REPO/'releases/0.12.0.json').read_text())
    assert read_notes('0.12.0',json.dumps(notes)).startswith('• Simplified')
    assert 'older release' in read_notes('0.11.0',None)
    with pytest.raises(ValueError,match='missing'):read_notes('0.12.0',None)
    for payload in ({'version':'0.11.0','notes':['Wrong release']},{'version':'0.12.0','notes':[]},{'version':'0.12.0','notes':['a\nb']},{'version':'0.12.0','notes':['x'*501]}):
        with pytest.raises(ValueError):read_notes('0.12.0',json.dumps(payload))
    assert '<script>' in read_notes('0.12.0',json.dumps(dict(version='0.12.0',notes=['<script>alert(1)</script>'])))


def test_host_fetches_notes_from_same_approved_sha_without_git_log(tmp_path):
    """Existing fixed-source host workflow previews real repository notes before install."""
    root,env=fixture(tmp_path,8);env.update(METADATA_VERSION='0.12.0',METADATA_SCHEMA='8')
    with patch.dict(os.environ,env,clear=True):release=Engine(root).check()
    assert release['notes_version']=='0.12.0' and release['notes_format']==1 and 'Simplified exercise' in release['notes']
    calls=[json.loads(line) for line in (root/'calls.jsonl').read_text().splitlines() if line]
    shows=[args[-1] for name,args in calls if name=='git' and 'show' in args]
    assert 'a'*40+':releases/0.12.0.json' in shows
    assert not any('log' in args for name,args in calls if name=='git')
    assert not (root/'stopped').exists()


def test_notes_escape_and_old_host_fallback_before_install(phase12_data):
    """Both old and new host results are safe display text, never executable HTML."""
    root,client,a,b,r,e,item,saved,other=phase12_data
    bridge=root/'config/updater-bridge';bridge.mkdir()
    (bridge/'client.json').write_text(json.dumps(dict(status_url='http://127.0.0.1:8001/status')))
    release=dict(id='a'*40,version='0.12.0',schema=8,source='Approved fixture',notes='<script>alert(1)</script>',notes_version='0.12.0',notes_format=1)
    state=dict(status='Available',events=[],release=release)
    with patch('workout_tracker.update_client.call',return_value=state):
        page=client.get('/settings/updates')
        assert b'&lt;script&gt;' in page.data and b'<script>alert(1)' not in page.data
        del release['notes_format']
        old=client.get('/settings/updates')
        assert b'older host updater' in old.data and b'alert(1)' not in old.data


@pytest.mark.parametrize('content',[
    '{"version":"0.12.0","version":"0.12.0","notes":["Duplicate key"]}',
    '{bad json}',
    json.dumps(dict(version='0.12.0',notes=['line\u2028break'])),
    json.dumps(dict(version='0.12.0',notes=['x']*21)),
    ' '*32769,
])
def test_malformed_or_oversized_notes_are_rejected(content):
    """Invalid release metadata never becomes an approved display/install summary."""
    with pytest.raises(ValueError):read_notes('0.12.0',content)
