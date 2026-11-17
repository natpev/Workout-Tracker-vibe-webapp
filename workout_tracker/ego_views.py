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


@bp.route("/people/<person_id>/ego-lifts", methods=["GET", "POST"])
def index(person_id):
    """Search/selection stays GET; only a signed Save Lift form writes an attempt."""
    error = None
    status = 200
    values = request.form.to_dict() if request.method == "POST" else {}
    exercise = (
        request.form.get("exercise_id", "")
        if request.method == "POST"
        else request.args.get("exercise", "")
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
                url_for("ego.index", person_id=person_id, exercise=exercise), code=303
            )
        except c.ValidationError as exc:
            error = str(exc)
            status = 400
    with connection() as db:
        person = c.person(db, person_id)
        library = c.definitions(db, person_id)
        selected = dict(c.definition(db, person_id, exercise)) if exercise else None
        defaults = (
            dict(c.exercise_defaults(db, person_id, exercise)) if exercise else None
        )
        if defaults:
            defaults["weight_basis"] = e.weight_basis(db, exercise)
        rows = e.history(db, person_id, exercise)
    if not token and exercise:
        token = signer().dumps([person_id, exercise, uuid4().hex])
    search = request.args.get("search", "").strip().casefold()
    library = [row for row in library if search in row["name"].casefold()]
    return (
        render_template(
            "ego.html",
            local_time=local_time,
            person=person,
            library=library,
            selected=selected,
            defaults=defaults,
            rows=rows,
            records=e.records(rows),
            values=values,
            submission=token,
            error=error,
            search=request.args.get("search", ""),
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
                url_for("ego.index", person_id=person_id, exercise=row["exercise_id"]),
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
