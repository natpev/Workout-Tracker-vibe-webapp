# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Phase 7 synthetic households verify global IDs, isolated results and safe upgrades.

Tests use only temporary roots. Exact old table cells, NULLs, audit chains and
original file bytes are checked around explicit candidate migration.
"""
import json
import sqlite3
from unittest.mock import patch
from uuid import uuid4

import pytest
from click.testing import CliRunner
from workout_tracker import APP_VERSION, create_app, catalog as c, history as h, workouts as w
from workout_tracker.__main__ import main
from workout_tracker.migrations import migrate_storage
from workout_tracker.storage import StorageError, database_session, inspect_storage
from workout_tracker import maintenance as m
from test_history import seed, manual, correction_payload
from test_catalog import weight, timed


@pytest.fixture
def library_root(phase4_root):
    """Upgrade disposable storage explicitly; production configuration is unused."""
    migrate_storage(phase4_root, target_version=5)
    return phase4_root


def selected(root):
    """Read the test manifest without changing any database selection."""
    return root/'data'/json.loads((root/'config'/'active.json').read_text())['database']


def test_release_metadata_never_opens_or_initializes_storage(tmp_path):
    """An updater detects the current target even without installed storage or an app worker."""
    from workout_tracker import TARGET_SCHEMA_VERSION
    absent = tmp_path / 'must-not-be-created'
    with patch('workout_tracker.__main__.inspect_storage', side_effect=AssertionError('No database reads')), \
         patch('workout_tracker.create_app', side_effect=AssertionError('No app startup')):
        result = CliRunner().invoke(main, ['release-info'], env={'WORKOUT_DATA_ROOT': str(absent)})
    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == {'app_version': APP_VERSION,
                                       'target_schema_version': TARGET_SCHEMA_VERSION}
    assert TARGET_SCHEMA_VERSION == 10 and not absent.exists()


def cells(db):
    """Capture every original table cell, preserving integer zero and SQL NULL."""
    names=[r[0] for r in db.execute("SELECT name FROM sqlite_schema WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    return {name:[tuple(r) for r in db.execute(f'SELECT * FROM {name} ORDER BY 1')] for name in names}


def test_populated_schema4_migration_preserves_every_value_and_draft(phase4_root):
    """Overlapping names, copies, audits, skips, zero and drafts all survive unchanged."""
    root=phase4_root
    with database_session(root,write=True) as db:
        a,b,r,item=seed(db)
        copied=c.copy_routine(db,a,r,b,'Old copy')
        identity,_=manual(db,a,r,'2020-01-01',weight_0='0')
        h.correct(db,a,identity,correction_payload(db,a,identity,weight_0='40.99',increase_0='1'))
        manual(db,b,copied,'2020-01-02',weight_0='20',minutes_1='0',seconds_1='45')
        manual(db,a,r,'2020-01-03',confirm_all_skipped='yes')
        native,_=w.start(db,b,copied,'UTC')
        e=w.entries(db,b,native)[0]
        w.finish(db,b,native,dict(revision='0',entry_id=e['id'],current_position='0',weight='0'))
        draft,_=w.start(db,a,r,'UTC')
        extra=c.create_definition(db,b,'Archived');c.update_definition(db,b,extra,None,'archive')
        before=cells(db)
        triggers=dict(db.execute("SELECT name,sql FROM sqlite_schema WHERE type='trigger'"))
    original=selected(root);original_bytes=original.read_bytes();mtime=original.stat().st_mtime_ns
    old_backup=m.backup(root,uuid4().hex)
    assert old_backup['status']=='verified'
    assert migrate_storage(root,5)==dict(changed=True,schema_version=5)
    assert original.read_bytes()==original_bytes and original.stat().st_mtime_ns==mtime
    assert selected(root)!=original and inspect_storage(root)['schema_version']==5
    with database_session(root,write=True) as db:
        after=cells(db)
        for table,values in before.items():
            assert (after[table][:-1] if table=='schema_migrations' else after[table])==values
        assert dict(db.execute("SELECT name,sql FROM sqlite_schema WHERE type='trigger'"))==triggers
        assert w.active(db,a)['id']==draft and w.entries(db,a,draft)[0]['actual_weight_tenths_lb'] is None
        assert h.effective(db,a,identity)[1][0]['actual_weight_tenths_lb']==409
        benches=[row for row in c.definitions(db,a) if row['name']=='Bench']
        assert len(benches)==2 and benches[0]['id']!=benches[1]['id']
        assert {row['id'] for row in c.definitions(db,a)}=={row['id'] for row in c.definitions(db,b)}
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]
        with pytest.raises(sqlite3.IntegrityError): db.execute("UPDATE workout_entries SET name='bad' WHERE session_id=?",(native,))
    # Old schema backups remain retained, but cannot silently downgrade schema 5.
    active_before=selected(root)
    assert m.restore(root,old_backup['id'],uuid4().hex,True)['status']=='failed'
    assert selected(root)==active_before
    backup=m.backup(root,uuid4().hex);assert backup['status']=='verified' and backup['schema_version']==5
    assert m.restore(root,backup['id'],uuid4().hex,True)['status']=='succeeded'
    with database_session(root) as db: assert w.active(db,a)['id']==draft
    m.logical_check(selected(root),5)


@pytest.mark.parametrize('fault',['ddl','cells','logical','activation','durability'])
def test_schema5_failure_preserves_original_selection(phase4_root,fault):
    """Candidate DDL/data/validation/publication faults leave original bytes selected."""
    from workout_tracker import migrations as migration, library_schema
    root=phase4_root
    with database_session(root,write=True) as db: seed(db)
    original=selected(root);before=original.read_bytes();manifest=(root/'config'/'active.json').read_bytes()
    upgrade=library_schema.upgrade_library;sync=migration._sync_directory;calls=0
    def changed(db):
        """Inject a logical data mutation into only the disposable candidate."""
        upgrade(db);db.execute("UPDATE exercises SET name='unapproved'")
    def failed_sync(path):
        """Fail once after publication so rollback can run normally."""
        nonlocal calls
        if path==root/'config':
            calls+=1
            if calls==2: raise OSError('simulated durability fault')
        sync(path)
    faults={
        'ddl':patch.object(library_schema,'upgrade_library',side_effect=sqlite3.OperationalError('test DDL')),
        'cells':patch.object(library_schema,'upgrade_library',side_effect=changed),
        'logical':patch.object(m,'logical_check',side_effect=StorageError('test logical check')),
        'activation':patch.object(migration.os,'replace',side_effect=OSError('test selection')),
        'durability':patch.object(migration,'_sync_directory',side_effect=failed_sync),
    }
    with faults[fault],pytest.raises(StorageError,match='original selection retained'): migrate_storage(root,5)
    assert original.read_bytes()==before and (root/'config'/'active.json').read_bytes()==manifest
    assert inspect_storage(root)['schema_version']==4


@pytest.mark.parametrize('destination_same',[True,False])
def test_shared_ids_independent_routines_and_personal_results(library_root,destination_same):
    """Copy never copies results; compatible same-person history crosses routines."""
    with database_session(library_root,write=True) as db:
        a,b=c.create_person(db,'A'),c.create_person(db,'B')
        r=c.create_routine(db,a,'A routine');item=c.add_entry(db,a,r,weight())
        original=c.entry(db,a,r,item);exercise=original['exercise_id']
        assert c.definition(db,b,exercise)['id']==exercise
        destination=a if destination_same else b
        copy=c.copy_routine(db,a,r,destination,'Named copy')
        row=db.execute('SELECT * FROM routine_exercises WHERE routine_id=?',(copy,)).fetchone()
        assert copy!=r and row['id']!=item and row['exercise_id']==exercise
        assert db.execute('SELECT count(*) FROM exercises').fetchone()[0]==1
        other=c.create_routine(db,b,'B routine');c.add_entry(db,b,other,weight(exercise_id=exercise))
        first,_=manual(db,a,r,'2020-01-01',weight_0='40',increase_0='1')
        manual(db,b,other,'2020-01-01',weight_0='20')
        for who,routine,expected,increase in [(a,r,400,1),(b,other,200,0)]:
            draft,_=w.start(db,who,routine,'UTC');entry=w.entries(db,who,draft)[0]
            prior,_=w.previous(db,who,w.session(db,who,draft),entry)
            assert prior['actual_weight_tenths_lb']==expected and prior['increase_next_time']==increase
            assert [g['highest']['raw'] for g in h.chart_series(db,who,{})]==[expected]
        c.update_entry(db,destination,copy,row['id'],weight(target_reps='8'))
        assert c.entry(db,a,r,item)['target_reps']==12
        if destination_same:
            # Existing draft did not reference the copied routine, but the query
            # still finds compatible results across routine identity boundaries.
            current=w.active(db,a)
            w.discard(db,a,current['id'],dict(revision=str(current['revision']),confirm='yes'))
            copied_draft,_=w.start(db,a,copy,'UTC')
            parent=w.session(db,a,copied_draft)
            snapshot=w.entries(db,a,copied_draft)[0]
            assert w.previous(db,a,parent,snapshot)[0]['actual_weight_tenths_lb']==400
        c.update_definition(db,b,exercise,'Global renamed','rename')
        assert c.entry(db,a,r,item)['name']=='Global renamed'
        assert h.effective(db,a,first)[1][0]['name']=='Bench'
        with pytest.raises(c.ValidationError): c.update_definition(db,b,exercise,None,'archive')
        with pytest.raises(c.MissingRecord): c.routine(db,b,r)
        with pytest.raises(c.ValidationError): c.create_definition(db,b,' GLOBAL RENAMED ')
        with pytest.raises(c.ValidationError): c.copy_routine(db,a,r,b,' ')
        # Incompatible meaning/type/unit never inherit these shared measurements.
        current=w.active(db,a);entry=dict(w.entries(db,a,current['id'])[0])
        for changes in ({'weight_meaning':'total barbell'},{'measurement_type':'time','unit':None},{'unit':'kg'}):
            assert w.previous(db,a,current,{**entry,**changes})==(None,None)


def test_versions_cli_noop_and_schema5_protection(library_root):
    """Active DB version is displayed, exact schema enforced, no-op has no copies."""
    root=library_root;original=selected(root);before=original.read_bytes();paths=set((root/'data').iterdir())
    runner=CliRunner()
    refused=runner.invoke(main,['migrate-storage','--data-root',str(root),'--target-version','5'])
    assert refused.exit_code!=0 and 'confirm-upgrade' in refused.output
    result=runner.invoke(main,['migrate-storage','--data-root',str(root),'--target-version','5','--confirm-upgrade'])
    assert result.exit_code==0 and 'no copy or write' in result.output
    client=create_app({'WORKOUT_DATA_ROOT':root,'TESTING':True}).test_client()
    assert client.get('/health/ready').json==dict(status='ready',app_version=APP_VERSION,schema_version=5)
    for path in ('/people','/settings'):
        response=client.get(path);assert response.status_code==200
        assert b'Workout Tracker v0.14.0' in response.data and b'Database v5' in response.data
    assert b'Application version: 0.14.0' in client.get('/settings/administration').data
    assert original.read_bytes()==before and set((root/'data').iterdir())==paths


def test_typed_ordered_copy_cross_owner_backup_and_atomic_failure(library_root):
    """Shared Weight/Time prescriptions copy exactly; partial-copy failure rolls back."""
    root=library_root
    with database_session(root,write=True) as db:
        a,b=c.create_person(db,'A'),c.create_person(db,'B')
        r=c.create_routine(db,a,'Mixed')
        c.add_entry(db,a,r,weight());c.add_entry(db,a,r,timed())
        before=[dict(row) for row in db.execute('SELECT * FROM routine_exercises WHERE routine_id=? ORDER BY position',(r,))]
        copied=c.copy_routine(db,a,r,b,'B mixed')
        after=[dict(row) for row in db.execute('SELECT * FROM routine_exercises WHERE routine_id=? ORDER BY position',(copied,))]
        fields=('exercise_id','position','measurement_type','target_sets','target_reps','target_duration_seconds','unit','weight_meaning','notes')
        assert [tuple(row[k] for k in fields) for row in before]==[tuple(row[k] for k in fields) for row in after]
        assert len({row['id'] for row in before+after})==4
        manual(db,b,copied,'2020-01-01',weight_0='0',minutes_1='1',seconds_1='5')
        draft,_=w.start(db,b,copied,'UTC')
        entry=w.entries(db,b,draft)[0]
        w.update(db,b,draft,dict(revision='0',entry_id=entry['id'],current_position='0',weight='42.56'))
        counts={table:db.execute(f'SELECT count(*) FROM {table}').fetchone()[0] for table in ('routines','routine_exercises','exercises','workout_sessions','historical_entries')}
    original_add=c.add_entry;calls=0
    def fail_second(*args,**kwargs):
        """Fail after the first copied item to prove the parent and item roll back."""
        nonlocal calls
        calls+=1
        if calls==2: raise RuntimeError('synthetic copy failure')
        return original_add(*args,**kwargs)
    with pytest.raises(RuntimeError):
        with database_session(root,write=True) as db:
            with patch.object(c,'add_entry',side_effect=fail_second): c.copy_routine(db,a,r,b,'Broken')
    with database_session(root) as db:
        assert all(db.execute(f'SELECT count(*) FROM {table}').fetchone()[0]==count for table,count in counts.items())
    # Historical JSON can reference an exercise registered by another person;
    # schema-5 backup validation must treat that as valid global provenance.
    backup=m.backup(root,uuid4().hex)
    assert backup['status']=='verified'
    assert m.restore(root,backup['id'],uuid4().hex,True)['status']=='succeeded'
    with database_session(root,write=True) as db:
        assert w.active(db,b)['id']==draft
        assert w.entries(db,b,draft)[0]['actual_weight_tenths_lb']==425
        # Archiving cannot break another person's active routine, even when
        # that person is archived. Only retiring all referencing routines allows it.
        c.update_person(db,b,None,'archive')
        db.execute('UPDATE routines SET archived=1 WHERE id=?',(r,))
        with pytest.raises(c.ValidationError): c.update_definition(db,a,before[0]['exercise_id'],None,'archive')
        db.execute('UPDATE routines SET archived=1 WHERE id=?',(copied,))
        c.update_definition(db,a,before[0]['exercise_id'],None,'archive')
        assert len(h.all_completed(db,b))==1
        with pytest.raises(c.ValidationError): c.create_definition(db,a,'bench')


@pytest.mark.parametrize('source_version',[1,2,3])
def test_direct_older_schema5_candidates(tmp_path,source_version):
    """Each supported older source can target 5 without changing its original file."""
    from workout_tracker.storage import initialize_storage
    root=tmp_path/'direct';initialize_storage(root)
    if source_version>1: migrate_storage(root,source_version)
    original=selected(root);before=original.read_bytes()
    assert migrate_storage(root,5)['schema_version']==5
    assert inspect_storage(root)['schema_version']==5 and original.read_bytes()==before
