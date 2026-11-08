# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""Management routes: browser forms -> CSRF/validation -> catalog -> SQLite.

Each request opens one locked schema-2 transaction and closes it before rendering.
Only people, exercise definitions and routine configurations can be changed.
Session cookies sign CSRF state; user selection remains passwordless navigation.
"""

import hashlib
import secrets

from flask import Blueprint, abort, current_app, redirect, render_template, request, session, url_for, g

from . import catalog
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
    return {"csrf_token": csrf_token}


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
            routines = db.execute("SELECT * FROM routines WHERE person_id=? AND archived=0 ORDER BY position",
                                  (person_id,)).fetchall()
            sources = db.execute("SELECT r.*,p.name AS person_name FROM routines r JOIN people p ON r.person_id=p.id "
                                 "WHERE r.archived=0 AND p.archived=0 ORDER BY p.name,r.position").fetchall()
    if request.method == "POST":
        return redirect(url_for("manage.edit_routine", person_id=person_id, routine_id=identity), code=303)
    with connection() as db:
        archived_routines = db.execute('SELECT id,name FROM routines WHERE person_id=? AND archived=1 ORDER BY name',(person_id,)).fetchall() if version>=6 else []
    return render_template("dashboard.html", person=selected, routines=routines, sources=sources, active_draft=draft, workout_enabled=version >= 3, archived_routines=archived_routines)


@bp.route("/people/<person_id>/exercises", methods=["GET", "POST"])
def exercises(person_id):
    """Manage the shared library; routine targets and historical names stay separate."""
    with connection(write=request.method == "POST") as db:
        selected = catalog.person(db, person_id)
        if request.method == "POST":
            if request.form.get("action") == "create":
                catalog.create_definition(db, person_id, request.form.get("name"))
            else:
                if request.form.get("action") == "archive":
                    if db.execute('PRAGMA user_version').fetchone()[0]>=6:
                        raise catalog.ValidationError('Use the dedicated household Permanent Delete Exercise page. Remove from Routine never deletes global history.')
                    confirmation()
                catalog.update_definition(db, person_id, request.form.get("exercise_id"),
                                          request.form.get("name"), request.form.get("action"))
        rows = (db.execute('SELECT * FROM exercises ORDER BY archived,name,id').fetchall()
                if db.execute('PRAGMA user_version').fetchone()[0]>=6 else catalog.definitions(db, person_id))
    if request.method == "POST":
        return redirect(url_for("manage.exercises", person_id=person_id), code=303)
    return render_template("exercises.html", person=selected, exercises=rows)


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
    with connection(write=request.method == "POST") as db:
        selected = catalog.person(db, person_id)
        parent = catalog.routine(db, person_id, routine_id)
        item = catalog.entry(db, person_id, routine_id, entry_id)
        if request.method == "POST":
            check_revision(db, person_id, routine_id)
            action = request.form.get("action")
            if action == "save":
                catalog.update_entry(db, person_id, routine_id, entry_id, request.form)
            elif action == "remove":
                confirmation()
                db.execute("DELETE FROM routine_exercises WHERE id=? AND person_id=? AND routine_id=?",
                           (entry_id, person_id, routine_id))
            elif action == "move":
                catalog.move(db, "routine_exercises", "routine_id", routine_id, entry_id, request.form.get("direction"))
            else:
                raise catalog.ValidationError("Unknown routine exercise action.")
        else:
            revision = routine_token(db, person_id, routine_id)
    if request.method == "POST":
        return redirect(url_for("manage.edit_routine", person_id=person_id, routine_id=routine_id), code=303)
    return render_template("entry.html", person=selected, routine=parent, item=item, revision=revision)
