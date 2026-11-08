# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""Phase 9 synthetic defaults, migration, administration, clock and asset checks.

Every database is disposable. Old-cell and byte comparisons protect routine,
draft, audit and NULL/zero history across the explicit schema-7 upgrade.
"""
import hashlib
import json
from pathlib import Path
import struct
from unittest.mock import patch
from uuid import uuid4
import xml.etree.ElementTree as ET

import pytest
from flask import abort
from workout_tracker import create_app,catalog as c,history as h,workouts as w,maintenance as m
from workout_tracker.storage import database_session,inspect_storage,StorageError
from workout_tracker.migrations import migrate_storage
from workout_tracker.presentation import clock,timestamp
from workout_tracker import preferences
from test_phase8_deletion import household,manual,token,selected


@pytest.fixture
def phase9_root(phase4_root):
    """Explicitly upgrade a disposable root, never initialized by application startup."""
    migrate_storage(phase4_root,7)
    return phase4_root


def test_schema7_preserves_every_existing_cell_and_original_bytes(phase4_root):
    """Candidate upgrade adds neutral defaults without choosing a person's routine."""
    root=phase4_root;migrate_storage(root,6)
    with database_session(root,write=True) as db:
        a,b,r,other,e=household(db);saved,_=manual(db,a,r,'2020-01-01',weight_0='0')
        w.start(db,b,other,'America/Indiana/Indianapolis')
        names=[row[0] for row in db.execute("SELECT name FROM sqlite_schema WHERE type='table'")]
        before={name:[tuple(row) for row in db.execute(f'SELECT * FROM {name} ORDER BY 1')] for name in names}
    original=selected(root);data=original.read_bytes()
    result=migrate_storage(root,7);assert result['changed']
    assert original.read_bytes()==data and selected(root)!=original
    with database_session(root) as db:
        for name,rows in before.items():
            actual=[tuple(row) for row in db.execute(f'SELECT * FROM {name} ORDER BY 1')]
            assert (actual[:-1] if name=='schema_migrations' else actual)==rows
        assert db.execute('SELECT count(*) FROM exercise_defaults').fetchone()[0]==db.execute('SELECT count(*) FROM exercises').fetchone()[0]
        assert not db.execute('PRAGMA foreign_key_check').fetchall()
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    current=selected(root);unchanged=current.read_bytes()
    assert not migrate_storage(root,7)['changed'] and current.read_bytes()==unchanged


@pytest.mark.parametrize('failure',['ddl','validate','activate'])
def test_schema7_failure_never_changes_original(phase4_root,failure):
    """Faults before selection leave schema 6 active and retain its exact bytes."""
    root=phase4_root;migrate_storage(root,6)
    original=selected(root);before=original.read_bytes()
    manifest=(root/'config/active.json').read_bytes()
    target={'ddl':'workout_tracker.defaults_schema.upgrade_defaults','validate':'workout_tracker.migrations._validate_candidate','activate':'workout_tracker.migrations._write_manifest'}[failure]
    with patch(target,side_effect=RuntimeError('Synthetic schema7 failure')),pytest.raises((RuntimeError,StorageError)):
        migrate_storage(root,7)
    assert original.read_bytes()==before and (root/'config/active.json').read_bytes()==manifest
    assert inspect_storage(root)['schema_version']==6


def test_defaults_copy_once_and_routines_remain_independent(phase9_root):
    """Shared preset IDs/settings never copy actual results or rewrite old routines."""
    with database_session(phase9_root,write=True) as db:
        a=c.create_person(db,'A');b=c.create_person(db,'B')
        exercise=c.create_definition(db,a,'Global plank',dict(measurement_type='time',target_sets='4',minutes='',seconds='120',notes='Brace'))
        x=c.create_routine(db,a,'A');y=c.create_routine(db,b,'B')
        one=c.add_entry(db,a,x,dict(exercise_id=exercise,use_library_defaults='yes'))
        two=c.add_entry(db,b,y,dict(exercise_id=exercise,use_library_defaults='yes'))
        assert c.entry(db,a,x,one)['target_duration_seconds']==120
        c.update_entry(db,a,x,one,dict(measurement_type='time',target_sets='2',minutes='1',seconds='90'))
        c.update_defaults(db,b,exercise,dict(measurement_type='weight',target_sets='5',target_reps='8',unit='lb',weight_meaning='Per hand',notes='New preset'))
        assert c.entry(db,b,y,two)['target_sets']==4 and c.entry(db,b,y,two)['measurement_type']=='time'
        assert c.entry(db,a,x,one)['target_duration_seconds']==150
        three=c.add_entry(db,b,y,dict(exercise_id=exercise,use_library_defaults='yes'))
        row=c.entry(db,b,y,three);assert row['measurement_type']=='weight' and row['target_sets']==5 and row['weight_meaning']=='Per hand'
        copied=c.copy_routine(db,a,x,b,'Independent copy')
        copy=db.execute('SELECT * FROM routine_exercises WHERE routine_id=?',(copied,)).fetchone()
        assert copy['exercise_id']==exercise and copy['target_sets']==2 and copy['target_duration_seconds']==150
        with pytest.raises(c.ValidationError):c.update_defaults(db,a,exercise,dict(measurement_type='weight',target_sets='1',target_reps='2',unit='kg'))


