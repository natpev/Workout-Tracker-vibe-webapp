# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""Phase 1 integration tests invoked by pytest.

Every database is a disposable tmp_path fixture, never configured household data.
Tests exercise CLI -> storage and browser -> Flask -> read-only SQLite flows.
"""

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
from unittest.mock import patch

from click.testing import CliRunner
import pytest

from workout_tracker import APP_VERSION, create_app
from workout_tracker.__main__ import main
from workout_tracker.storage import (
    REPOSITORY_ROOT, StorageError, initialize_storage, inspect_storage,
)


@pytest.fixture
def storage(tmp_path):
    """Initialize only an isolated new temporary path and return its location."""
    root = tmp_path / "storage"
    initialize_storage(root)
    return root


def database_path(root):
    """Read this test's manifest to locate its disposable database."""
    manifest = json.loads((root / "config" / "active.json").read_text())
    return root / "data" / manifest["database"]


def snapshot(root):
    """Capture file names and bytes so unexpected copies or writes fail tests."""
    # Phase 5 may append diagnostics; all database/config/archive bytes remain protected.
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.rglob("*") if path.is_file() and "logs" not in path.relative_to(root).parts}


def test_explicit_confirmation_required(tmp_path):
    """Missing confirmation must leave even the proposed directory absent."""
    root = tmp_path / "uninitialized"
    result = CliRunner().invoke(main, ["init-storage", "--data-root", str(root)])
    assert result.exit_code != 0
    assert "confirmation" in result.output or "confirm-new-storage" in result.output
    assert not root.exists()


def test_cli_initialize_and_check(tmp_path):
    """The documented explicit installation and read-only check both work."""
    root = tmp_path / "new-storage"
    runner = CliRunner()
    result = runner.invoke(main, ["init-storage", "--data-root", str(root), "--confirm-new-storage"])
    assert result.exit_code == 0, result.output
    before = snapshot(root)
    result = runner.invoke(main, ["check-storage", "--data-root", str(root)])
    assert result.exit_code == 0, result.output
    assert "schema version 1" in result.output
    assert snapshot(root) == before
    assert root.stat().st_mode & 0o777 == 0o700
    assert database_path(root).stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("existing", ["empty", "initialized", "orphan"])
def test_initialization_never_reuses_existing_directory(tmp_path, existing):
    """An empty directory or lost manifest must never authorize replacement."""
    root = tmp_path / "existing"
    if existing == "empty":
        root.mkdir()
    else:
        initialize_storage(root)
        if existing == "orphan":
            (root / "config" / "active.json").unlink()
    before = snapshot(root)
    with pytest.raises(StorageError):
        initialize_storage(root)
    assert snapshot(root) == before


@pytest.mark.parametrize("value", [None, "relative", str(REPOSITORY_ROOT), str(REPOSITORY_ROOT / "data")])
def test_invalid_configuration_creates_nothing(value):
    """Implicit, relative, and repository storage selections fail before IO."""
    with pytest.raises(StorageError):
        create_app({"WORKOUT_DATA_ROOT": value})


def test_missing_tree_is_not_initialized(tmp_path):
    """Normal application startup never acts as a first-install command."""
    root = tmp_path / "missing"
    with pytest.raises(StorageError):
        create_app({"WORKOUT_DATA_ROOT": root})
    assert not root.exists()


@pytest.mark.parametrize("damage", [
    "missing-manifest", "bad-json", "duplicate-key", "traversal", "wrong-id",
    "missing-db", "corrupt-db", "old-version", "new-version", "wrong-app",
    "missing-table", "changed-table", "extra-table", "wrong-migration", "unreadable",
    "journal", "wal", "shm", "wal-header",
])
def test_unsafe_storage_is_refused_without_changes(storage, damage):
    """Damaged selection/schema/access is a failure, never a reset or migration."""
    manifest = storage / "config" / "active.json"
    db = database_path(storage)
    if damage == "missing-manifest":
        manifest.unlink()
    elif damage == "bad-json":
        manifest.write_text("{")
    elif damage == "duplicate-key":
        manifest.write_text('{"database":"a","database":"b","storage_id":"c"}')
    elif damage in ("traversal", "wrong-id"):
        selection = json.loads(manifest.read_text())
        selection["database" if damage == "traversal" else "storage_id"] = (
            "../../outside.sqlite3" if damage == "traversal" else "a" * 32
        )
        manifest.write_text(json.dumps(selection))
    elif damage == "missing-db":
        db.unlink()
    elif damage == "corrupt-db":
        db.write_bytes(b"not a SQLite database")
    elif damage in ("journal", "wal", "shm"):
        Path(str(db) + "-" + damage).write_bytes(b"preserve investigation evidence")
    elif damage == "wal-header":
        connection = sqlite3.connect(db)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.close()
    elif damage == "unreadable":
        db.chmod(0)
    else:
        statements = {
            "old-version": "PRAGMA user_version=0",
            "new-version": "PRAGMA user_version=999",
            "wrong-app": "PRAGMA application_id=0",
            "missing-table": "DROP TABLE schema_migrations",
            "changed-table": "ALTER TABLE storage_metadata ADD COLUMN unexpected TEXT",
            "extra-table": "CREATE TABLE unexpected (id INTEGER)",
            "wrong-migration": "UPDATE schema_migrations SET name='unknown'",
        }
        with sqlite3.connect(db) as connection:
            connection.execute(statements[damage])
    # Unreadable files cannot be hashed; restore permissions only after the check.
    before = None if damage == "unreadable" else snapshot(storage)
    try:
        with pytest.raises(StorageError):
            create_app({"WORKOUT_DATA_ROOT": storage})
    finally:
        if damage == "unreadable":
            db.chmod(0o600)
    if before is not None:
        assert snapshot(storage) == before


