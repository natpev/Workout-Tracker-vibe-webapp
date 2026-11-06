# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""Flask application factory called by tests, Flask, and Gunicorn.

Configuration selects external storage. Browser GET requests read readiness and
render Jinja templates. Management and workout blueprints use CSRF-protected
forms; only explicitly migrated schema 3 enables workout recording. Later
history exploration and recovery interfaces remain absent.
"""

import os

from flask import Flask, jsonify, render_template, redirect, url_for
from werkzeug.exceptions import SecurityError

from .storage import StorageError, inspect_storage, load_signing_key

APP_VERSION = "0.3.0"


def create_app(test_config=None):
    """Validate storage before serving; overrides let tests use disposable paths."""
    app = Flask(__name__)
    app.config.from_mapping(
        WORKOUT_DATA_ROOT=os.environ.get("WORKOUT_DATA_ROOT"),
        TRUSTED_HOSTS=os.environ.get("WORKOUT_TRUSTED_HOSTS", "localhost,127.0.0.1,[::1]").split(","),
        MAX_CONTENT_LENGTH=16 * 1024,
        SECRET_KEY=os.environ.get("WORKOUT_SECRET_KEY"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",

    )
    if test_config:
        app.config.update(test_config)
    initial = inspect_storage(app.config["WORKOUT_DATA_ROOT"])
    if initial["schema_version"] >= 2 and not app.config["SECRET_KEY"]:
        # Signing keys are provisioned by explicit migration, never startup.
        # Do not follow a key symlink or print its private bytes in an error.
        app.config["SECRET_KEY"] = load_signing_key(app.config["WORKOUT_DATA_ROOT"])
    from .views import bp
    from .catalog import ValidationError, MissingRecord
    app.register_blueprint(bp)
    from .workout_views import bp as workout_bp
    from .workouts import configured_timezone
    app.config["WORKOUT_TIMEZONE"] = configured_timezone(app.config.get("WORKOUT_TIMEZONE") or os.environ.get("WORKOUT_TIMEZONE"))
    app.register_blueprint(workout_bp)

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
