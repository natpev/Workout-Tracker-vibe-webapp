# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""Flask application factory called by tests, Flask, and Gunicorn.

Configuration selects external storage. Browser GET requests read readiness and
render Jinja templates; Phase 1 has no data-changing HTTP endpoints or sessions.
"""

import os

from flask import Flask, jsonify, render_template

from .storage import StorageError, inspect_storage

APP_VERSION = "0.1.0"


def create_app(test_config=None):
    """Validate storage before serving; overrides let tests use disposable paths."""
    app = Flask(__name__)
    app.config.from_mapping(
        WORKOUT_DATA_ROOT=os.environ.get("WORKOUT_DATA_ROOT"),
        TRUSTED_HOSTS=os.environ.get("WORKOUT_TRUSTED_HOSTS", "localhost,127.0.0.1,[::1]").split(","),
        MAX_CONTENT_LENGTH=16 * 1024,
    )
    if test_config:
        app.config.update(test_config)
    inspect_storage(app.config["WORKOUT_DATA_ROOT"])

    @app.get("/")
    def home():
        """Render the foundation shell; it reads no workout or person records."""
        return render_template("home.html", version=APP_VERSION)

    @app.get("/health/ready")
    def readiness():
        """Recheck storage and return 503 on failure without leaking paths."""
        try:
            details = inspect_storage(app.config["WORKOUT_DATA_ROOT"])
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
