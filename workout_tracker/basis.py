# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Temporary, explicitly confirmed Weight Basis transition services for schema 9.

Caller owns the storage lock and atomic transaction. Exact integer arithmetic
appends ordinary corrections plus basis audit links; immutable originals never
change. Global defaults and personal history baselines are independent.
"""
import hashlib
import json
import re
from datetime import datetime
from uuid import uuid4
from . import catalog as c,workouts as w
from .storage import StorageError

LABELS={'not_configured':'Not Configured','total':'Total Weight','per_side':'Per Hand / Side'}


def enabled(db):
    """Only explicit schema 9 enables this transition; startup never migrates."""
    return db.execute('PRAGMA user_version').fetchone()[0]>=9


def parse(values,kind):
    """Validate a convention, never infer it from a name, equipment or old text."""
    value=values.get('weight_basis','not_configured')
    if not isinstance(value,str) or value not in LABELS:raise c.ValidationError('Choose a listed Weight Basis.')
    return value if kind!='time' else 'not_configured'


def label(value):
    """Return a fixed display label; unknown values are not silently classified."""
    return LABELS.get(value,'Not Configured')


def baseline(db,person,exercise):
    """Read the last convention actually applied by this person, not global defaults."""
    row=db.execute('SELECT new_basis,revision FROM basis_transitions WHERE person_id=? AND exercise_id=? ORDER BY revision DESC LIMIT 1',(person,exercise)).fetchone()
    return (row[0],row[1]) if row else ('not_configured',0)


def convert(value,old,new):
    """Convert exact tenths, retaining NULL/zero and refusing precision/overflow loss."""
    if value is None:return None
    if type(value) is not int or not 0<=value<=w.MAX_INTEGER:raise c.ValidationError('Weight exceeds supported storage limits.')
    if old=='total' and new=='per_side':
        if value%2:raise c.ValidationError('Dividing this weight by 2 needs more than one decimal place.')
        return value//2
    if old=='per_side' and new=='total':
        if value>w.MAX_INTEGER//2:raise c.ValidationError('Doubling this weight exceeds supported storage limits.')
        return value*2
    return value


def payload(values):
    """Canonicalize validated configuration without changing a stored preset yet."""
    fields=('measurement_type','target_sets','target_reps','target_duration_seconds','unit','weight_meaning','notes')
    result=dict(zip(fields,c.configure(values)))
    result['weight_basis']=parse(values,result['measurement_type'])
    result['name']=c.text(values.get('name'),'Exercise name')
    return c.default_values(result)


def digest(values):
    """Bind retry IDs to exactly the settings that were confirmed."""
    from .history import json_text
    return hashlib.sha256(json_text(values).encode()).hexdigest()


def fingerprint(db):
    """Detect new workouts, corrections, drafts or edits after preview, under lock."""
    result=hashlib.sha256()
    for name, in db.execute("SELECT name FROM sqlite_schema WHERE type='table' AND substr(name,1,7)!='sqlite_' ORDER BY name"):
        result.update(name.encode())
        result.update(repr([tuple(r) for r in db.execute(f'SELECT * FROM "{name}" ORDER BY 1')]).encode())
    return result.hexdigest()


def overlay(db,person,workout,rows):
    """Overlay classification only; numerical weights already use ordinary corrections."""
    if not enabled(db):return rows
    assignments=db.execute('SELECT a.* FROM basis_assignments a JOIN basis_transitions t ON t.id=a.transition_id WHERE a.person_id=? AND a.workout_id=? ORDER BY t.revision',(person,workout)).fetchall()
    by_id={row['entry_id']:row for row in assignments}
    for row in rows:
        if row['id'] in by_id:row['weight_basis']=by_id[row['id']]['after_basis']
    return rows


def plan(db,person,exercise,values):
    """Preview all personal configurations/history; fail before any write if unsafe."""
    if not enabled(db):raise c.ValidationError('Weight Basis needs explicit schema-9 migration.')
    definition=c.definition(db,person,exercise)
    settings=payload(values)
    if settings['name']!=definition['name']:c.unique_name(db,person,settings['name'],exercise)
    if db.execute("SELECT 1 FROM workout_entries e JOIN workout_sessions s ON s.id=e.session_id WHERE e.person_id=? AND e.exercise_id=? AND s.status='draft'",(person,exercise)).fetchone():
        raise c.ValidationError('Finish or discard your active workout containing this exercise before updating routines and history. Defaults Only remains available.')
    routines=[dict(r) for r in db.execute('SELECT id,routine_id FROM routine_exercises WHERE person_id=? AND exercise_id=? ORDER BY id',(person,exercise))]
    old,revision=baseline(db,person,exercise)
    new=settings['weight_basis'] if settings['measurement_type']!='time' else old
    from . import history as h
    affected=[];counts={'divide':0,'multiply':0,'classify':0};previous=set()
    for parent,rows in h.all_completed(db,person):
        chosen=[]
        for row in rows:
            if row['exercise_id']!=exercise or row['measurement_type']=='time' or settings['measurement_type']=='time':continue
            before=row['weight_basis'];previous.add(before)
            if new=='not_configured' and before!='not_configured':
                raise c.ValidationError('Classified history cannot return to Not Configured. Choose Total Weight or Per Hand / Side.')
            if before==new:continue
            try:after=convert(row['actual_weight_tenths_lb'],before,new)
            except c.ValidationError as error:
                raise c.ValidationError(f"{row['name']} — workout {parent['workout_date']} ({parent['id']}): {error} Correct that recorded weight, then review this operation again.") from error
            chosen.append(dict(entry_id=row['id'],before_basis=before,after_basis=new,before_weight=row['actual_weight_tenths_lb'],after_weight=after))
            if row['actual_weight_tenths_lb'] is not None:
                action='divide' if before=='total' and new=='per_side' else 'multiply' if before=='per_side' and new=='total' else 'classify'
                counts[action]+=1
        if chosen:affected.append((parent,rows,chosen))
    if new=='not_configured' and old!='not_configured':raise c.ValidationError('An applied history basis cannot be reset to Not Configured.')
    return dict(settings=settings,old=old,new=new,revision=revision,routines=len({r['routine_id'] for r in routines}),items=routines,
                workouts=affected,counts=counts,previous=sorted(previous),fingerprint=fingerprint(db))


def apply(db,person,exercise,values,token,expected,*,confirmed=False):
    """Atomically save defaults, personal configurations and append-only conversion audits.

    A repeated confirmed request returns its original result. Every different
    operation needs a fresh preview. External callers must commit/rollback the
    entire transaction; no partial writes or in-place completed-row updates.
    """
    if not confirmed:raise c.ValidationError('Explicit confirmation is required.')
    if not enabled(db):raise c.ValidationError('Weight Basis needs explicit schema-9 migration.')
    if not isinstance(token,str) or not re.fullmatch('[0-9a-f]{32}',token):raise c.ValidationError('Invalid operation token.')
    settings=payload(values);hashed=digest(settings)
    replay=db.execute('SELECT person_id,exercise_id,payload_hash FROM basis_transitions WHERE id=?',(token,)).fetchone()
    if replay:
        if tuple(replay)!=(person,exercise,hashed):raise w.RevisionConflict('This operation token belongs to different settings.')
        return False
    if not expected or fingerprint(db)!=expected:raise w.RevisionConflict('Data changed after preview. Review the current impact again.')
    preview=plan(db,person,exercise,settings)
    c.update_defaults(db,person,exercise,settings)
    definition=c.definition(db,person,exercise)
    if definition['name']!=settings['name']:c.update_definition(db,person,exercise,settings['name'],'rename')
    # Include retained archived routines too; IDs/order and snapshots stay fixed.
    configuration=c.configure(settings)
    db.execute('UPDATE routine_exercises SET measurement_type=?,target_sets=?,target_reps=?,target_duration_seconds=?,unit=?,weight_meaning=?,notes=?,weight_basis=? WHERE person_id=? AND exercise_id=?',(*configuration,settings['weight_basis'],person,exercise))
    from . import history as h
    stamp=w.now().isoformat()
    corrections={parent['id']:uuid4().hex for parent,_,_ in preview['workouts']}
    effects=[dict(row,workout_id=parent['id'],correction_id=corrections[parent['id']]) for parent,_,chosen in preview['workouts'] for row in chosen]
    db.execute('INSERT INTO basis_transitions VALUES (?,?,?,?,?,?,?,?,?,?)',(token,person,exercise,preview['revision']+1,preview['old'],preview['new'],stamp,h.json_text(settings),hashed,h.json_text(effects)))
    for parent,rows,chosen in preview['workouts']:
        before=h.value_state(parent,rows);after=json.loads(h.json_text(before))
        changes={r['entry_id']:r for r in chosen}
        for row in after['entries']:
            if row['id'] in changes:row['actual_weight_tenths_lb']=changes[row['id']]['after_weight']
        correction=corrections[parent['id']]
        # A no-value-change revision on first classification also invalidates
        # stale correction pages, without altering the original measurements.
        db.execute('INSERT INTO workout_corrections VALUES (?,?,?,?,?,?,?)',(correction,parent['id'],person,parent['correction_revision']+1,stamp,h.json_text(before),h.json_text(after)))
        for row in chosen:
            db.execute('INSERT INTO basis_assignments VALUES (?,?,?,?,?,?,?,?,?,?)',(token,parent['id'],person,exercise,row['entry_id'],row['before_basis'],row['after_basis'],row['before_weight'],row['after_weight'],correction))
    from .maintenance import logical_check_connection
    logical_check_connection(db,9)
    return True


def validate(db):
    """Check transition chains, exact arithmetic and correction linkage read-only.

    Called at schema-9 startup and before backup/restore/migration activation.
    Original basis columns remain immutable; later ordinary corrections may
    change actuals, but never silently reverse/reapply a recorded conversion.
    """
    from . import history as h
    try:
        chains={};entry_bases={};linked={}
        for event in db.execute('SELECT * FROM basis_transitions ORDER BY person_id,exercise_id,revision'):
            key=(event['person_id'],event['exercise_id']);old,revision=chains.get(key,('not_configured',0))
            if event['revision']!=revision+1 or event['old_basis']!=old:raise ValueError('Basis chain mismatch')
            if datetime.fromisoformat(event['created_at']).tzinfo is None:raise ValueError('Basis timestamp is not aware')
            settings=json.loads(event['payload_json'])
            if settings!=payload(settings) or digest(settings)!=event['payload_hash']:raise ValueError('Basis payload mismatch')
            if settings['measurement_type']!='time' and settings['weight_basis']!=event['new_basis']:raise ValueError('Basis target mismatch')
            if old!='not_configured' and event['new_basis']=='not_configured':raise ValueError('Applied history cannot be unclassified')
            chains[key]=(event['new_basis'],event['revision'])
            assigned=list(db.execute('SELECT * FROM basis_assignments WHERE transition_id=?',(event['id'],)))
            actual=[{key:r[key] for key in ('entry_id','before_basis','after_basis','before_weight','after_weight','workout_id','correction_id')} for r in assigned]
            if sorted(actual,key=lambda r:(r['workout_id'],r['entry_id']))!=sorted(json.loads(event['effects_json']),key=lambda r:(r['workout_id'],r['entry_id'])):raise ValueError('Missing or unexpected basis assignments')
            for assignment in assigned:
                if (assignment['person_id'],assignment['exercise_id'])!=key or assignment['after_basis']!=event['new_basis']:raise ValueError('Basis ownership mismatch')
                parent,rows=h.original(db,event['person_id'],assignment['workout_id'])
                row=next(r for r in rows if r['id']==assignment['entry_id'])
                if row['exercise_id']!=event['exercise_id'] or row['measurement_type']=='time':raise ValueError('Basis identity mismatch')
                entry_key=(assignment['workout_id'],row['id'])
                if assignment['before_basis']!=entry_bases.get(entry_key,row['weight_basis']):raise ValueError('Entry basis chain mismatch')
                if convert(assignment['before_weight'],assignment['before_basis'],assignment['after_basis'])!=assignment['after_weight']:raise ValueError('Basis arithmetic mismatch')
                entry_bases[entry_key]=assignment['after_basis']
                audit=db.execute('SELECT * FROM workout_corrections WHERE id=? AND workout_id=? AND person_id=?',(assignment['correction_id'],assignment['workout_id'],event['person_id'])).fetchone()
                if audit is None or audit['corrected_at']!=event['created_at']:raise ValueError('Missing conversion correction')
                before=json.loads(audit['before_json']);after=json.loads(audit['after_json'])
                b=next(r for r in before['entries'] if r['id']==row['id']);a=next(r for r in after['entries'] if r['id']==row['id'])
                if b['actual_weight_tenths_lb']!=assignment['before_weight'] or a['actual_weight_tenths_lb']!=assignment['after_weight']:raise ValueError('Conversion correction mismatch')
                linked.setdefault(audit['id'],[]).append(assignment)
        for identity,assignments in linked.items():
            audit=db.execute('SELECT * FROM workout_corrections WHERE id=?',(identity,)).fetchone()
            before=json.loads(audit['before_json']);after=json.loads(audit['after_json'])
            expected=json.loads(audit['before_json']);weights={a['entry_id']:a['after_weight'] for a in assignments}
            for row in expected['entries']:
                if row['id'] in weights:row['actual_weight_tenths_lb']=weights[row['id']]
            if expected!=after:raise ValueError('Conversion changed unrelated fields')
        # Verify ordinary corrections after a conversion too: future edits
        # must continue the same exact before/after chain, not undo an overlay.
        for record in db.execute('SELECT id,person_id FROM workout_registry'):
            parent,rows=h.original(db,record['person_id'],record['id'])
            current=h.value_state(parent,rows);h.validate_state(parent,rows,current)
            for index,audit in enumerate(h.audit(db,record['person_id'],record['id']),1):
                if audit['revision']!=index or audit['before']!=current:raise ValueError('Correction chain mismatch after basis transition')
                h.validate_state(parent,rows,audit['after']);current=audit['after']
        for form in db.execute('SELECT * FROM historical_forms'):
            snapshots=json.loads(form['snapshots_json'])
            for snapshot in snapshots:
                value=snapshot.get('weight_basis','not_configured')
                if value not in LABELS or (snapshot['measurement_type']=='time' and value!='not_configured'):raise ValueError('Invalid prepared basis')
                if type(snapshot.get('basis_epoch',0)) is not int or snapshot.get('basis_epoch',0)<0:raise ValueError('Invalid preparation epoch')
            saved=db.execute('SELECT id FROM historical_workouts WHERE form_id=?',(form['id'],)).fetchone()
            if saved:
                rows=db.execute('SELECT weight_basis FROM historical_entries WHERE session_id=? ORDER BY position',(saved['id'],)).fetchall()
                if [r[0] for r in rows]!=[r.get('weight_basis','not_configured') for r in snapshots]:raise ValueError('Original snapshot basis mismatch')
    except (ValueError,TypeError,KeyError,StopIteration,c.ValidationError,c.MissingRecord,IndexError,OverflowError) as error:
        raise StorageError('Weight Basis audit validation failed.') from error


def status(db,person):
    """Count unresolved configuration and history identities, never weight totals."""
    if not enabled(db):return None
    defaults=list(db.execute("SELECT exercise_id,weight_basis FROM exercise_defaults WHERE measurement_type!='time'"))
    routines=list(db.execute("SELECT exercise_id,weight_basis FROM routine_exercises WHERE person_id=? AND measurement_type!='time'",(person,)))
    from .history import all_completed
    history=[row for _,rows in all_completed(db,person) for row in rows if row['measurement_type']!='time']
    def count(rows):
        groups={}
        for row in rows:groups.setdefault(row['exercise_id'],[]).append(row['weight_basis'])
        return sum(all(v!='not_configured' for v in group) for group in groups.values()),len(groups)
    return dict(defaults=count(defaults),routines=count(routines),history=count(history))
