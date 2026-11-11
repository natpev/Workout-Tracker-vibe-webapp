# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Synthetic schema-8/9 migration, exact conversion, isolation and audit regressions.

Every operation uses disposable storage. Original bytes/rows and correction JSON
are compared explicitly; no real workout data or server configuration is read.
"""
import hashlib
import json
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch
import pytest
from workout_tracker import catalog as c,history as h,workouts as w,basis as b,create_app
from workout_tracker.storage import database_session,inspect_storage,StorageError
from workout_tracker.migrations import migrate_storage
from workout_tracker.maintenance import logical_check,backup,restore
from workout_tracker import deletions as d
from test_combined import phase11_root,phase9_root
from test_history import manual,correction_payload
from test_phase8_deletion import approval,token


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


@pytest.fixture
def basis_data(phase11_root):
    """Upgrade only a separate candidate after realistic schema-8 data exists."""
    data=seed8(phase11_root);migrate_storage(phase11_root,9);return data


def settings(db,data,basis='total',**changes):
    """Current valid preset with explicit convention; never infer from legacy text."""
    result=dict(c.default_values(c.exercise_defaults(db,data['a'],data['e'])),name=c.definition(db,data['a'],data['e'])['name'],weight_basis=basis)
    result.update(changes);return result


def apply(db,data,value,**changes):
    """Model a fresh preview and deliberate confirmation in the caller's transaction."""
    values=settings(db,data,value,**changes);preview=b.plan(db,data['a'],data['e'],values)
    identity=uuid4().hex;b.apply(db,data['a'],data['e'],values,identity,preview['fingerprint'],confirmed=True)
    return identity


def weights(db,person,exercise):
    """Return current effective values keyed by permanent workout/entry, including NULL."""
    return {(p['id'],r['id']):r['actual_weight_tenths_lb'] for p,rows in h.all_completed(db,person) for r in rows if r['exercise_id']==exercise and r['measurement_type']!='time'}


def dump(db):return '\n'.join(db.iterdump())


def test_schema9_preserves_every_original_cell_meaning_and_protection(basis_data):
    data=basis_data;root=data['root']
    assert data['original'].read_bytes()==data['source']
    assert inspect_storage(root)['schema_version']==9
    import sqlite3
    with sqlite3.connect(data['original']) as source,database_session(root) as db:
        for name, in source.execute("SELECT name FROM sqlite_schema WHERE type='table' AND substr(name,1,7)!='sqlite_' ORDER BY name"):
            cols=','.join('"'+r[1]+'"' for r in source.execute(f'PRAGMA table_info({name})'))
            old=source.execute(f'SELECT {cols} FROM {name} ORDER BY 1').fetchall();new=[tuple(r) for r in db.execute(f'SELECT {cols} FROM {name} ORDER BY 1')]
            if name=='schema_migrations':new=[r for r in new if r[0]<=8]
            assert old==new,name
        for table in ('exercise_defaults','routine_exercises','workout_entries','historical_entries'):
            assert not db.execute(f"SELECT 1 FROM {table} WHERE weight_basis!='not_configured'").fetchone()
        assert not db.execute('SELECT 1 FROM basis_transitions').fetchone()
        assert c.exercise_defaults(db,data['a'],data['e'])['weight_meaning']=='old free text'
    logical_check((root/'data'/json.loads((root/'config/active.json').read_text())['database']),9)
    with database_session(root,write=True) as db:
        with pytest.raises(sqlite3.IntegrityError,match='Immutable'):
            db.execute("UPDATE workout_entries SET weight_basis='total'")


