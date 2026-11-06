# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""Settings browser forms -> CSRF -> locked external metadata/maintenance services.

Only server-listed IDs select backups. GET does not create settings or jobs.
No route downloads files or exposes filesystem paths/technical stack frames.
"""
from uuid import uuid4
from flask import Blueprint,current_app,render_template,request,redirect,url_for,abort

from . import operations as o,maintenance as m,diagnostics as d,scheduler
from .storage import storage_lock,_inspect_unlocked,StorageError
from .views import protect_forms

bp=Blueprint('settings',__name__)
bp.before_request(protect_forms)


def root_value():
    """Use only operator-configured external storage, never a request pathname."""
    return current_app.config['WORKOUT_DATA_ROOT']


@bp.route('/settings',methods=['GET','POST'])
def index():
    """Read database/schedule status, or explicitly save validated settings."""
    if request.method=='POST':
        scheduler.configure(root_value(),request.form)
        return redirect(url_for('settings.index'),code=303)
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
    return redirect(url_for('settings.backup_detail',backup_id=record['id']),code=303)


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
    return redirect(url_for('settings.index'),code=303)


@bp.post('/settings/backups/<backup_id>/restore')
def restore(backup_id):
    """Require acknowledgment and typed RESTORE; revalidate source under exclusive lock."""
    record=m.restore(root_value(),backup_id,request.form.get('operation_id'),
                     request.form.get('confirm')=='yes' and request.form.get('confirmation')=='RESTORE')
    # Restoring changes the dataset-generation CSRF suffix; subsequent pages issue
    # fresh tokens while forms left open against the previous dataset are refused.
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
