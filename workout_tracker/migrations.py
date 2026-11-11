# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Explicit known-schema -> target-2-through-11 candidate migration called only by the CLI.

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
from .workout_schema import WORKOUT_TABLES, WORKOUT_OBJECTS
from .history_schema import HISTORY_TABLES, HISTORY_OBJECTS
from .storage import StorageError, _inspect_unlocked, _sync_directory, storage_lock, load_signing_key


def _digest(path):
    """Hash original bytes without writing them; detect unsupported external edits."""
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _upgrade_candidate(connection, target_version=2):
    """Add the requested known schema only to a copied candidate in one transaction."""
    connection.execute("PRAGMA foreign_keys=" + ("OFF" if target_version >= 5 else "ON"))
    connection.execute("PRAGMA synchronous=FULL")
    connection.execute("BEGIN IMMEDIATE")
    try:
        current = connection.execute("PRAGMA user_version").fetchone()[0]
        if current == 1:
            for statement in PHASE2_TABLES.values():
                connection.execute(statement)
            connection.execute("INSERT INTO schema_migrations VALUES (2, 'people_and_routines')")
        if current < 3 and target_version >= 3:
            for statement in WORKOUT_OBJECTS.values():
                connection.execute(statement)
            connection.execute("INSERT INTO schema_migrations VALUES (3, 'workout_tracking')")
        if current < 4 and target_version >= 4:
            for statement in HISTORY_OBJECTS.values():
                connection.execute(statement)
            # Original completed rows are not touched; the registry only links
            # them for future correction ownership. Counts are checked below.
            connection.execute("INSERT INTO workout_registry(id,person_id,live_session_id) SELECT id,person_id,id FROM workout_sessions WHERE status='completed'")
            connection.execute("INSERT INTO schema_migrations VALUES (4, 'history_and_corrections')")
        if current < 5 and target_version >= 5:
            from .library_schema import upgrade_library
            upgrade_library(connection)
            connection.execute("INSERT INTO schema_migrations VALUES (5, 'shared_exercise_library')")
        if current < 6 and target_version >= 6:
            from .deletion_schema import upgrade_deletion
            upgrade_deletion(connection)
            connection.execute("INSERT INTO schema_migrations VALUES (6, 'permanent_deletion')")
        if current < 7 and target_version >= 7:
            from .defaults_schema import upgrade_defaults
            upgrade_defaults(connection)
            connection.execute("INSERT INTO schema_migrations VALUES (7, 'exercise_defaults')")
        if current < 8 and target_version >= 8:
            from .combined_schema import upgrade_combined
            upgrade_combined(connection)
            connection.execute("INSERT INTO schema_migrations VALUES (8, 'combined_weight_duration')")
        if current < 9 and target_version >= 9:
            from .basis_schema import upgrade_basis
            upgrade_basis(connection)
            connection.execute("INSERT INTO schema_migrations VALUES (9, 'weight_basis_transition')")
        if current < 10 and target_version >= 10:
            from .final_schema import upgrade_final
            upgrade_final(connection)
            connection.execute("INSERT INTO schema_migrations VALUES (10, 'actual_repetitions_and_permanent_basis')")
        if current < 11 and target_version >= 11:
            from .interface_schema import upgrade_interface
            upgrade_interface(connection)
            connection.execute("INSERT INTO schema_migrations VALUES (11, 'exercise_interface_and_icons')")
        connection.execute(f"PRAGMA user_version={target_version}")
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


