# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Selected-person Garmin settings: CSRF forms, secret entry and safe status only."""
from flask import (
    Blueprint,
    current_app,
    request,
    render_template,
    redirect,
    url_for,
    flash,
)
from . import garmin, catalog as c
from .storage import database_session
from .views import protect_forms

bp = Blueprint("garmin", __name__)
bp.before_request(protect_forms)


@bp.route("/people/<person_id>/garmin", methods=["GET", "POST"])
def settings(person_id):
    """Keys are never passed back to templates, even after validation failure."""
    root = current_app.config["WORKOUT_DATA_ROOT"]
    zone = current_app.config["WORKOUT_TIMEZONE"]
    with database_session(root, minimum_version=13) as db:
        person = c.person(db, person_id)
    error = None
    status = 200
    if request.method == "POST":
        try:
            action = request.form.get("action")
            if action == "connect":
                garmin.connect(root, person_id, request.form.get("api_key", ""), zone)
            elif action == "disconnect":
                if request.form.get("confirm") != "yes":
                    raise c.ValidationError(
                        "Confirm disconnecting Garmin; imported measurements will remain."
                    )
                garmin.disconnect(root, person_id)
            elif action == "sync":
                count = garmin.sync(root, person_id, zone)
                flash(
                    f"Garmin synchronization complete: {count} new or updated measurements.",
                    "success",
                )
            elif action == "schedule":
                garmin.schedule(
                    root,
                    person_id,
                    request.form.get("automatic") == "yes",
                    request.form.get("hours", "6"),
                )
            else:
                raise c.ValidationError("Choose a listed Garmin action.")
            return redirect(url_for("garmin.settings", person_id=person_id), code=303)
        except c.ValidationError as exc:
            error = str(exc)
            status = 400
    return (
        render_template(
            "garmin.html",
            person=person,
            status=garmin.public(root, person_id),
            error=error,
        ),
        status,
    )
