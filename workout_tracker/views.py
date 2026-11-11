# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Management routes: browser forms -> CSRF/validation -> catalog -> SQLite.

Each request opens one locked schema-2 transaction and closes it before rendering.
Only people, exercise definitions and routine configurations can be changed.
Session cookies sign CSRF state; user selection remains passwordless navigation.
"""

import hashlib
import secrets

from flask import Blueprint, abort, current_app, redirect, render_template, request, session, url_for, g

from . import catalog
from .routine_listing import selectable_routines
from .storage import StorageError, database_session

bp = Blueprint("manage", __name__)


def csrf_token():
    """Return a per-browser unguessable token stored in a signed session cookie."""
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    # Bind forms to the current active selection; never silently apply a form
    # rendered before restore to a newly selected dataset.
    from .storage import storage_root, _regular_file
    active=storage_root(current_app.config['WORKOUT_DATA_ROOT'])/'config'/'active.json'
    _regular_file(active)
    generation=hashlib.sha256(active.read_bytes()).hexdigest()
    return session["csrf"]+'.'+generation


@bp.before_request
def protect_forms():
    """Reject forged mutating requests before any database connection is opened."""
    if not current_app.secret_key:
        # A process started against schema 1 must restart after explicit upgrade
        # so every worker loads the same provisioned key before serving forms.
        raise StorageError("Restart the application after explicit schema migration.")
    if request.method == "POST":
        expected = csrf_token() if session.get("csrf") else ""
        provided = request.form.get("csrf_token", "")
        if not expected or not secrets.compare_digest(expected.encode(), provided.encode()):
            from .diagnostics import emit
            emit(current_app.config['WORKOUT_DATA_ROOT'],'WARNING','Security','Form security or dataset-generation check rejected a request')
            abort(400, description="Form security token missing or expired, or database selection changed. Reload the page and try again.")
        g.dataset_generation=provided.rsplit('.',1)[-1]


@bp.app_context_processor
def form_helpers():
    """Expose token generation and routine conflict checks to Jinja forms."""
    from .basis import label as basis_label
    return {"basis_label":basis_label,"csrf_token": csrf_token,"labels_for_exercises":catalog.exercise_labels,"labels_for_choices":lambda choices:catalog.exercise_labels([dict(id=identity,name=name) for identity,name in choices.items()])}


def connection(write=False):
    """Select the configured external database through the storage lock protocol."""
    return database_session(current_app.config["WORKOUT_DATA_ROOT"], write=write)


def routine_token(db, person_id, routine_id):
    """Fingerprint the current routine and items to detect stale browser forms."""
    parent = catalog.routine(db, person_id, routine_id)
    rows = db.execute("SELECT re.*, e.name FROM routine_exercises re JOIN exercises e ON e.id=re.exercise_id "
                      "WHERE re.routine_id=? ORDER BY re.position", (routine_id,)).fetchall()
    return hashlib.sha256(repr((tuple(parent), [tuple(row) for row in rows])).encode()).hexdigest()


def check_revision(db, person_id, routine_id):
    """Prevent an old page from overwriting a more recent routine change."""
    if not secrets.compare_digest(request.form.get("revision", "").encode(), routine_token(db, person_id, routine_id).encode()):
        abort(409, description="This routine changed in another page. Reload before editing again.")


def confirmation():
    """Require an explicit checkbox on removal/archive forms, even without JS."""
    if request.form.get("confirm") != "yes":
        raise catalog.ValidationError("Check the confirmation box before removing this record.")


@bp.route("/people", methods=["GET", "POST"])
def people():
    """List/select household users or create one with a permanent identity."""
    with connection(write=request.method == "POST") as db:
        if request.method == "POST":
            identity = catalog.create_person(db, request.form.get("name"))
            destination = url_for("manage.dashboard", person_id=identity)
        else:
            rows = db.execute("SELECT * FROM people ORDER BY archived, name COLLATE NOCASE, id").fetchall()
    if request.method == "POST":
        return redirect(destination, code=303)
    return render_template("people.html", people=rows)


@bp.post("/people/<person_id>/manage")
def manage_person(person_id):
    """Rename/archive/reactivate; never physically delete a person or history."""
    with connection(write=True) as db:
        action = request.form.get("action")
        if action == "archive":
            confirmation()
        catalog.update_person(db, person_id, request.form.get("name"), action)
    return redirect(url_for("manage.people"), code=303)


@bp.route("/people/<person_id>", methods=["GET", "POST"])
def dashboard(person_id):
    """Show only this person's routines; create or independently copy one."""
    with connection(write=request.method == "POST") as db:
        selected = catalog.person(db, person_id)
        if request.method == "POST":
            if request.form.get("action") == "copy":
                source = request.form.get("source", "").split(":")
                if len(source) != 2:
                    raise catalog.ValidationError("Choose a source routine.")
                identity = catalog.copy_routine(db, source[0], source[1], person_id, request.form.get("name"))
            elif request.form.get("action") == "create":
                identity = catalog.create_routine(db, person_id, request.form.get("name"))
            else:
                raise catalog.ValidationError("Choose create or copy.")
        else:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            from .workouts import active
            draft = active(db, person_id) if version >= 3 else None
            routines = selectable_routines(db, person_id)
            statistics=None
            if version>=10:
                from .history import all_completed
                from .weight_statistics import summary
                statistics=summary(all_completed(db,person_id))
            sources = db.execute("SELECT r.*,p.name AS person_name FROM routines r JOIN people p ON r.person_id=p.id "
                                 "WHERE r.archived=0 AND p.archived=0 ORDER BY p.name,r.position").fetchall()
    if request.method == "POST":
        return redirect(url_for("manage.edit_routine", person_id=person_id, routine_id=identity), code=303)
    with connection() as db:
        archived_routines = db.execute('SELECT id,name FROM routines WHERE person_id=? AND archived=1 ORDER BY name',(person_id,)).fetchall() if version>=6 else []
    return render_template("dashboard.html", person=selected, routines=routines, sources=sources, active_draft=draft, workout_enabled=version >= 3, archived_routines=archived_routines,statistics=statistics)


