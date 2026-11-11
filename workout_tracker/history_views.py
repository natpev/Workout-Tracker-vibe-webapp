# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""History routes: browser forms/filters -> validation -> effective-value reader.

All app writes use schema-4 locked transactions. CSRF protects preparations,
manual completions and append-only corrections. GETs never create records.
"""

from flask import Blueprint, current_app, redirect, render_template, request, url_for, Response

from . import catalog as c, history as h, workouts as w
from .storage import database_session
from .views import protect_forms
from . import historical_forms as forms
from .presentation import clock
from . import progress_ranges as ranges

bp=Blueprint('history',__name__)
bp.before_request(protect_forms)


def navigation_context():
    """Carry explicit Progress selection through this person's history-area URLs."""
    return {key:request.args[key] for key in ('progress_range','progress_from','progress_to','progress_exercise') if key in request.args}


@bp.context_processor
def progress_navigation():
    """Expose only filter context, not a remembered household identity."""
    return dict(progress_context=navigation_context())


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
        statistics=None
        if db.execute('PRAGMA user_version').fetchone()[0]>=10:
            from .weight_statistics import summary
            statistics=summary(h.all_completed(db,person_id),workout_id)
    return render_template('history_detail.html',person=person,workout=parent,entries=rows,audit=revisions,
                           original_workout=original_parent,original_entries=original_rows,display=w.display_measurement,statistics=statistics)


@bp.get('/people/<person_id>/progress')
@bp.get('/people/<person_id>/progress.csv',endpoint='export_csv')
def progress(person_id):
    """Apply URL ranges without altering chart calculations or historical identities."""
    from zoneinfo import ZoneInfo
    today=w.now().astimezone(ZoneInfo(current_app.config['WORKOUT_TIMEZONE'])).date()
    errors={};status=200;requested=request.args.to_dict();export_error=None
    selected_export=request.args.getlist('export_exercise')
    # Revealing Custom Range is not yet an edited range: start with the last
    # valid preset bounds so merely opening the controls keeps the graph intact.
    if requested.get('range')=='custom' and 'from' not in requested and 'to' not in requested:
        requested.update({'from':requested.get('previous_from',''),'to':requested.get('previous_to','')})
    try:filters,token,description=ranges.selection(requested,today)
    except c.ValidationError as error:
        errors={'range':str(error)};status=400;token='custom';filters=request.args.to_dict();description='Correct the custom dates to apply this range.'
    with connection() as db:
        person=owner(db,person_id)
        # On invalid custom input keep the most recent valid URL range when
        # supplied by the form, otherwise fall back to the default three-month view.
        chart_filters=filters
        if errors:
            previous=dict(range=request.args.get('previous_range','3m'),exercise=request.args.get('exercise',''),
                          **{'from':request.args.get('previous_from',''),'to':request.args.get('previous_to','')})
            try:chart_filters,_,_=ranges.selection(previous,today)
            except c.ValidationError:chart_filters,_,_=ranges.selection({'exercise':request.args.get('exercise','')},today)
        # Successful downloads do not need to prepare SVG charts. Errors below
        # still render the original filters and previous valid chart state.
        if request.path.endswith('/progress.csv'):
            if not errors:
                from .csv_export import wide_csv
                try:
                    text=wide_csv(db,person_id,filters,selected_export)
                    return Response(text.encode('utf-8-sig'),content_type='text/csv; charset=utf-8',
                                    headers={'Content-Disposition':f'attachment; filename="workout-progress-{today.isoformat()}.csv"','Cache-Control':'no-store'})
                except c.ValidationError as error:export_error=str(error)
            else:export_error='Correct the date range before exporting.'
            status=400
        from .exercise_listing import ordering,chart_order
        completed=h.all_completed(db,person_id)
        _,exercises,_=ordering(db,person_id,completed)
        series=chart_order(db,person_id,chart_filters,completed,exercises)
    return render_template('progress.html',person=person,series=series,exercises=exercises,filters=filters,
                           selected_export=selected_export,export_error=export_error,
                           range_token=token,range_description=description,range_options=ranges.RANGES,range_errors=errors,
                           invalid_dates={key for key in ('from','to') if not ranges.valid_date(filters.get(key,''))},
                           applied=chart_filters,progress_context=dict(progress_range=chart_filters.get('range','3m'),progress_from=chart_filters.get('from',''),progress_to=chart_filters.get('to',''),progress_exercise=chart_filters.get('exercise',''))),status