@pytest.mark.parametrize('minutes,seconds,total',[('','120',120),('1','90',150),('2','',120),('','45',45),('3','150',330),('0','75',75),('5','0',300),('','',None)])
def test_duration_parts_normalize_everywhere(minutes,seconds,total):
    """Actual values and target presets share positive normalized total semantics."""
    assert w.duration_seconds(minutes,seconds)==total
    values=dict(measurement_type='time',target_sets='3',minutes=minutes,seconds=seconds)
    if total is None:
        with pytest.raises(c.ValidationError):c.configure(values)
    else:assert c.configure(values)[3]==total


@pytest.mark.parametrize('minutes,seconds',[('-1','0'),('0','-2'),('x','2'),('1.5','2'),('0','0'),('','0'),('9'*101,'1'),('0',str(w.MAX_INTEGER+1))])
def test_invalid_or_unsafe_durations_never_become_skips(minutes,seconds):
    """Malformed, zero and overflowing performed values remain hard validation errors."""
    with pytest.raises(c.ValidationError):w.duration_seconds(minutes,seconds)


def test_administration_is_open_centralized_and_csrf_protected(phase9_root):
    """One future access-policy boundary covers all maintenance without login today."""
    client=create_app({'TESTING':True,'WORKOUT_DATA_ROOT':phase9_root}).test_client()
    page=client.get('/settings/administration');assert page.status_code==200 and b'Administration' in page.data
    assert b'type="password"' not in page.data and client.get('/admin/login').status_code==404
    assert client.post('/settings/backup',data={}).status_code==400
    paths=['/settings/administration','/settings/logs','/settings/updates','/settings/updates/status','/settings/backups/'+'a'*32,'/settings/restores/'+'a'*32]
    def denied():
        """Simulate a future gate to prove every administrative route uses it."""
        abort(403)
    with patch('workout_tracker.administration.administrative_access',side_effect=denied):
        for path in paths:assert client.get(path).status_code==403,path
        assert client.get('/settings').status_code==200
        for path in ('/settings/backup','/settings/backups/'+'a'*32+'/delete','/settings/backups/'+'a'*32+'/restore','/settings','/settings/updates'):
            assert client.post(path,data={'csrf_token':token(page),'operation_id':uuid4().hex,'confirm':'yes','confirmation':'RESTORE','action':'check'}).status_code==403,path


def test_clock_display_and_minute_correction_preserve_original_precision(phase9_root):
    """HH:mm hides seconds without rewriting the native timestamp or DST instant."""
    from datetime import datetime,timezone
    assert clock('00:00:31')=='00:00' and clock('12:00:00')=='12:00' and clock('23:15:55')=='23:15'
    assert '14:45:30' in timestamp('2020-01-01T14:45:30+00:00') and 'PM' not in timestamp('2020-01-01T14:45:30+00:00')
    with database_session(phase9_root,write=True) as db:
        a,b,r,other,e=household(db)
        with patch.object(w,'now',return_value=datetime(2020,1,1,14,45,35,123456,tzinfo=timezone.utc)):
            session,_=w.start(db,a,r,'America/Indiana/Indianapolis')
            rows=w.entries(db,a,session)
            values=dict(revision='0',entry_id=rows[0]['id'],current_position='0',weight='40')
            w.finish(db,a,session,values)
        parent,rows=h.effective(db,a,session)
        h.correct(db,a,session,dict(confirm='yes',correction_revision='0',workout_date=parent['workout_date'],workout_time=parent['workout_time'][:5],weight_0='41'))
        corrected,_=h.effective(db,a,session)
        assert corrected['occurred_at']==parent['occurred_at'] and corrected['workout_time']==parent['workout_time']
        assert c.entry(db,a,r,db.execute('SELECT id FROM routine_exercises WHERE routine_id=? ORDER BY position',(r,)).fetchone()[0])['target_sets']==3


