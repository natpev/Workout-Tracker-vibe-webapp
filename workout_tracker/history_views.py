# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""History routes: browser forms/filters -> validation -> effective-value reader.

All app writes use schema-4 locked transactions. CSRF protects preparations,
manual completions and append-only corrections. GETs never create records.
"""

from flask import Blueprint, current_app, redirect, render_template, request, url_for

from . import catalog as c, history as h, workouts as w
from .storage import database_session
from .views import protect_forms

bp=Blueprint('history',__name__)
bp.before_request(protect_forms)


@bp.errorhandler(w.RevisionConflict)
def stale_correction(error):
    """Return 409 for stale audit revisions instead of a generic validation status."""
    return render_template('error.html',message=str(error)),409


def connection(write=False):
    """Require an explicit schema-4 candidate upgrade for these interfaces."""
    return database_session(current_app.config['WORKOUT_DATA_ROOT'],write=write,minimum_version=4)


def owner(db, identity):
    """Archived people retain their historical records and may still view them."""
    return c.person(db,identity,archived=True)


@bp.get('/people/<person_id>/history')
def index(person_id):
    """List effective completed workouts newest first with inclusive filters."""
    with connection() as db:
        person=owner(db,person_id);rows=h.listing(db,person_id,request.args)
        routines,exercises=h.choices(db,person_id)
    return render_template('history.html',person=person,workouts=rows,routines=routines,exercises=exercises,filters=request.args,display=w.display_measurement)


@bp.get('/people/<person_id>/history/<workout_id>')
def detail(person_id,workout_id):
    """Show immutable snapshot metadata plus latest actual values and full audit."""
    with connection() as db:
        person=owner(db,person_id);parent,rows=h.effective(db,person_id,workout_id)
        original_parent,original_rows=h.original(db,person_id,workout_id)
        revisions=h.audit(db,person_id,workout_id)
    return render_template('history_detail.html',person=person,workout=parent,entries=rows,audit=revisions,
                           original_workout=original_parent,original_entries=original_rows,display=w.display_measurement)


@bp.get('/people/<person_id>/progress')
def progress(person_id):
    """Render locally generated responsive SVGs and accessible data tables."""
    with connection() as db:
        person=owner(db,person_id);series=h.chart_series(db,person_id,request.args)
        _,exercises=h.choices(db,person_id)
    return render_template('progress.html',person=person,series=series,exercises=exercises,filters=request.args)


@bp.route('/people/<person_id>/historical',methods=['GET','POST'])
def historical(person_id):
    """Choose routine/actual occurrence; append an independent review preparation."""
    with connection(write=request.method=='POST') as db:
        person=c.person(db,person_id)
        if request.method=='POST':
            form_id=h.prepare(db,person_id,request.form.get('routine_id'),request.form,current_app.config['WORKOUT_TIMEZONE'])
        else:
            routines=db.execute('SELECT * FROM routines WHERE person_id=? AND archived=0 ORDER BY position',(person_id,)).fetchall()
    if request.method=='POST':
        return redirect(url_for('history.review_historical',person_id=person_id,form_id=form_id),code=303)
    return render_template('historical_start.html',person=person,routines=routines,zone=current_app.config['WORKOUT_TIMEZONE'])


@bp.route('/people/<person_id>/historical/<form_id>',methods=['GET','POST'])
def review_historical(person_id,form_id):
    """Review copied targets and atomically save all actual measurements once."""
    with connection(write=request.method=='POST') as db:
        person=owner(db,person_id);form,rows=h.prepared(db,person_id,form_id)
        if request.method=='POST':
            identity=h.complete_historical(db,person_id,form_id,request.form)
    if request.method=='POST':
        return redirect(url_for('history.detail',person_id=person_id,workout_id=identity),code=303)
    return render_template('history_form.html',person=person,workout=form,entries=rows,correction=False)


@bp.route('/people/<person_id>/history/<workout_id>/correct',methods=['GET','POST'])
def correct(person_id,workout_id):
    """Require confirmation/revision; append an audit record without changing originals."""
    with connection(write=request.method=='POST') as db:
        person=owner(db,person_id);parent,rows=h.effective(db,person_id,workout_id)
        if request.method=='POST':
            h.correct(db,person_id,workout_id,request.form)
    if request.method=='POST':
        return redirect(url_for('history.detail',person_id=person_id,workout_id=workout_id),code=303)
    fold=''
    if parent['occurred_at']:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        fold=str(datetime.fromisoformat(parent['occurred_at']).astimezone(ZoneInfo(parent['timezone'])).fold)
    return render_template('history_form.html',person=person,workout=parent,entries=rows,correction=True,fold=fold)