@bp.route('/people/<person_id>/historical',methods=['GET','POST'])
def historical(person_id):
    """Prepare an owned immutable snapshot; expected errors stay beside raw inputs."""
    values=request.form.to_dict() if request.method=='POST' else {};errors={};status=200
    try:
        with connection(write=request.method=='POST') as db:
            person=c.person(db,person_id)
            routines=db.execute('SELECT * FROM routines WHERE person_id=? AND archived=0 ORDER BY position',(person_id,)).fetchall()
            if request.method=='POST':
                normalized=forms.normalized(values)
                errors=forms.occurrence_errors(normalized,current_app.config['WORKOUT_TIMEZONE'])
                if values.get('routine_id') not in {row['id'] for row in routines}:errors['routine_id']='Choose one of this person’s available routines.'
                if errors:raise forms.FormErrors(errors)
                try:form_id=h.prepare(db,person_id,values.get('routine_id'),normalized,current_app.config['WORKOUT_TIMEZONE'])
                except c.ValidationError as error:raise forms.FormErrors({'routine_id':str(error)}) from error
        if request.method=='POST':return redirect(url_for('history.review_historical',person_id=person_id,form_id=form_id,**navigation_context()),code=303)
    except forms.FormErrors as error:errors=error.errors;status=400
    return render_template('historical_start.html',person=person,routines=routines,zone=current_app.config['WORKOUT_TIMEZONE'],values=values,errors=errors),status


@bp.route('/people/<person_id>/historical/<form_id>',methods=['GET','POST'])
def review_historical(person_id,form_id):
    """Collect all field errors, roll back, then render the same complete raw form."""
    values=request.form.to_dict() if request.method=='POST' else None;errors={};status=200
    try:
        with connection(write=request.method=='POST') as db:
            person=owner(db,person_id);parent,rows=h.prepared(db,person_id,form_id)
            parent['schema_version']=db.execute('PRAGMA user_version').fetchone()[0]
            if request.method=='POST':
                existing=db.execute('SELECT id FROM historical_workouts WHERE form_id=? AND person_id=?',(form_id,person_id)).fetchone()
                errors={} if existing else forms.measurement_errors(rows,values,db.execute('PRAGMA user_version').fetchone()[0]>=10)
                if errors:raise forms.FormErrors(errors)
                try:identity=h.complete_historical(db,person_id,form_id,values)
                except c.ValidationError as error:raise forms.FormErrors({'form':str(error)}) from error
        if request.method=='POST':return redirect(url_for('history.detail',person_id=person_id,workout_id=identity,**navigation_context()),code=303)
    except forms.FormErrors as error:errors=error.errors;status=400
    if values is None:values=forms.values_for_rows(parent,rows,False,clock,blank_reps='schema_version' in parent and parent['schema_version']>=11)
    return render_template('history_form.html',person=person,workout=parent,entries=rows,correction=False,values=values,errors=errors),status


@bp.route('/people/<person_id>/history/<workout_id>/correct',methods=['GET','POST'])
def correct(person_id,workout_id):
    """Keep raw corrections/revision on error; only the existing atomic service writes."""
    values=request.form.to_dict() if request.method=='POST' else None;errors={};status=200
    try:
        with connection(write=request.method=='POST') as db:
            person=owner(db,person_id);parent,rows=h.effective(db,person_id,workout_id)
            if request.method=='POST':
                normalized=forms.normalized(values)
                errors=forms.occurrence_errors(normalized,parent['timezone']) | forms.measurement_errors(rows,values,db.execute('PRAGMA user_version').fetchone()[0]>=10)
                if values.get('confirm')!='yes':errors['confirm']='Confirm these corrections before applying them.'
                if values.get('correction_revision')!=str(parent['correction_revision']):
                    raise w.RevisionConflict('This workout was corrected in another page. Your inputs are retained. Reload and review the latest values before applying corrections.')
                if errors:raise forms.FormErrors(errors)
                try:h.correct(db,person_id,workout_id,normalized)
                except c.ValidationError as error:raise forms.FormErrors({'form':str(error)}) from error
        if request.method=='POST':return redirect(url_for('history.detail',person_id=person_id,workout_id=workout_id,**navigation_context()),code=303)
    except w.RevisionConflict as error:errors={'form':str(error)};status=409
    except forms.FormErrors as error:errors=error.errors;status=400
    if values is None:
        fold=''
        if parent['occurred_at']:
            from datetime import datetime
            from zoneinfo import ZoneInfo
            fold=str(datetime.fromisoformat(parent['occurred_at']).astimezone(ZoneInfo(parent['timezone'])).fold)
        values=forms.values_for_rows(parent,rows,True,clock,fold)
    return render_template('history_form.html',person=person,workout=parent,entries=rows,correction=True,values=values,errors=errors),status
