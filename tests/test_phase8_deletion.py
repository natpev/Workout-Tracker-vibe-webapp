# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""Synthetic schema-6 preservation, hard deletion, confirmation and rollback tests.

Real locked transactions verify original migration files, immutable guards,
NULL/zero, cross-person erasure, audit projection and retained routine history.
"""
import json
import sqlite3
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from workout_tracker import create_app,catalog as c,history as h,workouts as w,deletions as d
from workout_tracker.__main__ import main
from workout_tracker.storage import database_session,StorageError,inspect_storage
from workout_tracker.migrations import migrate_storage
from workout_tracker.maintenance import logical_check
from test_history import seed,manual,correction_payload
from test_shared_library import cells,selected
from test_catalog import weight


@pytest.fixture
def phase8_root(phase4_root):
    """Upgrade disposable schema 5 explicitly; no household configuration is read."""
    migrate_storage(phase4_root,5);migrate_storage(phase4_root,6)
    return phase4_root


def approval(db,kind,identity,person):
    """Build the exact current typed destructive confirmation without bypassing checks."""
    impact=d.impact(db,kind,identity,person)
    return dict(phrase='DELETE',confirm='yes',revision=impact['revision'])


def household(db):
    """Seed two users sharing one exercise plus an unrelated timed exercise."""
    a,b,r,item=seed(db)
    copied=c.copy_routine(db,a,r,b,'B routine')
    exercise=c.entry(db,a,r,item)['exercise_id']
    return a,b,r,copied,exercise


def test_migration6_preserves_all_original_cells_and_sources(phase4_root):
    """Schema-5 source bytes, drafts, audit values and relationships stay unchanged."""
    root=phase4_root;migrate_storage(root,5)
    with database_session(root,write=True) as db:
        a,b,r,other,e=household(db)
        identity,_=manual(db,a,r,'2020-01-01',weight_0='0')
        h.correct(db,a,identity,correction_payload(db,a,identity,weight_0='40.99'))
        w.start(db,b,other,'UTC');before=cells(db)
    original=selected(root);source=original.read_bytes();manifest=(root/'config/active.json').read_bytes()
    assert migrate_storage(root,6)['schema_version']==6
    assert original.read_bytes()==source and selected(root)!=original
    assert any(p.read_bytes()==manifest for p in (root/'archives').glob('*.json'))
    with database_session(root,write=True) as db:
        after=cells(db)
        for name,rows in before.items(): assert (after[name][:-1] if name=='schema_migrations' else after[name])==rows
        with pytest.raises(sqlite3.IntegrityError):db.execute("UPDATE historical_entries SET name='bad'")
        with pytest.raises(sqlite3.IntegrityError):db.execute('DELETE FROM workout_corrections')
    logical_check(selected(root),6)


@pytest.mark.parametrize('fault',['ddl','validation','activation'])
def test_migration6_failure_retains_schema5(phase4_root,fault):
    """Faulted schema-6 candidates never overwrite or replace their source selection."""
    from workout_tracker import deletion_schema,migrations
    root=phase4_root;migrate_storage(root,5);original=selected(root);before=original.read_bytes();manifest=(root/'config/active.json').read_bytes()
    faults={'ddl':patch.object(deletion_schema,'upgrade_deletion',side_effect=RuntimeError('fixture')),
            'validation':patch.object(migrations,'_validate_candidate',side_effect=StorageError('fixture')),
            'activation':patch.object(migrations.os,'replace',side_effect=OSError('fixture'))}
    with faults[fault],pytest.raises(StorageError):migrate_storage(root,6)
    assert original.read_bytes()==before and (root/'config/active.json').read_bytes()==manifest
    assert inspect_storage(root)['schema_version']==5


def test_global_delete_projects_corrections_preserves_others_and_releases_name(phase8_root):
    """One identity disappears for both people, while every unrelated value remains."""
    root=phase8_root
    with database_session(root,write=True) as db:
        a,b,r,other,e=household(db)
        ids=[]
        for person,routine in ((a,r),(b,other)):
            identity,_=manual(db,person,routine,'2020-01-01',weight_0='40',minutes_1='0',seconds_1='45')
            h.correct(db,person,identity,correction_payload(db,person,identity,weight_0='42.56',minutes_1='1',seconds_1='5'))
            ids.append((person,identity))
        preview=d.impact(db,'exercise',e,a)
        assert (preview['people'],preview['routines'],preview['entries'])==(2,2,2)
        stale=correction_payload(db,a,ids[0][1],weight_0='80')
        d.delete_exercise(db,a,e,approval(db,'exercise',e,a))
        assert db.execute('SELECT 1 FROM exercises WHERE id=?',(e,)).fetchone() is None
        for person,identity in ids:
            parent,rows=h.effective(db,person,identity)
            assert len(rows)==1 and rows[0]['name']=='Plank' and rows[0]['position']==0
            assert rows[0]['actual_duration_seconds']==65 and rows[0]['actual_weight_tenths_lb'] is None
            assert len(h.audit(db,person,identity))==2
            assert all(len(audit['before']['entries'])==len(audit['after']['entries'])==1 for audit in h.audit(db,person,identity))
            assert all(group['exercise_id']!=e for group in h.chart_series(db,person,{}))
        with pytest.raises(w.RevisionConflict):h.correct(db,a,ids[0][1],stale)
        fresh=c.create_definition(db,a,'Bench');assert fresh!=e
        draft,_=w.start(db,a,r,'UTC')
        assert all(row['exercise_id']!=e for row in w.entries(db,a,draft))
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]
    logical_check(selected(root),6)


def test_routine_hard_delete_preserves_completed_native_and_historical_workouts(phase8_root):
    """Routine references are immutable snapshot IDs, not required live definitions."""
    with database_session(phase8_root,write=True) as db:
        a,b,r,other,e=household(db)
        historical,_=manual(db,a,r,'2020-01-01',weight_0='0')
        native,_=w.start(db,a,r,'UTC');entry=w.entries(db,a,native)[0]
        w.finish(db,a,native,dict(revision='0',entry_id=entry['id'],current_position='0',weight='40'))
        before=[(identity,h.effective(db,a,identity)[1]) for identity in (historical,native)]
        d.delete_routine(db,a,r,approval(db,'routine',r,a))
        assert db.execute('SELECT 1 FROM routines WHERE id=?',(r,)).fetchone() is None
        assert db.execute('SELECT count(*) FROM routine_exercises WHERE routine_id=?',(r,)).fetchone()[0]==0
        assert c.definition(db,b,e)['id']==e and c.routine(db,b,other)['id']==other
        assert c.create_routine(db,a,'Mixed')!=r
        for identity,rows in before:
            parent,actual=h.effective(db,a,identity)
            assert parent['routine_deleted'] and rows==actual
    logical_check(selected(phase8_root),6)


@pytest.mark.parametrize('kind',['exercise','routine'])
def test_active_draft_and_invalid_or_stale_confirmation_are_blocked(phase8_root,kind):
    """Draft protection and typed/revision checks precede all row writes."""
    with database_session(phase8_root,write=True) as db:
        a,b,r,other,e=household(db);identity=e if kind=='exercise' else r
        delete=d.delete_exercise if kind=='exercise' else d.delete_routine
        form=approval(db,kind,identity,a);before=cells(db)
        for values in ({**form,'confirm':''},{**form,'phrase':'INVALID'},{**form,'revision':'stale'}):
            with pytest.raises(c.ValidationError):delete(db,a,identity,values)
            assert cells(db)==before
        draft,_=w.start(db,a,r,'UTC')
        with pytest.raises(c.ValidationError,match='active workout draft'):delete(db,a,identity,approval(db,kind,identity,a))
        assert w.active(db,a)['id']==draft


def test_empty_workouts_pending_forms_and_atomic_failure(phase8_root):
    """Empty saved workouts disappear; pending forms invalidate; failure rolls all back."""
    root=phase8_root
    with database_session(root,write=True) as db:
        a=c.create_person(db,'A');r=c.create_routine(db,a,'Single');item=c.add_entry(db,a,r,weight())
        e=c.entry(db,a,r,item)['exercise_id'];saved,form=manual(db,a,r,'2020-01-01',weight_0='0')
        pending=h.prepare(db,a,r,dict(workout_date='2020-02-01',workout_time=''),'UTC');before=cells(db)
    with pytest.raises(RuntimeError):
        with database_session(root,write=True) as db:
            with patch.object(d,'reorder',side_effect=RuntimeError('fixture fault')):
                d.delete_exercise(db,a,e,approval(db,'exercise',e,a))
    with database_session(root,write=True) as db:
        assert cells(db)==before
        d.delete_exercise(db,a,e,approval(db,'exercise',e,a))
        assert h.all_completed(db,a)==[]
        assert db.execute('SELECT count(*) FROM historical_forms').fetchone()[0]==0
        with pytest.raises(c.MissingRecord):h.complete_historical(db,a,pending,{'weight_0':'1'})
    logical_check(selected(root),6)


def token(response):
    """Extract the real CSRF hidden field from the rendered page, not a fabricated value."""
    import re
    return re.search(r'name="csrf_token" value="([^"]+)"',response.get_data(as_text=True)).group(1)



def test_schema6_backup_restore_and_removed_data_in_old_backups(phase8_root):
    """Same-schema restore verifies guards/audits; old backups can restore erased data."""
    from uuid import uuid4
    from workout_tracker import maintenance as m
    root=phase8_root
    with database_session(root,write=True) as db:
        a,b,r,other,e=household(db)
        identity,_=manual(db,a,r,'2020-01-01',weight_0='0')
    old=m.backup(root,uuid4().hex);assert old['status']=='verified' and old['schema_version']==6
    with database_session(root,write=True) as db:d.delete_exercise(db,a,e,approval(db,'exercise',e,a))
    recent=m.backup(root,uuid4().hex);assert recent['status']=='verified'
    assert m.restore(root,recent['id'],uuid4().hex,True)['status']=='succeeded'
    with database_session(root) as db:assert db.execute('SELECT 1 FROM exercises WHERE id=?',(e,)).fetchone() is None
    # This is deliberately synthetic: ordinary old-backup restore is explicitly
    # confirmed and can resurrect a deletion, as warned in the confirmation UI.
    assert m.restore(root,old['id'],uuid4().hex,True)['status']=='succeeded'
    with database_session(root) as db:
        assert c.definition(db,a,e)['id']==e
        assert h.effective(db,a,identity)[1][0]['actual_weight_tenths_lb']==0
    logical_check(selected(root),6)


def test_native_global_delete_order_skips_and_previous_reference(phase8_root):
    """Native completed snapshots reconcile counts while retaining zero and skipped rows."""
    with database_session(phase8_root,write=True) as db:
        a,b,r,other,e=household(db)
        native,_=w.start(db,a,r,'UTC');entry=w.entries(db,a,native)[0]
        w.finish(db,a,native,dict(revision='0',entry_id=entry['id'],current_position='0',weight='0'))
        d.delete_exercise(db,a,e,approval(db,'exercise',e,a))
        parent,rows=h.effective(db,a,native)
        assert parent['entry_count']==1 and rows[0]['name']=='Plank' and rows[0]['position']==0
        assert rows[0]['actual_duration_seconds'] is None
        assert h.chart_series(db,a,{})[0]['points']==[]
        fresh=c.create_definition(db,a,'Bench');c.add_entry(db,a,r,weight(exercise_id=fresh))
        draft,_=w.start(db,a,r,'UTC');new=w.entries(db,a,draft)[1]
        assert w.previous(db,a,w.session(db,a,draft),new)==(None,None)


def test_detached_routine_insert_ownership_guards(phase8_root):
    """Removing historical routine FKs does not permit new cross-person snapshots."""
    with database_session(phase8_root,write=True) as db:
        a,b,r,other,e=household(db)
        form=h.prepare(db,a,r,dict(workout_date='2020-01-01',workout_time=''),'UTC')
        with pytest.raises(sqlite3.IntegrityError):
            db.execute('INSERT INTO historical_forms SELECT ?,?,routine_id,routine_name,timezone,workout_date,workout_time,occurred_at,prepared_at,snapshots_json FROM historical_forms WHERE id=?',('forged',b,form))
