# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""Verified backup/restore services called by Settings and the dedicated scheduler.

Every operation holds the storage-root lock shared with all workout connections.
Source databases and backups are read-only; only distinct candidates are written.
External JSON records attempts before work, so interrupted submissions never rerun.
"""
import json
import os
import sqlite3
import re
from itertools import zip_longest
from contextlib import contextmanager, closing
from datetime import datetime
from zoneinfo import ZoneInfo
from uuid import uuid4

from . import operations as o
from .storage import StorageError, storage_lock, _inspect_unlocked, _regular_file, _sync_directory, APPLICATION_ID, DIRECTORIES, _unique_object
from .migrations import _digest, _write_manifest


class ActivationUncertain(StorageError):
    """Signal that durability and rollback both failed; never report ordinary failure/success."""


@contextmanager
def connect(path):
    """Open a verified source read-only, never creating or recovering a database."""
    db=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)
    db.row_factory=sqlite3.Row
    db.execute('PRAGMA query_only=ON');db.execute('PRAGMA foreign_keys=ON')
    try: yield db
    finally: db.close()


def logical_check(path,version):
    """Check all logical invariants through a read-only connection for maintenance."""
    with connect(path) as db:
        logical_check_connection(db,version)


def logical_check_connection(db,version):
    """Validate snapshots/audits on an existing connection, including before commit."""
    from . import history as h
    if version>=3:
        for parent in db.execute('SELECT * FROM workout_sessions'):
            started=datetime.fromisoformat(parent['started_at'])
            if started.tzinfo is None or started.astimezone(ZoneInfo(parent['timezone'])).date().isoformat()!=parent['workout_date']:
                raise StorageError('Workout date/time consistency failed.')
            positions=[row[0] for row in db.execute('SELECT position FROM workout_entries WHERE session_id=? ORDER BY position',(parent['id'],))]
            if positions!=list(range(parent['entry_count'])):
                raise StorageError('Workout snapshot count/order verification failed.')
    if version<4: return
    # Preparation JSON is durable data too. Verify typed targets and owner
    # references, and ensure saved historical prescriptions equal that form.
    from . import catalog as c
    fields=('exercise_id','name','position','measurement_type','target_sets','target_reps','target_duration_seconds','unit','weight_meaning','notes')
    for form in db.execute('SELECT * FROM historical_forms'):
        snapshots=json.loads(form['snapshots_json'])
        if not isinstance(snapshots,list) or not snapshots: raise StorageError('Prepared snapshot is empty or malformed.')
        h.validate_state(form,[],dict(workout_date=form['workout_date'],workout_time=form['workout_time'],occurred_at=form['occurred_at'],entries=[]))
        for index,row in enumerate(snapshots):
            if type(row['position']) is not int or row['position']<0 or (index>0 and row['position']<=snapshots[index-1]['position']) or row['person_id']!=form['person_id'] or row['routine_id']!=form['routine_id']:
                raise StorageError('Prepared snapshot ownership/order failed.')
            identity_sql = 'SELECT 1 FROM exercises WHERE id=?' + (' AND person_id=?' if version < 5 else '')
            identity_args = (row['exercise_id'], form['person_id']) if version < 5 else (row['exercise_id'],)
            if not db.execute(identity_sql, identity_args).fetchone():
                raise StorageError('Prepared exercise identity failed.')
            values={k:str(row[k]) for k in ('target_sets','target_reps','measurement_type','weight_meaning','notes')}
            duration=row['target_duration_seconds']
            if duration is not None: values.update(minutes=str(duration//60),seconds=str(duration%60))
            configured=c.configure(values)
            if configured!=tuple(row[k] for k in ('measurement_type','target_sets','target_reps','target_duration_seconds','unit','weight_meaning','notes')):
                raise StorageError('Prepared target configuration failed.')
        # Routine positions can have gaps after removals. Completion keeps
        # their relative order but normalizes saved positions to 0..n-1.
        saved=db.execute('SELECT * FROM historical_workouts WHERE form_id=?',(form['id'],)).fetchone()
        if saved:
            if any(saved[k]!=form[k] for k in ('person_id','routine_id','routine_name','timezone','workout_date','workout_time','occurred_at')):
                raise StorageError('Historical parent differs from its preparation.')
            actual=db.execute('SELECT * FROM historical_entries WHERE session_id=? ORDER BY position',(saved['id'],)).fetchall()
            if len(actual)!=len(snapshots) or any(tuple(a[k] for k in fields)!=tuple(dict(b,position=index)[k] for k in fields) for index,(a,b) in enumerate(zip(actual,snapshots))):
                raise StorageError('Historical prescriptions differ from their preparation.')
    expected={(r['id'],r['person_id'],r['id'],None) for r in db.execute("SELECT id,person_id FROM workout_sessions WHERE status='completed'")}
    expected|={(r['id'],r['person_id'],None,r['id']) for r in db.execute('SELECT id,person_id FROM historical_workouts')}
    actual={tuple(r) for r in db.execute('SELECT id,person_id,live_session_id,historical_session_id FROM workout_registry')}
    if actual!=expected: raise StorageError('Workout registry verification failed.')
    for record in db.execute('SELECT id,person_id FROM workout_registry'):
        parent,rows=h.original(db,record['person_id'],record['id'])
        current=h.value_state(parent,rows)
        h.validate_state(parent,rows,current)
        for index,audit in enumerate(h.audit(db,record['person_id'],record['id']),1):
            if audit['revision']!=index or audit['before']!=current:
                raise StorageError('Correction audit chain verification failed.')
            h.validate_state(parent,rows,audit['after'])
            current=audit['after']
        h.effective(db,record['person_id'],record['id'])


def validate(root,path,selection):
    """Reuse exact schema/identity/integrity/FK validation on an isolated file."""
    details=_inspect_unlocked(root,selection=selection,database_override=path)
    try:
        logical_check(path,details['schema_version'])
    except (ValueError,TypeError,KeyError,OverflowError) as error:
        raise StorageError('Logical history/audit validation failed.') from error
    return details


def compare(source,target):
    """Stream every original table cell, including NULL/zero, and compare exactly."""
    with connect(source) as before, connect(target) as after:
        tables=[row[0] for row in before.execute("SELECT name FROM sqlite_schema WHERE type='table' AND substr(name,1,7)!='sqlite_' ORDER BY name")]
        for name in tables:
            # Table names come from already verified project DDL, never form input.
            left=before.execute(f'SELECT * FROM "{name}" ORDER BY 1')
            right=after.execute(f'SELECT * FROM "{name}" ORDER BY 1')
            if any(a!=b for a,b in zip_longest(left,right)):
                raise StorageError('Copied database does not preserve every original value.')


def copy_database(source,target):
    """Reserve a private unique destination and use SQLite's consistent backup API."""
    with target.open('xb'):
        target.chmod(0o600)
    with connect(source) as original, closing(sqlite3.connect(target.as_uri()+'?mode=rw',uri=True)) as candidate:
        original.backup(candidate)
    with target.open('rb') as handle: os.fsync(handle.fileno())
    _sync_directory(target.parent)


