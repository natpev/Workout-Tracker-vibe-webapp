# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""Candidate-migration safety tests; pytest uses only disposable tmp_path data.

Calls CLI -> migration -> SQLite backup/DDL/validation -> atomic selection.
Fault injection proves that failed candidates never replace the original data.
"""

import hashlib
import json
import os
import sqlite3
from unittest.mock import patch

from click.testing import CliRunner
import pytest

from workout_tracker.__main__ import main
from workout_tracker.migrations import migrate_storage
from workout_tracker.storage import StorageError, initialize_storage, inspect_storage, storage_lock


@pytest.fixture
def legacy(tmp_path):
    """Return a new disposable Phase 1 tree and its original selected database."""
    root = tmp_path / "legacy"
    initialize_storage(root)
    manifest = root / "config" / "active.json"
    db = root / "data" / json.loads(manifest.read_text())["database"]
    return root, manifest, db


def tree_bytes(root):
    """Record all persisted bytes to detect unexpected compatible-update writes."""
    # Phase 5 may append diagnostics; all database/config/archive bytes remain protected.
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file() and "logs" not in p.relative_to(root).parts}


def test_candidate_migration_preserves_original_and_metadata(legacy):
    """Success retains original bytes/mtime and activates only a verified schema 2."""
    root, manifest, original = legacy
    before, selection, modified = original.read_bytes(), manifest.read_bytes(), original.stat().st_mtime_ns
    result = migrate_storage(root)
    assert result == {"changed": True, "schema_version": 2}
    assert original.read_bytes() == before
    assert original.stat().st_mtime_ns == modified
    assert inspect_storage(root)["schema_version"] == 2
    selected = root / "data" / json.loads(manifest.read_text())["database"]
    assert selected != original
    assert list((root / "archives").glob("selection-before-*.json"))[0].read_bytes() == selection
    with sqlite3.connect(selected) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute("SELECT * FROM schema_migrations ORDER BY version").fetchall() == [
            (1, "foundation"), (2, "people_and_routines")]
        assert connection.execute("SELECT count(*) FROM people").fetchone() == (0,)
        assert connection.execute("PRAGMA user_version").fetchone() == (2,)


@pytest.mark.parametrize("fault", ["ddl", "invalid-candidate", "publication", "post-switch-sync"])
def test_failed_upgrade_keeps_original_selection(legacy, fault):
    """DDL, validation, activation and durability failures preserve the original."""
    root, manifest, original = legacy
    original_bytes, selection = original.read_bytes(), manifest.read_bytes()
    from workout_tracker import migrations
    upgrade = migrations._upgrade_candidate
    sync = migrations._sync_directory
    config_syncs = 0

    def corrupt_candidate(connection):
        """Corrupt only candidate identity so real startup validation rejects it."""
        upgrade(connection)
        connection.execute("UPDATE storage_metadata SET storage_id='invalid'")
        connection.commit()

    def fail_after_switch(path):
        """Fail only the post-publication config sync, allowing rollback sync."""
        nonlocal config_syncs
        if path == root / "config":
            config_syncs += 1
            if config_syncs == 2:
                raise OSError("simulated durability failure")
        sync(path)

    patches = {
        "ddl": patch.object(migrations, "_upgrade_candidate", side_effect=sqlite3.OperationalError("DDL failure")),
        "invalid-candidate": patch.object(migrations, "_upgrade_candidate", side_effect=corrupt_candidate),
        "publication": patch.object(migrations.os, "replace", side_effect=OSError("activation failure")),
        "post-switch-sync": patch.object(migrations, "_sync_directory", side_effect=fail_after_switch),
    }
    with patches[fault], pytest.raises(StorageError, match="original selection retained"):
        migrate_storage(root)
    assert original.read_bytes() == original_bytes
    assert manifest.read_bytes() == selection
    assert inspect_storage(root)["schema_version"] == 1
    assert len(list((root / "data").glob("*.sqlite3"))) == 2


def test_compatible_upgrade_and_startup_never_copy_or_modify(legacy):
    """Repeating an explicit upgrade on schema 2 is a verified read-only no-op."""
    root, _, _ = legacy
    migrate_storage(root)
    before = tree_bytes(root)
    assert migrate_storage(root)["changed"] is False
    inspect_storage(root)
    assert tree_bytes(root) == before


def test_migration_refuses_active_app_lock(legacy):
    """Existing request connections must drain before exclusive maintenance."""
    root, _, _ = legacy
    before = tree_bytes(root)
    with storage_lock(root), pytest.raises(StorageError, match="busy"):
        migrate_storage(root)
    assert tree_bytes(root) == before


@pytest.mark.parametrize("damage", ["missing", "corrupt", "unknown", "sidecar"])
def test_unsafe_source_is_never_copied_or_reinitialized(legacy, damage):
    """Only a known healthy source schema can enter candidate creation."""
    root, _, original = legacy
    if damage == "missing":
        original.unlink()
    elif damage == "corrupt":
        original.write_bytes(b"corrupt fixture")
    elif damage == "sidecar":
        original.with_name(original.name + "-wal").write_bytes(b"evidence")
    else:
        with sqlite3.connect(original) as connection:
            connection.execute("PRAGMA user_version=42")
    before = tree_bytes(root)
    with pytest.raises(StorageError):
        migrate_storage(root)
    assert tree_bytes(root) == before


def test_explicit_cli_confirmation_and_success(legacy):
    """Operator confirmation is mandatory; the documented command then succeeds."""
    root, _, _ = legacy
    runner = CliRunner()
    before = tree_bytes(root)
    assert runner.invoke(main, ["migrate-storage", "--data-root", str(root)]).exit_code != 0
    assert tree_bytes(root) == before
    result = runner.invoke(main, ["migrate-storage", "--data-root", str(root), "--confirm-upgrade"])
    assert result.exit_code == 0, result.output
    assert "original preserved" in result.output
    assert "Schema 3 verified" in result.output
    assert inspect_storage(root)["schema_version"] == 3


def test_schema3_migration_preserves_populated_catalog_and_nulls(phase2_root):
    """Upgrade populated Phase 2 through a separate candidate without changing its bytes."""
    from workout_tracker import catalog as c
    from workout_tracker.storage import database_session
    root=phase2_root
    with database_session(root,write=True) as db:
        person=c.create_person(db,'Migration fixture')
        routine=c.create_routine(db,person,'Source')
        c.add_entry(db,person,routine,dict(name='Weight',measurement_type='weight',target_sets='3',target_reps='12'))
        c.add_entry(db,person,routine,dict(name='Time',measurement_type='time',target_sets='3',minutes='0',seconds='45'))
        before_rows=[tuple(row) for row in db.execute('SELECT * FROM routine_exercises ORDER BY id')]
    original=root/'data'/json.loads((root/'config'/'active.json').read_text())['database']
    original_bytes=original.read_bytes(); modified=original.stat().st_mtime_ns
    assert migrate_storage(root,target_version=3)=={'changed':True,'schema_version':3}
    assert original.read_bytes()==original_bytes and original.stat().st_mtime_ns==modified
    with database_session(root,minimum_version=3) as db:
        assert [tuple(row) for row in db.execute('SELECT * FROM routine_exercises ORDER BY id')]==before_rows
        assert db.execute('SELECT count(*) FROM workout_entries').fetchone()[0]==0
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]
    before=tree_bytes(root)
    assert migrate_storage(root,target_version=3)['changed'] is False
    assert tree_bytes(root)==before


@pytest.mark.parametrize('fault',['ddl','data-change','activation','post-switch'])
def test_schema3_failure_retains_populated_original(phase2_root,fault):
    """Data equality validation and activation rollback protect populated schema 2."""
    from workout_tracker import migrations, catalog as c
    from workout_tracker.storage import database_session
    root=phase2_root
    with database_session(root,write=True) as db:
        c.create_person(db,'Must survive')
    selection=(root/'config'/'active.json').read_bytes()
    source=root/'data'/json.loads(selection)['database']; original=source.read_bytes()
    upgrade=migrations._upgrade_candidate; sync=migrations._sync_directory
    count=0

    def change_data(connection,target_version):
        """Inject logically wrong but structurally valid data into the candidate only."""
        upgrade(connection,target_version)
        connection.execute("UPDATE people SET name='Changed'");connection.commit()

    def failed_sync(path):
        """Fail one sync after publication and allow selection rollback to complete."""
        nonlocal count
        if path==root/'config':
            count+=1
            if count==2:
                raise OSError('simulated sync failure')
        sync(path)

    patches={
        'ddl':patch.object(migrations,'_upgrade_candidate',side_effect=sqlite3.OperationalError('DDL failure')),
        'data-change':patch.object(migrations,'_upgrade_candidate',side_effect=change_data),
        'activation':patch.object(migrations.os,'replace',side_effect=OSError('activation failure')),
        'post-switch':patch.object(migrations,'_sync_directory',side_effect=failed_sync),
    }
    with patches[fault],pytest.raises(StorageError):
        migrate_storage(root,target_version=3)
    assert source.read_bytes()==original
    assert (root/'config'/'active.json').read_bytes()==selection
    assert inspect_storage(root)['schema_version']==2


def test_schema4_migration_preserves_completed_and_active_workouts(phase3_root):
    """All original rows/NULLs and the schema-3 file survive; registry links completed only."""
    from workout_tracker import catalog as c, workouts as w
    from workout_tracker.storage import database_session
    root=phase3_root
    with database_session(root,write=True) as db:
        person=c.create_person(db,'Migration fixture');routine=c.create_routine(db,person,'Source')
        c.add_entry(db,person,routine,dict(name='Weight',measurement_type='weight',target_sets='3',target_reps='12'))
        c.add_entry(db,person,routine,dict(name='Time',measurement_type='time',target_sets='3',minutes='0',seconds='45'))
        identity,_=w.start(db,person,routine,'UTC');entry=w.entries(db,person,identity)[0]
        w.finish(db,person,identity,dict(revision='0',entry_id=entry['id'],current_position='0',weight='0'))
        draft,_=w.start(db,person,routine,'UTC')
        before={name:[tuple(row) for row in db.execute(f'SELECT * FROM {name} ORDER BY id')] for name in ('people','exercises','routines','routine_exercises','workout_sessions','workout_entries')}
    original=root/'data'/json.loads((root/'config'/'active.json').read_text())['database']
    content=original.read_bytes();modified=original.stat().st_mtime_ns
    assert migrate_storage(root,target_version=4)=={'changed':True,'schema_version':4}
    assert original.read_bytes()==content and original.stat().st_mtime_ns==modified
    with database_session(root,minimum_version=4) as db:
        for name,rows in before.items():
            assert [tuple(row) for row in db.execute(f'SELECT * FROM {name} ORDER BY id')]==rows
        assert [tuple(row) for row in db.execute('SELECT id,person_id,live_session_id FROM workout_registry')]==[(identity,person,identity)]
        assert w.active(db,person)['id']==draft
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]
    before_files=tree_bytes(root)
    assert migrate_storage(root,target_version=4)['changed'] is False
    assert tree_bytes(root)==before_files


@pytest.mark.parametrize('fault',['ddl','data-change','activation','post-switch'])
def test_schema4_failure_keeps_selected_schema3(phase3_root,fault):
    """Candidate failure and activation rollback never overwrite or select over schema 3."""
    from workout_tracker import migrations, catalog as c
    from workout_tracker.storage import database_session
    root=phase3_root
    with database_session(root,write=True) as db:
        c.create_person(db,'Must survive')
    selection=(root/'config'/'active.json').read_bytes()
    original=root/'data'/json.loads(selection)['database'];content=original.read_bytes()
    upgrade=migrations._upgrade_candidate;sync=migrations._sync_directory;count=0

    def change_data(connection,target):
        """Change copied logical data while leaving its structural schema valid."""
        upgrade(connection,target)
        connection.execute("UPDATE people SET name='wrong'");connection.commit()

    def fail_sync(path):
        """Fail after activation once; rollback can then sync the original selection."""
        nonlocal count
        if path==root/'config':
            count+=1
            if count==2: raise OSError('simulated durability error')
        sync(path)

    patches={
        'ddl':patch.object(migrations,'_upgrade_candidate',side_effect=sqlite3.OperationalError('DDL')),
        'data-change':patch.object(migrations,'_upgrade_candidate',side_effect=change_data),
        'activation':patch.object(migrations.os,'replace',side_effect=OSError('activation')),
        'post-switch':patch.object(migrations,'_sync_directory',side_effect=fail_sync),
    }
    with patches[fault],pytest.raises(StorageError): migrate_storage(root,target_version=4)
    assert original.read_bytes()==content
    assert (root/'config'/'active.json').read_bytes()==selection
    assert inspect_storage(root)['schema_version']==3
