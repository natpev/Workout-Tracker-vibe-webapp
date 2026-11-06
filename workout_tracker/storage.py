# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""Storage safeguards called by the CLI and Flask factory.

Only explicit initialization writes a new, external storage directory. Startup
reads its manifest and SQLite metadata; it never creates or repairs storage.
This module uses pathlib, SQLite, and POSIX file syncing, not a workout database.
"""

import json
import os
from pathlib import Path
import re
import sqlite3
from uuid import uuid4

SCHEMA_VERSION = 1
APPLICATION_ID = 0x5754524B
REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
DIRECTORIES = ("data", "archives", "backups", "config", "logs")
TABLES = {
    "storage_metadata": """CREATE TABLE storage_metadata (
        singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
        storage_id TEXT NOT NULL UNIQUE
    ) STRICT""",
    "schema_migrations": """CREATE TABLE schema_migrations (
        version INTEGER PRIMARY KEY,
        name TEXT NOT NULL
    ) STRICT""",
}


class StorageError(RuntimeError):
    """Report unsafe storage without exposing private filesystem paths to HTTP."""


def storage_root(value):
    """Validate an absolute external path without creating it or following links.

    Configuration comes from the CLI or environment. Reject links even when they
    point inside storage so an operator cannot accidentally select another tree.
    """
    if not value or not Path(value).is_absolute():
        raise StorageError("Set WORKOUT_DATA_ROOT to an absolute external directory.")
    root = Path(os.path.abspath(value))
    if root == REPOSITORY_ROOT or REPOSITORY_ROOT in root.parents:
        raise StorageError("Storage must be outside the repository.")
    for part in (root, *root.parents):
        if part.is_symlink():
            raise StorageError("Storage paths must not contain symbolic links.")
    return root


def _regular_file(path):
    """Require an existing ordinary file; never create a missing database."""
    if path.is_symlink() or not path.is_file():
        raise StorageError("A required storage file is missing or unsafe.")


def _sync_directory(path):
    """Persist directory entries after first-install files are published on Linux."""
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _unique_object(pairs):
    """Reject duplicate manifest keys rather than silently selecting the last one."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise StorageError("The active database manifest has duplicate fields.")
        result[key] = value
    return result


def inspect_storage(value):
    """Read and validate selected storage, returning its ID and schema version.

    Flask calls this before serving and for readiness checks. SQLite is opened
    with mode=ro, so a missing file cannot become an empty replacement. Every
    connection enables foreign keys and rejects SQL writes. No backups, schema
    changes, repairs, or active-file switching happen here.
    """
    root = storage_root(value)
    try:
        for name in DIRECTORIES:
            directory = root / name
            if directory.is_symlink() or not directory.is_dir():
                raise StorageError("The persistent storage layout is incomplete or unsafe.")
        manifest_path = root / "config" / "active.json"
        _regular_file(manifest_path)
        if manifest_path.stat().st_size > 4096:
            raise StorageError("The active database manifest is too large.")
        manifest = json.loads(manifest_path.read_text(), object_pairs_hook=_unique_object)
        if not isinstance(manifest, dict) or set(manifest) != {"database", "storage_id"}:
            raise StorageError("The active database manifest has invalid fields.")
        storage_id = manifest["storage_id"]
        if not isinstance(storage_id, str) or not re.fullmatch(r"[0-9a-f]{32}", storage_id):
            raise StorageError("The active database identity is invalid.")
        filename = manifest["database"]
        if filename != f"schema-1-{storage_id}.sqlite3":
            raise StorageError("The active database selection is invalid or unsupported.")
        database = root / "data" / filename
        _regular_file(database)
        # Phase 1 uses rollback journals. A sidecar means interrupted or foreign
        # storage: refuse it rather than recovering/modifying anything at startup.
        for suffix in ("-journal", "-wal", "-shm"):
            if os.path.lexists(str(database) + suffix):
                raise StorageError("Database sidecars require operator investigation.")
        connection = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True, timeout=5)
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA trusted_schema = OFF")
            connection.execute("PRAGMA query_only = ON")
            if connection.execute("PRAGMA application_id").fetchone()[0] != APPLICATION_ID:
                raise StorageError("The database belongs to another application.")
            if connection.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
                raise StorageError("Unsupported schema version; automatic migration is disabled.")
            if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                raise StorageError("Database integrity verification failed.")
            if connection.execute("PRAGMA foreign_key_check").fetchall():
                raise StorageError("Database foreign key verification failed.")
            # Validate actual DDL, not just a version marker that could be wrong.
            objects = dict(connection.execute(
                "SELECT name, sql FROM sqlite_schema WHERE substr(name, 1, 7) != 'sqlite_'"
            ))
            if objects != TABLES:
                raise StorageError("The database schema does not match this release.")
            if connection.execute("SELECT * FROM storage_metadata").fetchall() != [(1, storage_id)]:
                raise StorageError("The database identity does not match its manifest.")
            if connection.execute("SELECT * FROM schema_migrations").fetchall() != [(1, "foundation")]:
                raise StorageError("The database migration record is unsupported.")
        finally:
            connection.close()
    except (OSError, ValueError, sqlite3.Error) as error:
        raise StorageError("Storage cannot be read or verified; no replacement was created.") from error
    return {"storage_id": storage_id, "schema_version": SCHEMA_VERSION}


def initialize_storage(value):
    """Create a brand-new storage tree for an explicitly confirmed first install.

    The CLI obtains confirmation before calling this function. Exclusive mkdir
    reserves the entire tree: even an empty pre-existing directory is refused.
    Failures deliberately leave evidence in place and never delete or retry over
    it. There is no migration, restore, or overwrite path in Phase 1.
    """
    root = storage_root(value)
    try:
        root.mkdir(mode=0o700, exist_ok=False)
        for name in DIRECTORIES:
            (root / name).mkdir(mode=0o700)
        storage_id = uuid4().hex
        filename = f"schema-1-{storage_id}.sqlite3"
        database = root / "data" / filename
        # Reserve the filename exclusively with private permissions before SQLite
        # opens it. Only this newly reserved file may be initialized.
        with database.open("xb"):
            database.chmod(0o600)
        connection = sqlite3.connect(database)
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA synchronous = FULL")
            connection.execute("PRAGMA journal_mode = DELETE")
            with connection:
                for statement in TABLES.values():
                    connection.execute(statement)
                connection.execute("INSERT INTO storage_metadata VALUES (1, ?)", (storage_id,))
                connection.execute("INSERT INTO schema_migrations VALUES (1, 'foundation')")
                connection.execute(f"PRAGMA application_id = {APPLICATION_ID}")
                connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        finally:
            connection.close()
        with database.open("rb") as handle:
            os.fsync(handle.fileno())
        _sync_directory(root / "data")
        # The active selection is published only after the database is durable.
        # A hard link publishes the complete file atomically and refuses overwrite.
        pending = root / "config" / "active.pending"
        descriptor = os.open(pending, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(descriptor, "w") as handle:
            json.dump({"database": filename, "storage_id": storage_id}, handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(pending, root / "config" / "active.json")
        pending.unlink()
        _sync_directory(root / "config")
        _sync_directory(root)
        _sync_directory(root.parent)
    except (OSError, sqlite3.Error) as error:
        raise StorageError(
            "Initialization refused or interrupted. Inspect existing storage; nothing was overwritten."
        ) from error
    return inspect_storage(root)
