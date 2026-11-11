# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Workout HTTP routes: browser form/fetch -> CSRF -> service -> transaction.

Autosave acknowledges only after leaving the committing context manager. Finish
includes pending form input in the completing transaction. No history explorer,
backdating, correction, backup or restore endpoints are introduced.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, url_for

from . import catalog, workouts
from .storage import database_session
from .views import protect_forms

bp = Blueprint('workout', __name__)
bp.before_request(protect_forms)


def connection(write=False):
    """Require an explicitly migrated schema 3, keeping every connection locked."""
    return database_session(current_app.config['WORKOUT_DATA_ROOT'], write=write, minimum_version=3)


@bp.errorhandler(catalog.ValidationError)
@bp.errorhandler(catalog.MissingRecord)
def request_error(error):
    """Return useful API errors while keeping unsaved browser inputs visible."""
    from .diagnostics import emit
    if request.method=='POST':
        emit(current_app.config['WORKOUT_DATA_ROOT'],'WARNING','Workout','Workout save/completion request rejected; transaction not committed',error=error)
    code = 404 if isinstance(error, catalog.MissingRecord) else 409 if isinstance(error, workouts.RevisionConflict) else 400
    if request.endpoint == 'workout.autosave':
        return jsonify(error=str(error),fields=getattr(error,'fields',{})), code
    if isinstance(error,workouts.MeasurementError):
        return render_template('workout.html',submitted=request.form,field_errors=error.fields,**page_context(person_id=request.view_args['person_id'],session_id=request.view_args['session_id'],message=str(error))),code
    return render_template('error.html', message=str(error)), code


def page_context(person_id, session_id, message=None):
    """Read an owned complete snapshot and reference performance before rendering."""
    with connection() as db:
        owner = catalog.person(db, person_id, archived=True)
        parent = workouts.session(db, person_id, session_id)
        rows = workouts.entries(db, person_id, session_id)
        if parent['status']=='completed' and db.execute('PRAGMA user_version').fetchone()[0]>=4:
            from .history import effective
            parent,rows=effective(db,person_id,session_id)
        statistics=None
        if parent['status']=='completed' and db.execute('PRAGMA user_version').fetchone()[0]>=10:
            from .history import all_completed
            from .weight_statistics import summary
            statistics=summary(all_completed(db,person_id),session_id)
        requested = request.form.get('view_position',str(parent['current_position'])) if request.method=='POST' else request.args.get('position',str(parent['current_position']))
        position = catalog.integer(requested, 'Exercise position', 0, len(rows) - 1)
        current = rows[position]
        from .exercise_icons import pairs
        artwork=pairs(db,[current['exercise_id']])[current['exercise_id']]
        prior, performed = workouts.previous(db, person_id, parent, current)
        return dict(artwork=artwork,statistics=statistics,person=owner, workout=parent, entries=rows, current=current, position=position,
                    previous=prior, last_performed=performed, completed=workouts.count_performed(rows), navigation_progress=len(rows) if parent['status']=='completed' else parent['current_position'],
                    display=workouts.display_measurement, message=message, history_enabled=db.execute('PRAGMA user_version').fetchone()[0]>=4,
                    local_started=datetime.fromisoformat(parent['started_at']).astimezone(ZoneInfo(parent['timezone'])))


@bp.post('/people/<person_id>/routines/<routine_id>/start')
def start(person_id, routine_id):
    """Create a blank snapshot or offer resume/discard of the already active draft."""
    with connection(write=True) as db:
        identity, created = workouts.start(db, person_id, routine_id, current_app.config['WORKOUT_TIMEZONE'])
    endpoint = 'workout.show' if created else 'workout.resume'
    return redirect(url_for(endpoint, person_id=person_id, session_id=identity), code=303)


@bp.get('/people/<person_id>/workouts/<session_id>/resume')
def resume(person_id, session_id):
    """Offer an explicit choice; starting another routine never replaces a draft."""
    context = page_context(person_id, session_id)
    if context['workout']['status'] != 'draft':
        return redirect(url_for('workout.show', person_id=person_id, session_id=session_id))
    return render_template('workout_resume.html', **context)


@bp.get('/people/<person_id>/workouts/<session_id>')
def show(person_id, session_id):
    """Render one exercise, or an immutable completion/discard confirmation."""
    context = page_context(person_id, session_id)
    template = 'workout.html' if context['workout']['status'] == 'draft' else 'workout_done.html'
    return render_template(template, **context)


@bp.post('/people/<person_id>/workouts/<session_id>/draft')
def autosave(person_id, session_id):
    """Acknowledge revision/progress only once SQLite commit has succeeded."""
    with connection(write=True) as db:
        parent = workouts.update(db, person_id, session_id, request.form)
        rows = workouts.entries(db, person_id, session_id)
        row = next(row for row in rows if row['id'] == request.form['entry_id'])
        response = dict(entry_id=row['id'], measurement_display=workouts.display_measurement(row), revision=parent['revision'], completed=workouts.count_performed(rows), total=len(rows), navigation_progress=parent['current_position'],
                        updated_at=parent['updated_at'], current_position=parent['current_position'],
                        weight='' if row['actual_weight_tenths_lb'] is None else f"{row['actual_weight_tenths_lb'] // 10}.{row['actual_weight_tenths_lb'] % 10}",
                        minutes='' if row['actual_duration_seconds'] is None else str(row['actual_duration_seconds'] // 60),
                        seconds='' if row['actual_duration_seconds'] is None else str(row['actual_duration_seconds'] % 60),
                        increase=row['increase_next_time'] == 1)
    return jsonify(response)


@bp.post('/people/<person_id>/workouts/<session_id>/save')
def save(person_id, session_id):
    """Provide an explicit form save as well as JavaScript autosave."""
    with connection(write=True) as db:
        workouts.update(db, person_id, session_id, request.form)
    return redirect(url_for('workout.show', person_id=person_id, session_id=session_id,position=request.form.get('view_position')), code=303)


@bp.post('/people/<person_id>/workouts/<session_id>/finish')
def finish(person_id, session_id):
    """Commit every snapshot row and pending input atomically, with retry safety."""
    try:
        with connection(write=True) as db:
            workouts.finish(db, person_id, session_id, request.form)
    except workouts.AllSkipped as error:
        from .diagnostics import emit
        emit(current_app.config['WORKOUT_DATA_ROOT'],'WARNING','Workout','Workout completion needs all-skipped confirmation')
        # The transaction rolled back. Previously committed draft values remain.
        return render_template('workout.html', submitted=request.form, **page_context(person_id, session_id, str(error))), 400
    return redirect(url_for('workout.show', person_id=person_id, session_id=session_id), code=303)


@bp.route('/people/<person_id>/workouts/<session_id>/discard', methods=['GET', 'POST'])
def discard(person_id, session_id):
    """GET shows acknowledgment dialog; only an acknowledged POST changes status."""
    if request.method == 'POST':
        with connection(write=True) as db:
            workouts.discard(db, person_id, session_id, request.form)
        return redirect(url_for('workout.show', person_id=person_id, session_id=session_id), code=303)
    context = page_context(person_id, session_id)
    if context['workout']['status'] != 'draft':
        raise workouts.RevisionConflict('Only an unfinished workout may be discarded.')
    return render_template('workout_discard.html', **context)


@bp.post('/people/<person_id>/workouts/<session_id>/exit')
def exit_workout(person_id,session_id):
    """Save current validated input atomically, preserving the draft before leaving it."""
    with connection(write=True) as db:
        workouts.update(db,person_id,session_id,request.form)
    return redirect(url_for('manage.dashboard',person_id=person_id,exited=session_id),code=303)
