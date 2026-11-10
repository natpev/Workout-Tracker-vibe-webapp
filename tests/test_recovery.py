# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Synthetic schema-4 recovery tests; never inspect household environment paths.

Failures injected at copying/validation/publication must preserve exact original
bytes and manifests. Large histories include NULL, explicit zero and audit rows.
"""
import json
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from uuid import uuid4

import pytest
from workout_tracker import catalog as c,history as h,workouts as w
from workout_tracker import maintenance as m,operations as o
from workout_tracker.storage import database_session,storage_lock,_inspect_unlocked,StorageError


def token():
    """Generate server-style operation tokens for disposable requests."""
    return uuid4().hex


def selected(root):
    """Read a fixture's active database and full protected bytes."""
    with storage_lock(root): return _inspect_unlocked(root)['database']


def populated(root,count=2):
    """Create mixed snapshot rows and a correction, including original NULL/zero."""
    with database_session(root,write=True) as db:
        person=c.create_person(db,'Synthetic recovery');routine=c.create_routine(db,person,'Mixed')
        c.add_entry(db,person,routine,dict(name='Zero',measurement_type='weight',target_sets='3',target_reps='12'))
        c.add_entry(db,person,routine,dict(name='Skipped',measurement_type='time',target_sets='2',minutes='0',seconds='45'))
        for _ in range(count):
            form=h.prepare(db,person,routine,dict(workout_date='2020-01-01',workout_time=''),'UTC')
            workout=h.complete_historical(db,person,form,{'weight_0':'0'})
        h.correct(db,person,workout,dict(confirm='yes',correction_revision='0',workout_date='2020-01-02',workout_time='',weight_0='40.99'))
    return person,routine,workout


def test_backup_exact_large_history_uniqueness_and_idempotence(phase4_root):
    """Every row/audit survives SQLite backup; duplicate tokens do not create copies."""
    root=phase4_root;person,_,workout=populated(root,1000);original=selected(root);before=original.read_bytes();mtime=original.stat().st_mtime_ns
    first=m.backup(root,token());second=m.backup(root,token())
    assert first['status']==second['status']=='verified' and first['filename']!=second['filename']
    assert m.backup(root,first['id'])==first
    assert len(list((root/'backups').glob('*.sqlite3')))==2
    with m.connect(m.backup_path(root,first)) as db:
        assert db.execute('SELECT count(*) FROM historical_workouts').fetchone()[0]==1000
        assert db.execute('SELECT count(*) FROM historical_entries WHERE actual_weight_tenths_lb=0').fetchone()[0]==1000
        assert db.execute('SELECT count(*) FROM historical_entries WHERE actual_duration_seconds IS NULL').fetchone()[0]==2000
        assert h.effective(db,person,workout)[1][0]['actual_weight_tenths_lb']==409
    assert original.read_bytes()==before and original.stat().st_mtime_ns==mtime


@pytest.mark.parametrize('failure',['copy','verification','logical'])
def test_failed_backup_preserves_prior_and_reports_failure(phase4_root,monkeypatch,failure):
    """Interrupted/corrupt new attempts never acquire verified status or remove earlier files."""
    root=phase4_root;populated(root);good=m.backup(root,token());path=m.backup_path(root,good);before=path.read_bytes();original=selected(root).read_bytes()
    if failure=='copy':
        def fail(source,target):
            """Leave an intentionally incomplete candidate for diagnostic evidence."""
            target.write_bytes(b'partial');raise OSError('simulated disk failure')
        monkeypatch.setattr(m,'copy_database',fail)
    else:
        def fail(*args):
            """Simulate failed structural/logical validation without touching source."""
            raise StorageError('injected validation failure')
        monkeypatch.setattr(m,'validate' if failure=='verification' else 'logical_check',fail)
    result=m.backup(root,token())
    assert result['status']=='failed' and result['error'] and m.backup(root,result['id'])['status']=='failed'
    assert path.read_bytes()==before and selected(root).read_bytes()==original