def backup_path(root,record):
    """Derive only a server-controlled timestamped basename; reject links/sidecars later."""
    o.identity(record['id'])
    filename=record['filename']
    if filename!=record['created_at'].replace(':','').replace('-','').replace('+0000','Z')+'-'+record['id']+'.sqlite3':
        raise StorageError('Backup metadata filename is invalid.')
    path=root/'backups'/filename
    if path.name!=filename: raise StorageError('Backup selection is unsafe.')
    return path


def event(root,level,category,message,error=None):
    """Write a fixed event without risking the transaction if diagnostics are unavailable."""
    from .diagnostics import emit
    emit(root,level,category,message,error=error)


def backup_locked(root,state,token,source='manual'):
    """Record intent durably before copying; retries return the existing result."""
    o.identity(token)
    if token in state['backups']: return state['backups'][token]
    created=o.now().isoformat()
    record=dict(id=token,created_at=created,source=source,status='in_progress',error=None,size=0,schema_version=None,
                filename=created.replace(':','').replace('-','').replace('+0000','Z')+'-'+token+'.sqlite3')
    state['backups'][token]=record;o.write_state(root,state)
    event(root,'INFO','Backup','Backup attempt started')
    try:
        details=_inspect_unlocked(root)
        record.update(schema_version=details['schema_version'],selection=dict(database=details['database'].name,storage_id=details['storage_id']))
        original_hash=_digest(details['database'])
        path=backup_path(root,record)
        copy_database(details['database'],path)
        validate(root,path,record['selection']);compare(details['database'],path)
        if _digest(details['database'])!=original_hash: raise StorageError('Source changed during backup.')
        record.update(status='verified',size=path.stat().st_size,sha256=_digest(path),verified_at=o.now().isoformat())
        o.write_state(root,state)
        event(root,'INFO','Backup','Backup completed and verified')
    except Exception as error:
        record.update(status='failed',error='Backup failed verification or was interrupted. Protected server logs contain diagnostic details.')
        o.write_state(root,state)
        event(root,'ERROR','Backup','Backup failed; previous verified files preserved',error)
    return record