@bp.route("/people/<person_id>/exercises", methods=["GET", "POST"])
def exercises(person_id):
    """Manage the shared library; routine targets and historical names stay separate."""
    error=None;status=200;values=request.form.to_dict() if request.method=='POST' else {}
    try:
        with connection(write=request.method=='POST') as db:
            selected=catalog.person(db,person_id)
            if request.method=='POST':
                if request.form.get('action')=='create':
                    catalog.create_definition(db,person_id,request.form.get('name'),request.form if 'measurement_type' in request.form else None)
                else:
                    if request.form.get('action')=='archive':
                        if db.execute('PRAGMA user_version').fetchone()[0]>=6:
                            raise catalog.ValidationError('Use the dedicated Permanent Delete Exercise page.')
                        confirmation()
                    catalog.update_definition(db,person_id,request.form.get('exercise_id'),request.form.get('name'),request.form.get('action'))
        if request.method=='POST':return redirect(url_for('manage.exercises',person_id=person_id),code=303)
    except catalog.ValidationError as exc:
        if values.get('action')!='create':raise
        error=str(exc);status=400
    with connection() as db:
        from .exercise_listing import ordering
        from .exercise_icons import pairs
        rows,_,_=ordering(db,person_id)
        artwork=pairs(db,[row['id'] for row in rows])
    return render_template('exercises.html',person=selected,exercises=rows,creation=values or None,creation_error=error,artwork=artwork),status


@bp.route("/people/<person_id>/routines/<routine_id>", methods=["GET", "POST"])
def edit_routine(person_id, routine_id):
    """Edit metadata/items and ordering; no workout measurements are accepted."""
    with connection(write=request.method == "POST") as db:
        selected = catalog.person(db, person_id)
        parent = catalog.routine(db, person_id, routine_id)
        if request.method == "POST":
            check_revision(db, person_id, routine_id)
            action = request.form.get("action")
            if action == "rename":
                db.execute("UPDATE routines SET name=? WHERE id=? AND person_id=?",
                           (catalog.text(request.form.get("name"), "Routine name"), routine_id, person_id))
            elif action == "delete":
                if db.execute('PRAGMA user_version').fetchone()[0] >= 6:
                    # Destructive deletion needs its own impact preview/confirmation
                    # route; never turn an old archive checkbox into consent.
                    return redirect(url_for('deletion.review',person_id=person_id,kind='routine',identity=routine_id),code=303)
                confirmation()
                db.execute("UPDATE routines SET archived=1 WHERE id=? AND person_id=?", (routine_id, person_id))
            elif action == "move":
                catalog.move(db, "routines", "person_id", person_id, routine_id, request.form.get("direction"))
            elif action == "add_defaults":
                catalog.add_entry(db,person_id,routine_id,dict(exercise_id=request.form.get("exercise_id"),use_library_defaults="yes"))
            elif action == "add":
                catalog.add_entry(db, person_id, routine_id, request.form)
            elif action == "duplicate":
                copied = catalog.copy_routine(db, person_id, routine_id, person_id, request.form.get("name"))
                return_to = url_for("manage.edit_routine", person_id=person_id, routine_id=copied)
            else:
                raise catalog.ValidationError("Unknown routine action.")
        else:
            rows = db.execute("SELECT re.*,e.name FROM routine_exercises re JOIN exercises e ON e.id=re.exercise_id "
                              "WHERE re.routine_id=? ORDER BY re.position", (routine_id,)).fetchall()
            definitions = catalog.definitions(db, person_id)
            revision = routine_token(db, person_id, routine_id)
            version = db.execute("PRAGMA user_version").fetchone()[0]
            from .workouts import active
            draft = active(db, person_id) if version >= 3 else None
    if request.method == "POST":
        if action == "delete":
            return redirect(url_for("manage.dashboard", person_id=person_id), code=303)
        return redirect(return_to if action == "duplicate" else request.path, code=303)
    return render_template("routine.html", person=selected, routine=parent, entries=rows,
                           exercises=definitions, revision=revision, item=None, workout_enabled=version >= 3, active_draft=draft)


