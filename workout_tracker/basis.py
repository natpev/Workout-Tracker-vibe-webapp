# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Permanent basis labels and read-only Phase 13 historical audit compatibility.

Only read/validation helpers remain. Arithmetic below verifies archived events;
it cannot append conversions. Old payload canonicalization preserves old hashes.
"""
import hashlib
import json
from datetime import datetime
from . import catalog as c,workouts as w
from .storage import StorageError

LABELS={'not_configured':'Not Configured','total':'Total Weight','per_side':'Per Hand / Side'}


def enabled(db):
    """Read basis metadata only when the schema explicitly contains it."""
    return db.execute('PRAGMA user_version').fetchone()[0]>=9


def parse(values,kind):
    """Validate a convention, never infer it from a name, equipment or old text."""
    value=values.get('weight_basis','not_configured')
    if not isinstance(value,str) or value not in LABELS:raise c.ValidationError('Choose a listed Weight Basis.')
    return value if kind!='time' else 'not_configured'


def label(value):
    """Return a fixed display label; unknown values are not silently classified."""
    return LABELS.get(value,'Not Configured')


def audit_weight(value,old,new):
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


def audit_payload(values):
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


def overlay(db,person,workout,rows):
    """Overlay classification only; numerical weights already use ordinary corrections."""
    if not enabled(db):return rows
    assignments=db.execute('SELECT a.* FROM basis_assignments a JOIN basis_transitions t ON t.id=a.transition_id WHERE a.person_id=? AND a.workout_id=? ORDER BY t.revision',(person,workout)).fetchall()
    by_id={row['entry_id']:row for row in assignments}
    for row in rows:
        if row['id'] in by_id:row['weight_basis']=by_id[row['id']]['after_basis']
    return rows


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
            if settings!=audit_payload(settings) or digest(settings)!=event['payload_hash']:raise ValueError('Basis payload mismatch')
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
                if audit_weight(assignment['before_weight'],assignment['before_basis'],assignment['after_basis'])!=assignment['after_weight']:raise ValueError('Basis arithmetic mismatch')
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
