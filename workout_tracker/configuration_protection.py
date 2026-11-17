# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Reusable, read-only semantic checks around isolated candidate migrations.

Capture configured values, never substitute generic 3×12 defaults. Future deliberate
changes must name the exact identity/field/old/new value and a nonempty reason.
"""
import sqlite3
from .storage import StorageError


def capture(db):
    """Map permanent configuration identities to semantic values across old schemas."""
    from .measurements import LEGACY

    old_factory = db.row_factory
    db.row_factory = sqlite3.Row
    result = {}
    try:
        names = {
            r[0]
            for r in db.execute("SELECT name FROM sqlite_schema WHERE type='table'")
        }
        for table in ("exercise_defaults", "routine_exercises", "exercises"):
            if table not in names:
                continue
            for stored in db.execute(f"SELECT * FROM {table}"):
                row = dict(stored)
                identity = row.get("id", row.get("exercise_id"))
                config = dict(row)
                if "measurement_type" in row:
                    config.pop("measurement_type")
                    config["capabilities"] = row.get("capabilities") or LEGACY.get(
                        row["measurement_type"]
                    )
                    config["weight_basis"] = row.get("weight_basis", "not_configured")
                result[(table, identity)] = config
        return result
    finally:
        db.row_factory = old_factory


def verify(before, after, authorized=None):
    """Reject every unexpected edit; an allowance is an exact documented transition."""
    authorized = authorized or {}
    consumed = set()
    for identity, fields in before.items():
        if identity not in after:
            raise StorageError("Migration removed a protected exercise configuration.")
        for field, value in fields.items():
            actual = after[identity].get(field)
            key = (*identity, field)
            if actual != value:
                change = authorized.get(key)
                if (
                    not change
                    or change[:2] != (value, actual)
                    or len(change) != 3
                    or not isinstance(change[2], str)
                    or not change[2].strip()
                ):
                    raise StorageError(
                        "Migration changed protected Exercise Library defaults or routine settings without authorization."
                    )
                consumed.add(key)
    if consumed != set(authorized):
        raise StorageError(
            "An authorized configuration transition did not match its declared change."
        )