@pytest.mark.parametrize('first',['total','per_side'])
def test_first_classification_no_weights_changed_person_isolation(basis_data,first):
    x=basis_data
    with database_session(x['root'],write=True) as db:
        before=weights(db,x['a'],x['e']);foreign=weights(db,x['other'],x['e'])
        apply(db,x,first)
        assert weights(db,x['a'],x['e'])==before and weights(db,x['other'],x['e'])==foreign
        assert b.baseline(db,x['a'],x['e'])==(first,1) and b.baseline(db,x['other'],x['e'])==('not_configured',0)
        assert {r['weight_basis'] for p,rows in h.all_completed(db,x['a']) for r in rows if r['exercise_id']==x['e']}=={first}
        assert {r[0] for r in db.execute('SELECT weight_basis FROM routine_exercises WHERE person_id=? AND exercise_id=?',(x['other'],x['e']))}=={'not_configured'}
        for identity,(parent,rows) in x['originals'].items():
            original,newrows=h.original(db,x['a'],identity)
            assert {k:v for k,v in original.items()}==parent
            assert [{k:v for k,v in row.items() if k!='weight_basis'} for row in newrows]==rows
        assert [{k:v for k,v in row.items() if k!='basis_transitions'} for row in h.audit(db,x['a'],x['first'])[:1]]==x['old_audit']


