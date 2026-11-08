# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""Confirmed LAN hard deletion inside one caller-owned, locked SQLite transaction.

Browser confirmation -> CSRF-protected routes -> impact fingerprint -> this service.
Schema-6-only capability is connection-local and reset in finally. The caller's
transaction rolls back every row/JSON change on failure. Backups are not changed.
"""
from contextlib import contextmanager
import hashlib
import json
from uuid import uuid4
from . import catalog as c, history as h, workouts as w
from .storage import StorageError


def schema6(db):
    """Refuse deletion against retained schemas; never migrate as a side effect."""
    if db.execute('PRAGMA user_version').fetchone()[0] < 6:
        raise c.ValidationError('Permanent deletion requires explicit schema-6 migration.')


@contextmanager
def capability(db):
    """Permit only this connection's deliberate transaction to reconcile protections."""
    schema6(db)
    db.create_function('deletion_in_progress', 0, lambda: 1)
    try: yield
    finally: db.create_function('deletion_in_progress', 0, lambda: 0)


def fingerprint(db):
    """Detect any relevant change between impact review and user confirmation.

    Household data is small: hashing exact rows also catches new drafts, corrected
    values and routine edits. Never accept counts alone as a stale-form check.
    """
    names=('people','exercises','routines','routine_exercises','workout_sessions','workout_entries',
           'historical_forms','historical_workouts','historical_entries','workout_registry','workout_corrections')
    digest=hashlib.sha256()
    for table in names:
        digest.update(repr([tuple(r) for r in db.execute(f'SELECT * FROM {table} ORDER BY 1')]).encode())
    return digest.hexdigest()


def impact(db, kind, identity, person_id):
    """Return global deletion impact counts and the exact review revision."""
    schema6(db); c.person(db,person_id)
    if kind=='routine':
        row=db.execute('SELECT * FROM routines WHERE id=? AND person_id=?',(identity,person_id)).fetchone()
        if row is None: raise c.MissingRecord('Routine no longer exists.')
        blocked=db.execute("SELECT 1 FROM workout_sessions WHERE routine_id=? AND status='draft'",(identity,)).fetchone()
        return dict(name=row['name'],people=1,routines=1,entries=0,blocked=bool(blocked),revision=fingerprint(db))
    row=db.execute('SELECT * FROM exercises WHERE id=?',(identity,)).fetchone()
    if row is None: raise c.MissingRecord('Exercise no longer exists.')
    owners=set();routines=set();count=0
    for re in db.execute('SELECT person_id,routine_id FROM routine_exercises WHERE exercise_id=?',(identity,)):
        owners.add(re['person_id']);routines.add(re['routine_id'])
    for table in ('workout_entries','historical_entries'):
        rows=db.execute(f'SELECT person_id FROM {table} WHERE exercise_id=?',(identity,)).fetchall()
        count+=len(rows);owners.update(r[0] for r in rows)
    blocked=db.execute("SELECT 1 FROM workout_entries e JOIN workout_sessions s ON s.id=e.session_id WHERE e.exercise_id=? AND s.status='draft'",(identity,)).fetchone()
    return dict(name=row['name'],people=len(owners),routines=len(routines),entries=count,blocked=bool(blocked),revision=fingerprint(db))


def confirm(db,kind,identity,person_id,values):
    """Require typed phrase, acknowledgment and fresh impact."""
    current=impact(db,kind,identity,person_id)
    if current['blocked']:
        raise c.ValidationError('An active workout draft uses this record. Finish or discard that draft through its existing workflow, then review deletion again.')
    if values.get('confirm')!='yes' or values.get('phrase') not in ('DELETE',current['name']):
        raise c.ValidationError('Acknowledge deletion and type DELETE or the exact name.')
    if values.get('revision')!=current['revision']:
        raise w.RevisionConflict('Data changed after the deletion preview. Review the current impact again.')
    return current


def reorder(db,table,column,identity):
    """Close position gaps in ascending order without temporary UNIQUE collisions."""
    for position,row in enumerate(db.execute(f'SELECT id FROM {table} WHERE {column}=? ORDER BY position',(identity,)).fetchall()):
        db.execute(f'UPDATE {table} SET position=? WHERE id=?',(position,row['id']))


def delete_routine(db,person_id,identity,values):
    """Delete configurations/definition, preserving global exercises and all snapshots."""
    confirm(db,'routine',identity,person_id,values)
    db.execute('DELETE FROM routine_exercises WHERE routine_id=?',(identity,))
    db.execute('DELETE FROM routines WHERE id=? AND person_id=?',(identity,person_id))
    if db.execute('PRAGMA foreign_key_check').fetchall(): raise StorageError('Deletion foreign key validation failed.')
    from .maintenance import logical_check_connection
    logical_check_connection(db,6)


