# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Report/download HTTP endpoints: owned snapshots, no remote services or retained files."""
from datetime import timedelta
from io import BytesIO
from flask import Blueprint, current_app, request, render_template, send_file
from zoneinfo import ZoneInfo
from . import catalog as c, history as h, reports, workouts as w
from .storage import database_session
from .views import protect_forms

bp = Blueprint("reports", __name__)
bp.before_request(protect_forms)


@bp.get("/people/<person_id>/reports")
def index(person_id):
    """Release the read lock before CPU-heavy rendering; every value is effective history."""
    root = current_app.config["WORKOUT_DATA_ROOT"]
    zone = current_app.config["WORKOUT_TIMEZONE"]
    today = w.now().astimezone(ZoneInfo(zone)).date()
    values = {
        "from": request.args.get("from", (today - timedelta(days=29)).isoformat()),
        "to": request.args.get("to", today.isoformat()),
    }
    error = None
    report = None
    with database_session(root, minimum_version=13) as db:
        person = dict(c.person(db, person_id))
        completed = h.all_completed(db, person_id)
    if request.args.get("format") not in (None, "", "pdf", "csv"):
        raise c.ValidationError("Choose PDF or CSV.")
    try:
        report = reports.build(person, completed, values["from"], values["to"], zone)
    except c.ValidationError as exc:
        error = str(exc)
    if report and request.args.get("format") in ("pdf", "csv"):
        extension = request.args["format"]
        data = (
            reports.pdf_bytes(report)
            if extension == "pdf"
            else reports.csv_bytes(report)
        )
        return send_file(
            BytesIO(data),
            mimetype=(
                "application/pdf" if extension == "pdf" else "text/csv; charset=utf-8"
            ),
            as_attachment=True,
            download_name=f'workout-summary-{values["from"]}-{values["to"]}.{extension}',
            max_age=0,
        )
    return render_template(
        "reports.html", person=person, values=values, report=report, error=error
    ), (400 if error and request.args else 200)


@bp.post("/settings/download-database")
def download_database():
    """Consistent verified SQLite snapshot; credentials/private settings stay outside SQLite."""
    from .administration import require_administration

    denied = require_administration()
    if denied is not None:
        return denied
    from .database_download import snapshot
    from . import APP_VERSION

    handle = snapshot(current_app.config["WORKOUT_DATA_ROOT"])
    try:
        response = send_file(
            handle,
            mimetype="application/vnd.sqlite3",
            as_attachment=True,
            download_name=f"workout-tracker-{APP_VERSION}-{w.now().date().isoformat()}.sqlite3",
            max_age=0,
        )
        response.call_on_close(handle.close)
        response.headers["Cache-Control"] = "no-store"
        return response
    except BaseException:
        handle.close()
        raise