def backup(value,token):
    """Manual entry point: serialize with workouts, scheduler, restore and deletion."""
    with storage_lock(value,exclusive=True) as root:
        return backup_locked(root,o.read_state(root),token)


def current_for_restore(root):
    """Identify a retained damaged active file only during explicit restore.

    Startup and normal operations keep strict validation. Recovery may preserve
    an unreadable database, but never invent a missing identity/file or downgrade
    a readable newer schema. The exact private manifest anchors storage identity.
    """
    try: return _inspect_unlocked(root)
    except StorageError as original_error:
        for name in DIRECTORIES:
            if (root/name).is_symlink() or not (root/name).is_dir(): raise original_error
        active=root/'config'/'active.json';_regular_file(active)
        if active.stat().st_size>4096: raise original_error
        selection=json.loads(active.read_text(),object_pairs_hook=_unique_object)
        if not isinstance(selection,dict) or set(selection)!= {'database','storage_id'}: raise original_error
        storage_id=selection['storage_id'];o.identity(storage_id)
        match=re.fullmatch(rf'schema-([2345678])-{storage_id}-[0-9a-f]{{32}}\.sqlite3',selection['database'])
        if not match: raise original_error
        path=root/'data'/selection['database'];_regular_file(path)
        for suffix in ('-journal','-wal','-shm'):
            if os.path.lexists(str(path)+suffix): raise original_error
        # immutable=1 is limited to this locked diagnostic probe: never recover a
        # journal or create sidecars when determining a damaged file's identity.
        try:
            with closing(sqlite3.connect(path.as_uri()+'?mode=ro&immutable=1',uri=True)) as db:
                version=db.execute('PRAGMA user_version').fetchone()[0]
                app_id=db.execute('PRAGMA application_id').fetchone()[0]
                if version!=int(match[1]) or app_id!=APPLICATION_ID: raise original_error
                identity_rows=db.execute('SELECT * FROM storage_metadata').fetchall()
                if identity_rows!=[(1,storage_id)]: raise original_error
        except sqlite3.DatabaseError:
            pass  # Unreadable bytes remain preserved under the original manifest.
        return dict(database=path,storage_id=storage_id,schema_version=int(match[1]))


def verified_backup(root,state,token):
    """Recheck bytes, exact schema, identity and logical consistency on every restore."""
    record=state['backups'].get(o.identity(token))
    if not record or record['status']!='verified': raise StorageError('Choose a verified backup.')
    path=backup_path(root,record)
    _regular_file(path)
    current=current_for_restore(root)
    if record['selection']['storage_id']!=current['storage_id']:
        raise StorageError('Backup belongs to another storage identity.')
    if record['schema_version']!=current['schema_version'] or current['schema_version']<2:
        raise StorageError('Restore requires the current exact schema version. Older backups require a separately reviewed offline recovery; no downgrade is performed.')
    validate(root,path,record['selection'])
    if _digest(path)!=record['sha256'] or path.stat().st_size!=record['size']:
        raise StorageError('Backup bytes no longer match the verified record.')
    return record,path,current


