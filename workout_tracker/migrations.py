# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""Explicit schema-1 -> schema-2 candidate migration called only by the CLI.

Reads the original SQLite database and copies it with SQLite's backup API.
Only the new candidate receives DDL. Fully validated candidates are selected by
atomic manifest replacement under the same root lock used by every app request.
No backup/restore/scheduler interface or automatic startup migration lives here.
"""

import hashlib
import json
import os
import sqlite3
from uuid import uuid4

from .schema import PHASE2_TABLES
from .storage import StorageError, _inspect_unlocked, _sync_directory, storage_lock


def _digest(path):
    """Hash original bytes without writing them; detect unsupported external edits."""
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _upgrade_candidate(connection):
    """Apply Phase 2 DDL only to a brand-new copied database in one transaction."""
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA synchronous=FULL")
    connection.execute("BEGIN IMMEDIATE")
    try:
        for statement in PHASE2_TABLES.values():
            connection.execute(statement)
        connection.execute("INSERT INTO schema_migrations VALUES (2, 'people_and_routines')")
        connection.execute("PRAGMA user_version=2")
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def _write_manifest(path, selection):
    """Write a distinct private manifest and sync bytes before publication."""
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w") as handle:
        json.dump(selection, handle)
        handle.flush()
        os.fsync(handle.fileno())


def migrate_storage(value):
    """Upgrade explicitly; keep original and failed candidates for inspection.

    This supports exactly the known metadata-only v1 schema. A compatible v2
    invocation is a read-only no-op. The caller must stop external tools and
    workers not following our locking protocol before requesting maintenance.
    """
    with storage_lock(value, exclusive=True, nonblocking=True) as root:
        source = _inspect_unlocked(root)
        if source["schema_version"] == 2:
            return {"changed": False, "schema_version": 2}
        original = source["database"]
        original_hash = _digest(original)
        active = root / "config" / "active.json"
        original_selection = json.loads(active.read_text())
        token = uuid4().hex
        candidate_name = f"schema-2-{source['storage_id']}-{token}.sqlite3"
        candidate = root / "data" / candidate_name
        pending = root / "config" / f"selection-{token}.pending"
        archive = root / "archives" / f"selection-before-{token}.json"
        switched = False
        try:
            with candidate.open("xb"):
                candidate.chmod(0o600)
            source_connection = sqlite3.connect(original.as_uri() + "?mode=ro", uri=True)
            target_connection = sqlite3.connect(candidate.as_uri() + "?mode=rw", uri=True)
            try:
                source_connection.backup(target_connection)
                _upgrade_candidate(target_connection)
                # Domain tables must be empty; metadata identity and prior
                # migration rows must be copied exactly, not reconstructed.
                for name in PHASE2_TABLES:
                    if target_connection.execute(f"SELECT count(*) FROM {name}").fetchone()[0] != 0:
                        raise StorageError("The migrated domain tables are unexpectedly nonempty.")
                for name in ("storage_metadata", "schema_migrations"):
                    before = source_connection.execute(f"SELECT * FROM {name} ORDER BY 1").fetchall()
                    after = target_connection.execute(f"SELECT * FROM {name} ORDER BY 1").fetchall()
                    if name == "schema_migrations":
                        after = [row for row in after if row[0] != 2]
                    if before != after:
                        raise StorageError("Migration changed pre-existing logical data.")
            finally:
                target_connection.close()
                source_connection.close()
            with candidate.open("rb") as handle:
                os.fsync(handle.fileno())
            _sync_directory(root / "data")
            selection = {"database": candidate_name, "storage_id": source["storage_id"]}
            # Reuse the exact startup validator against an isolated manifest view
            # without selecting the candidate for application connections yet.
            _validate_candidate(root, candidate, selection)
            if _digest(original) != original_hash or json.loads(active.read_text()) != original_selection:
                raise StorageError("Original storage changed during maintenance; activation refused.")
            os.link(active, archive)
            _sync_directory(root / "archives")
            _write_manifest(pending, selection)
            _sync_directory(root / "config")
            os.replace(pending, active)
            switched = True
            _sync_directory(root / "config")
        except Exception as error:
            if switched:
                # Restore selection after a post-switch durability error. Both
                # database files and the archived original manifest stay intact.
                rollback = root / "config" / f"rollback-{token}.pending"
                try:
                    os.link(archive, rollback)
                    os.replace(rollback, active)
                    _sync_directory(root / "config")
                except OSError as rollback_error:
                    raise StorageError("Activation durability is uncertain; stop and inspect both preserved databases.") from rollback_error
            raise StorageError("Migration failed; original selection retained and candidate preserved for inspection.") from error
        return {"changed": True, "schema_version": 2}


def _validate_candidate(root, candidate, selection):
    """Validate full candidate using the same checks as startup, before switching.

    _inspect_unlocked accepts an explicit candidate selection only for this
    maintenance call. The public inspect_storage always reads active.json.
    """
    details = _inspect_unlocked(root, selection=selection)
    if details["schema_version"] != 2 or details["database"] != candidate:
        raise StorageError("Candidate validation did not select schema 2.")