def test_repeated_reversible_conversions_effective_readers_and_later_correction(basis_data):
    x=basis_data
    with database_session(x['root'],write=True) as db:
        before=weights(db,x['a'],x['e']);foreign=weights(db,x['other'],x['e'])
        durations={r['id']:r['actual_duration_seconds'] for p,rs in h.all_completed(db,x['a']) for r in rs}
        apply(db,x,'total')
        for _ in range(3):
            apply(db,x,'per_side')
            assert weights(db,x['a'],x['e'])=={k:None if v is None else v//2 for k,v in before.items()}
            apply(db,x,'per_side') # A fresh same-basis save never divides again.
            apply(db,x,'total');assert weights(db,x['a'],x['e'])==before
        apply(db,x,'per_side')
        h.correct(db,x['a'],x['first'],correction_payload(db,x['a'],x['first'],weight_0='12.5'))
        assert h.effective(db,x['a'],x['first'])[1][0]['actual_weight_tenths_lb']==125
        apply(db,x,'total');assert h.effective(db,x['a'],x['first'])[1][0]['actual_weight_tenths_lb']==250
        apply(db,x,'per_side');assert h.effective(db,x['a'],x['first'])[1][0]['actual_weight_tenths_lb']==125
        assert weights(db,x['other'],x['e'])==foreign
        assert {r['id']:r['actual_duration_seconds'] for p,rs in h.all_completed(db,x['a']) for r in rs}==durations
        from workout_tracker.csv_export import wide_csv
        exported=wide_csv(db,x['a'],{},[x['e']]);assert 'Per Hand / Side' in exported and '12.5' in exported
        assert any(s['highest']['raw']==250 for s in h.chart_series(db,x['a'],{'exercise':x['e']}) if s['kind']=='weight' and s['highest'])
        draft,_=w.start(db,x['a'],x['r'],'UTC');parent=w.session(db,x['a'],draft);row=w.entries(db,x['a'],draft)[0]
        previous,_=w.previous(db,x['a'],parent,row);assert previous is not None and previous['weight_basis']=='per_side'
        assert row['actual_weight_tenths_lb'] is None


@pytest.mark.parametrize('bad,old,new',[('25.5','total','per_side'),(f'{w.MAX_INTEGER//10}.{w.MAX_INTEGER%10}','per_side','total')])
def test_precision_and_overflow_refuse_whole_operation(basis_data,bad,old,new):
    x=basis_data
    with database_session(x['root'],write=True) as db:
        apply(db,x,old)
        h.correct(db,x['a'],x['first'],correction_payload(db,x['a'],x['first'],weight_0=bad))
    with database_session(x['root']) as db:before=dump(db)
    with pytest.raises(c.ValidationError,match='workout.*Correct'):
        with database_session(x['root'],write=True) as db:apply(db,x,new,name='Must roll back',notes='Unsaved')
    with database_session(x['root']) as db:assert dump(db)==before


def test_defaults_only_copy_inheritance_and_all_personal_configuration_fields(basis_data):
    x=basis_data
    with database_session(x['root'],write=True) as db:
        original=weights(db,x['a'],x['e']);other=[tuple(r) for r in db.execute('SELECT * FROM routine_exercises WHERE person_id=?',(x['other'],))]
        vals=settings(db,x,'total',measurement_type='weight_duration',target_sets='7',minutes='2',seconds='15',weight_meaning='new total convention',notes='New global notes')
        c.update_defaults(db,x['other'],x['e'],vals)
        assert b.baseline(db,x['a'],x['e'])==('not_configured',0)
        assert weights(db,x['a'],x['e'])==original
        new=c.create_routine(db,x['other'],'New');item=c.add_entry(db,x['other'],new,dict(exercise_id=x['e'],use_library_defaults='yes'))
        assert c.entry(db,x['other'],new,item)['weight_basis']=='total'
        copied=c.copy_routine(db,x['other'],x['rb'],x['a'],'Independent old settings')
        assert db.execute('SELECT weight_basis FROM routine_exercises WHERE routine_id=? ORDER BY position',(copied,)).fetchone()[0]=='not_configured'
        token=uuid4().hex;preview=b.plan(db,x['a'],x['e'],vals);b.apply(db,x['a'],x['e'],vals,token,preview['fingerprint'],confirmed=True)
        for row in db.execute('SELECT * FROM routine_exercises WHERE person_id=? AND exercise_id=?',(x['a'],x['e'])):
            assert (row['measurement_type'],row['target_sets'],row['target_reps'],row['target_duration_seconds'],row['unit'],row['weight_meaning'],row['weight_basis'],row['notes'])==('weight_duration',7,None,135,'lb','new total convention','total','New global notes')
        assert [tuple(r) for r in db.execute('SELECT * FROM routine_exercises WHERE person_id=? AND routine_id!=?',(x['other'],new))]==other
        # Another person's global edit never changes A's actual applied baseline.
        c.update_defaults(db,x['other'],x['e'],dict(vals,weight_basis='per_side'))
        assert b.baseline(db,x['a'],x['e'])[0]=='total'
        apply(db,x,'per_side')
        assert weights(db,x['a'],x['e'])=={k:None if v is None else v//2 for k,v in original.items()}


def test_retries_stale_previews_active_drafts_and_pending_reviews(basis_data):
    x=basis_data
    with database_session(x['root'],write=True) as db:
        vals=settings(db,x,'total');preview=b.plan(db,x['a'],x['e'],vals);identity=uuid4().hex
        b.apply(db,x['a'],x['e'],vals,identity,preview['fingerprint'],confirmed=True)
        after=dump(db)
        assert b.apply(db,x['a'],x['e'],vals,identity,preview['fingerprint'],confirmed=True) is False and dump(db)==after
        with pytest.raises(w.RevisionConflict):b.apply(db,x['a'],x['e'],dict(vals,notes='Tamper'),identity,preview['fingerprint'],confirmed=True)
        pending=h.prepare(db,x['a'],x['r'],dict(workout_date='2020-02-01',workout_time=''),'UTC')
        stale=b.plan(db,x['a'],x['e'],settings(db,x,'per_side'))
        c.update_defaults(db,x['other'],x['e'],dict(vals,notes='Changed elsewhere'))
        with pytest.raises(w.RevisionConflict):b.apply(db,x['a'],x['e'],settings(db,x,'per_side'),uuid4().hex,stale['fingerprint'],confirmed=True)
        apply(db,x,'per_side')
        with pytest.raises(c.ValidationError,match='Prepare a new review'):h.complete_historical(db,x['a'],pending,dict(weight_0='40'))
        assert h.complete_historical(db,x['a'],x['form'],dict(weight_0='99'))==x['first']
        w.start(db,x['a'],x['r'],'UTC')
        with pytest.raises(c.ValidationError,match='active workout'):b.plan(db,x['a'],x['e'],vals)
        c.update_defaults(db,x['a'],x['e'],vals) # Defaults Only remains independent.


@pytest.mark.parametrize('value',[0,10,250,400,None])
def test_integer_conversion_never_rounds(value):
    assert b.convert(b.convert(value,'total','per_side'),'per_side','total')==value


@pytest.mark.parametrize('value',[1,127,255,w.MAX_INTEGER])
def test_odd_tenths_refuse_division(value):
    with pytest.raises(c.ValidationError):b.convert(value,'total','per_side')


@pytest.mark.parametrize('stage',['upgrade','preservation','logical','activation','post_activation'])
def test_schema9_failed_candidate_never_replaces_source(phase11_root,stage):
    """Fault each migration boundary; original bytes, manifest and all records survive."""
    from workout_tracker import migrations as m
    from workout_tracker import basis_schema
    x=seed8(phase11_root);root=x['root'];active=root/'config/active.json';manifest=active.read_bytes()
    if stage=='upgrade':context=patch('workout_tracker.basis_schema.upgrade_basis',side_effect=RuntimeError('synthetic upgrade fault'))
    elif stage=='preservation':
        real=basis_schema.upgrade_basis
        def corrupt(db):
            real(db);db.execute("UPDATE exercise_defaults SET weight_meaning='unexpected rewrite'")
        context=patch('workout_tracker.basis_schema.upgrade_basis',side_effect=corrupt)
    elif stage=='logical':context=patch('workout_tracker.basis.validate',side_effect=StorageError('synthetic logical failure'))
    elif stage=='activation':context=patch('workout_tracker.migrations._write_manifest',side_effect=OSError('synthetic manifest fault'))
    else:
        real=m._sync_directory;failed=[]
        def fail_once(path):
            if path.name=='config' and b'schema-9-' in active.read_bytes() and not failed:
                failed.append(True);raise OSError('synthetic activation sync fault')
            return real(path)
        context=patch('workout_tracker.migrations._sync_directory',side_effect=fail_once)
    with context,pytest.raises(StorageError,match='original selection retained'):migrate_storage(root,9)
    assert active.read_bytes()==manifest and x['original'].read_bytes()==x['source']
    assert inspect_storage(root)['schema_version']==8 and list((root/'data').glob('schema-9-*'))


def test_backup_restore_schema9_audits_and_original_preservation(basis_data):
    """Verified schema-9 backups restore only through another distinct candidate."""
    x=basis_data;root=x['root']
    with database_session(root,write=True) as db:apply(db,x,'total')
    saved=backup(root,uuid4().hex);assert saved['status']=='verified' and saved['schema_version']==9
    with database_session(root,write=True) as db:apply(db,x,'per_side')
    current=root/'data'/json.loads((root/'config/active.json').read_text())['database'];data=current.read_bytes()
    result=restore(root,saved['id'],uuid4().hex,confirm=True)
    assert result['status']=='succeeded' and current.read_bytes()==data
    assert json.loads((root/'config/active.json').read_text())['database']!=current.name
    with database_session(root) as db:assert b.baseline(db,x['a'],x['e'])==('total',1)
    assert x['original'].read_bytes()==x['source']


def test_permanent_deletion_preserves_unrelated_values_and_reconciles_basis_audits(basis_data):
    """The existing explicit destructive capability cascades only the deleted identity."""
    x=basis_data;root=x['root']
    with database_session(root,write=True) as db:
        apply(db,x,'total');apply(db,x,'per_side')
        unchanged=[(p['id'],[(r['exercise_id'],r['actual_duration_seconds']) for r in rows if r['exercise_id']!=x['e']]) for p,rows in h.all_completed(db,x['a'])]
        d.delete_exercise(db,x['a'],x['e'],approval(db,'exercise',x['e'],x['a']))
        assert not db.execute('SELECT 1 FROM basis_transitions').fetchone() and not db.execute('SELECT 1 FROM basis_assignments').fetchone()
        for identity,rows in unchanged:
            if rows:assert [(r['exercise_id'],r['actual_duration_seconds']) for r in h.effective(db,x['a'],identity)[1]]==rows
    assert inspect_storage(root)['schema_version']==9


def test_audit_delete_and_edit_are_protected_and_missing_assignment_is_detected(basis_data):
    """Even value-preserving metadata tampering cannot masquerade as a valid audit."""
    import sqlite3
    x=basis_data;root=x['root']
    with database_session(root,write=True) as db:
        apply(db,x,'total')
        for sql in ('DELETE FROM basis_assignments','UPDATE basis_transitions SET new_basis=old_basis'):
            with pytest.raises(sqlite3.IntegrityError,match='Append-only'):db.execute(sql)
    path=root/'data'/json.loads((root/'config/active.json').read_text())['database']
    with sqlite3.connect(path) as db:
        db.create_function('deletion_in_progress',0,lambda:1)
        db.execute('DELETE FROM basis_assignments WHERE rowid=(SELECT rowid FROM basis_assignments LIMIT 1)')
    with pytest.raises(StorageError,match='Basis audit'):inspect_storage(root)


def test_http_save_scopes_confirmation_replay_and_validation_preserve_inputs(basis_data):
    """Real CSRF forms require review, and retries reuse the confirmed operation."""
    import re,html
    x=basis_data;root=x['root'];client=create_app({'TESTING':True,'WORKOUT_DATA_ROOT':root}).test_client()
    path=f"/people/{x['a']}/exercises/{x['e']}/defaults"
    page=client.get(path)
    values=dict(csrf_token=token(page),revision=re.search(r'name="revision" value="([^"]+)"',page.get_data(as_text=True))[1],
                name='Shared carry',measurement_type='weight',target_sets='4',target_reps='10',unit='lb',weight_meaning='keep old description',weight_basis='total',notes='New settings',action='apply')
    preview=client.post(path,data=values);assert preview.status_code==200 and b'Divide by 2: 0' in preview.data
    with database_session(root) as db:
        assert c.exercise_defaults(db,x['a'],x['e'])['weight_basis']=='not_configured';before=dump(db)
    signed=html.unescape(re.search(r'name="preview" value="([^"]+)"',preview.get_data(as_text=True))[1])
    confirmation=dict(csrf_token=token(preview),action='confirm',preview=signed)
    assert client.post(path,data=confirmation).status_code==400
    with database_session(root) as db:assert dump(db)==before
    confirmation['confirm']='yes';assert client.post(path,data=confirmation).status_code==303
    with database_session(root) as db:after=dump(db)
    assert client.post(path,data=confirmation).status_code==303
    with database_session(root) as db:assert dump(db)==after
    # Defaults Only changes no personal configuration or effective measurement.
    page=client.get(path);values.update(csrf_token=token(page),revision=re.search(r'name="revision" value="([^"]+)"',page.get_data(as_text=True))[1],weight_basis='per_side',action='defaults')
    with database_session(root) as db:before_weights=weights(db,x['a'],x['e']);before_routines=[tuple(r) for r in db.execute('SELECT * FROM routine_exercises')]
    assert client.post(path,data=values).status_code==303
    with database_session(root) as db:
        assert weights(db,x['a'],x['e'])==before_weights and [tuple(r) for r in db.execute('SELECT * FROM routine_exercises')]==before_routines
        assert b.baseline(db,x['a'],x['e'])[0]=='total'


@pytest.mark.parametrize('same_token',[False,True])
def test_concurrent_confirmations_serialize_and_never_double_convert(basis_data,same_token):
    """Real thread/lock contention permits one transition; retries reuse its audit."""
    from concurrent.futures import ThreadPoolExecutor
    x=basis_data
    with database_session(x['root'],write=True) as db:
        before=weights(db,x['a'],x['e']);apply(db,x,'total')
        values=settings(db,x,'per_side');preview=b.plan(db,x['a'],x['e'],values)
    first=uuid4().hex;tokens=[first,first if same_token else uuid4().hex]
    def worker(identity):
        try:
            with database_session(x['root'],write=True) as db:
                return b.apply(db,x['a'],x['e'],values,identity,preview['fingerprint'],confirmed=True)
        except w.RevisionConflict:return 'stale'
    with ThreadPoolExecutor(max_workers=2) as executor:results=list(executor.map(worker,tokens))
    assert results.count(True)==1 and (False in results if same_token else 'stale' in results)
    with database_session(x['root']) as db:
        assert weights(db,x['a'],x['e'])=={k:None if v is None else v//2 for k,v in before.items()}
        assert b.baseline(db,x['a'],x['e'])==('per_side',2)


def test_classified_new_snapshot_does_not_use_global_or_person_baseline_as_its_origin(basis_data):
    """Explicit per-entry metadata handles independent routines before first bulk apply."""
    x=basis_data
    with database_session(x['root'],write=True) as db:
        old=weights(db,x['a'],x['e'])
        values=settings(db,x,'per_side');c.update_defaults(db,x['a'],x['e'],values)
        r=c.create_routine(db,x['a'],'New classified routine');c.add_entry(db,x['a'],r,dict(exercise_id=x['e'],use_library_defaults='yes'))
        form=h.prepare(db,x['a'],r,dict(workout_date='2020-02-01',workout_time=''),'UTC')
        saved=h.complete_historical(db,x['a'],form,dict(weight_0='20'))
        assert b.baseline(db,x['a'],x['e'])==('not_configured',0)
        apply(db,x,'total')
        assert h.effective(db,x['a'],saved)[1][0]['actual_weight_tenths_lb']==400
        assert all(weights(db,x['a'],x['e'])[k]==v for k,v in old.items())


def test_mode_changes_clear_incompatible_basis_without_rewriting_snapshots(basis_data):
    x=basis_data
    with database_session(x['root'],write=True) as db:
        apply(db,x,'total');before=weights(db,x['a'],x['e'])
        draft,_=w.start(db,x['a'],x['r'],'UTC');frozen=[dict(r) for r in w.entries(db,x['a'],draft)]
        item=db.execute('SELECT id FROM routine_exercises WHERE person_id=? AND exercise_id=? LIMIT 1',(x['a'],x['e'])).fetchone()[0]
        parent=db.execute('SELECT routine_id FROM routine_exercises WHERE id=?',(item,)).fetchone()[0]
        c.update_entry(db,x['a'],parent,item,dict(measurement_type='time',target_sets='5',minutes='2',seconds='30',weight_basis='per_side'))
        assert c.entry(db,x['a'],parent,item)['weight_basis']=='not_configured'
        assert [dict(r) for r in w.entries(db,x['a'],draft)]==frozen
        w.discard(db,x['a'],draft,dict(revision='0',confirm='yes'))
        apply(db,x,'not_configured',measurement_type='time',target_sets='2',minutes='1',seconds='0')
        assert weights(db,x['a'],x['e'])==before and b.baseline(db,x['a'],x['e'])[0]=='total'


def test_first_assignment_invalidates_stale_correction_even_when_weights_unchanged(basis_data):
    x=basis_data
    with database_session(x['root'],write=True) as db:
        stale=correction_payload(db,x['a'],x['first'],weight_0='10')
        apply(db,x,'total')
        with pytest.raises(w.RevisionConflict):h.correct(db,x['a'],x['first'],stale)


def test_http_precision_error_retains_every_submitted_setting_and_signed_tampering_fails(basis_data):
    import re
    x=basis_data;root=x['root'];client=create_app({'TESTING':True,'WORKOUT_DATA_ROOT':root}).test_client()
    with database_session(root,write=True) as db:
        apply(db,x,'total');h.correct(db,x['a'],x['first'],correction_payload(db,x['a'],x['first'],weight_0='25.5'))
    path=f"/people/{x['a']}/exercises/{x['e']}/defaults";page=client.get(path)
    values=dict(csrf_token=token(page),revision=re.search(r'name="revision" value="([^"]+)"',page.get_data(as_text=True))[1],name='My unsaved rename',measurement_type='weight_duration',target_sets='7',minutes='2',seconds='15',unit='lb',weight_meaning='Reference text',weight_basis='per_side',notes='Do not lose these notes',action='apply')
    with database_session(root) as db:before=dump(db)
    result=client.post(path,data=values)
    assert result.status_code==400 and b'more than one decimal' in result.data and x['first'].encode() in result.data
    assert all(value.encode() in result.data for value in ('My unsaved rename','Reference text','Do not lose these notes','value="7"','value="2"','value="15"'))
    assert client.post(path,data=dict(csrf_token=token(result),action='confirm',preview='not-a-signed-preview',confirm='yes')).status_code==400
    with database_session(root) as db:assert dump(db)==before


@pytest.mark.parametrize('name,meaning',[('Farmer carry','per hand'),('Barbell squat','total weight')])
def test_migration_never_infers_basis_from_names_or_meanings(phase11_root,name,meaning):
    with database_session(phase11_root,write=True) as db:
        person=c.create_person(db,'New person')
        exercise=c.create_definition(db,person,name,dict(measurement_type='weight',target_sets='3',target_reps='12',weight_meaning=meaning))
    migrate_storage(phase11_root,9)
    with database_session(phase11_root) as db:
        row=c.exercise_defaults(db,person,exercise)
        assert row['weight_basis']=='not_configured' and row['weight_meaning']==meaning


@pytest.mark.parametrize('kind',['weight','weight_duration','time'])
@pytest.mark.parametrize('chosen',['total','per_side'])
def test_new_definition_routine_inheritance_and_duration_neutral_basis(basis_data,kind,chosen):
    x=basis_data
    with database_session(x['root'],write=True) as db:
        values=dict(measurement_type=kind,target_sets='2',target_reps='10',seconds='60',weight_basis=chosen)
        exercise=c.create_definition(db,x['other'],'New definition',values)
        item=c.add_entry(db,x['other'],x['rb'],dict(exercise_id=exercise,use_library_defaults='yes'))
        expected=chosen if kind!='time' else 'not_configured'
        assert c.exercise_defaults(db,x['a'],exercise)['weight_basis']==expected
        assert c.entry(db,x['other'],x['rb'],item)['weight_basis']==expected


def test_first_assignment_of_odd_tenths_is_not_a_division(basis_data):
    x=basis_data
    with database_session(x['root'],write=True) as db:
        h.correct(db,x['a'],x['first'],correction_payload(db,x['a'],x['first'],weight_0='25.5'))
        apply(db,x,'total')
        assert h.effective(db,x['a'],x['first'])[1][0]['actual_weight_tenths_lb']==255


@pytest.mark.parametrize('stage',['rename','routine','audit','validation'])
def test_mid_operation_failure_rolls_back_defaults_routines_and_all_audits(basis_data,stage):
    """Inject failures after writes start; caller transaction must leave no partial result."""
    from contextlib import nullcontext
    x=basis_data
    with database_session(x['root']) as db:before=dump(db)
    context=patch('workout_tracker.catalog.update_definition',side_effect=RuntimeError('Synthetic rename failure')) if stage=='rename' else patch('workout_tracker.maintenance.logical_check_connection',side_effect=StorageError('Synthetic audit verification failure')) if stage=='validation' else nullcontext()
    with context,pytest.raises((RuntimeError,StorageError)):
        with database_session(x['root'],write=True) as db:
            if stage in ('routine','audit'):
                table='routine_exercises' if stage=='routine' else 'workout_corrections'
                operation='UPDATE' if stage=='routine' else 'INSERT'
                db.execute(f"CREATE TEMP TRIGGER synthetic_fault BEFORE {operation} ON main.{table} BEGIN SELECT RAISE(ABORT,'Synthetic write failure'); END")
            apply(db,x,'total',name='Proposed global rename',notes='Must roll back')
    with database_session(x['root']) as db:assert dump(db)==before
    assert x['original'].read_bytes()==x['source']


def test_database_guards_reject_wrong_transition_baseline_and_assignment_ownership(basis_data):
    """Ownership is enforced in SQLite before a malformed audit can be appended."""
    import sqlite3
    x=basis_data
    with database_session(x['root'],write=True) as db:
        apply(db,x,'total')
        event=db.execute('SELECT * FROM basis_transitions').fetchone()
        values=list(event);values[0]=uuid4().hex;values[3]=2;values[4]='not_configured'
        with pytest.raises(sqlite3.IntegrityError,match='actual baseline'):
            db.execute('INSERT INTO basis_transitions VALUES (?,?,?,?,?,?,?,?,?,?)',values)
        assignment=db.execute('SELECT * FROM basis_assignments LIMIT 1').fetchone()
        values=list(assignment);values[2]=x['other']
        with pytest.raises(sqlite3.IntegrityError,match='ownership'):
            db.execute('INSERT INTO basis_assignments VALUES (?,?,?,?,?,?,?,?,?,?)',values)