@bp.route("/people/<person_id>/routines/<routine_id>/items/<entry_id>", methods=["GET", "POST"])
def edit_entry(person_id, routine_id, entry_id):
    """Edit/remove/reorder a routine item, preserving its permanent exercise ID."""
    from itsdangerous import URLSafeTimedSerializer,BadSignature
    serializer=URLSafeTimedSerializer(current_app.secret_key,salt='routine-type-correction-v1')
    preview=None;raw=request.form.to_dict();signed=None
    if raw.get('action')=='confirm_type':
        try:
            signed=serializer.loads(raw.get('preview',''),max_age=1800)
            if (signed['person'],signed['routine'],signed['entry'])!=(person_id,routine_id,entry_id):raise BadSignature('Wrong configuration')
            if raw.get('confirm')!='yes':raise catalog.ValidationError('Confirm the measurement-type correction.')
        except (BadSignature,KeyError,TypeError) as error:
            raise catalog.ValidationError('Correction confirmation expired or is invalid.') from error
    with connection(write=request.method=='POST') as db:
        selected=catalog.person(db,person_id);parent=catalog.routine(db,person_id,routine_id)
        item=catalog.entry(db,person_id,routine_id,entry_id)
        if request.method=='POST':
            check_revision(db,person_id,routine_id)
            action=raw.get('action')
            if action=='confirm_type':
                if signed['revision']!=routine_token(db,person_id,routine_id):raise catalog.ValidationError('Routine changed. Review the correction again.')
                catalog.update_entry(db,person_id,routine_id,entry_id,signed['values'],confirmed_type_change=True)
            elif action=='save':
                changing=db.execute('PRAGMA user_version').fetchone()[0]>=11 and raw.get('measurement_type')!=item['measurement_type']
                if changing:
                    checked=catalog.locked_configuration(db,item['exercise_id'],item,raw,confirmed_type_change=True)
                    catalog.configure(checked)
                    revision=routine_token(db,person_id,routine_id)
                    token=serializer.dumps(dict(person=person_id,routine=routine_id,entry=entry_id,values=checked,revision=revision))
                    preview=dict(person=selected,routine=parent,item=item,new_kind=raw.get('measurement_type'),token=token,revision=revision)
                else:catalog.update_entry(db,person_id,routine_id,entry_id,raw)
            elif action=='remove':
                confirmation();db.execute('DELETE FROM routine_exercises WHERE id=? AND person_id=? AND routine_id=?',(entry_id,person_id,routine_id))
            elif action=='move':catalog.move(db,'routine_exercises','routine_id',routine_id,entry_id,raw.get('direction'))
            else:raise catalog.ValidationError('Unknown routine exercise action.')
        else:
            revision=routine_token(db,person_id,routine_id)
            if db.execute('PRAGMA user_version').fetchone()[0]>=11:
                from .measurement_rules import assigned
                item=dict(item,weight_basis=assigned(db,item['exercise_id']) or 'not_configured')
    if preview:return render_template('measurement_confirm.html',**preview)
    if request.method=='POST':return redirect(url_for('manage.edit_routine',person_id=person_id,routine_id=routine_id),code=303)
    return render_template('entry.html',person=selected,routine=parent,item=item,revision=revision)


@bp.route('/people/<person_id>/exercises/<exercise_id>/defaults',methods=['GET','POST'])
def edit_defaults(person_id,exercise_id):
    """Legacy defaults-only editing; schema 9 explicitly adds the confirmed scope."""
    from . import basis
    with connection() as db:modern=basis.enabled(db)
    if modern:
        from .defaults_views import editor
        return editor(person_id,exercise_id)
    error=None;item=None
    try:
        with connection(write=request.method=='POST') as db:
            selected=catalog.person(db,person_id)
            definition=catalog.definition(db,person_id,exercise_id)
            item=catalog.exercise_defaults(db,person_id,exercise_id) if db.execute('PRAGMA user_version').fetchone()[0]>=7 else None
            # Include the name as well as the preset so a stale page cannot undo
            # another person's rename. Caller commits both edits or neither.
            revision=hashlib.sha256(repr((tuple(definition),tuple(item) if item else None)).encode()).hexdigest()
            if request.method=='POST':
                if request.form.get('revision')!=revision:
                    raise catalog.ValidationError('Exercise name or defaults changed; reload before saving.')
                name=catalog.text(request.form.get('name',definition['name']),'Exercise name')
                if item is not None:catalog.update_defaults(db,person_id,exercise_id,request.form)
                if name!=definition['name']:catalog.update_definition(db,person_id,exercise_id,name,'rename')
    except catalog.ValidationError as exc:
        # A duplicate name or invalid target rolls back the whole transaction.
        # Retain raw fields on the same form instead of losing typed settings.
        error=str(exc)
        if item is not None:item={**dict(item),**request.form.to_dict()}
    if request.method=='POST' and not error:return redirect(url_for('manage.exercises',person_id=person_id),code=303)
    return render_template('exercise_defaults.html',person=selected,item=item,definition=definition,revision=revision,
                           name=request.form.get('name',definition['name']),error=error),400 if error else 200