def delete_exercise(db,person_id,identity,values):
    """Erase one global identity and only its routine/history/correction components.

    Empty completed/discarded workouts and their registry/audits are removed.
    Mixed workouts keep all other measurements, occurrence and prescription fields.
    A value-preserving audit barrier invalidates stale correction forms. Pending
    historical preparations containing the deleted identity are invalidated.
    """
    confirm(db,'exercise',identity,person_id,values)
    with capability(db):
        routines=[r[0] for r in db.execute('SELECT DISTINCT routine_id FROM routine_exercises WHERE exercise_id=?',(identity,))]
        db.execute('DELETE FROM routine_exercises WHERE exercise_id=?',(identity,))
        for routine in routines: reorder(db,'routine_exercises','routine_id',routine)
        for table,parent in (('workout_entries','workout_sessions'),('historical_entries','historical_workouts')):
            sessions=[r[0] for r in db.execute(f'SELECT DISTINCT session_id FROM {table} WHERE exercise_id=?',(identity,))]
            for session_id in sessions:
                removed={r[0] for r in db.execute(f'SELECT id FROM {table} WHERE session_id=? AND exercise_id=?',(session_id,identity))}
                db.execute(f'DELETE FROM {table} WHERE session_id=? AND exercise_id=?',(session_id,identity))
                remaining=db.execute(f'SELECT * FROM {table} WHERE session_id=? ORDER BY position',(session_id,)).fetchall()
                if not remaining:
                    db.execute('DELETE FROM workout_corrections WHERE workout_id=?',(session_id,))
                    db.execute('DELETE FROM workout_registry WHERE id=?',(session_id,))
                    db.execute(f'DELETE FROM {parent} WHERE id=?',(session_id,))
                    continue
                reorder(db,table,'session_id',session_id)
                if parent=='workout_sessions':
                    db.execute('UPDATE workout_sessions SET entry_count=?,current_position=min(current_position,?) WHERE id=?',(len(remaining),len(remaining)-1,session_id))
                else:
                    db.execute('UPDATE historical_workouts SET entry_count=? WHERE id=?',(len(remaining),session_id))
                for audit in db.execute('SELECT * FROM workout_corrections WHERE workout_id=? ORDER BY revision',(session_id,)).fetchall():
                    projected=[]
                    for column in ('before_json','after_json'):
                        state=json.loads(audit[column]);state['entries']=[e for e in state['entries'] if e['id'] not in removed]
                        projected.append(h.json_text(state))
                    db.execute('UPDATE workout_corrections SET before_json=?,after_json=? WHERE id=?',(*projected,audit['id']))
                registry=db.execute('SELECT person_id FROM workout_registry WHERE id=?',(session_id,)).fetchone()
                if registry:
                    # Append a no-measurement-change revision so old indexed
                    # browser forms cannot apply a deleted row's value to another.
                    effective,rows=h.effective(db,registry['person_id'],session_id)
                    state=h.json_text(h.value_state(effective,rows))
                    db.execute('INSERT INTO workout_corrections VALUES (?,?,?,?,?,?,?)',
                               (uuid4().hex,session_id,registry['person_id'],effective['correction_revision']+1,w.now().isoformat(),state,state))
        for form in db.execute('SELECT * FROM historical_forms').fetchall():
            original=json.loads(form['snapshots_json'])
            kept=[r for r in original if r['exercise_id']!=identity]
            if len(kept)==len(original): continue
            completed=db.execute('SELECT 1 FROM historical_workouts WHERE form_id=?',(form['id'],)).fetchone()
            if not completed:
                db.execute('DELETE FROM historical_forms WHERE id=?',(form['id'],))
            else:
                for index,row in enumerate(kept): row['position']=index
                db.execute('UPDATE historical_forms SET snapshots_json=? WHERE id=?',(h.json_text(kept),form['id']))
        db.execute('DELETE FROM exercises WHERE id=?',(identity,))
        if db.execute('PRAGMA foreign_key_check').fetchall(): raise StorageError('Deletion foreign key validation failed.')
        # Reuse the same logical audit/snapshot invariants as backup validation,
        # on this uncommitted connection before the caller can commit.
        from .maintenance import logical_check_connection
        logical_check_connection(db,6)
