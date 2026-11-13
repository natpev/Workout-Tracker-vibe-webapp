# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Candidate-only schema-13 preservation using real archived workout/audit fixtures."""
import json
from unittest.mock import patch
import pytest
from workout_tracker.storage import database_session, inspect_storage, StorageError
from workout_tracker.migrations import migrate_storage
from test_basis import basis_data


def test_unified_candidate_preserves_legacy_cells_and_never_invents_sets(basis_data):
    """Every old value remains exact; duration compatibility has no fabricated set rows."""
    root = basis_data["root"]
    migrate_storage(root, 12)
    source = (
        root
        / "data"
        / json.loads((root / "config/active.json").read_text())["database"]
    )
    original = source.read_bytes()
    with database_session(root) as db:
        tables = [
            r[0]
            for r in db.execute(
                "SELECT name FROM sqlite_schema WHERE type='table' AND substr(name,1,7)!='sqlite_'"
            )
        ]
        columns = {
            t: [r[1] for r in db.execute(f"PRAGMA table_info({t})")] for t in tables
        }
        before = {
            t: [tuple(r) for r in db.execute(f"SELECT * FROM {t} ORDER BY 1")]
            for t in tables
        }
    migrate_storage(root, 13)
    assert (
        source.read_bytes() == original
        and inspect_storage(root)["schema_version"] == 13
    )
    with database_session(root) as db:
        for table in tables:
            projection = ",".join('"' + c + '"' for c in columns[table])
            rows = [
                tuple(r)
                for r in db.execute(f"SELECT {projection} FROM {table} ORDER BY 1")
            ]
            if table == "schema_migrations":
                rows = rows[:-1]
            assert rows == before[table]
        for table in ("workout_entries", "historical_entries"):
            assert not db.execute(
                f"SELECT 1 FROM {table} WHERE capabilities IS NOT NULL"
            ).fetchone()
        for table in ("workout_sets", "historical_sets", "body_weights"):
            assert not db.execute(f"SELECT 1 FROM {table}").fetchone()
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert not db.execute("PRAGMA foreign_key_check").fetchall()


def test_unified_failed_candidate_retains_original_selection(basis_data):
    """An upgrade exception cannot activate a partially rebuilt schema."""
    root = basis_data["root"]
    migrate_storage(root, 12)
    manifest = (root / "config/active.json").read_bytes()
    original = root / "data" / json.loads(manifest)["database"]
    data = original.read_bytes()
    with patch(
        "workout_tracker.unified_schema.upgrade_unified",
        side_effect=RuntimeError("Synthetic failure"),
    ), pytest.raises(StorageError):
        migrate_storage(root, 13)
    assert (
        root / "config/active.json"
    ).read_bytes() == manifest and original.read_bytes() == data


@pytest.mark.parametrize("fault", ["schema", "old_value", "missing_audit"])
def test_candidate_validation_refuses_corruption_before_activation(basis_data, fault):
    """Successful DDL is insufficient: object/cell/logical corruption must retain source."""
    from workout_tracker.unified_schema import upgrade_unified

    root = basis_data["root"]
    migrate_storage(root, 12)
    manifest = (root / "config/active.json").read_bytes()
    source = root / "data" / json.loads(manifest)["database"]
    before = source.read_bytes()

    def corrupt(db):
        upgrade_unified(db)
        if fault == "schema":
            db.execute("DROP TRIGGER body_weight_audit_update_protected")
        elif fault == "old_value":
            db.execute(
                "UPDATE exercises SET name='Corrupted synthetic name' WHERE id=?",
                (basis_data["e"],),
            )
        else:
            db.execute(
                "INSERT INTO body_weights(id,person_id,weight_milli_lb,measured_at,source,created_at,updated_at) VALUES (?,?,?,?,?,?,?)",
                (
                    "f" * 32,
                    basis_data["a"],
                    200000,
                    "2020-01-01T00:00:00+00:00",
                    "manual",
                    "2020-01-01T00:00:00+00:00",
                    "2020-01-01T00:00:00+00:00",
                ),
            )

    with patch(
        "workout_tracker.unified_schema.upgrade_unified", side_effect=corrupt
    ), pytest.raises(StorageError):
        migrate_storage(root, 13)
    assert (
        source.read_bytes() == before
        and (root / "config/active.json").read_bytes() == manifest
    )
    assert inspect_storage(root)["schema_version"] == 12
