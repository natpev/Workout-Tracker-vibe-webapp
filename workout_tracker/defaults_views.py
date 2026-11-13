# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Global default editor with confirmed, atomic selected-person routine updates.

Browser -> signed settings-only preview -> locked catalog services. No completed
history, correction or basis-conversion record can be written by this module.
"""
import hashlib
from flask import current_app, request, render_template, redirect, url_for
from itsdangerous import URLSafeTimedSerializer, BadSignature
from . import catalog as c, workouts as w


def fingerprint(db, person, exercise):
    """Bind confirmation to the definition, defaults and selected-person routines."""
    rows=[tuple(db.execute('SELECT * FROM exercises WHERE id=?',(exercise,)).fetchone()),
          tuple(db.execute('SELECT * FROM exercise_defaults WHERE exercise_id=?',(exercise,)).fetchone())]
    rows += [tuple(row) for row in db.execute('SELECT * FROM routine_exercises WHERE person_id=? AND exercise_id=? ORDER BY id',(person,exercise))]
    return hashlib.sha256(repr(rows).encode()).hexdigest()


def settings(db, person, exercise, raw):
    """Canonicalize user settings through permanent lock validation before preview."""
    current=c.exercise_defaults(db,person,exercise)
    from .measurements import adapt
    values=c.locked_configuration(db,exercise,current,adapt(db,raw),confirmed_type_change=True)
    fields=('measurement_type','target_sets','target_reps','target_duration_seconds','unit','weight_meaning','notes')
    result=dict(zip(fields,c.configure(values)))
    if db.execute('PRAGMA user_version').fetchone()[0]>=13:result['capabilities']=values['capabilities']
    result.update(name=c.text(raw.get('name'),'Exercise name'),weight_basis=values.get('weight_basis',current['weight_basis']))
    return c.default_values(result)


def save(db, person, exercise, values, update_routines=False, *, confirmed_type_change=False):
    """One caller-owned transaction saves globals and compatible personal fields."""
    values=settings(db,person,exercise,values)
    c.update_defaults(db,person,exercise,values,confirmed_type_change=confirmed_type_change)
    if c.definition(db,person,exercise)['name']!=values['name']:
        c.update_definition(db,person,exercise,values['name'],'rename')
    if update_routines:
        for row in db.execute('SELECT id,routine_id FROM routine_exercises WHERE person_id=? AND exercise_id=?',(person,exercise)).fetchall():
            # Includes archived routines without altering IDs/order or snapshots.
            current=db.execute('SELECT * FROM routine_exercises WHERE id=?',(row['id'],)).fetchone()
            configuration=c.configure(dict(values,weight_meaning=current['weight_meaning']))
            c.locked_configuration(db,exercise,current,values,confirmed_type_change=confirmed_type_change)
            if db.execute('PRAGMA user_version').fetchone()[0]>=13:
                db.execute('UPDATE routine_exercises SET measurement_type=?,target_sets=?,target_reps=?,target_duration_seconds=?,unit=?,weight_meaning=?,notes=?,weight_basis=?,capabilities=? WHERE id=?',(*configuration,values['weight_basis'],values['capabilities'],row['id']))
            elif db.execute('PRAGMA user_version').fetchone()[0]>=11:
                db.execute('UPDATE routine_exercises SET measurement_type=?,target_sets=?,target_reps=?,target_duration_seconds=?,unit=?,weight_meaning=?,notes=?,weight_basis=? WHERE id=?',(*configuration,values['weight_basis'],row['id']))
            else:
                db.execute('UPDATE routine_exercises SET measurement_type=?,target_sets=?,target_reps=?,target_duration_seconds=?,unit=?,weight_meaning=?,notes=? WHERE id=?',(*configuration,row['id']))


def editor(person_id, exercise_id):
    """Retain raw settings on errors; expired/stale signed previews cannot write."""
    from .views import connection
    raw=request.form.to_dict(); signed=None; error=None; status=200; preview_context=None
    serializer=URLSafeTimedSerializer(current_app.secret_key,salt='permanent-defaults-preview-v3')
    if request.method=='POST' and raw.get('action')=='confirm':
        try:
            signed=serializer.loads(raw.get('preview',''),max_age=1800)
            if signed['person']!=person_id or signed['exercise']!=exercise_id:
                raise BadSignature('Wrong exercise')
            raw=signed['values']
        except (BadSignature,KeyError,TypeError):
            return render_template('error.html',message='Confirmation expired or is invalid. Review the settings again.'),400
    try:
        with connection(write=request.method=='POST') as db:
            person=c.person(db,person_id);definition=c.definition(db,person_id,exercise_id)
            item=c.exercise_defaults(db,person_id,exercise_id)
            revision=fingerprint(db,person_id,exercise_id)
            from .exercise_icons import pairs
            artwork=pairs(db,[exercise_id])[exercise_id]
            if request.method=='POST':
                if signed:
                    if request.form.get('confirm')!='yes':
                        raise c.ValidationError('Confirm overwriting your routine settings.')
                    if signed['revision']!=revision:
                        raise w.RevisionConflict('Settings changed after preview. Review the current settings again.')
                    save(db,person_id,exercise_id,raw,signed.get('scope')=='apply',confirmed_type_change=True)
                else:
                    if raw.get('revision')!=revision:
                        raise w.RevisionConflict('Exercise name or settings changed; reload before saving.')
                    raw.setdefault('name',definition['name'])
                    values=settings(db,person_id,exercise_id,raw)
                    type_change=(values['measurement_type']!=item['measurement_type'] or (values.get('capabilities') is not None and values.get('capabilities')!=dict(item).get('capabilities'))) and db.execute('PRAGMA user_version').fetchone()[0]>=11
                    if raw.get('action')=='apply' or (raw.get('action','defaults')=='defaults' and type_change):
                        counts=db.execute('SELECT count(DISTINCT routine_id),count(*) FROM routine_exercises WHERE person_id=? AND exercise_id=?',(person_id,exercise_id)).fetchone()
                        token=serializer.dumps(dict(person=person_id,exercise=exercise_id,values=values,revision=revision,scope=raw.get('action','defaults')))
                        preview_context=dict(person=person,definition=definition,settings=values,routines=counts[0],items=counts[1],token=token,type_change=type_change,old_kind=item['measurement_type'],scope=raw.get('action','defaults'))
                    elif raw.get('action','defaults')=='defaults':
                        save(db,person_id,exercise_id,values)
                    else:
                        raise c.ValidationError('Choose a listed save operation.')
        if preview_context:
            return render_template('defaults_confirm.html',**preview_context)
        if request.method=='POST':
            return redirect(url_for('manage.exercises',person_id=person_id),code=303)
    except c.ValidationError as exc:
        error=str(exc);status=409 if isinstance(exc,w.RevisionConflict) else 400
        # A rejected crafted basis cannot change the read-only displayed value.
        item={**dict(item),**raw,'weight_basis':item['weight_basis']}
    return render_template('exercise_defaults.html',person=person,definition=definition,item=item,revision=revision,name=raw.get('name',definition['name']),error=error,artwork=artwork),status
