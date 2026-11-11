# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Schema-9 defaults editor and signed, expiring bulk-application confirmation.

Browser fields -> validation/preview without writes -> explicit CSRF confirmation
-> locked atomic service. Signed values and a full data fingerprint prevent stale
or tampered previews. No form can invoke a migration or overwrite original history.
"""
import hashlib
from uuid import uuid4
from flask import current_app,request,render_template,redirect,url_for
from itsdangerous import URLSafeTimedSerializer,BadSignature
from . import catalog as c,basis,workouts as w


def editor(person_id,exercise_id):
    """Handle the two distinct save scopes, retaining submitted settings on failure."""
    from .views import connection
    error=None;status=200;raw=request.form.to_dict();signed=None;preview_context=None
    serializer=URLSafeTimedSerializer(current_app.secret_key,salt='weight-basis-preview-v1')
    if request.method=='POST' and raw.get('action')=='confirm':
        try:
            signed=serializer.loads(raw.get('preview',''),max_age=1800)
            if signed['person']!=person_id or signed['exercise']!=exercise_id:raise BadSignature('Wrong exercise')
            raw=signed['values']
        except (BadSignature,KeyError,TypeError):
            return render_template('error.html',message='Confirmation expired or is invalid. Open Edit Defaults and review the operation again.'),400
    try:
        with connection(write=request.method=='POST') as db:
            person=c.person(db,person_id);definition=c.definition(db,person_id,exercise_id)
            item=c.exercise_defaults(db,person_id,exercise_id)
            applied_basis,applied_revision=basis.baseline(db,person_id,exercise_id)
            revision=hashlib.sha256(repr((tuple(definition),tuple(item))).encode()).hexdigest()
            if request.method=='POST':
                if signed:
                    basis.apply(db,person_id,exercise_id,raw,signed['token'],signed['fingerprint'],confirmed=request.form.get('confirm')=='yes')
                else:
                    if raw.get('revision')!=revision:raise w.RevisionConflict('Exercise name or defaults changed; reload before saving.')
                    raw.setdefault('name',definition['name'])
                    raw.setdefault('weight_basis',item['weight_basis'])
                    settings=basis.payload(raw)
                    if settings['name']!=definition['name']:c.unique_name(db,person_id,settings['name'],exercise_id)
                    if raw.get('action')=='apply':
                        preview=basis.plan(db,person_id,exercise_id,settings)
                        token=serializer.dumps(dict(person=person_id,exercise=exercise_id,values=settings,token=uuid4().hex,fingerprint=preview['fingerprint']))
                        preview_context=dict(person=person,definition=definition,preview=preview,token=token)
                    else:
                        if raw.get('action','defaults')!='defaults':raise c.ValidationError('Choose a listed save operation.')
                        c.update_defaults(db,person_id,exercise_id,settings)
                        if settings['name']!=definition['name']:c.update_definition(db,person_id,exercise_id,settings['name'],'rename')
        # Rendering opens read-only template metadata connections: release the
        # exclusive transaction first, as with every existing management form.
        if preview_context:return render_template('basis_confirm.html',**preview_context)
        if request.method=='POST':return redirect(url_for('manage.exercises',person_id=person_id),code=303)
    except c.ValidationError as exc:
        error=str(exc);status=409 if isinstance(exc,w.RevisionConflict) else 400
        item={**dict(item),**raw}
    return render_template('exercise_defaults.html',person=person,definition=definition,item=item,revision=revision,
                           name=raw.get('name',definition['name']),error=error,applied_basis=applied_basis,applied_revision=applied_revision),status
