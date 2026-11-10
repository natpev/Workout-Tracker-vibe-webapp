# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Passwordless trusted-LAN browser forms -> CSRF -> fixed local host operations.

All reachable household users may review/confirm updates. Person selection is
context, not authentication. Host source validation is independent of these forms.
"""
from flask import Blueprint,current_app,render_template,request,redirect,url_for,jsonify
from . import update_client
from .storage import StorageError,inspect_storage
from .views import protect_forms,connection
from .catalog import person

bp=Blueprint('updates',__name__)
bp.before_request(protect_forms)
from .administration import require_administration
bp.before_request(require_administration)


@bp.route('/settings/updates',methods=['GET','POST'])
def index():
    """Check/review/install approved releases with no login, explicit consent and CSRF."""
    root=current_app.config['WORKOUT_DATA_ROOT'];error=None;state=None;settings={};selected=None
    if request.args.get('person_id'):
        with connection() as db:selected=person(db,request.args['person_id'],archived=True)
    try:
        _,settings=update_client.bridge(root)
        if request.method=='POST':
            action=request.form.get('action')
            if action=='check':state=update_client.call(root,'check')
            elif action=='install':
                state=update_client.call(root,'status');release=state.get('release')
                if not release or request.form.get('release')!=release['id']:raise StorageError('Review the approved release again.')
                if request.form.get('confirm')!='yes':raise StorageError('Explicit update confirmation required.')
                current=inspect_storage(root)['schema_version'];migration=request.form.get('migration')=='yes'
                if release['schema']>current and not migration:raise StorageError('Confirm the separate-candidate database structure change before installing.')
                state=update_client.call(root,'install',release=release['id'],confirm=True,migration=migration)
            else:raise StorageError('Unknown update action.')
            if action=='install' and request.accept_mimetypes.best=='application/json':return jsonify(state=state),202
            return redirect(url_for('updates.index',person_id=selected['id'] if selected else None),code=303)
        state=update_client.call(root,'status')
    except StorageError as exc:
        error=str(exc)
        if request.method=='POST' and request.accept_mimetypes.best=='application/json':return jsonify(error=error),400
    return render_template('updates.html',person=selected,state=state,error=error,status_url=settings.get('status_url')),(400 if request.method=='POST' and error else 200)


@bp.get('/settings/updates/status')
def status():
    """Read persistent host stages; no percentages or speculative release values."""
    return jsonify(update_client.call(current_app.config['WORKOUT_DATA_ROOT'],'status'))
