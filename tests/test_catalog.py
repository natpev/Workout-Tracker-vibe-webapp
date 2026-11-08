# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""Catalog tests: validated services -> locked SQLite transactions.

Only disposable migrated fixtures are used. SQL probes check ownership,
configuration constraints, stable IDs, independence and transaction rollback.
"""

import sqlite3
from unittest.mock import patch

import pytest

from workout_tracker import catalog as c
from workout_tracker.storage import database_session


def weight(**overrides):
    """Build a Weight target configuration, not an actual workout measurement."""
    return {"name": "Bench", "measurement_type": "weight", "target_sets": "3", "target_reps": "12",
            "weight_meaning": "per dumbbell", "notes": "Slow movement", **overrides}


def timed(**overrides):
    """Build a timed target; minute/second parts must become integer seconds."""
    return {"name": "Plank", "measurement_type": "time", "target_sets": "3", "minutes": "1", "seconds": "5",
            "notes": "Keep steady", **overrides}


def test_typed_configuration_identity_edit_remove_and_reorder(phase2_root):
    """Round trips retain IDs, clear incompatible fields and preserve definitions."""
    with database_session(phase2_root, write=True) as db:
        person = c.create_person(db, "Alex")
        routine = c.create_routine(db, person, "Strength")
        a = c.add_entry(db, person, routine, weight())
        b = c.add_entry(db, person, routine, timed())
        first = c.entry(db, person, routine, a)
        permanent = first["exercise_id"]
        assert first["target_reps"] == 12 and first["target_duration_seconds"] is None
        second = c.entry(db, person, routine, b)
        assert second["target_duration_seconds"] == 65 and second["target_reps"] is None
        assert second["unit"] is None
        c.update_entry(db, person, routine, a, timed(target_reps="999", weight_meaning="obsolete"))
        updated = c.entry(db, person, routine, a)
        assert updated["exercise_id"] == permanent
        assert updated["target_reps"] is None and updated["weight_meaning"] == ""
        assert updated["target_duration_seconds"] == 65
        c.update_entry(db, person, routine, a, weight(minutes="99", seconds="45"))
        assert c.entry(db, person, routine, a)["target_duration_seconds"] is None
        c.move(db, "routine_exercises", "routine_id", routine, b, "up")
        assert [row[0] for row in db.execute("SELECT id FROM routine_exercises ORDER BY position")] == [b, a]
        c.update_definition(db, person, permanent, "Renamed Bench", "rename")
        assert c.entry(db, person, routine, a)["name"] == "Renamed Bench"
        db.execute("DELETE FROM routine_exercises WHERE id=?", (a,))
        assert c.definition(db, person, permanent)["id"] == permanent
        c.update_definition(db, person, permanent, None, "archive")
        with pytest.raises(c.MissingRecord):
            c.definition(db, person, permanent)


@pytest.mark.parametrize("values", [
    weight(target_sets="0"), weight(target_sets="1.5"), weight(target_sets="-1"), weight(target_sets="1001"),
    weight(target_reps=""), weight(target_reps="0"), weight(target_reps="1.5"), weight(target_reps="10001"),
    weight(measurement_type="distance"), weight(notes="x" * 2001), weight(weight_meaning="x" * 201),
    timed(minutes="-1"), timed(minutes="0.5"), timed(minutes="bad"), timed(seconds="bad"),
    timed(seconds="-60"), timed(seconds="1.5"), timed(minutes="0", seconds="0"), timed(minutes="6000"),
])
def test_invalid_configuration_rejected_before_insert(phase2_root, values):
    """Malformed typed targets fail with no exercise definition or item inserted."""
    with database_session(phase2_root, write=True) as db:
        person = c.create_person(db, "Alex")
        routine = c.create_routine(db, person, "Routine")
        with pytest.raises(c.ValidationError):
            c.add_entry(db, person, routine, values)
        assert db.execute("SELECT count(*) FROM exercises").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM routine_exercises").fetchone()[0] == 0


@pytest.mark.parametrize("values,seconds", [(timed(minutes=0, seconds=45), 45),
                                          (timed(minutes=1, seconds=5), 65),
                                          (timed(minutes=2, seconds=0), 120)])
def test_duration_seconds_conversion(values, seconds):
    """Time targets use exact seconds and are never multiplied by three sets."""
    assert c.configure(values)[3] == seconds


def test_user_ownership_and_permanent_ids(phase2_root):
    """Services reject cross-user references; archive/reactivate never loses IDs."""
    with database_session(phase2_root, write=True) as db:
        a, b = c.create_person(db, "A"), c.create_person(db, "B")
        r = c.create_routine(db, a, "A routine")
        e = c.create_definition(db, a, "A exercise")
        other = c.create_routine(db, b, "B routine")
        for operation in (
            lambda: c.routine(db, b, r), lambda: c.definition(db, b, e),
            lambda: c.add_entry(db, b, other, weight(exercise_id=e)),
        ):
            with pytest.raises(c.MissingRecord):
                operation()
        c.update_person(db, a, "Renamed A", "rename")
        c.update_person(db, a, None, "archive")
        with pytest.raises(c.MissingRecord):
            c.person(db, a)
        assert c.person(db, a, archived=True)["id"] == a
        c.update_person(db, a, None, "reactivate")
        assert c.routine(db, a, r)["id"] == r
        assert c.definition(db, a, e)["id"] == e


@pytest.mark.parametrize("same_user", [True, False])
def test_copied_routines_are_independent_definitions_only(phase2_root, same_user):
    """Duplicate/copy changes never link routine settings or exercise identities."""
    with database_session(phase2_root, write=True) as db:
        a, b = c.create_person(db, "A"), c.create_person(db, "B")
        source = c.create_routine(db, a, "Source")
        original_item = c.add_entry(db, a, source, weight())
        original_exercise = c.entry(db, a, source, original_item)["exercise_id"]
        c.add_entry(db, a, source, timed())
        destination = a if same_user else b
        copied = c.copy_routine(db, a, source, destination, "Independent")
        items = db.execute("SELECT * FROM routine_exercises WHERE routine_id=? ORDER BY position", (copied,)).fetchall()
        assert len(items) == 2
        assert items[0]["exercise_id"] != original_exercise
        assert items[0]["person_id"] == destination
        assert items[0]["notes"] == "Slow movement"
        assert items[1]["target_duration_seconds"] == 65
        c.update_definition(db, destination, items[0]["exercise_id"], "Copy name", "rename")
        c.update_entry(db, destination, copied, items[0]["id"], timed())
        assert c.entry(db, a, source, original_item)["measurement_type"] == "weight"
        assert c.entry(db, a, source, original_item)["name"] == "Bench"
        assert not {"weight", "actual_duration_seconds", "increase_next_time"}.intersection(items[0].keys())
        db.execute("UPDATE routines SET archived=1 WHERE id=?", (source,))
        assert c.routine(db, destination, copied)["id"] == copied
        assert db.execute("SELECT count(*) FROM routines WHERE id=?", (source,)).fetchone()[0] == 1


def test_copy_rollback_is_atomic(phase2_root):
    """A mid-copy failure rolls back every copied row, not just the failing item."""
    with database_session(phase2_root, write=True) as db:
        a = c.create_person(db, "A")
        source = c.create_routine(db, a, "Source")
        c.add_entry(db, a, source, weight())
    with pytest.raises(RuntimeError):
        with database_session(phase2_root, write=True) as db:
            with patch.object(c, "create_definition", side_effect=RuntimeError("simulated copy failure")):
                c.copy_routine(db, a, source, a, "Broken copy")
    with database_session(phase2_root) as db:
        assert db.execute("SELECT count(*) FROM routines").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM exercises").fetchone()[0] == 1


@pytest.mark.parametrize("change", [
    "target_reps=NULL", "target_reps=0", "target_duration_seconds=45", "unit=NULL",
    "measurement_type='time'", "target_sets=0", "target_sets=1.5",
])
def test_database_constraints_reject_invalid_typed_rows(phase2_root, change):
    """SQL constraints defend against bypassing browser/service validation."""
    with database_session(phase2_root, write=True) as db:
        a = c.create_person(db, "A")
        r = c.create_routine(db, a, "Routine")
        item = c.add_entry(db, a, r, weight())
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(f"UPDATE routine_exercises SET {change} WHERE id=?", (item,))


def test_routine_ordering_and_exercise_archive_guard(phase2_root):
    """Ordering preserves IDs; used permanent definitions cannot be archived."""
    with database_session(phase2_root, write=True) as db:
        a = c.create_person(db, "A")
        r1, r2 = c.create_routine(db, a, "First"), c.create_routine(db, a, "Second")
        item = c.add_entry(db, a, r1, weight())
        e = c.entry(db, a, r1, item)["exercise_id"]
        c.move(db, "routines", "person_id", a, r2, "up")
        assert [row[0] for row in db.execute("SELECT id FROM routines ORDER BY position")] == [r2, r1]
        with pytest.raises(c.ValidationError):
            c.update_definition(db, a, e, None, "archive")


def test_ordering_ignores_archived_routines_without_position_collisions(phase2_root):
    """Archived rows remain retained but cannot consume an active movement step."""
    with database_session(phase2_root, write=True) as db:
        a = c.create_person(db, "A")
        r1 = c.create_routine(db, a, "First")
        removed = c.create_routine(db, a, "Archived middle")
        r2 = c.create_routine(db, a, "Last")
        db.execute("UPDATE routines SET archived=1 WHERE id=?", (removed,))
        c.move(db, "routines", "person_id", a, r2, "up")
        assert [row[0] for row in db.execute("SELECT id FROM routines WHERE archived=0 ORDER BY position")] == [r2, r1]
        assert db.execute("SELECT count(*) FROM routines WHERE id=?", (removed,)).fetchone()[0] == 1