@pytest.mark.parametrize("target", ["root", "manifest", "database", "directory"])
def test_symlinks_refused(storage, tmp_path, target):
    """Even links pointing to valid storage must not redirect application reads."""
    if target == "root":
        link = tmp_path / "linked-storage"
        link.symlink_to(storage, target_is_directory=True)
        selected = link
    else:
        path = {"manifest": storage / "config" / "active.json",
                "database": database_path(storage), "directory": storage / "backups"}[target]
        moved = tmp_path / "moved"
        path.rename(moved)
        path.symlink_to(moved, target_is_directory=target == "directory")
        selected = storage
    with pytest.raises(StorageError):
        inspect_storage(selected)


def test_readonly_connection_configuration(storage):
    """Each inspected connection enables foreign keys and rejects writes."""
    original = sqlite3.connect
    observations = []

    class CheckedConnection(sqlite3.Connection):
        """Inspect actual connection protections before the application closes it."""

        def close(self):
            """Record safety flags and prove a write is rejected, then release IO."""
            observations.append((self.execute("PRAGMA foreign_keys").fetchone()[0],
                                 self.execute("PRAGMA query_only").fetchone()[0],
                                 self.execute("PRAGMA trusted_schema").fetchone()[0]))
            with pytest.raises(sqlite3.OperationalError, match="readonly"):
                self.execute("DELETE FROM storage_metadata")
            super().close()

    def tracked_connect(*args, **kwargs):
        """Use a real connection while recording safety settings before close."""
        return original(*args, **kwargs, factory=CheckedConnection)

    with patch("workout_tracker.storage.sqlite3.connect", side_effect=tracked_connect):
        inspect_storage(storage)
    assert observations == [(1, 1, 0)]
    # A direct SQLite mode=ro probe demonstrates that the chosen URI cannot write.
    connection = original(database_path(storage).as_uri() + "?mode=ro", uri=True)
    try:
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            connection.execute("DELETE FROM storage_metadata")
    finally:
        connection.close()


def test_startup_and_requests_do_not_change_storage(storage):
    """Repeated factories simulate process replacement against retained storage."""
    before = snapshot(storage)
    for _ in range(2):
        app = create_app({"WORKOUT_DATA_ROOT": storage, "TESTING": True})
        client = app.test_client()
        response = client.get("/")
        assert response.status_code == 200
        assert b"SHAMEFULLY VIBE-CODED" in response.data
        assert b"Workout tracking is not available yet" in response.data
        assert client.get("/health/ready").json == {
            "status": "ready", "app_version": APP_VERSION, "schema_version": 1,
        }
        for asset in ("style.css", "theme.js"):
            assert client.get("/static/" + asset).status_code == 200
        assert client.post("/").status_code == 405
        assert client.get("/", headers={"Host": "attacker.example"}).status_code == 400
        assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
        assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert snapshot(storage) == before


def test_readiness_detects_storage_loss_without_leaking_paths(storage):
    """A running process reports 503 if storage disappears, with no replacement."""
    client = create_app({"WORKOUT_DATA_ROOT": storage, "TESTING": True}).test_client()
    database_path(storage).unlink()
    before = snapshot(storage)
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json == {"status": "unavailable"}
    assert str(storage).encode() not in response.data
    assert snapshot(storage) == before


def test_interrupted_initialization_is_preserved(tmp_path):
    """Simulated publication failure leaves evidence and prevents blind retry."""
    root = tmp_path / "interrupted"
    with patch("workout_tracker.storage.os.link", side_effect=OSError("simulated disk failure")):
        with pytest.raises(StorageError):
            initialize_storage(root)
    assert not (root / "config" / "active.json").exists()
    before = snapshot(root)
    with pytest.raises(StorageError):
        initialize_storage(root)
    with pytest.raises(StorageError):
        inspect_storage(root)
    assert snapshot(root) == before


def test_competing_first_install_commands_do_not_overwrite(tmp_path):
    """Only one operator process may reserve the same new storage directory."""
    root = tmp_path / "competing"

    def attempt():
        """Attempt one isolated first installation and report refusal separately."""
        try:
            return initialize_storage(root)
        except StorageError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    assert sum(result is not None for result in results) == 1
    assert inspect_storage(root)["schema_version"] == 1
    assert len(list((root / "data").glob("*.sqlite3"))) == 1