def activate(root,candidate,selection,token):
    """Archive selection, sync candidate and atomically select it; roll back on sync failure."""
    active=root/'config'/'active.json'
    archive=root/'archives'/f'selection-before-restore-{token}.json'
    pending=root/'config'/f'restore-{token}.pending'
    switched=False
    try:
        os.link(active,archive);_sync_directory(root/'archives')
        _write_manifest(pending,selection);_sync_directory(root/'config')
        os.replace(pending,active);switched=True;_sync_directory(root/'config')
    except Exception as error:
        if switched:
            rollback=root/'config'/f'restore-rollback-{token}.pending'
            try:
                os.link(archive,rollback);os.replace(rollback,active);_sync_directory(root/'config')
            except Exception as rollback_error:
                raise ActivationUncertain('Restore durability is uncertain. Stop writers and inspect the preserved selections and databases.') from rollback_error
        raise StorageError('Restore activation failed; original selection retained.') from error


def restore(value,backup_id,token,confirm=False):
    """Explicit confirmed restore, one intent token per attempt; never overwrite either source."""
    if not confirm: raise StorageError('Acknowledge and explicitly confirm restoration first.')
    o.identity(token)
    with storage_lock(value,exclusive=True) as root:
        state=o.read_state(root)
        if token in state['restores']:
            prior=state['restores'][token]
            if prior['backup_id']!=backup_id: raise StorageError('Restore token already belongs to another backup.')
            return prior
        attempt=dict(id=token,backup_id=o.identity(backup_id),started_at=o.now().isoformat(),status='in_progress',error=None)
        state['restores'][token]=attempt;o.write_state(root,state)
        event(root,'WARNING','Restore','Explicit restore attempt started')
        switched=False
        try:
            record,path,current=verified_backup(root,state,backup_id)
            selection=dict(database=f"schema-{current['schema_version']}-{current['storage_id']}-{uuid4().hex}.sqlite3",storage_id=current['storage_id'])
            candidate=root/'data'/selection['database']
            attempt.update(previous_database=current['database'].name,candidate=selection['database'])
            o.write_state(root,state)
            original_hash=_digest(current['database']);backup_hash=_digest(path)
            copy_database(path,candidate)
            validate(root,candidate,selection);compare(path,candidate)
            if _digest(current['database'])!=original_hash or _digest(path)!=backup_hash:
                raise StorageError('A preserved source changed; activation refused.')
            # This journal is durable before activation; a crash leaves an explicit
            # unresolved attempt, never a retry that might unexpectedly restore again.
            attempt['activation_pending']=True;o.write_state(root,state)
            activate(root,candidate,selection,token);switched=True
            attempt.update(status='succeeded',finished_at=o.now().isoformat(),activation_pending=False)
            o.write_state(root,state)
            event(root,'WARNING','Restore','Restore completed; pre-restore database and backup preserved')
        except Exception as error:
            if switched:
                # A metadata durability failure after selection must also undo
                # activation. The preserved manifest is never reconstructed.
                try:
                    rollback=root/'config'/f'restore-state-rollback-{token}.pending'
                    os.link(root/'archives'/f'selection-before-restore-{token}.json',rollback)
                    os.replace(rollback,root/'config'/'active.json');_sync_directory(root/'config')
                    switched=False
                except Exception:
                    pass  # Keep an explicit uncertain result if rollback itself fails.
            attempt.update(status='uncertain' if switched or isinstance(error,ActivationUncertain) else 'failed' ,error='Restore did not complete normally. Stop and inspect protected logs and retained selections before retrying.')
            try: o.write_state(root,state)
            finally: event(root,'CRITICAL' if switched else 'ERROR','Restore','Restore failed or requires operator inspection',error)
        return attempt


def delete_backup(value,token,confirm=False):
    """Explicit deletion only; mark intent first and retain metadata/audit history."""
    if not confirm: raise StorageError('Confirm backup deletion first.')
    with storage_lock(value,exclusive=True) as root:
        state=o.read_state(root);record=state['backups'].get(o.identity(token))
        if not record: raise StorageError('Backup not found.')
        if record['status']=='deleted': return
        path=backup_path(root,record)
        record['status']='deletion_pending';o.write_state(root,state)
        if os.path.lexists(path):
            _regular_file(path);path.unlink();_sync_directory(root/'backups')
        record.update(status='deleted',deleted_at=o.now().isoformat());o.write_state(root,state)
        event(root,'WARNING','Backup','Backup explicitly deleted; audit metadata retained')
