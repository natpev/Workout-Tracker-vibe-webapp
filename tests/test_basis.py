# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Permanent basis, migration, old audit compatibility and repetition regressions.

Phase 13 SQL is a frozen synthetic fixture, not a retained conversion writer.
Every database is disposable; no production storage or configuration is accessed.
"""
import json
import sqlite3
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch
import pytest
from workout_tracker import catalog as c,history as h,workouts as w,basis as b,create_app
from workout_tracker.storage import initialize_storage,database_session,inspect_storage,StorageError
from workout_tracker.migrations import migrate_storage
from workout_tracker.maintenance import backup,restore
from workout_tracker import weight_statistics as stats, deletions as d
from test_combined import phase11_root,phase9_root
from test_history import manual,correction_payload
from test_phase8_deletion import approval,token


def legacy_fixture(tmp_path):
    """Load an archived schema-9 household with conversions, corrections and a draft."""
    root=tmp_path/'phase13';details=initialize_storage(root);identity=details['storage_id']
    path=root/'data'/f'schema-9-{identity}-{uuid4().hex}.sqlite3'
    with sqlite3.connect(path) as db:
        db.executescript((Path(__file__).parent/'fixtures/phase13.sql').read_text())
        db.execute('UPDATE storage_metadata SET storage_id=?',(identity,))
    path.chmod(0o600)
    (root/'config/active.json').write_text(json.dumps(dict(database=path.name,storage_id=identity)))
    (root/'config/session.key').write_text('a'*64);(root/'config/session.key').chmod(0o600)
    with database_session(root) as db:
        a=db.execute("SELECT id FROM people WHERE name='A'").fetchone()[0]
        other=db.execute("SELECT id FROM people WHERE name='B'").fetchone()[0]
        e=db.execute("SELECT id FROM exercises WHERE name='Shared carry'").fetchone()[0]
        r=db.execute("SELECT id FROM routines WHERE name='Weight routine'").fetchone()[0]
        rb=db.execute("SELECT id FROM routines WHERE name='B copy'").fetchone()[0]
        first=db.execute("SELECT id FROM historical_workouts WHERE person_id=? AND workout_date='2020-01-01'",(a,)).fetchone()[0]
        foreign=db.execute('SELECT id FROM historical_workouts WHERE person_id=?',(other,)).fetchone()[0]
    return dict(root=root,a=a,other=other,e=e,r=r,rb=rb,first=first,foreign=foreign,original=path,source=path.read_bytes())


@pytest.fixture
def basis_data(tmp_path):
    x=legacy_fixture(tmp_path);migrate_storage(x['root'],10);return x


def weights(db,person,exercise):
    return {(p['id'],r['id']):r['actual_weight_tenths_lb'] for p,rows in h.all_completed(db,person) for r in rows if r['exercise_id']==exercise and r['measurement_type']!='time'}


def dump(db):
    return '\n'.join(db.iterdump())


def settings(db,x,**changes):
    result=dict(c.default_values(c.exercise_defaults(db,x['a'],x['e'])),name='Shared carry')
    result.update(changes);return result


def draft_values(db,x,**changes):
    parent=w.active(db,x['a']);rows=w.entries(db,x['a'],parent['id']);row=rows[0]
    values=dict(revision=str(parent['revision']),entry_id=row['id'],current_position='0',weight='40')
    values.update({f'reps_{i}':str(row['target_reps']) for i in range(row['target_sets'])});values.update(changes)
    return parent,rows,values


def test_schema10_preserves_originals_audits_nulls_and_effective_values(basis_data):
    x=basis_data;assert x['original'].read_bytes()==x['source']
    with sqlite3.connect(x['original']) as before,database_session(x['root']) as db:
        for name, in before.execute("SELECT name FROM sqlite_schema WHERE type='table' AND substr(name,1,7)!='sqlite_'"):
            cols=','.join('"'+r[1]+'"' for r in before.execute(f'PRAGMA table_info({name})'))
            old=before.execute(f'SELECT {cols} FROM {name} ORDER BY 1').fetchall()
            new=[tuple(r) for r in db.execute(f'SELECT {cols} FROM {name} ORDER BY 1')]
            if name=='schema_migrations':new=[r for r in new if r[0]<=9]
            assert old==new,name
        parent,rows=h.effective(db,x['a'],x['first'])
        assert rows[0]['actual_weight_tenths_lb']==250 and rows[0]['actual_reps'] is None
        assert stats.workout_total(rows)==1800
        assert len(h.audit(db,x['a'],x['first']))==3
        assert db.execute('SELECT count(*) FROM basis_transitions').fetchone()[0]==4
        assert all(row['actual_reps_json'] is None for row in db.execute('SELECT actual_reps_json FROM historical_entries'))
        assert w.active(db,x['a']) is not None
    assert inspect_storage(x['root'])['schema_version']==10


@pytest.mark.parametrize('table',['exercise_defaults','routine_exercises'])
@pytest.mark.parametrize('basis',['total','not_configured'])
def test_database_basis_lock(basis_data,table,basis):
    with database_session(basis_data['root'],write=True) as db:
        with pytest.raises(sqlite3.IntegrityError):db.execute(f'UPDATE {table} SET weight_basis=? WHERE exercise_id=?',(basis,basis_data['e']))


@pytest.mark.parametrize('operation',['defaults','routine'])
@pytest.mark.parametrize('changes',[{'weight_basis':'total'},{'weight_basis':'not_configured'},{'measurement_type':'time','seconds':'45'}])
def test_service_lock_rejects_crafted_changes(basis_data,operation,changes):
    x=basis_data
    with database_session(x['root'],write=True) as db:
        values=settings(db,x,**changes);before=dump(db)
        with pytest.raises(c.ValidationError,match='[Ll]ocked|permanent'):
            if operation=='defaults':c.update_defaults(db,x['a'],x['e'],values)
            else:
                row=db.execute('SELECT id FROM routine_exercises WHERE routine_id=? ORDER BY position',(x['r'],)).fetchone()
                c.update_entry(db,x['a'],x['r'],row[0],values)
        assert dump(db)==before


@pytest.mark.parametrize('basis',[None,'','not_configured','invalid'])
def test_creation_requires_explicit_basis(basis_data,basis):
    x=basis_data
    with database_session(x['root'],write=True) as db:
        values=dict(measurement_type='weight',target_sets='3',target_reps='12')
        if basis is not None:values['weight_basis']=basis
        with pytest.raises(c.ValidationError):c.create_definition(db,x['a'],'New',values)
        assert not db.execute("SELECT 1 FROM exercises WHERE name='New'").fetchone()


@pytest.mark.parametrize('basis',['total','per_side'])
@pytest.mark.parametrize('kind',['weight','weight_duration','time'])
def test_creation_permanent_modes_and_inheritance(basis_data,basis,kind):
    x=basis_data
    with database_session(x['root'],write=True) as db:
        values=dict(measurement_type=kind,target_sets='5',target_reps='12',seconds='45',weight_basis=basis)
        exercise=c.create_definition(db,x['a'],'New',values)
        added=c.add_entry(db,x['other'],x['rb'],dict(exercise_id=exercise,use_library_defaults='yes'))
        assert c.entry(db,x['other'],x['rb'],added)['weight_basis']==('not_configured' if kind=='time' else basis)


@pytest.mark.parametrize('table',['exercise_defaults','routine_exercises','workout_entries'])
def test_unclassified_migration_preserves_original(tmp_path,table):
    x=legacy_fixture(tmp_path)
    with database_session(x['root'],write=True) as db:
        # Fixtures only: a new unclassified identity requires no old audit rewrite.
        e=c.create_definition(db,x['a'],'Unclassified',dict(measurement_type='weight',target_sets='3',target_reps='12'))
        if table!='exercise_defaults':
            c.update_defaults(db,x['a'],e,dict(measurement_type='weight',target_sets='3',target_reps='12',weight_basis='total'))
            c.add_entry(db,x['other'],x['rb'],dict(exercise_id=e,measurement_type='weight',target_sets='3',target_reps='12'))
            if table=='workout_entries':
                w.start(db,x['other'],x['rb'],'UTC')
                db.execute("UPDATE routine_exercises SET weight_basis='total' WHERE exercise_id=?",(e,))
    source=x['original'].read_bytes();manifest=(x['root']/'config/active.json').read_bytes()
    with pytest.raises(StorageError,match='Update 1 first'):migrate_storage(x['root'],10)
    assert source==x['original'].read_bytes() and manifest==(x['root']/'config/active.json').read_bytes()
    assert inspect_storage(x['root'])['schema_version']==9


def test_library_wins_current_conflict_without_rewriting_history(tmp_path):
    x=legacy_fixture(tmp_path)
    with database_session(x['root'],write=True) as db:
        db.execute("UPDATE routine_exercises SET weight_basis='total' WHERE exercise_id=?",(x['e'],))
        before=weights(db,x['a'],x['e'])
    original=x['original'].read_bytes();migrate_storage(x['root'],10)
    with database_session(x['root']) as db:
        assert {row[0] for row in db.execute('SELECT weight_basis FROM routine_exercises WHERE exercise_id=?',(x['e'],))}=={'per_side'}
        assert weights(db,x['a'],x['e'])==before
    assert x['original'].read_bytes()==original


@pytest.mark.parametrize('stage',['upgrade','preservation','logical','activation','post_activation'])
def test_failed_migration_retains_original(tmp_path,stage):
    x=legacy_fixture(tmp_path);active=x['root']/'config/active.json';manifest=active.read_bytes()
    from workout_tracker import migrations as m,final_schema
    if stage=='upgrade':context=patch('workout_tracker.final_schema.upgrade_final',side_effect=RuntimeError('fault'))
    elif stage=='preservation':
        real=final_schema.upgrade_final
        def corrupt(db):
            real(db);db.execute("UPDATE exercise_defaults SET notes='changed'")
        context=patch('workout_tracker.final_schema.upgrade_final',side_effect=corrupt)
    elif stage=='logical':context=patch('workout_tracker.migrations._validate_candidate',side_effect=StorageError('fault'))
    elif stage=='activation':context=patch('workout_tracker.migrations._write_manifest',side_effect=OSError('fault'))
    else:
        real=m._sync_directory;failed=[]
        def once(path):
            if path.name=='config' and b'schema-10-' in active.read_bytes() and not failed:
                failed.append(True);raise OSError('fault')
            return real(path)
        context=patch('workout_tracker.migrations._sync_directory',side_effect=once)
    with context,pytest.raises(StorageError):migrate_storage(x['root'],10)
    assert active.read_bytes()==manifest and x['original'].read_bytes()==x['source']


@pytest.mark.parametrize('values',[[12,12,10],[12,10,0],[0,0,0],[15,15,15]])
def test_repetition_autosave_resume_completion_and_correction(basis_data,values):
    x=basis_data
    with database_session(x['root'],write=True) as db:
        parent,rows,raw=draft_values(db,x,**{f'reps_{i}':str(v) for i,v in enumerate(values)})
        w.update(db,x['a'],parent['id'],raw)
        assert w.entries(db,x['a'],parent['id'])[0]['actual_reps']==values
    with database_session(x['root'],write=True) as db:
        parent,rows,raw=draft_values(db,x,**{f'reps_{i}':str(v) for i,v in enumerate(values)})
        w.finish(db,x['a'],parent['id'],raw)
        assert h.effective(db,x['a'],parent['id'])[1][0]['actual_reps']==values
        original=h.original(db,x['a'],parent['id'])[1][0]
        corrected=correction_payload(db,x['a'],parent['id'],weight_0='40',**{f'reps_0_{i}':'1' for i in range(3)})
        h.correct(db,x['a'],parent['id'],corrected)
        effective=h.effective(db,x['a'],parent['id'])[1][0]
        assert effective['actual_reps']==[1,1,1] and stats.entry_total(effective)==240
        assert h.original(db,x['a'],parent['id'])[1][0]==original


@pytest.mark.parametrize('bad',['','-1','1.5','abc','10001','99999999999999999999999999999999'])
def test_repetitions_invalid_no_partial_save(basis_data,bad):
    x=basis_data
    with database_session(x['root']) as db:before=dump(db)
    with pytest.raises(c.ValidationError):
        with database_session(x['root'],write=True) as db:
            parent,_,raw=draft_values(db,x,reps_1=bad)
            w.update(db,x['a'],parent['id'],raw)
    with database_session(x['root']) as db:assert dump(db)==before


def test_legacy_repetition_correction_audits_backup_restore(basis_data):
    x=basis_data
    with database_session(x['root'],write=True) as db:
        old=h.audit(db,x['a'],x['first'])
        raw=correction_payload(db,x['a'],x['first'],weight_0='25',reps_0_0='12',reps_0_1='12',reps_0_2='10')
        h.correct(db,x['a'],x['first'],raw)
        assert h.audit(db,x['a'],x['first'])[:-1]==old
        assert stats.workout_total(h.effective(db,x['a'],x['first'])[1])==1700
    saved=backup(x['root'],uuid4().hex);assert saved['status']=='verified'
    assert restore(x['root'],saved['id'],uuid4().hex,confirm=True)['status']=='succeeded'
    with database_session(x['root']) as db:
        assert h.effective(db,x['a'],x['first'])[1][0]['actual_reps']==[12,12,10]


def test_conversion_writers_removed_and_database_closed(basis_data):
    x=basis_data
    for name in ('apply','plan','baseline','status','convert','payload'):
        assert not hasattr(b,name)
    with database_session(x['root'],write=True) as db:
        for table in ('basis_transitions','basis_assignments'):
            row=db.execute(f'SELECT * FROM {table} LIMIT 1').fetchone()
            with pytest.raises(sqlite3.IntegrityError,match='closed'):
                db.execute(f"INSERT INTO {table} VALUES ({','.join('?' for _ in row)})",tuple(row))


def test_defaults_both_scopes_atomic_and_other_person_unchanged(basis_data):
    from workout_tracker.defaults_views import save
    x=basis_data
    with database_session(x['root'],write=True) as db:
        original=weights(db,x['a'],x['e']);foreign=[tuple(r) for r in db.execute('SELECT * FROM routine_exercises WHERE person_id=?',(x['other'],))]
        values=settings(db,x,target_sets='5',target_reps='10',notes='New shared default')
        save(db,x['a'],x['e'],values)
        assert db.execute('SELECT target_sets FROM routine_exercises WHERE routine_id=? ORDER BY position',(x['r'],)).fetchone()[0]==3
        save(db,x['a'],x['e'],values,True)
        assert {r[0] for r in db.execute('SELECT target_sets FROM routine_exercises WHERE person_id=? AND exercise_id=?',(x['a'],x['e']))}=={5}
        assert [tuple(r) for r in db.execute('SELECT * FROM routine_exercises WHERE person_id=?',(x['other'],))]==foreign
        assert weights(db,x['a'],x['e'])==original


def test_http_locked_editor_old_conversion_confirmation_and_history(basis_data):
    import re
    x=basis_data;client=create_app({'TESTING':True,'WORKOUT_DATA_ROOT':x['root']}).test_client()
    path=f"/people/{x['a']}/exercises/{x['e']}/defaults";page=client.get(path)
    assert b'name="weight_basis"' not in page.data and b'name="weight_meaning"' not in page.data
    assert b'Not Configured' not in page.data and b'Weight Basis setup' not in client.get(f"/people/{x['a']}/exercises").data
    revision=re.search(r'name="revision" value="([^"]+)"',page.get_data(as_text=True))[1]
    with database_session(x['root']) as db:before=dump(db);values=settings(db,x)
    raw={k:str(v) for k,v in values.items() if v is not None};raw.update(csrf_token=token(page),revision=revision,weight_basis='total')
    assert client.post(path,data=raw).status_code==400
    assert client.post(path,data=dict(csrf_token=token(page),action='confirm',preview='old-conversion-token',confirm='yes')).status_code==400
    with database_session(x['root']) as db:assert dump(db)==before
    detail=client.get(f"/people/{x['a']}/history/{x['first']}")
    assert detail.status_code==200 and b'Actual repetitions were not recorded' in detail.data and b'25.0 lb' in detail.data
def seed8(root):
    """Make realistic live/manual/combined/NULL/zero/corrected shared identities."""
    with database_session(root,write=True) as db:
        a=c.create_person(db,'A');other=c.create_person(db,'B')
        e=c.create_definition(db,a,'Shared carry',dict(measurement_type='weight',target_sets='3',target_reps='12',weight_meaning='old free text',notes='Keep defaults'))
        r=c.create_routine(db,a,'Weight routine')
        c.add_entry(db,a,r,dict(exercise_id=e,use_library_defaults='yes'))
        c.add_entry(db,a,r,dict(name='Plank',measurement_type='time',target_sets='2',seconds='45'))
        rb=c.copy_routine(db,a,r,other,'B copy')
        rc=c.create_routine(db,a,'Combined routine')
        c.add_entry(db,a,rc,dict(exercise_id=e,measurement_type='weight_duration',target_sets='2',seconds='60',weight_meaning='legacy hold',notes='Historical prescription'))
        first,form=manual(db,a,r,'2020-01-01',weight_0='25',seconds_1='45',increase_0='1')
        h.correct(db,a,first,correction_payload(db,a,first,weight_0='50'))
        combined,_=manual(db,a,rc,'2020-01-02',weight_0='50',seconds_0='90')
        zero,_=manual(db,a,r,'2020-01-03',weight_0='0')
        skipped,_=manual(db,a,r,'2020-01-04',confirm_all_skipped='yes')
        foreign,_=manual(db,other,rb,'2020-01-01',weight_0='40')
        live,_=w.start(db,a,r,'UTC');parent=w.session(db,a,live);entry=w.entries(db,a,live)[0]
        w.finish(db,a,live,dict(revision=str(parent['revision']),entry_id=entry['id'],current_position='0',weight='40'))
        removed=c.copy_routine(db,a,r,a,'Removed routine')
        retained,_=manual(db,a,removed,'2020-01-05',weight_0='40')
        d.delete_routine(db,a,removed,approval(db,'routine',removed,a))
        originals={p['id']:h.original(db,a,p['id']) for p,_ in h.all_completed(db,a)}
        old_audit=h.audit(db,a,first)
    original=(root/'data'/json.loads((root/'config/active.json').read_text())['database']);source=original.read_bytes()
    return dict(root=root,a=a,other=other,e=e,r=r,rb=rb,rc=rc,first=first,form=form,combined=combined,foreign=foreign,live=live,retained=retained,original=original,source=source,originals=originals,old_audit=old_audit)


@pytest.mark.parametrize('kind',['weight','weight_duration','time'])
def test_manual_history_and_csv_effective_reps(basis_data,kind):
    from workout_tracker.csv_export import wide_csv
    x=basis_data
    with database_session(x['root'],write=True) as db:
        r=c.create_routine(db,x['a'],'Manual routine')
        e=c.create_definition(db,x['a'],'Manual exercise',dict(measurement_type=kind,target_sets='2',target_reps='12',seconds='45',weight_basis='total'))
        c.add_entry(db,x['a'],r,dict(exercise_id=e,use_library_defaults='yes'))
        prepared=h.prepare(db,x['a'],r,dict(workout_date='2020-03-01',workout_time=''),'UTC')
        raw=dict(weight_0='40' if kind!='time' else '',seconds_0='60' if kind!='weight' else '',reps_0_0='12',reps_0_1='10')
        identity=h.complete_historical(db,x['a'],prepared,raw)
        assert h.complete_historical(db,x['a'],prepared,raw)==identity
        rows=h.effective(db,x['a'],identity)[1]
        assert rows[0]['actual_reps']==([12,10] if kind=='weight' else None)
        assert stats.workout_total(rows)==(880 if kind=='weight' else 80 if kind=='weight_duration' else 0)
        exported=wide_csv(db,x['a'],{},[e])
        if kind=='weight':assert 'Actual Repetitions by Set' in exported and '12; 10' in exported
        else:assert 'Actual Repetitions' not in exported


def test_skipped_nulls_zero_reps_and_completion_retry(basis_data):
    x=basis_data
    with database_session(x['root'],write=True) as db:
        parent,_,raw=draft_values(db,x,weight='',confirm_all_skipped='yes')
        w.finish(db,x['a'],parent['id'],raw)
        row=h.effective(db,x['a'],parent['id'])[1][0]
        assert row['actual_reps'] is None and row['actual_weight_tenths_lb'] is None
        assert w.finish(db,x['a'],parent['id'],raw)['id']==parent['id']
        assert db.execute('SELECT count(*) FROM workout_registry WHERE id=?',(parent['id'],)).fetchone()[0]==1
        assert db.execute('SELECT actual_reps_json FROM workout_entries WHERE id=?',(row['id'],)).fetchone()[0] is None


def test_lifetime_person_drafts_retained_routine_and_history_deletion(basis_data):
    from workout_tracker import deletions as d
    x=basis_data
    with database_session(x['root'],write=True) as db:
        before=stats.summary(h.all_completed(db,x['a']))
        foreign=stats.summary(h.all_completed(db,x['other']))
        assert before['lifetime']!=foreign['lifetime']
        # A retained deleted-routine workout is already in the archived fixture.
        assert any(parent['routine_deleted'] for parent,_ in h.all_completed(db,x['a']))
        draft=w.active(db,x['a']);w.discard(db,x['a'],draft['id'],dict(revision=str(draft['revision']),confirm='yes'))
        assert stats.summary(h.all_completed(db,x['a']))==before
        d.delete_exercise(db,x['a'],x['e'],approval(db,'exercise',x['e'],x['a']))
        assert stats.summary(h.all_completed(db,x['a']))['lifetime']=='0 lb'
        assert stats.summary(h.all_completed(db,x['other']))['lifetime']=='0 lb'
    assert inspect_storage(x['root'])['schema_version']==10


@pytest.mark.parametrize('value',['[]','[1,2]','[1,2,3.5]','[1,2,-1]','[1,2,10001]','[1,2,null]','{"0":1}'])
def test_database_rejects_invalid_repetition_arrays(basis_data,value):
    x=basis_data
    with database_session(x['root'],write=True) as db:
        parent,rows,_=draft_values(db,x)
        with pytest.raises(sqlite3.IntegrityError):db.execute('UPDATE workout_entries SET actual_reps_json=? WHERE id=?',(value,rows[0]['id']))


def test_sql_permanent_basis_current_routine_insert_rejects_mismatch(basis_data):
    x=basis_data
    with database_session(x['root'],write=True) as db:
        row=list(db.execute('SELECT * FROM routine_exercises WHERE routine_id=? ORDER BY position',(x['r'],)).fetchone())
        names=[r[1] for r in db.execute('PRAGMA table_info(routine_exercises)')]
        row[names.index('id')]=uuid4().hex;row[names.index('position')]=99;row[names.index('weight_basis')]='total'
        with pytest.raises(sqlite3.IntegrityError,match='Library'):
            db.execute(f"INSERT INTO routine_exercises VALUES ({','.join('?' for _ in row)})",row)


def test_effective_legacy_unknown_reps_remain_unknown_after_weight_only_correction(basis_data):
    x=basis_data
    with database_session(x['root'],write=True) as db:
        h.correct(db,x['a'],x['first'],correction_payload(db,x['a'],x['first'],weight_0='30'))
        rows=h.effective(db,x['a'],x['first'])[1]
        assert rows[0]['actual_reps'] is None and stats.workout_total(rows)==2160


def test_http_history_totals_refresh_after_actual_rep_correction(basis_data):
    x=basis_data;client=create_app({'TESTING':True,'WORKOUT_DATA_ROOT':x['root']}).test_client()
    with database_session(x['root']) as db:
        before=stats.summary(h.all_completed(db,x['a']))
    assert before['lifetime'].encode() in client.get(f"/people/{x['a']}").data
    with database_session(x['root'],write=True) as db:
        h.correct(db,x['a'],x['first'],correction_payload(db,x['a'],x['first'],weight_0='25',reps_0_0='0',reps_0_1='0',reps_0_2='0'))
        after=stats.summary(h.all_completed(db,x['a']))
        assert after['lifetime']!=before['lifetime']
    page=client.get(f"/people/{x['a']}")
    assert after['lifetime'].encode() in page.data
    assert after['lifetime'].encode() in client.get(f"/people/{x['a']}/history/{x['first']}").data


def test_legacy_audit_tampering_still_rejected(basis_data):
    x=basis_data
    with sqlite3.connect(x['root']/'data'/json.loads((x['root']/'config/active.json').read_text())['database']) as db:
        db.create_function('deletion_in_progress',0,lambda:1)
        db.execute('DELETE FROM basis_assignments WHERE rowid=(SELECT min(rowid) FROM basis_assignments)')
    with pytest.raises(StorageError,match='Basis audit'):inspect_storage(x['root'])


def test_confirmed_default_update_rolls_back_all_fields_on_failure(basis_data):
    from workout_tracker.defaults_views import save
    x=basis_data
    with database_session(x['root']) as db:before=dump(db)
    with pytest.raises(StorageError):
        with database_session(x['root'],write=True) as db:
            db.execute("CREATE TEMP TRIGGER injected_failure BEFORE UPDATE ON main.routine_exercises BEGIN SELECT RAISE(ABORT,'Synthetic failure'); END")
            save(db,x['a'],x['e'],settings(db,x,name='Must roll back',notes='Must roll back'),True)
    with database_session(x['root']) as db:assert dump(db)==before


def test_retained_update1_migration_preserves_schema8_cells(phase11_root):
    x=seed8(phase11_root);migrate_storage(x['root'],9)
    assert x['original'].read_bytes()==x['source']
    with database_session(x['root']) as db:
        assert c.exercise_defaults(db,x['a'],x['e'])['weight_basis']=='not_configured'
        assert not db.execute('SELECT 1 FROM basis_transitions').fetchone()
        assert h.effective(db,x['a'],x['first'])[1][0]['actual_weight_tenths_lb']==500
    with pytest.raises(StorageError,match='Update 1 first'):migrate_storage(x['root'],10)
    assert inspect_storage(x['root'])['schema_version']==9


def test_new_install_empty_upgrade_and_scheduled_backup(tmp_path,monkeypatch):
    from workout_tracker import scheduler,operations as o
    from datetime import datetime,timezone
    root=tmp_path/'new';initialize_storage(root);migrate_storage(root,10)
    assert inspect_storage(root)['schema_version']==10
    assert migrate_storage(root,10)['changed'] is False
    record=backup(root,uuid4().hex);assert record['status']=='verified'
    assert restore(root,record['id'],uuid4().hex,confirm=True)['status']=='succeeded'
    monkeypatch.setattr(o,'now',lambda:datetime(2026,1,1,9,tzinfo=timezone.utc))
    scheduler.configure(root,dict(enabled='yes',days='1',time='10:30',timezone='Etc/UTC',retention_days='30'))
    monkeypatch.setattr(o,'now',lambda:datetime(2026,1,1,11,tzinfo=timezone.utc))
    scheduler.tick(root);scheduler.tick(root)
    automatic=[r for r in o.read_state(root)['backups'].values() if r['source']=='automatic']
    assert len(automatic)==1 and automatic[0]['status']=='verified' and automatic[0]['schema_version']==10


def test_schema10_damaged_active_restore_retains_damaged_source(basis_data):
    x=basis_data;root=x['root']
    saved=backup(root,uuid4().hex);assert saved['status']=='verified'
    active=root/'data'/json.loads((root/'config/active.json').read_text())['database']
    damaged=b'Synthetic damaged schema-10 database';active.write_bytes(damaged)
    with pytest.raises(StorageError):inspect_storage(root)
    result=restore(root,saved['id'],uuid4().hex,confirm=True)
    assert result['status']=='succeeded' and active.read_bytes()==damaged
    assert inspect_storage(root)['schema_version']==10
    with database_session(root) as db:
        assert h.effective(db,x['a'],x['first'])[1][0]['actual_weight_tenths_lb']==250


def test_schema10_routine_copy_retains_independent_original_configuration(basis_data):
    x=basis_data
    with database_session(x['root'],write=True) as db:
        source=x['r']
        # Model grandfathered routine text distinct from the shared Library preset.
        db.execute("UPDATE routine_exercises SET weight_meaning='legacy hold' WHERE routine_id=? AND exercise_id=?",(source,x['e']))
        before=[dict(row) for row in db.execute('SELECT * FROM routine_exercises WHERE routine_id=? ORDER BY position',(source,))]
        copied=c.copy_routine(db,x['a'],source,x['other'],'Independent source copy')
        after=[dict(row) for row in db.execute('SELECT * FROM routine_exercises WHERE routine_id=? ORDER BY position',(copied,))]
        for old,new in zip(before,after):
            assert {k:v for k,v in old.items() if k not in ('id','person_id','routine_id')}=={k:v for k,v in new.items() if k not in ('id','person_id','routine_id')}
        assert after[0]['exercise_id']==x['e'] and after[0]['weight_meaning']=='legacy hold'