def test_restore_preserves_both_sources_and_exact_audits(phase4_root):
    """Restoring selects a new file, restoring every value/audit and retaining newer records."""
    root=phase4_root;person,routine,workout=populated(root);good=m.backup(root,token());backup_path=m.backup_path(root,good);backup_bytes=backup_path.read_bytes()
    with database_session(root,write=True) as db:
        c.create_person(db,'After backup');draft,_=w.start(db,person,routine,'UTC')
    original=selected(root);before=original.read_bytes();selection=(root/'config'/'active.json').read_bytes();restore_token=token()
    with pytest.raises(StorageError): m.restore(root,good['id'],restore_token)
    result=m.restore(root,good['id'],restore_token,True)
    assert result['status']=='succeeded' and selected(root)!=original
    assert original.read_bytes()==before and backup_path.read_bytes()==backup_bytes
    assert (root/'archives'/f'selection-before-restore-{restore_token}.json').read_bytes()==selection
    assert m.restore(root,good['id'],restore_token,True)==result
    with database_session(root) as db:
        assert db.execute('SELECT count(*) FROM people').fetchone()[0]==1
        assert h.effective(db,person,workout)[1][0]['actual_weight_tenths_lb']==409
        assert db.execute('SELECT count(*) FROM workout_corrections').fetchone()[0]==1
    with m.connect(original) as db: assert w.session(db,person,draft)['status']=='draft'


@pytest.mark.parametrize('failure',['corrupt','missing','schema','identity','symlink','sidecar','audit','count','preparation'])
def test_restore_rejects_untrusted_backup(phase4_root,monkeypatch,failure):
    """Reject unsafe files and internally inconsistent histories even if a digest was changed."""
    root=phase4_root;populated(root);good=m.backup(root,token());path=m.backup_path(root,good)
    if failure=='corrupt': path.write_bytes(b'not SQLite')
    elif failure=='missing': path.unlink()
    elif failure=='symlink':
        path.unlink();path.symlink_to(selected(root))
    elif failure=='sidecar': path.with_name(path.name+'-wal').write_bytes(b'')
    elif failure in ('schema','identity','audit','count','preparation'):
        with sqlite3.connect(path) as db:
            if failure=='schema': db.execute('PRAGMA user_version=999')
            elif failure=='identity': db.execute("UPDATE storage_metadata SET storage_id=?",('a'*32,))
            elif failure=='audit':
                db.execute('DROP TRIGGER workout_corrections_update_protected');db.execute("UPDATE workout_corrections SET before_json='{}'")
                from workout_tracker.history_schema import HISTORY_OBJECTS
                db.execute(HISTORY_OBJECTS['workout_corrections_update_protected'])
            elif failure=='preparation':
                db.execute('DROP TRIGGER historical_forms_update_protected');db.execute("UPDATE historical_forms SET snapshots_json='broken'")
                from workout_tracker.history_schema import HISTORY_OBJECTS
                db.execute(HISTORY_OBJECTS['historical_forms_update_protected'])
            else:
                db.execute('DROP TRIGGER historical_entries_delete_protected');db.execute('DELETE FROM historical_entries WHERE position=1')
                from workout_tracker.history_schema import HISTORY_OBJECTS
                db.execute(HISTORY_OBJECTS['historical_entries_delete_protected'])
        with storage_lock(root,exclusive=True):
            state=o.read_state(root);state['backups'][good['id']]['sha256']=m._digest(path);o.write_state(root,state)
    original=selected(root);before=original.read_bytes();manifest=(root/'config'/'active.json').read_bytes()
    result=m.restore(root,good['id'],token(),True)
    assert result['status']=='failed' and original.read_bytes()==before and (root/'config'/'active.json').read_bytes()==manifest


@pytest.mark.parametrize('failure',['candidate','activation','post_sync','metadata'])
def test_restore_rollback_and_failed_candidate_retention(phase4_root,monkeypatch,failure):
    """Publication and durability failures roll back selection while preserving all files."""
    root=phase4_root;populated(root);good=m.backup(root,token());original=selected(root);before=original.read_bytes();manifest=(root/'config'/'active.json').read_bytes();identifier=token()
    if failure=='candidate':
        real=m.validate
        def fail(root,path,selection):
            """Refuse only the copied candidate after accepting the listed backup."""
            if path.parent.name=='data': raise StorageError('injected candidate failure')
            return real(root,path,selection)
        monkeypatch.setattr(m,'validate',fail)
    elif failure=='activation':
        def fail(*args):
            """Fail before atomic selection publication."""
            raise OSError('injected activation failure')
        monkeypatch.setattr(m,'_write_manifest',fail)
    elif failure=='post_sync':
        real=m._sync_directory;fired=False
        def fail(path):
            """Inject one post-switch sync failure; allow rollback durability to succeed."""
            nonlocal fired
            if path==root/'config' and json.loads((path/'active.json').read_text())['database']!=original.name and not fired:
                fired=True;raise OSError('injected post-switch failure')
            return real(path)
        monkeypatch.setattr(m,'_sync_directory',fail)
    else:
        real=o.write_state;fired=False
        def fail(root,state):
            """Reject the first success-result write after activation, allowing rollback record."""
            nonlocal fired
            if state['restores'].get(identifier,{}).get('status')=='succeeded' and not fired:
                fired=True;raise OSError('injected metadata failure')
            return real(root,state)
        monkeypatch.setattr(o,'write_state',fail)
    result=m.restore(root,good['id'],identifier,True)
    assert result['status']=='failed' and original.read_bytes()==before and (root/'config'/'active.json').read_bytes()==manifest
    assert len(list((root/'data').glob('schema-4-*.sqlite3')))==2


