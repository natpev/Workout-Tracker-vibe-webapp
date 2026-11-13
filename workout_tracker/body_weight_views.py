# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Body-weight browser forms -> person-owned validated atomic SQLite operations."""
from flask import Blueprint, current_app, request, render_template, redirect, url_for
from zoneinfo import ZoneInfo
from datetime import datetime
from . import body_weight as b, catalog as c, workouts as w
from .storage import database_session
from .views import protect_forms

bp = Blueprint("body_weight", __name__)
bp.before_request(protect_forms)


def connection(write=False):
    """Only explicit schema 13 enables body-weight storage; never initialize on GET."""
    return database_session(
        current_app.config["WORKOUT_DATA_ROOT"], write=write, minimum_version=13
    )


@bp.route("/people/<person_id>/weight", methods=["GET", "POST"])
def index(person_id):
    """Keep invalid submitted values visible; every list reads local SQLite only."""
    error = None
    status = 200
    zone = current_app.config["WORKOUT_TIMEZONE"]
    local = w.now().astimezone(ZoneInfo(zone))
    values = dict(date=local.date().isoformat(), time=local.strftime("%H:%M"))
    if request.method == "POST":
        values = request.form.to_dict()
        try:
            with connection(True) as db:
                b.manual(db, person_id, values, zone)
            return redirect(url_for("body_weight.index", person_id=person_id), code=303)
        except c.ValidationError as exc:
            error = str(exc)
            status = 400
    try:
        with connection() as db:
            person = c.person(db, person_id)
            rows = b.records(db, person_id, zone, request.args)
            all_rows = b.records(
                db, person_id, zone, {"source": request.args.get("source", "")}
            )
    except c.ValidationError as exc:
        error = str(exc)
        status = 400
        with connection() as db:
            person = c.person(db, person_id)
            rows = []
            all_rows = []
    chart = b.trends(all_rows)
    shown_trend = [
        r
        for r in chart
        if (not request.args.get("from") or r["day"] >= request.args["from"])
        and (not request.args.get("to") or r["day"] <= request.args["to"])
    ]
    from .analytics import body_chart

    plot = body_chart(rows, chart, request.args)
    return (
        render_template(
            "body_weight.html",
            person=person,
            rows=rows,
            trend=shown_trend,
            plot=plot,
            values=values,
            error=error,
            filters=request.args,
        ),
        status,
    )


@bp.route("/people/<person_id>/weight/<identity>", methods=["GET", "POST"])
def edit(person_id, identity):
    """Edit/remove Manual readings only; confirmation and revisions protect removals."""
    error = None
    status = 200
    zone = current_app.config["WORKOUT_TIMEZONE"]
    with connection() as db:
        person = c.person(db, person_id)
        row = b.record(db, person_id, identity)
    if row["source"] != "manual":
        raise c.ValidationError("Garmin-origin readings are read-only here.")
    local = datetime.fromisoformat(row["measured_at"]).astimezone(ZoneInfo(zone))
    values = dict(
        weight=b.display(row["weight_milli_lb"]),
        date=local.date().isoformat(),
        time=local.strftime("%H:%M"),
        revision=str(row["revision"]),
    )
    if request.method == "POST":
        values = request.form.to_dict()
        try:
            with connection(True) as db:
                if request.form.get("action") == "remove":
                    b.remove(db, person_id, identity, values)
                else:
                    b.manual(db, person_id, values, zone, identity)
            return redirect(url_for("body_weight.index", person_id=person_id), code=303)
        except c.ValidationError as exc:
            error = str(exc)
            status = 409 if isinstance(exc, w.RevisionConflict) else 400
    return (
        render_template(
            "body_weight_edit.html", person=person, values=values, error=error
        ),
        status,
    )