def test_schema7_backups_restore_defaults_and_global_delete_cascades(phase9_root):
    """Exact-schema restore retains presets; global erasure leaves no default orphan."""
    from workout_tracker import deletions as d
    from test_phase8_deletion import approval
    root=phase9_root
    with database_session(root,write=True) as db:a,b,r,other,e=household(db)
    backup=m.backup(root,uuid4().hex);assert backup['schema_version']==7 and backup['status']=='verified'
    with database_session(root,write=True) as db:d.delete_exercise(db,a,e,approval(db,'exercise',e,a))
    with database_session(root) as db:assert db.execute('SELECT count(*) FROM exercise_defaults WHERE exercise_id=?',(e,)).fetchone()[0]==0
    assert m.restore(root,backup['id'],uuid4().hex,True)['status']=='succeeded'
    with database_session(root) as db:assert c.exercise_defaults(db,b,e)['target_reps']==12


def test_all_palette_tokens_and_local_favicon_formats(phase9_root):
    """Old selections remain valid; shipped local icons have the requested dimensions."""
    assert len(preferences.PALETTE)==12 and preferences.PALETTE[:6]==('blue','teal','green','purple','orange','red')
    root=Path(__file__).resolve().parents[1]/'workout_tracker/static/icons'
    assert ET.fromstring((root/'favicon.svg').read_text()).tag.endswith('svg')
    for name,size in (('favicon-16.png',16),('favicon-32.png',32),('apple-touch-icon.png',180)):
        data=(root/name).read_bytes();assert data[:8]==b'\x89PNG\r\n\x1a\n' and struct.unpack('>II',data[16:24])==(size,size)
    assert (root/'favicon.ico').read_bytes()[:6]==b'\0\0\1\0\2\0'
    client=create_app({'TESTING':True,'WORKOUT_DATA_ROOT':phase9_root}).test_client()
    page=client.get('/people')
    for name in ('favicon.svg','favicon.ico','favicon-16.png','favicon-32.png','apple-touch-icon.png'):
        assert name.encode() in page.data and client.get('/static/icons/'+name).status_code==200


@pytest.mark.parametrize('source_schema',[6,7])
def test_v4_supports_release09_schema7_and_code_only_updates(tmp_path,source_schema):
    """Run the actual Bash/engine with synthetic Git/Docker and real candidate storage."""
    import os,subprocess
    from test_phase8_updater import fixture,REPO
    root,env=fixture(tmp_path,source_schema)
    env.update(MODE='ok',METADATA_VERSION='0.9.0',METADATA_SCHEMA='7')
    original=selected(root/'data/storage');before=original.read_bytes()
    result=subprocess.run(['bash',str(REPO/'deployment/update_workout_tracker_v4.sh'),'--root',str(root),'--confirm','--allow-migration'],env=env,text=True,capture_output=True,timeout=70)
    assert result.returncode==0,result.stdout+result.stderr
    state=json.loads((root/'updater/status.json').read_text())
    assert state['installed_version']=='0.9.0' and state['installed_schema']==7 and state['status']=='Completed'
    assert original.read_bytes()==before
    assert (selected(root/'data/storage')!=original)==(source_schema==6)
    calls=(root/'calls.jsonl').read_text()
    assert ('migrate-storage' in calls)==(source_schema==6)


def test_historical_seconds_only_completion_keeps_zero_and_null(phase9_root):
    """Historical review uses normalized actuals without changing an active draft."""
    with database_session(phase9_root,write=True) as db:
        a,b,r,other,e=household(db);draft,_=w.start(db,a,r,'America/Indiana/Indianapolis')
        saved,_=manual(db,a,r,'2020-01-02',weight_0='0',seconds_1='120')
        parent,rows=h.effective(db,a,saved)
        assert rows[0]['actual_weight_tenths_lb']==0 and rows[1]['actual_duration_seconds']==120
        assert w.active(db,a)['id']==draft
        h.correct(db,a,saved,dict(confirm='yes',correction_revision='0',workout_date=parent['workout_date'],workout_time='',weight_0='0',minutes_1='3',seconds_1='150'))
        assert h.effective(db,a,saved)[1][1]['actual_duration_seconds']==330


def test_rejected_new_defaults_never_insert_an_incomplete_identity(phase9_root):
    """Even when a caller catches validation inside a transaction, no partial row remains."""
    with database_session(phase9_root,write=True) as db:
        person=c.create_person(db,'Preset validation')
        with pytest.raises(c.ValidationError):
            c.create_definition(db,person,'Invalid preset',dict(measurement_type='time',target_sets='3',seconds='-1'))
        assert db.execute('SELECT count(*) FROM exercises').fetchone()[0]==0
        assert db.execute('SELECT count(*) FROM exercise_defaults').fetchone()[0]==0
    assert inspect_storage(phase9_root)['schema_version']==7
