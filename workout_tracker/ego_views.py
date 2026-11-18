# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""CSRF-protected Ego forms; signed submission identities and person-qualified transactions."""
from uuid import uuid4
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import (
    Blueprint,
    current_app,
    request,
    render_template,
    redirect,
    url_for,
    flash,
)
from itsdangerous import URLSafeSerializer, BadSignature
from . import ego_lifts as e, catalog as c, workouts as w
from .storage import database_session
from .views import protect_forms

bp = Blueprint("ego", __name__)
bp.before_request(protect_forms)


def connection(write=False):
    """Refuse older storage; never migrate from a page request."""
    return database_session(
        current_app.config["WORKOUT_DATA_ROOT"], write=write, minimum_version=14
    )


def signer():
    """Bind idempotency tokens to this installation, selected person and exercise."""
    return URLSafeSerializer(current_app.secret_key, salt="ego-lift-submission")


def local_time(value):
    """Display automatic UTC occurrence/audit instants in the configured IANA zone."""
    return (
        datetime.fromisoformat(value)
        .astimezone(ZoneInfo(current_app.config["WORKOUT_TIMEZONE"]))
        .strftime("%Y-%m-%d %H:%M")
    )


@bp.route("/people/<person_id>/ego-lifts/record/<exercise_id>", methods=["GET", "POST"])
def record_lift(person_id, exercise_id):
    """Only this signed recording form writes attempts; selection is a separate GET view."""
    error = None
    status = 200
    values = request.form.to_dict() if request.method == "POST" else {}
    exercise = (
        request.form.get("exercise_id", "") if request.method == "POST" else exercise_id
    )
    if exercise != exercise_id:
        raise c.ValidationError(
            "The selected exercise changed; reload the recording form."
        )
    token = values.get("submission", "")
    if request.method == "POST":
        try:
            try:
                claim = signer().loads(token)
            except BadSignature:
                raise c.ValidationError(
                    "Reload this lift form before saving."
                ) from None
            if (
                not isinstance(claim, list)
                or len(claim) != 3
                or claim[:2] != [person_id, exercise]
            ):
                raise c.ValidationError(
                    "This lift form belongs to another person or exercise."
                )
            values["submission_id"] = claim[2]
            with connection(True) as db:
                e.save(db, person_id, exercise, values)
            flash("Ego Lift saved.", "success")
            return redirect(
                url_for("ego.record_lift", person_id=person_id, exercise_id=exercise),
                code=303,
            )
        except c.ValidationError as exc:
            error = str(exc)
            status = 400
    with connection() as db:
        person = c.person(db, person_id)
        selected = dict(c.definition(db, person_id, exercise)) if exercise else None
        defaults = (
            dict(c.exercise_defaults(db, person_id, exercise)) if exercise else None
        )
        if defaults:
            defaults["weight_basis"] = e.weight_basis(db, exercise)
        rows = e.history(db, person_id, exercise)
        from .exercise_icons import pairs

        artwork = pairs(db, [exercise])[exercise]
    if not token and exercise:
        token = signer().dumps([person_id, exercise, uuid4().hex])
    return (
        render_template(
            "ego_record.html",
            artwork=artwork,
            local_time=local_time,
            person=person,
            selected=selected,
            defaults=defaults,
            rows=rows,
            records=e.records(rows),
            values=values,
            submission=token,
            error=error,
        ),
        status,
    )


@bp.route("/people/<person_id>/ego-lifts/<identity>", methods=["GET", "POST"])
def edit(person_id, identity):
    """Keep submitted values on error; require confirmation and a current revision."""
    with connection() as db:
        person = c.person(db, person_id)
        row = e.record(db, person_id, identity)
    values = (
        request.form.to_dict()
        if request.method == "POST"
        else dict(
            weight=f"{row['weight_tenths_lb']//10}.{row['weight_tenths_lb']%10}",
            repetitions=str(row["repetitions"]),
            revision=str(row["revision"]),
        )
    )
    error = None
    status = 200
    if request.method == "POST":
        try:
            with connection(True) as db:
                e.correct(db, person_id, identity, values)
            flash(
                (
                    "Ego Lift removed."
                    if values.get("action") == "delete"
                    else "Ego Lift corrected."
                ),
                "success",
            )
            return redirect(
                url_for(
                    "ego.history", person_id=person_id, exercise=row["exercise_id"]
                ),
                code=303,
            )
        except c.ValidationError as exc:
            error = str(exc)
            status = 409 if isinstance(exc, w.RevisionConflict) else 400
    with connection() as db:
        audits = db.execute(
            "SELECT changed_at,revision FROM ego_lift_audit WHERE lift_id=? ORDER BY revision",
            (identity,),
        ).fetchall()
    return (
        render_template(
            "ego_edit.html",
            local_time=local_time,
            person=person,
            row=row,
            values=values,
            error=error,
            audits=audits,
        ),
        status,
    )


@bp.get("/people/<person_id>/ego-lifts")
def index(person_id):
    """Read-only selection preview; choosing an option never leaves this screen."""
    exercise = request.args.get("exercise", "")
    with connection() as db:
        person = c.person(db, person_id)
        library = c.definitions(db, person_id)
        selected = c.definition(db, person_id, exercise) if exercise else None
        rows = e.history(db, person_id, exercise)[:5] if exercise else []
        from .exercise_icons import pairs

        artwork = pairs(db, [exercise])[exercise] if exercise else None
    return render_template(
        "ego_select.html",
        person=person,
        library=library,
        selected=selected,
        rows=rows,
        artwork=artwork,
        local_time=local_time,
    )


@bp.get("/people/<person_id>/ego-history")
def history(person_id):
    """Third history tab uses existing effective Ego rows and confirmation routes."""
    exercise = request.args.get("exercise", "")
    with connection() as db:
        person = c.person(db, person_id)
        library = c.definitions(db, person_id)
        rows = e.history(db, person_id, exercise)
        # Retained snapshots keep archived identities filterable without name-based matching.
        choices = {row["id"]: row["name"] for row in library}
        for row in rows:
            choices.setdefault(row["exercise_id"], row["exercise_name"])
        library = [
            dict(id=identity, name=name)
            for identity, name in sorted(
                choices.items(), key=lambda item: (item[1].casefold(), item[0])
            )
        ]
    return render_template(
        "ego_history.html",
        person=person,
        library=library,
        rows=rows,
        selected_id=exercise,
        records=e.records(rows),
        local_time=local_time,
    )


@bp.context_processor
def progress_navigation():
    """Reuse existing filter context so visiting Ego History retains Progress selections."""
    from .history_views import navigation_context

    return dict(progress_context=navigation_context())
