# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Settings browser forms -> CSRF -> locked external metadata/maintenance services.

Only server-listed IDs select backups. GET does not create settings or jobs.
No route downloads files or exposes filesystem paths/technical stack frames.
"""
from uuid import uuid4
from flask import Blueprint,current_app,render_template,request,redirect,url_for,abort,g

from . import operations as o,maintenance as m,diagnostics as d,scheduler
from .storage import storage_lock,_inspect_unlocked,StorageError,database_session
from .views import protect_forms

bp=Blueprint('settings',__name__)
bp.before_request(protect_forms)


@bp.before_request
def administration_boundary():
    """Keep personal appearance separate; all maintenance shares one open boundary."""
    from .administration import require_administration
    if request.endpoint not in ('settings.index','settings.accent') or (request.endpoint=='settings.index' and request.method=='POST'):
        return require_administration()


@bp.get('/settings/administration')
def administration():
    """Render the grouped maintenance area using the existing Settings data flow."""
    return index()



def root_value():
    """Use only operator-configured external storage, never a request pathname."""
    return current_app.config['WORKOUT_DATA_ROOT']


def selected_person():
    """Read URL person context once per request; never remember/switch an account.

    After restore a person may no longer exist, or damaged storage may be
    unavailable. In those cases recovery pages stay usable without inventing a
    different person. Valid IDs resolve the current name/accent from storage.
    """
    if not hasattr(g,'settings_person'):
        g.settings_person=None
        identity=request.args.get('person_id')
        if identity:
            from .catalog import person,MissingRecord
            try:
                with database_session(root_value()) as db:
                    g.settings_person=person(db,identity,archived=True)
            except (StorageError,MissingRecord):pass
    return g.settings_person


@bp.context_processor
def person_context():
    """Supply the same explicit person to every Settings template/header."""
    return dict(person=selected_person())


def context_url(endpoint,**values):
    """Carry URL context through redirects without a global/session identity."""
    return url_for(endpoint,person_id=request.args.get('person_id') or None,**values)


@bp.route('/settings',methods=['GET','POST'])
def index():
    """Read database/schedule status, or explicitly save validated settings."""
    if request.method=='POST':
        scheduler.configure(root_value(),request.form)
        return redirect(context_url('settings.administration'),code=303)
    with storage_lock(root_value()) as root:
        state=o.read_state(root)
        try:
            details=_inspect_unlocked(root);database_ok=True
        except StorageError:
            details={'schema_version':'Unavailable'};database_ok=False
    successes=[row for row in state['backups'].values() if row['status']=='verified']
    latest=max((row['verified_at'] for row in successes),default=None)
    return render_template('settings.html',last_backup=latest,schema=details['schema_version'],database_ok=database_ok,state=state,operation_id=uuid4().hex)


@bp.post('/settings/backup')
def backup():
    """Wait for durable verification; failed attempts never display success."""
    record=m.backup(root_value(),request.form.get('operation_id'))
    return redirect(context_url('settings.backup_detail',backup_id=record['id']),code=303)


@bp.get('/settings/backups/<backup_id>')
def backup_detail(backup_id):
    """Show only safe backup metadata and deliberate restore/deletion controls."""
    with storage_lock(root_value()) as root:
        state=o.read_state(root);record=state['backups'].get(o.identity(backup_id))
        if not record: abort(404)
    return render_template('backup_detail.html',record=record,operation_id=uuid4().hex)


@bp.post('/settings/backups/<backup_id>/delete')
def delete(backup_id):
    """Explicit checkbox plus Delete action; metadata survives file deletion."""
    m.delete_backup(root_value(),backup_id,request.form.get('confirm')=='yes')
    return redirect(context_url('settings.administration'),code=303)


@bp.post('/settings/backups/<backup_id>/restore')
def restore(backup_id):
    """Require acknowledgment and typed RESTORE; revalidate source under exclusive lock."""
    record=m.restore(root_value(),backup_id,request.form.get('operation_id'),
                     request.form.get('confirm')=='yes' and request.form.get('confirmation')=='RESTORE')
    # Restoring changes the dataset-generation CSRF suffix; subsequent pages issue
    # fresh tokens while forms left open against the previous dataset are refused.
    # Redirect to a read-only recorded result: refreshing must not repost a
    # stale pre-restore CSRF token or request a second restoration.
    return redirect(context_url('settings.restore_result',operation_id=record['id']),code=303)


@bp.get('/settings/restores/<operation_id>')
def restore_result(operation_id):
    """Display an existing restore outcome without replaying any maintenance."""
    with storage_lock(root_value()) as root:
        record=o.read_state(root)['restores'].get(o.identity(operation_id))
        if not record:abort(404)
    return render_template('restore_result.html',record=record),200 if record['status']=='succeeded' else 503


@bp.get('/settings/logs')
def logs():
    """Filter/page structured safe log summaries; no user-supplied filename is opened."""
    rows,more=d.query(root_value(),request.args,request.args.get('page','1'))
    page=int(request.args.get('page','1'))
    next_args=request.args.to_dict();next_args['page']=page+1
    previous_args=request.args.to_dict();previous_args['page']=max(1,page-1)
    return render_template('logs.html',rows=rows,filters=request.args,levels=d.LEVELS,categories=d.CATEGORIES,
                           page=page,more=more,next_args=next_args,previous_args=previous_args)


@bp.post('/settings/people/<person_id>/accent')
def accent(person_id):
    """CSRF-protected preference save affects only this person's presentation."""
    from .preferences import set_color
    set_color(root_value(),person_id,request.form.get('accent'))
    return redirect(url_for('settings.index',person_id=person_id),code=303)