def _migrate_storage(value, target_version=2):
    """Upgrade explicitly; keep original and failed candidates for inspection.

    Known schemas 1–10 may upgrade to supported targets through 11. A matching target
    invocation is a read-only no-op; downgrades and unknown versions are refused. The caller must stop external tools and
    workers not following our locking protocol before requesting maintenance.
    """
    with storage_lock(value, exclusive=True, nonblocking=True) as root:
        source = _inspect_unlocked(root)
        if target_version not in (2, 3, 4, 5, 6, 7, 8, 9, 10, 11) or source["schema_version"] > target_version:
            raise StorageError("Unsupported migration target; downgrade is not permitted.")
        if source["schema_version"] == target_version:
            return {"changed": False, "schema_version": target_version}
        original = source["database"]
        original_hash = _digest(original)
        active = root / "config" / "active.json"
        original_selection = json.loads(active.read_text())
        token = uuid4().hex
        candidate_name = f"schema-{target_version}-{source['storage_id']}-{token}.sqlite3"
        candidate = root / "data" / candidate_name
        pending = root / "config" / f"selection-{token}.pending"
        archive = root / "archives" / f"selection-before-{token}.json"
        switched = False
        try:
            with candidate.open("xb"):
                candidate.chmod(0o600)
            source_connection = sqlite3.connect(original.as_uri() + "?mode=ro", uri=True)
            target_connection = None
            try:
                target_connection = sqlite3.connect(candidate.as_uri() + "?mode=rw", uri=True)
                source_connection.backup(target_connection)
                if target_version == 2:
                    _upgrade_candidate(target_connection)
                else:
                    _upgrade_candidate(target_connection, target_version)
                # Compare every pre-existing table, row and NULL exactly. Counts
                # alone could miss a changed value or ownership relationship.
                existing = ["storage_metadata", "schema_migrations"]
                if source["schema_version"] >= 2:
                    existing += list(PHASE2_TABLES)
                if source["schema_version"] >= 3:
                    existing += list(WORKOUT_TABLES)
                if source["schema_version"] >= 4:
                    existing += list(HISTORY_TABLES)
                if source['schema_version'] >= 7:
                    existing.append('exercise_defaults')
                if source["schema_version"] >= 9:
                    existing += ["basis_transitions", "basis_assignments"]
                if source["schema_version"]>=11:
                    existing += ["exercise_icons", "exercise_weight_basis"]
                for name in existing:
                    # New metadata columns are allowed; every original column/cell
                    # must remain exactly identical, including NULL and audit JSON.
                    columns=','.join('"'+r[1]+'"' for r in source_connection.execute(f'PRAGMA table_info({name})'))
                    before = source_connection.execute(f"SELECT {columns} FROM {name} ORDER BY 1").fetchall()
                    after = target_connection.execute(f"SELECT {columns} FROM {name} ORDER BY 1").fetchall()
                    if name == "schema_migrations":
                        after = [row for row in after if row[0] <= source["schema_version"]]
                    if target_version >= 10 and source['schema_version']<10 and name == 'routine_exercises':
                        # Library convention wins for future configurations only.
                        # Every other original cell remains identical.
                        basis_index=[r[1] for r in source_connection.execute(f'PRAGMA table_info({name})')].index('weight_basis') if source['schema_version']>=9 else None
                        if basis_index is not None:
                            before=[tuple(v for i,v in enumerate(row) if i!=basis_index) for row in before]
                            after=[tuple(v for i,v in enumerate(row) if i!=basis_index) for row in after]
                    if before != after:
                        raise StorageError("Migration changed pre-existing logical data.")
                if target_version>=9 and source['schema_version']<9:
                    for table in ('routine_exercises','exercise_defaults','workout_entries','historical_entries'):
                        if target_connection.execute(f"SELECT 1 FROM {table} WHERE weight_basis!='not_configured'").fetchone():
                            raise StorageError('Migration unexpectedly classified an exercise.')
                    for table in ('basis_transitions','basis_assignments'):
                        if target_connection.execute(f'SELECT 1 FROM {table}').fetchone():
                            raise StorageError('Migration unexpectedly created a conversion.')
                if target_version >= 10 and source['schema_version'] >= 9:
                    # Verify effective values too: immutable source cells alone
                    # would not detect applying a conversion overlay twice.
                    from .history import all_completed
                    source_connection.row_factory=sqlite3.Row
                    target_connection.row_factory=sqlite3.Row
                    for person, in source_connection.execute('SELECT id FROM people'):
                        before_history=all_completed(source_connection,person)
                        after_history=all_completed(target_connection,person)
                        if len(before_history)!=len(after_history):
                            raise StorageError('Migration changed completed history.')
                        for (old_parent,old_rows),(new_parent,new_rows) in zip(before_history,after_history):
                            projected=[{key:row[key] for key in old} for old,row in zip(old_rows,new_rows)]
                            if old_parent!=new_parent or len(old_rows)!=len(new_rows) or old_rows!=projected:
                                raise StorageError('Migration changed effective historical values.')
                    source_connection.row_factory=None
                    target_connection.row_factory=None
                added = list(WORKOUT_TABLES) if source["schema_version"] < 3 and target_version >= 3 else []
                if source["schema_version"] < 4 and target_version >= 4:
                    added += [name for name in HISTORY_TABLES if name != 'workout_registry']
                    links = target_connection.execute("SELECT id,person_id,live_session_id,historical_session_id FROM workout_registry ORDER BY id").fetchall()
                    expected_links = target_connection.execute("SELECT id,person_id,id,NULL FROM workout_sessions WHERE status='completed' ORDER BY id").fetchall()
                    if links != expected_links:
                        raise StorageError("Completed-workout registry consistency failed.")
                if source["schema_version"] == 1:
                    added += list(PHASE2_TABLES)
                for name in added:
                    if target_connection.execute(f"SELECT count(*) FROM {name}").fetchone()[0] != 0:
                        raise StorageError("New tables are unexpectedly nonempty.")
            finally:
                if target_connection is not None:
                    target_connection.close()
                source_connection.close()
            with candidate.open("rb") as handle:
                os.fsync(handle.fileno())
            _sync_directory(root / "data")
            selection = {"database": candidate_name, "storage_id": source["storage_id"]}
            # Reuse the exact startup validator against an isolated manifest view
            # without selecting the candidate for application connections yet.
            _validate_candidate(root, candidate, selection)
            # Validate prepared snapshots, chronology and every correction chain.
            from .maintenance import logical_check
            logical_check(candidate, target_version)
            if _digest(original) != original_hash or json.loads(active.read_text()) != original_selection:
                raise StorageError("Original storage changed during maintenance; activation refused.")
            # Session signing material is created only by explicit maintenance,
            # never by startup. Existing configured keys are never overwritten.
            key = root / "config" / "session.key"
            if not os.path.lexists(key):
                descriptor = os.open(key, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                with os.fdopen(descriptor, "w") as handle:
                    handle.write(os.urandom(32).hex())
                    handle.flush()
                    os.fsync(handle.fileno())
            load_signing_key(root)
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
            raise StorageError("Migration failed; original selection retained and candidate preserved for inspection. " + (str(error) if isinstance(error, StorageError) else "")) from error
        return {"changed": True, "schema_version": target_version}


def _validate_candidate(root, candidate, selection):
    """Validate full candidate using the same checks as startup, before switching.

    _inspect_unlocked accepts an explicit candidate selection only for this
    maintenance call. The public inspect_storage always reads active.json.
    """
    details = _inspect_unlocked(root, selection=selection)
    if details["schema_version"] not in (2, 3, 4, 5, 6, 7, 8, 9, 10, 11) or details["database"] != candidate:
        raise StorageError("Candidate schema validation failed.")


def migrate_storage(value, target_version=2):
    """Record meaningful explicit upgrade outcomes, but keep matching-version no-ops read-only."""
    # Read-only compatibility checks must retain their original no-write behavior.
    from .storage import inspect_storage
    from .diagnostics import emit
    try:
        compatible=inspect_storage(value)['schema_version']==target_version
    except StorageError as error:
        emit(value,'ERROR','Database','Explicit migration refused unsafe source storage',error=error)
        raise
    if compatible:
        return _migrate_storage(value,target_version)
    emit(value,'INFO','Database','Explicit candidate migration requested')
    try:
        result=_migrate_storage(value,target_version)
    except Exception as error:
        emit(value,'ERROR','Database','Candidate migration failed; inspect retained sources',error=error)
        raise
    emit(value,'INFO','Database','Candidate migration completed; original database preserved')
    return result
