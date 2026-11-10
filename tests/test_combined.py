# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""Phase 11 tests use candidate upgrades and synthetic household records only.

Configuration, paired actuals, immutable snapshots, correction chains, charts,
CSV and maintenance round trips share real service/SQLite code, never live data.
"""
import csv
import json
import sqlite3
from io import StringIO
from unittest.mock import patch
from uuid import uuid4
import pytest
from workout_tracker import create_app, catalog as c, workouts as w, history as h, maintenance as m
from workout_tracker.storage import database_session, inspect_storage, StorageError
from workout_tracker.migrations import migrate_storage
from workout_tracker.csv_export import wide_csv
from test_phase9 import phase9_root
from test_phase8_deletion import selected, manual
from test_history import correction_payload
from test_workout_http import fields


@pytest.fixture
def phase11_root(phase9_root):
    """Upgrade only disposable schema 7 via the production candidate migrator."""
    migrate_storage(phase9_root,8)
    return phase9_root


def seed(db):
    """Create an ordinary combined default and copy it once into one owned routine."""
    a=c.create_person(db,'A');b=c.create_person(db,'B');r=c.create_routine(db,a,'Carry')
    values=dict(measurement_type='weight_duration',target_sets='1',minutes='6',weight_meaning='per hand',notes='Walk steadily')
    e=c.create_definition(db,a,'Weighted carry',values)
    item=c.add_entry(db,a,r,dict(exercise_id=e,use_library_defaults='yes'))
    return a,b,r,e,item


def test_defaults_routines_copy_and_mode_switch_independence(phase11_root):
    """Shared identities copy targets, never keep a live link to Library defaults."""
    with database_session(phase11_root,write=True) as db:
        a,b,r,e,item=seed(db)
        c.update_defaults(db,a,e,dict(measurement_type='weight_duration',target_sets='2',seconds='90',weight_meaning='total weight'))
        assert c.entry(db,a,r,item)['target_duration_seconds']==360
        copy=c.copy_routine(db,a,r,b,'Independent')
        other=db.execute('SELECT * FROM routine_exercises WHERE routine_id=?',(copy,)).fetchone()
        assert other['exercise_id']==e and other['target_duration_seconds']==360
        c.update_entry(db,a,r,item,dict(measurement_type='time',target_sets='3',seconds='45',weight_meaning='discard this',target_reps='12'))
        row=c.entry(db,a,r,item)
        assert row['unit'] is None and row['weight_meaning']=='' and row['target_reps'] is None
        assert other['unit']=='lb' and other['weight_meaning']=='per hand'
        c.update_entry(db,a,r,item,dict(measurement_type='weight_duration',target_sets='1',seconds='120',weight_meaning='per hand',target_reps='999'))
        assert c.entry(db,a,r,item)['target_reps'] is None


@pytest.mark.parametrize('weight,minutes,seconds,expected',[
    ('20.99','6','0',(209,360)),('0','','90',(0,90)),('25','2','',(250,120)),
    ('25','1','90',(250,150)),('','','',(None,None)),('0','','1',(0,1))])
def test_combined_measurements_exact_zero_normalized_and_skipped(weight,minutes,seconds,expected):
    """One pair per exercise; duration never multiplies by the prescribed sets."""
    actual=w.measurement({'measurement_type':'weight_duration'},dict(weight=weight,minutes=minutes,seconds=seconds,increase='1'))
    assert actual[:2]==expected
    assert actual[2]==(None if expected==(None,None) else 1)


@pytest.mark.parametrize('values,field',[
    ({'seconds':'45'},'weight'),({'weight':'20'},'minutes'),({'weight':'20','seconds':'0'},'seconds'),
    ({'weight':'-1','seconds':'45'},'weight'),({'weight':'bad','seconds':'45'},'weight'),
    ({'weight':'20','seconds':'1.5'},'seconds'),({'weight':'20','minutes':'-1'},'minutes')])
def test_partial_or_malformed_pairs_are_field_errors(values,field):
    """Neither a partial actual nor malformed input can be silently saved as skipped."""
    with pytest.raises(w.MeasurementError) as error:w.measurement({'measurement_type':'weight_duration'},values)
    assert field in error.value.fields


def test_http_pair_validation_navigation_restart_and_completion(phase11_root):
    """Invalid autosave retains old values/revision; Next alone raises progress."""
    root=phase11_root
    with database_session(root,write=True) as db:
        a,b,r,e,item=seed(db)
        c.add_entry(db,a,r,dict(name='Plank',measurement_type='time',target_sets='1',seconds='45'))
    client=create_app({'TESTING':True,'WORKOUT_DATA_ROOT':root}).test_client();base=f'/people/{a}/routines/{r}'
    path=client.post(base+'/start',data=fields(client.get(base))).location
    page=client.get(path);payload=fields(page)
    bad=client.post(path+'/draft',data={**payload,'weight':'20'})
    assert bad.status_code==400 and 'minutes' in bad.json['fields']
    good=client.post(path+'/draft',data={**payload,'weight':'20.99','seconds':'360','increase':'1'})
    assert good.status_code==200 and good.json['navigation_progress']==0 and good.json['seconds']=='0'
    assert '20.9 lb per hand' in good.json['measurement_display'] and '6:00' in good.json['measurement_display']
    with database_session(root) as db:
        row=db.execute('SELECT * FROM workout_entries WHERE exercise_id=?',(e,)).fetchone()
        assert (row['actual_weight_tenths_lb'],row['actual_duration_seconds'])==(209,360)
    page=client.get(path);payload=fields(page)
    result=client.post(path+'/draft',data={**payload,'weight':'0','seconds':'1','current_position':'1','navigation_action':'next'})
    assert result.json['navigation_progress']==1
    restarted=create_app({'TESTING':True,'WORKOUT_DATA_ROOT':root}).test_client()
    assert b'Plank' in restarted.get(path).data
    final=restarted.post(path+'/finish',data=fields(restarted.get(path)))
    assert final.status_code==303
    with database_session(root) as db:
        saved=h.effective(db,a,path.rsplit('/',1)[1])[1]
        assert saved[0]['actual_weight_tenths_lb']==0 and saved[1]['actual_duration_seconds'] is None


def test_history_audits_previous_two_charts_csv_and_backup_restore(phase11_root):
    """All effective readers use paired corrections; source records remain immutable."""
    root=phase11_root
    with database_session(root,write=True) as db:
        a,b,r,e,item=seed(db)
        one,_=manual(db,a,r,'2020-01-01',weight_0='0',seconds_0='360')
        skipped,_=manual(db,a,r,'2020-01-02',confirm_all_skipped='yes')
        c.update_entry(db,a,r,item,dict(measurement_type='weight_duration',target_sets='2',seconds='90',weight_meaning='per hand'))
        two,_=manual(db,a,r,'2020-01-03',weight_0='25.99',seconds_0='80')
        before=h.original(db,a,two)[1][0]
        h.correct(db,a,two,correction_payload(db,a,two,weight_0='30.99',minutes_0='0',seconds_0='120'))
        assert h.original(db,a,two)[1][0]==before
        assert h.audit(db,a,two)[0]['after']['entries'][0]['actual_weight_tenths_lb']==309
        with pytest.raises(sqlite3.IntegrityError):db.execute('UPDATE historical_entries SET actual_weight_tenths_lb=999 WHERE session_id=?',(two,))
        with pytest.raises(w.MeasurementError):h.correct(db,a,two,correction_payload(db,a,two,weight_0='',seconds_0='120'))
        assert len(h.audit(db,a,two))==1
        current,_=w.start(db,a,r,'UTC');parent=w.session(db,a,current);entry=w.entries(db,a,current)[0]
        previous,_=w.previous(db,a,parent,entry)
        assert (previous['actual_weight_tenths_lb'],previous['actual_duration_seconds'])==(309,120)
        charts=h.chart_series(db,a,{})
        assert [s['kind'] for s in charts]==['weight','time'] and all(s['combined'] for s in charts)
        assert [p['raw'] for p in charts[0]['points']]==[0,309]
        assert [p['raw'] for p in charts[1]['points']]==[360,120]
        assert charts[1]['target_y'] is None and len(charts[1]['targets'])==2
        filtered=h.chart_series(db,a,{'from':'2020-01-03'})
        assert filtered[1]['target_label']=='1:30'
        assert not h.chart_series(db,b,{})
        data=list(csv.reader(StringIO(wide_csv(db,a,{},[e]))))
        assert data[0][4:]==['Weighted carry (per hand) — Weight (lb)','Weighted carry (per hand) — Duration','Weighted carry (per hand) — Sets × Target Duration']
        assert data[1][4:]==['0','6:00','1 × 6:00'] and data[2][4:]==['','','1 × 6:00']
        assert data[3][4:]==['30.9','2:00','2 × 1:30']
        original=selected(root)
    backup=m.backup(root,uuid4().hex);assert backup['status']=='verified' and backup['schema_version']==8
    restored=m.restore(root,backup['id'],uuid4().hex,confirm=True)
    assert restored['status']=='succeeded' and selected(root)!=original and original.exists()
    with database_session(root) as db:assert h.effective(db,a,two)[1][0]['actual_duration_seconds']==120


def test_schema8_preserves_every_schema7_value_and_trigger(phase9_root):
    """Compare cells, source bytes and triggers across a populated candidate upgrade."""
    root=phase9_root
    from test_phase8_deletion import household
    with database_session(root,write=True) as db:
        a,b,r,other,e=household(db)
        saved,_=manual(db,a,r,'2020-01-01',weight_0='0')
        h.correct(db,a,saved,correction_payload(db,a,saved,weight_0='40.99'))
        w.start(db,b,other,'UTC')
        h.prepare(db,a,r,dict(workout_date='2020-01-02',workout_time=''),'UTC')
        tables=[row[0] for row in db.execute("SELECT name FROM sqlite_schema WHERE type='table'")]
        before={name:[tuple(row) for row in db.execute(f'SELECT * FROM {name} ORDER BY 1')] for name in tables}
        triggers=dict(db.execute("SELECT name,sql FROM sqlite_schema WHERE type='trigger'"))
    original=selected(root);data=original.read_bytes();manifest=(root/'config/active.json').read_bytes()
    assert migrate_storage(root,8)['changed']
    assert selected(root)!=original and original.read_bytes()==data
    with database_session(root) as db:
        for name,rows in before.items():
            actual=[tuple(row) for row in db.execute(f'SELECT * FROM {name} ORDER BY 1')]
            assert (actual[:-1] if name=='schema_migrations' else actual)==rows
        assert dict(db.execute("SELECT name,sql FROM sqlite_schema WHERE type='trigger'"))==triggers
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and not db.execute('PRAGMA foreign_key_check').fetchall()
    active=selected(root);unchanged=active.read_bytes()
    assert not migrate_storage(root,8)['changed'] and active.read_bytes()==unchanged
    assert create_app({'TESTING':True,'WORKOUT_DATA_ROOT':root}).test_client().get('/health/ready').json['schema_version']==8


@pytest.mark.parametrize('failure',['ddl','validate','activate','post_activation'])
def test_schema8_failure_retains_original(phase9_root,failure):
    """Failed DDL/validation/publication/durability never select an incomplete copy."""
    root=phase9_root;original=selected(root);data=original.read_bytes();manifest=(root/'config/active.json').read_bytes()
    target={'ddl':'workout_tracker.combined_schema.upgrade_combined','validate':'workout_tracker.migrations._validate_candidate','activate':'workout_tracker.migrations._write_manifest'}
    if failure=='post_activation':
        from workout_tracker import migrations
        real=migrations._sync_directory
        def fail_after_switch(path):
            """Inject one durability fault only after the manifest points at schema 8."""
            if path.name=='config' and b'schema-8-' in (root/'config/active.json').read_bytes():raise OSError('Synthetic sync failure')
            return real(path)
        context=patch('workout_tracker.migrations._sync_directory',side_effect=fail_after_switch)
    else:context=patch(target[failure],side_effect=RuntimeError('Synthetic schema8 fault'))
    with context,pytest.raises(StorageError):migrate_storage(root,8)
    assert original.read_bytes()==data and (root/'config/active.json').read_bytes()==manifest
    assert inspect_storage(root)['schema_version']==7


def test_sql_rejects_partial_pairs(phase11_root):
    """CHECK constraints are independent of forms; a partial pair is never valid SQL."""
    with database_session(phase11_root,write=True) as db:
        a,b,r,e,item=seed(db);session,_=w.start(db,a,r,'UTC')
        for statement in ("actual_weight_tenths_lb=0,increase_next_time=0","actual_duration_seconds=45,increase_next_time=0"):
            with pytest.raises(sqlite3.IntegrityError):db.execute('UPDATE workout_entries SET '+statement)


def test_schema7_stays_readable_without_implicit_migration(phase9_root):
    """Old storage works normally; new mode requests fail before any identity write."""
    root=phase9_root
    with database_session(root,write=True) as db:a=c.create_person(db,'A')
    original=selected(root);before=original.read_bytes()
    client=create_app({'TESTING':True,'WORKOUT_DATA_ROOT':root}).test_client()
    assert client.get('/health/ready').json['schema_version']==7 and original.read_bytes()==before
    with database_session(root,write=True) as db:
        with pytest.raises(c.ValidationError,match='schema-8'):
            c.create_definition(db,a,'Combined',dict(measurement_type='weight_duration',target_sets='1',seconds='45'))
        assert db.execute('SELECT count(*) FROM exercises').fetchone()[0]==0


def test_fresh_cli_target8_and_old_backup_refused_after_upgrade(tmp_path,phase9_root):
    """CLI supports target 8; exact-schema Restore cannot downgrade existing data."""
    from flask import Flask
    from click.testing import CliRunner
    from workout_tracker.__main__ import main as cli
    root=phase9_root;record=m.backup(root,uuid4().hex)
    migrate_storage(root,8);active=selected(root);data=active.read_bytes()
    attempt=m.restore(root,record['id'],uuid4().hex,confirm=True)
    assert attempt['status']=='failed' and selected(root)==active and active.read_bytes()==data
    new=tmp_path/'fresh';runner=CliRunner()
    assert runner.invoke(cli,['init-storage','--data-root',str(new),'--confirm-new-storage']).exit_code==0
    result=runner.invoke(cli,['migrate-storage','--data-root',str(new),'--target-version','8','--confirm-upgrade'])
    assert result.exit_code==0,result.output
    assert inspect_storage(new)['schema_version']==8


def test_native_all_skipped_pairs_and_previous_skip_fallback(phase11_root):
    """Retained NULL pairs do not hide the last successful paired performance."""
    with database_session(phase11_root,write=True) as db:
        a,b,r,e,item=seed(db)
        manual(db,a,r,'2020-01-01',weight_0='20',seconds_0='360',increase_0='1')
        manual(db,a,r,'2020-01-02',confirm_all_skipped='yes')
        session,_=w.start(db,a,r,'UTC');parent=w.session(db,a,session);row=w.entries(db,a,session)[0]
        previous,last=w.previous(db,a,parent,row)
        assert previous['actual_weight_tenths_lb'] is None and previous['actual_duration_seconds'] is None
        assert last['actual_weight_tenths_lb']==200 and last['actual_duration_seconds']==360 and last['increase_next_time']==1
        values=dict(revision='0',entry_id=row['id'],current_position='0')
        with pytest.raises(w.AllSkipped):w.finish(db,a,session,values)
        # The service increments a revision inside this test transaction; a real
        # rejected request rolls back. Use the current revision for confirmation.
        values.update(revision=str(w.session(db,a,session)['revision']),confirm_all_skipped='yes')
        w.finish(db,a,session,values)
        actual=w.entries(db,a,session)[0]
        assert all(actual[k] is None for k in ('actual_weight_tenths_lb','actual_duration_seconds','increase_next_time'))
        state=h.value_state(*h.original(db,a,session));state['entries'][0]['actual_weight_tenths_lb']=0
        with pytest.raises(ValueError,match='both'):h.validate_state(*h.original(db,a,session),state)


def test_schema8_restore_preserves_damaged_original(phase11_root):
    """Explicit recovery recognizes schema-8 manifests without replacing damaged bytes."""
    root=phase11_root
    with database_session(root,write=True) as db:seed(db)
    record=m.backup(root,uuid4().hex);original=selected(root);original.write_bytes(b'Synthetic damaged storage')
    restored=m.restore(root,record['id'],uuid4().hex,confirm=True)
    assert restored['status']=='succeeded' and original.read_bytes()==b'Synthetic damaged storage'
    assert inspect_storage(root)['schema_version']==8 and selected(root)!=original


def test_combined_csv_absent_group_is_three_blanks_and_mode_series_stay_separate(phase11_root):
    """Changing a mode never combines earlier weight-only results with paired data."""
    with database_session(phase11_root,write=True) as db:
        a,b,r,e,item=seed(db)
        manual(db,a,r,'2020-01-01',weight_0='20',seconds_0='360')
        c.update_entry(db,a,r,item,dict(measurement_type='weight',target_sets='3',target_reps='12',weight_meaning='per hand'))
        manual(db,a,r,'2020-01-02',weight_0='25')
        series=h.chart_series(db,a,{})
        assert len(series)==3 and [s['combined'] for s in series]==[True,True,False]
        other=c.create_routine(db,a,'Other')
        row=c.add_entry(db,a,other,dict(name='Unrelated curl',measurement_type='weight',target_sets='2',target_reps='15'))
        curl=c.entry(db,a,other,row)['exercise_id']
        manual(db,a,other,'2020-02-01',weight_0='10')
        data=list(csv.reader(StringIO(wide_csv(db,a,{'from':'2020-02-01'},[e,curl]))))
        # All historical modes of the absent selected ID retain their columns.
        assert len(data[0])==11 and data[1][4:9]==['']*5 and data[1][9:]==['10','2 × 15']