def test_storage_identity_and_older_schema_are_not_silently_restored(phase4_root,phase2_root):
    """Metadata identity/schema mismatches cannot select a foreign or downgraded dataset."""
    root=phase4_root;good=m.backup(root,token())
    for key,value in (('schema_version',2),('selection',dict(good['selection'],storage_id='a'*32))):
        with storage_lock(root,exclusive=True):
            state=o.read_state(root);state['backups'][good['id']]=dict(good,**{key:value});o.write_state(root,state)
        assert m.restore(root,good['id'],token(),True)['status']=='failed'


def test_delete_confirmation_path_safety_and_retained_metadata(phase4_root):
    """Explicit deletion cannot target archives, directories, unlisted files or path traversal."""
    root=phase4_root;record=m.backup(root,token());original=selected(root).read_bytes()
    with pytest.raises(StorageError): m.delete_backup(root,record['id'])
    for bad in ('../config/active.json','a'*31,'/etc/passwd'):
        with pytest.raises(StorageError): m.delete_backup(root,bad,True)
    m.delete_backup(root,record['id'],True)
    assert not m.backup_path(root,record).exists() and selected(root).read_bytes()==original
    with storage_lock(root): assert o.read_state(root)['backups'][record['id']]['status']=='deleted'


def test_workout_save_waits_for_restore_then_targets_current_selection(phase4_root,monkeypatch):
    """A real competing writer cannot observe an incomplete restore candidate."""
    root=phase4_root;person,routine,_=populated(root)
    with database_session(root,write=True) as db: draft,_=w.start(db,person,routine,'UTC')
    good=m.backup(root,token());entered=Event();release=Event();real=m.copy_database
    def paused(source,target):
        """Pause while restore owns root lock, allowing a writer to queue behind it."""
        entered.set();assert release.wait(5);return real(source,target)
    monkeypatch.setattr(m,'copy_database',paused)
    def save():
        """Write after selecting storage inside the exclusive lock."""
        with database_session(root,write=True) as db:
            entry=w.entries(db,person,draft)[0];w.update(db,person,draft,dict(entry_id=entry['id'],revision='0',current_position='0',weight='42'))
    with ThreadPoolExecutor(2) as pool:
        restoring=pool.submit(m.restore,root,good['id'],token(),True);assert entered.wait(5)
        saving=pool.submit(save);assert not saving.done();release.set()
        assert restoring.result()['status']=='succeeded';saving.result()
    with database_session(root) as db: assert w.entries(db,person,draft)[0]['actual_weight_tenths_lb']==420


def test_explicit_restore_can_recover_damaged_active_but_preserves_its_bytes(phase4_root):
    """Corruption recovery is deliberate; ordinary startup still refuses the damaged file."""
    root=phase4_root;populated(root);good=m.backup(root,token());original=selected(root)
    original.write_bytes(b'corrupted retained original')
    damaged=original.read_bytes()
    with pytest.raises(StorageError): selected(root)
    result=m.restore(root,good['id'],token(),True)
    assert result['status']=='succeeded' and original.read_bytes()==damaged
    assert selected(root)!=original


def test_duplicate_concurrent_backup_and_restore_tokens_execute_once(phase4_root):
    """Separate callers with the same token cannot create extra files or activations."""
    root=phase4_root;populated(root);identifier=token()
    with ThreadPoolExecutor(2) as pool:
        results=list(pool.map(lambda _:m.backup(root,identifier),range(2)))
    assert results[0]==results[1] and len(list((root/'backups').glob('*.sqlite3')))==1
    restore_token=token()
    with ThreadPoolExecutor(2) as pool:
        results=list(pool.map(lambda _:m.restore(root,identifier,restore_token,True),range(2)))
    assert results[0]==results[1] and results[0]['status']=='succeeded'
    assert len(list((root/'data').glob('schema-4-*.sqlite3')))==2


