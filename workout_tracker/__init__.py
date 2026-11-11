# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Flask application factory called by tests, Flask, and Gunicorn.

Configuration selects external storage. Browser GET requests read readiness and
render Jinja templates. Management and workout blueprints use CSRF-protected
forms. Explicit schema 3 enables workout recording; schema 4 enables history,
local charts, manual completion and append-only corrections. Phase 5 adds
explicit recovery controls, external operations state and private diagnostics.
"""

import os

from flask import Flask, jsonify, render_template, redirect, url_for
from werkzeug.exceptions import SecurityError

from .storage import StorageError, inspect_storage, load_signing_key

APP_VERSION = "0.14.0"
# Release metadata describes the desired full-feature schema, not a request to
# upgrade storage. Updaters can read it without constructing an app or opening SQL.
TARGET_SCHEMA_VERSION = 10


def create_app(test_config=None):
    """Validate storage before serving; overrides let tests use disposable paths."""
    app = Flask(__name__)
    app.config.from_mapping(
        WORKOUT_DATA_ROOT=os.environ.get("WORKOUT_DATA_ROOT"),
        TRUSTED_HOSTS=os.environ.get("WORKOUT_TRUSTED_HOSTS", "localhost,127.0.0.1,[::1]").split(","),
        MAX_CONTENT_LENGTH=512 * 1024,
        SECRET_KEY=os.environ.get("WORKOUT_SECRET_KEY"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",

    )
    from .presentation import clock,timestamp,workout_timestamp
    app.jinja_env.filters.update(clock=clock,timestamp=timestamp,workout_timestamp=workout_timestamp)
    if test_config:
        app.config.update(test_config)
    from .diagnostics import emit
    try:
        initial = inspect_storage(app.config["WORKOUT_DATA_ROOT"])
    except StorageError as error:
        emit(app.config["WORKOUT_DATA_ROOT"], "ERROR", "Database", "Application startup refused unsafe storage", error=error)
        raise
    if initial["schema_version"] >= 2 and not app.config["SECRET_KEY"]:
        # Signing keys are provisioned by explicit migration, never startup.
        # Do not follow a key symlink or print its private bytes in an error.
        app.config["SECRET_KEY"] = load_signing_key(app.config["WORKOUT_DATA_ROOT"])
    from .views import bp
    from .catalog import ValidationError, MissingRecord
    app.register_blueprint(bp)
    from .deletion_views import bp as deletion_bp
    app.register_blueprint(deletion_bp)
    from .update_views import bp as update_bp
    app.register_blueprint(update_bp)
    from .workout_views import bp as workout_bp
    from .workouts import configured_timezone
    app.config["WORKOUT_TIMEZONE"] = configured_timezone(app.config.get("WORKOUT_TIMEZONE") or os.environ.get("WORKOUT_TIMEZONE"))
    app.register_blueprint(workout_bp)
    from .history_views import bp as history_bp
    app.register_blueprint(history_bp)
    from .settings_views import bp as settings_bp
    from .diagnostics import emit
    app.register_blueprint(settings_bp)
    emit(app.config["WORKOUT_DATA_ROOT"], "INFO", "Application", "Application worker started")
    import atexit
    def shutdown_event():
        """Record orderly process exit when the external tree still exists (not SIGKILL)."""
        from pathlib import Path
        if Path(app.config["WORKOUT_DATA_ROOT"]).is_dir():
            emit(app.config["WORKOUT_DATA_ROOT"], "INFO", "Application", "Application worker stopped")
    if not app.testing:
        atexit.register(shutdown_event)

    @app.context_processor
    def version_information():
        """Read active schema for display; report unavailable rather than guessing.

        A failed recovery page must remain usable even if its selected database
        is damaged. Version strings have one application source of truth.
        """
        try:
            schema = inspect_storage(app.config['WORKOUT_DATA_ROOT'])['schema_version']
        except StorageError:
            schema = 'Unavailable'
        return dict(application_version=APP_VERSION, active_schema_version=schema)

    @app.context_processor
    def appearance_helpers():
        """Read appearance lazily once per request; corrupt preferences never block recovery UI."""
        from flask import g
        from . import preferences
        def accent_for(identity):
            """Return a safe CSS palette name, not arbitrary browser-supplied CSS."""
            if not hasattr(g, 'person_colors'):
                try: g.person_colors=preferences.colors(app.config['WORKOUT_DATA_ROOT'])
                except StorageError: g.person_colors={}
            return g.person_colors.get(identity,'blue')
        return dict(accent_for=accent_for,accent_palette=preferences.PALETTE)

    @app.errorhandler(ValidationError)
    def invalid_form(error):
        """Render actionable validation errors; no partial transaction commits."""
        return render_template("error.html", message=str(error)), 400

    @app.errorhandler(MissingRecord)
    def missing_record(error):
        """Hide records outside the requested ownership boundary."""
        return render_template("error.html", message=str(error)), 404

    @app.errorhandler(StorageError)
    def unavailable_storage(error):
        """Expose a safe operational message without filenames or SQL payloads."""
        emit(app.config["WORKOUT_DATA_ROOT"], "ERROR", "Database", "Storage verification failed; request transaction not committed", error=error)
        app.logger.error("Storage unavailable; request transaction not committed.")
        return render_template("error.html", message="Storage unavailable. Check storage, complete any explicit upgrade, and restart the application before editing."), 503

    @app.errorhandler(400)
    @app.errorhandler(409)
    def request_error(error):
        """Present CSRF/conflict errors with status preserved and escaped text."""
        if isinstance(error, SecurityError):
            # An untrusted Host has no URL adapter; do not render navigation.
            return "Invalid host header.", 400
        return render_template("error.html", message=error.description), error.code


    def log_exception(exc_info):
        """Replace Flask's raw exception-text dump with bounded protected technical frames."""
        emit(app.config["WORKOUT_DATA_ROOT"], "ERROR", "Application", "Unexpected request failure", error=exc_info[1])
        app.logger.error("Unexpected request failure; inspect protected diagnostic event identifiers.")
    app.log_exception=log_exception

    @app.errorhandler(500)
    def unexpected_error(error):
        """Keep request bodies/tracebacks out of responses; protect technical frames on disk."""
        emit(app.config["WORKOUT_DATA_ROOT"], "ERROR", "Application", "Unexpected application exception", error=getattr(error, "original_exception", error))
        return render_template("error.html", message="Unexpected application error. Inspect Settings logs or contact the server operator."), 500

    @app.get("/")
    def home():
        """Render the foundation shell; it reads no workout or person records."""
        if inspect_storage(app.config["WORKOUT_DATA_ROOT"])["schema_version"] >= 2:
            return redirect(url_for("manage.people"))
        return render_template("home.html", version=APP_VERSION)

    @app.get("/health/ready")
    def readiness():
        """Recheck storage and return 503 on failure without leaking paths."""
        try:
            details = inspect_storage(app.config["WORKOUT_DATA_ROOT"])
            if details["schema_version"] >= 2 and not app.secret_key:
                raise StorageError("Restart required after explicit migration.")
        except StorageError:
            emit(app.config["WORKOUT_DATA_ROOT"], "ERROR", "Database", "Storage readiness verification failed; writes remain unavailable")
            app.logger.error("Storage readiness verification failed; writes remain unavailable.")
            return jsonify(status="unavailable"), 503
        return jsonify(status="ready", app_version=APP_VERSION,
                       schema_version=details["schema_version"])

    @app.after_request
    def secure_response(response):
        """Restrict browser resources to local assets and prevent page framing."""
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response

    return app