def test_process_interruption_leaves_unverified_evidence_and_never_replays(phase4_root,monkeypatch):
    """A hard interruption bypasses normal handlers; next scheduler check marks it failed."""
    from workout_tracker.scheduler import tick
    root=phase4_root;identifier=token();original=selected(root).read_bytes()
    def interrupted(source,target):
        """Simulate abrupt process loss after creating a partial backup file."""
        target.write_bytes(b'partial');raise KeyboardInterrupt()
    monkeypatch.setattr(m,'copy_database',interrupted)
    with pytest.raises(KeyboardInterrupt): m.backup(root,identifier)
    with storage_lock(root): assert o.read_state(root)['backups'][identifier]['status']=='in_progress'
    tick(root)
    with storage_lock(root): assert o.read_state(root)['backups'][identifier]['status']=='failed'
    assert m.backup(root,identifier)['status']=='failed' and selected(root).read_bytes()==original


def test_uncertain_restore_is_never_labeled_success(phase4_root,monkeypatch):
    """If even rollback durability fails, surface uncertainty and retain both candidates."""
    root=phase4_root;record=m.backup(root,token());original=selected(root);before=original.read_bytes()
    def uncertain(*args):
        """Represent double failure during atomic selection and rollback sync."""
        raise m.ActivationUncertain('Simulated uncertain durability')
    monkeypatch.setattr(m,'activate',uncertain)
    result=m.restore(root,record['id'],token(),True)
    assert result['status']=='uncertain' and original.read_bytes()==before


@pytest.mark.parametrize('failure',['missing','newer_schema','foreign_identity'])
def test_restore_never_invents_missing_active_storage_or_downgrades(phase4_root,failure):
    """Explicit recovery still requires an existing file/manifest and matching readable identity."""
    root=phase4_root;good=m.backup(root,token());original=selected(root);manifest=(root/'config'/'active.json').read_bytes()
    if failure=='missing': original.unlink()
    else:
        with sqlite3.connect(original) as db:
            if failure=='newer_schema': db.execute('PRAGMA user_version=999')
            else: db.execute('UPDATE storage_metadata SET storage_id=?',('b'*32,))
    before=original.read_bytes() if original.exists() else None
    assert m.restore(root,good['id'],token(),True)['status']=='failed'
    assert (root/'config'/'active.json').read_bytes()==manifest
    assert (original.read_bytes() if original.exists() else None)==before


def test_explicit_offline_recovery_cli_when_startup_refuses_corruption(phase4_root):
    """An operator can inspect IDs and deliberately recover without auto-repairing startup."""
    from click.testing import CliRunner
    from workout_tracker.__main__ import main
    root=phase4_root;good=m.backup(root,token());original=selected(root);original.write_bytes(b'broken startup')
    runner=CliRunner();listing=runner.invoke(main,['list-backups','--data-root',str(root)])
    assert listing.exit_code==0 and good['id'] in listing.output
    args=['restore-backup','--data-root',str(root),'--backup-id',good['id'],'--operation-id',token()]
    assert runner.invoke(main,args).exit_code!=0 and original.read_bytes()==b'broken startup'
    result=runner.invoke(main,args+['--confirm-restore'])
    assert result.exit_code==0 and 'Verified restore candidate selected' in result.output
    assert original.read_bytes()==b'broken startup' and selected(root)!=original


def test_valid_historical_preparation_after_routine_removal_has_gapped_positions(phase4_root):
    """Legacy preparations keep routine position gaps; saved snapshots normalize only order."""
    root=phase4_root;person,routine,_=populated(root)
    with database_session(root,write=True) as db:
        db.execute('DELETE FROM routine_exercises WHERE routine_id=? AND position=0',(routine,))
        form=h.prepare(db,person,routine,dict(workout_date='2020-02-01',workout_time=''),'UTC')
        assert h.prepared(db,person,form)[1][0]['position']==1
        h.complete_historical(db,person,form,dict(minutes_0='0',seconds_0='45'))
    assert m.backup(root,token())['status']=='verified'
