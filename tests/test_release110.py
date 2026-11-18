# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""v1.1 synthetic data: automatic sets, immutable settings, separate Ego attempts and precision."""
from uuid import uuid4
from unittest.mock import patch
from decimal import Decimal
import json
import pytest
from workout_tracker import (
    catalog as c,
    workouts as w,
    measurements as m,
    history as h,
    ego_lifts as e,
    garmin as g,
    body_weight as b,
)
from workout_tracker.storage import (
    initialize_storage,
    database_session,
    inspect_storage,
    StorageError,
)
from workout_tracker.migrations import migrate_storage
from workout_tracker.maintenance import logical_check_connection, backup, restore
from workout_tracker.configuration_protection import capture, verify


@pytest.fixture
def root110(tmp_path):
    """Explicitly migrate only newly created, disposable storage."""
    root = tmp_path / "release110"
    initialize_storage(root)
    migrate_storage(root, 14)
    return root


def setup(db, caps=3, sets=3):
    """One person/routine/exercise with intentionally non-generic defaults."""
    person = c.create_person(db, "Synthetic A")
    routine = c.create_routine(db, person, "Routine")
    item = c.add_entry(
        db,
        person,
        routine,
        dict(
            name="Example",
            measurement_type="flex",
            capabilities=caps,
            target_sets=str(sets),
            target_reps="15",
            seconds="45",
            weight_basis="total",
        ),
    )
    exercise = c.entry(db, person, routine, item)["exercise_id"]
    return person, routine, exercise


def fields(db, person, sid, **extra):
    """Read current revision and snapshot ID, as the live browser does."""
    row = w.entries(db, person, sid)[0]
    return dict(
        automatic_sets="yes",
        entry_id=row["id"],
        revision=str(w.session(db, person, sid)["revision"]),
        current_position="0",
        **extra,
    )


@pytest.mark.parametrize("caps", range(1, 8))
def test_automatic_all_capabilities_zero_skips_and_nulls(root110, caps):
    """Only measured/Done sets count; untouched blanks become NULL skips on completion."""
    with database_session(root110, write=True) as db:
        person, routine, _ = setup(db, caps)
        sid, _ = w.start(db, person, routine, "UTC")
        raw = dict(weight="0" if caps & 1 else "", increase="1")
        if caps & 2:
            raw["reps_0"] = "0"
        if caps & 4:
            raw["seconds_0"] = "90"
        if caps == 1:
            raw["done_0"] = "yes"
        w.update(db, person, sid, fields(db, person, sid, **raw))
        rows = w.entries(db, person, sid)
        assert rows[0]["sets"][0]["status"] == "completed"
        assert rows[0]["sets"][1]["status"] == "incomplete"
        saved = [dict(r) for r in rows[0]["sets"]]
        w.finish(db, person, sid, fields(db, person, sid, **raw))
        rows = w.entries(db, person, sid)
        assert rows[0]["sets"][0] == saved[0]
        assert (
            rows[0]["sets"][1:]
            == [dict(status="skipped", actual_reps=None, actual_duration_seconds=None)]
            * 2
        )
        assert rows[0]["actual_weight_tenths_lb"] == (0 if caps & 1 else None)
        assert w.count_performed(rows) == 1
        logical_check_connection(db, 14)


@pytest.mark.parametrize("caps", [1, 3, 5, 6, 7])
def test_partial_sets_rejected_and_drafts_resume_without_false_completion(
    root110, caps
):
    """Partial inputs/Done are durable, but cannot silently become a completed/skipped set."""
    with database_session(root110, write=True) as db:
        person, routine, _ = setup(db, caps)
        sid, _ = w.start(db, person, routine, "UTC")
        raw = (
            dict(done_0="yes")
            if caps == 1
            else dict(seconds_0="20") if caps & 4 else dict(reps_0="12")
        )
        w.update(db, person, sid, fields(db, person, sid, **raw))
        assert w.entries(db, person, sid)[0]["sets"][0]["status"] == "incomplete"
    with pytest.raises(c.ValidationError):
        with database_session(root110, write=True) as db:
            w.finish(db, person, sid, fields(db, person, sid, **raw))
    with database_session(root110) as db:
        assert w.session(db, person, sid)["status"] == "draft"
        assert w.entries(db, person, sid)[0]["sets"][0]["status"] == "incomplete"
        if caps == 1:
            assert db.execute("SELECT done FROM workout_set_checks").fetchone()[0] == 1


@pytest.mark.parametrize("caps", [1, 3, 5, 7])
def test_shared_weight_without_performed_sets_is_not_a_lift(root110, caps):
    """A typed weight alone cannot count; all-skipped confirmation still gates the transaction."""
    with database_session(root110, write=True) as db:
        person, routine, _ = setup(db, caps)
        sid, _ = w.start(db, person, routine, "UTC")
    with pytest.raises(w.AllSkipped):
        with database_session(root110, write=True) as db:
            w.finish(
                db, person, sid, fields(db, person, sid, weight="40", increase="1")
            )
    with database_session(root110, write=True) as db:
        w.finish(
            db,
            person,
            sid,
            fields(
                db, person, sid, weight="40", increase="1", confirm_all_skipped="yes"
            ),
        )
        row = w.entries(db, person, sid)[0]
        assert (
            row["actual_weight_tenths_lb"] is None and row["increase_next_time"] is None
        )
        assert w.count_performed([row]) == 0
        logical_check_connection(db, 14)


def test_next_back_checkpoint_does_not_require_populated_sets(root110):
    """Next can acknowledge blank sets, but only Finish gives them skipped status."""
    with database_session(root110, write=True) as db:
        person, routine, _ = setup(db)
        c.add_entry(
            db,
            person,
            routine,
            dict(
                name="Second",
                measurement_type="flex",
                capabilities=4,
                target_sets="2",
                seconds="30",
            ),
        )
        sid, _ = w.start(db, person, routine, "UTC")
        raw = fields(db, person, sid)
        raw.update(current_position="1", navigation_action="next")
        w.update(db, person, sid, raw)
        assert w.session(db, person, sid)["current_position"] == 1
        assert all(
            r["status"] == "incomplete" for r in w.entries(db, person, sid)[0]["sets"]
        )
        second = w.entries(db, person, sid)[1]
        w.update(
            db,
            person,
            sid,
            dict(
                raw,
                entry_id=second["id"],
                revision="1",
                current_position="0",
                navigation_action="back",
            ),
        )
        assert w.session(db, person, sid)["current_position"] == 1


def test_migration_preserves_custom_configurations_and_rounds_garmin_audited(tmp_path):
    """Current values, IDs, NULLs and old audits survive; only authorized precision changes."""
    root = tmp_path / "old"
    initialize_storage(root)
    migrate_storage(root, 13)
    with database_session(root, write=True) as db:
        person, routine, exercise = setup(db)
        other = c.create_person(db, "Other")
        for index, (sets, reps, caps) in enumerate(
            ((2, 15, 3), (3, 12, 3), (4, 8, 3), (2, 15, 4), (2, 15, 7))
        ):
            c.add_entry(
                db,
                person,
                routine,
                dict(
                    name=f"Custom {index}",
                    measurement_type="flex",
                    capabilities=caps,
                    target_sets=str(sets),
                    target_reps=str(reps),
                    seconds="65",
                    notes="Preserve exactly",
                    weight_basis="per_side",
                ),
            )
        copied = c.copy_routine(db, person, routine, other, "Independent")
        custom = db.execute(
            "SELECT id FROM routine_exercises WHERE routine_id=? ORDER BY position LIMIT 1",
            (copied,),
        ).fetchone()[0]
        c.update_entry(
            db,
            other,
            copied,
            custom,
            dict(
                measurement_type="flex",
                capabilities=3,
                target_sets="4",
                target_reps="8",
                weight_basis="total",
                notes="Person B only",
            ),
        )
        configured = capture(db)
        b.manual(
            db, person, dict(date="2020-01-01", time="08:00", weight="220.462"), "UTC"
        )
        g.import_weights(
            db,
            person,
            [
                dict(
                    measured_at="2020-01-01T09:00:00.000000+00:00",
                    weight_milli_lb=220462,
                    source_value='{"unit":"g","value":"100000"}',
                )
            ],
        )
        old_audits = [
            tuple(r) for r in db.execute("SELECT * FROM body_weight_audit ORDER BY id")
        ]
    original = (
        root
        / "data"
        / json.loads((root / "config/active.json").read_text())["database"]
    )
    before = original.read_bytes()
    migrate_storage(root, 14)
    assert original.read_bytes() == before
    with database_session(root) as db:
        verify(configured, capture(db))
        rows = [
            dict(r) for r in db.execute("SELECT * FROM body_weights ORDER BY source")
        ]
        assert (
            rows[0]["source"] == "garmin"
            and rows[0]["weight_milli_lb"] == 220500
            and rows[0]["revision"] == 1
        )
        assert rows[1]["source"] == "manual" and rows[1]["weight_milli_lb"] == 220462
        for audit in old_audits:
            assert (
                tuple(
                    db.execute(
                        "SELECT * FROM body_weight_audit WHERE id=?", (audit[0],)
                    ).fetchone()
                )
                == audit
            )
        logical_check_connection(db, 14)


@pytest.mark.parametrize("table", ["exercise_defaults", "routine_exercises"])
def test_unauthorized_candidate_settings_reset_is_rejected(tmp_path, table):
    """A plausible 3×12 reset cannot pass just because integrity/foreign keys remain valid."""
    from workout_tracker import migrations

    root = tmp_path / "old"
    initialize_storage(root)
    migrate_storage(root, 13)
    with database_session(root, write=True) as db:
        person, routine, exercise = setup(db, sets=2)
    original = (
        root
        / "data"
        / json.loads((root / "config/active.json").read_text())["database"]
    )
    before = original.read_bytes()
    selection = (root / "config/active.json").read_bytes()
    upgrade = migrations._upgrade_candidate

    def reset(db, target_version):
        """Inject an otherwise-valid unauthorized library reset after the actual migration."""
        upgrade(db, target_version)
        db.execute(
            f"UPDATE {table} SET target_sets=3,target_reps=12 WHERE exercise_id=?",
            (exercise,),
        )
        db.commit()

    with patch.object(migrations, "_upgrade_candidate", side_effect=reset):
        with pytest.raises(StorageError, match="protected"):
            migrate_storage(root, 14)
    assert (
        original.read_bytes() == before
        and (root / "config/active.json").read_bytes() == selection
    )
    assert len(list((root / "data").glob("schema-14-*"))) == 1


def test_explicit_semantic_change_allowance_is_narrow_and_verified():
    """Future authorized migrations must identify exact old/new values and their reason."""
    before = {("exercise_defaults", "permanent"): dict(target_sets=2, target_reps=15)}
    after = {("exercise_defaults", "permanent"): dict(target_sets=3, target_reps=15)}
    verify(
        before,
        after,
        {
            ("exercise_defaults", "permanent", "target_sets"): (
                2,
                3,
                "Explicitly approved change",
            )
        },
    )
    with pytest.raises(StorageError):
        verify(
            before,
            after,
            {("exercise_defaults", "permanent", "target_sets"): (2, 3, "")},
        )
    with pytest.raises(StorageError):
        verify(
            before,
            {("exercise_defaults", "permanent"): dict(target_sets=3, target_reps=12)},
            {
                ("exercise_defaults", "permanent", "target_sets"): (
                    2,
                    3,
                    "Explicitly approved change",
                )
            },
        )


@pytest.mark.parametrize(
    "pounds,expected", [("100.05", 100100), ("100.04", 100000), ("100.15", 100200)]
)
def test_garmin_rounds_once_from_source_half_up(pounds, expected):
    """Nearest tenth uses original grams, not a rounded intermediate thousandth."""
    grams = Decimal(pounds) * Decimal("453.59237")
    raw = '[{"timestampGMT":1577865600000,"weight":' + str(grams) + "}]"
    assert g.decoded_weights(raw)[0]["weight_milli_lb"] == expected


def test_ego_identity_idempotence_person_isolation_corrections_and_records(root110):
    """Attempts/audits are independent from normal workouts, totals, defaults and other people."""
    with database_session(root110, write=True) as db:
        person, routine, exercise = setup(db)
        other = c.create_person(db, "Other")
        protected = capture(db)
        raw = dict(weight="40.99", repetitions="6", submission_id=uuid4().hex)
        identity = e.save(db, person, exercise, raw)
        assert e.save(db, person, exercise, raw) == identity
        assert e.record(db, person, identity)["weight_tenths_lb"] == 409
        assert not e.history(db, other, exercise)
        with pytest.raises(c.MissingRecord):
            e.record(db, other, identity)
        with pytest.raises(c.ValidationError):
            e.correct(db, person, identity, dict(raw, revision="0"))
        e.correct(
            db,
            person,
            identity,
            dict(weight="50", repetitions="1", confirm="yes", revision="0"),
        )
        with pytest.raises(w.RevisionConflict):
            e.correct(
                db,
                person,
                identity,
                dict(weight="20", repetitions="1", confirm="yes", revision="0"),
            )
        records = e.records(e.history(db, person, exercise))
        assert (
            records[0]["estimate"] == 50 and records[0]["heaviest"]["repetitions"] == 1
        )
        verify(protected, capture(db))
        assert h.all_completed(db, person) == []
        assert db.execute("SELECT count(*) FROM workout_sessions").fetchone()[0] == 0
        e.correct(
            db, person, identity, dict(action="delete", confirm="yes", revision="1")
        )
        assert not e.history(db, person, exercise)
        assert db.execute("SELECT count(*) FROM ego_lift_audit").fetchone()[0] == 3
        logical_check_connection(db, 14)


@pytest.mark.parametrize(
    "weight,reps", [("", 1), ("-1", 1), ("x", 1), ("40", 0), ("40", "1.5"), ("40", "")]
)
def test_ego_invalid_attempts_never_write(root110, weight, reps):
    """No empty, negative or malformed attempt becomes a zero lift."""
    with database_session(root110, write=True) as db:
        person, routine, exercise = setup(db)
        with pytest.raises(c.ValidationError):
            e.save(
                db,
                person,
                exercise,
                dict(weight=weight, repetitions=reps, submission_id=uuid4().hex),
            )
        assert e.history(db, person) == []


def test_ego_backup_restore_and_restart_persists_records(root110):
    """Normal verified backups include Ego records and audits, without any special backup path."""
    with database_session(root110, write=True) as db:
        person, routine, exercise = setup(db)
        identity = e.save(
            db,
            person,
            exercise,
            dict(weight="0", repetitions="3", submission_id=uuid4().hex),
        )
    result = backup(root110, uuid4().hex)
    assert result["status"] == "verified"
    with database_session(root110, write=True) as db:
        e.correct(
            db,
            person,
            identity,
            dict(weight="30", repetitions="1", confirm="yes", revision="0"),
        )
    restored = restore(root110, result["id"], uuid4().hex, confirm=True)
    assert restored["status"] == "succeeded"
    with database_session(root110) as db:
        assert e.record(db, person, identity)["weight_tenths_lb"] == 0
        assert e.history(db, person, exercise)[0]["id"] == identity
        logical_check_connection(db, 14)


def test_previous_performance_survives_multiple_skips_across_routines_and_corrections(
    root110,
):
    """Latest session and latest performed result are separate, corrected and person/basis specific."""
    with database_session(root110, write=True) as db:
        person, routine, exercise = setup(db)
        copied = c.copy_routine(db, person, routine, person, "Copied")
        other = c.create_person(db, "Other")
        for day, skipped in [
            ("2020-01-01", False),
            ("2020-01-02", True),
            ("2020-01-03", True),
        ]:
            form = h.prepare(
                db,
                person,
                routine if not skipped else copied,
                dict(workout_date=day, workout_time="08:00"),
                "UTC",
            )
            raw = {
                f"status_0_{i}": "skipped" if skipped else "completed" for i in range(3)
            }
            if not skipped:
                raw.update(
                    weight_0="40",
                    increase_0="1",
                    reps_0_0="12",
                    reps_0_1="12",
                    reps_0_2="11",
                )
            identity = h.complete_historical(
                db, person, form, dict(raw, confirm_all_skipped="yes")
            )
            if not skipped:
                original = identity
                h.correct(
                    db,
                    person,
                    identity,
                    dict(
                        raw,
                        weight_0="42.5",
                        workout_date=day,
                        workout_time="08:00",
                        confirm="yes",
                        correction_revision="0",
                    ),
                )
        sid, _ = w.start(db, person, copied, "UTC")
        parent = w.session(db, person, sid)
        entry = w.entries(db, person, sid)[0]
        previous, performed = w.previous(db, person, parent, entry)
        assert w.performance_status(previous) == "Skipped"
        assert (
            performed["actual_weight_tenths_lb"] == 425
            and performed["increase_next_time"] == 1
        )
        assert performed["workout_date"] == "2020-01-01"
        assert [r["actual_reps"] for r in performed["sets"]] == [12, 12, 11]
        assert w.previous(db, other, parent, entry) == (None, None)
        assert w.performance_status(performed) == "Completed"
        partial = dict(
            performed,
            sets=[
                performed["sets"][0],
                dict(status="skipped", actual_reps=None, actual_duration_seconds=None),
            ],
        )
        assert w.performance_status(partial) == "Partially completed"
        assert h.original(db, person, original)[1][0]["actual_weight_tenths_lb"] == 400


def test_ego_basis_groups_estimates_unweighted_defaults_and_global_deletion(root110):
    """Fallback total never edits an unweighted exercise; incompatible basis records stay apart."""
    from workout_tracker import deletions

    with database_session(root110, write=True) as db:
        person, routine, exercise = setup(db, caps=4)
        protected = capture(db)
        identity = e.save(
            db,
            person,
            exercise,
            dict(weight="50", repetitions="6", submission_id=uuid4().hex),
        )
        lift = e.record(db, person, identity)
        assert lift["weight_basis"] == "total"
        assert e.records([lift])[0]["estimate"] == 60
        assert e.records([dict(lift, repetitions=11)])[0]["estimate"] is None
        assert len(e.records([lift, dict(lift, weight_basis="per_side")])) == 2
        verify(protected, capture(db))
        current = deletions.impact(db, "exercise", exercise, person)
        assert current["ego_count"] == 1
        deletions.delete_exercise(
            db,
            person,
            exercise,
            dict(confirm="yes", phrase="DELETE", revision=current["revision"]),
        )
        assert not e.history(db, person)
        logical_check_connection(db, 14)


def test_ego_does_not_touch_an_existing_draft_or_its_increase_flag(root110):
    """A quick strength attempt is independent even while this person has an active session."""
    with database_session(root110, write=True) as db:
        person, routine, exercise = setup(db)
        sid, _ = w.start(db, person, routine, "UTC")
        w.update(
            db,
            person,
            sid,
            fields(db, person, sid, weight="40", reps_0="10", increase="1"),
        )
        parent = dict(w.session(db, person, sid))
        rows = w.entries(db, person, sid)
        e.save(
            db,
            person,
            exercise,
            dict(weight="80", repetitions="1", submission_id=uuid4().hex),
        )
        assert (
            dict(w.session(db, person, sid)) == parent
            and w.entries(db, person, sid) == rows
        )
        assert h.all_completed(db, person) == []


def test_ego_http_signed_double_submission_timezone_and_owner_checks(root110):
    """Real CSRF/signed forms bind retries to person/exercise and use configured local display."""
    from workout_tracker import create_app
    from test_phase8_deletion import token
    from datetime import datetime, timezone
    import re

    with database_session(root110, write=True) as db:
        person, routine, exercise = setup(db)
        other = c.create_person(db, "Other person")
        protected = capture(db)
    client = create_app(
        dict(
            TESTING=True, WORKOUT_DATA_ROOT=root110, WORKOUT_TIMEZONE="Pacific/Honolulu"
        )
    ).test_client()
    path = f"/people/{person}/ego-lifts/record/{exercise}"
    page = client.get(path)
    signature = re.search(rb'name="submission" value="([^"]+)"', page.data)[1].decode()
    payload = dict(
        csrf_token=token(page),
        exercise_id=exercise,
        submission=signature,
        weight="40.99",
        repetitions="6",
    )
    stamp = datetime(2026, 11, 17, 5, 30, tzinfo=timezone.utc)
    with patch.object(w, "now", return_value=stamp):
        assert (
            client.post(
                f"/people/{person}/ego-lifts/record/{exercise}", data=payload
            ).status_code
            == 303
        )
        assert (
            client.post(
                f"/people/{person}/ego-lifts/record/{exercise}", data=payload
            ).status_code
            == 303
        )
    page = client.get(path)
    assert b"2026-11-16 19:30" in page.data
    assert (
        client.post(
            f"/people/{other}/ego-lifts/record/{exercise}", data=payload
        ).status_code
        == 400
    )
    with database_session(root110) as db:
        rows = e.history(db, person, exercise)
        assert len(rows) == 1 and rows[0]["occurred_at"] == stamp.isoformat()
        assert db.execute("SELECT count(*) FROM ego_lift_audit").fetchone()[0] == 1
        assert not e.history(db, other)
        verify(protected, capture(db))
    assert client.get(f'/people/{other}/ego-lifts/{rows[0]["id"]}').status_code == 404
    assert (
        client.post(
            f"/people/{person}/ego-lifts/record/{exercise}",
            data=dict(payload, csrf_token="invalid"),
        ).status_code
        == 400
    )


def test_ego_uses_dormant_permanent_basis_without_changing_defaults(root110):
    """Disabling Weight cannot make an already established convention disappear for Ego records."""
    with database_session(root110, write=True) as db:
        person, routine, exercise = setup(db)
        c.update_defaults(
            db,
            person,
            exercise,
            dict(
                measurement_type="flex",
                capabilities=2,
                target_sets="2",
                target_reps="15",
                weight_basis="total",
            ),
            confirmed_type_change=True,
        )
        protected = capture(db)
        identity = e.save(
            db,
            person,
            exercise,
            dict(weight="0", repetitions="1", submission_id=uuid4().hex),
        )
        assert e.record(db, person, identity)["weight_basis"] == "total"
        verify(protected, capture(db))


def test_garmin_precision_migration_retries_keep_source_identity_and_private_credentials(
    tmp_path,
):
    """A real cached connection and higher-precision rows survive migration and repeated sync."""
    from test_garmin import response

    root = tmp_path / "old-garmin"
    initialize_storage(root)
    migrate_storage(root, 13)
    with database_session(root, write=True) as db:
        person, routine, exercise = setup(db)
        original_source = '{"unit":"g","value":"100000"}'
        g.import_weights(
            db,
            person,
            [
                dict(
                    measured_at="2020-01-01T08:00:00.000000+00:00",
                    weight_milli_lb=220462,
                    source_value=original_source,
                ),
                dict(
                    measured_at="2020-01-01T18:00:00.000000+00:00",
                    weight_milli_lb=220462,
                    source_value=original_source,
                ),
            ],
        )
        before = [dict(r) for r in db.execute("SELECT * FROM body_weights ORDER BY id")]
    with patch.object(g, "request", side_effect=response):
        g.connect(root, person, "synthetic-a")
    secrets = (root / "config/garmin-private.json").read_bytes()
    migrate_storage(root, 14)
    assert (root / "config/garmin-private.json").read_bytes() == secrets
    with patch.object(g, "request", side_effect=response):
        assert g.sync(root, person, "UTC") == 0
        assert g.sync(root, person, "UTC") == 0
    with database_session(root) as db:
        after = [dict(r) for r in db.execute("SELECT * FROM body_weights ORDER BY id")]
        for old, new in zip(before, after):
            for field in (
                "id",
                "person_id",
                "measured_at",
                "source",
                "external_id",
                "source_value",
                "created_at",
            ):
                assert old[field] == new[field]
            assert new["weight_milli_lb"] == 220500
        assert db.execute("SELECT count(*) FROM body_weight_audit").fetchone()[0] == 4
        logical_check_connection(db, 14)


def test_declared_future_configuration_change_passes_both_migration_comparisons(
    tmp_path,
):
    """A reviewed exact allowance must work end to end, not be blocked by physical-cell checks."""
    from workout_tracker import migrations

    root = tmp_path / "approved"
    initialize_storage(root)
    migrate_storage(root, 13)
    with database_session(root, write=True) as db:
        person, routine, exercise = setup(db, sets=2)
    original = (
        root
        / "data"
        / json.loads((root / "config/active.json").read_text())["database"]
    )
    before = original.read_bytes()
    upgrade = migrations._upgrade_candidate

    def approved(db, target_version):
        """Only this synthetic test authorizes changing one library setting."""
        upgrade(db, target_version)
        db.execute(
            "UPDATE exercise_defaults SET target_sets=3 WHERE exercise_id=?",
            (exercise,),
        )
        db.commit()

    allowed = {
        ("exercise_defaults", exercise, "target_sets"): (
            2,
            3,
            "Explicit synthetic approval of one setting",
        )
    }
    with patch.object(
        migrations, "_upgrade_candidate", side_effect=approved
    ), patch.object(
        migrations, "authorized_configuration_changes", return_value=allowed
    ):
        migrate_storage(root, 14)
    assert original.read_bytes() == before
    with database_session(root) as db:
        assert c.exercise_defaults(db, person, exercise)["target_sets"] == 3
        assert (
            db.execute(
                "SELECT target_sets FROM routine_exercises WHERE routine_id=?",
                (routine,),
            ).fetchone()[0]
            == 2
        )
        logical_check_connection(db, 14)


def test_equivalent_configuration_representation_is_compared_semantically(tmp_path):
    """Equivalent capabilities may retain different physical type labels without losing settings."""
    from workout_tracker import migrations
    root=tmp_path/'equivalent';initialize_storage(root);migrate_storage(root,13)
    with database_session(root,write=True) as db:
        person,routine,exercise=setup(db,sets=2)
        protected=capture(db)
    upgrade=migrations._upgrade_candidate
    def equivalent(db,target_version):
        """Use the existing compatible legacy label for the same Weight+Reps capabilities."""
        upgrade(db,target_version)
        db.execute("UPDATE exercise_defaults SET measurement_type='weight' WHERE exercise_id=?",(exercise,))
        db.execute("UPDATE routine_exercises SET measurement_type='weight' WHERE exercise_id=?",(exercise,))
        db.commit()
    with patch.object(migrations,'_upgrade_candidate',side_effect=equivalent):migrate_storage(root,14)
    with database_session(root) as db:
        verify(protected,capture(db))
        assert c.exercise_defaults(db,person,exercise)['measurement_type']=='weight'
        assert c.exercise_defaults(db,person,exercise)['target_sets']==2
        logical_check_connection(db,14)


def test_ego_selection_latest_five_custom_artwork_and_no_default_selection(root110):
    """Selection reuses sanitized artwork and only the selected person's newest five attempts."""
    from workout_tracker import create_app, exercise_icons

    with database_session(root110, write=True) as db:
        person, routine, exercise = setup(db)
        other = c.create_person(db, "Other")
        for index in range(7):
            e.save(
                db,
                person,
                exercise,
                dict(weight=str(index), repetitions="1", submission_id=uuid4().hex),
            )
        e.save(
            db,
            other,
            exercise,
            dict(weight="999", repetitions="1", submission_id=uuid4().hex),
        )
        exercise_icons.update(
            db,
            exercise,
            "start",
            b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><path d="M0 0L10 10"/></svg>',
        )
    client = create_app(dict(TESTING=True, WORKOUT_DATA_ROOT=root110)).test_client()
    blank = client.get(f"/people/{person}/ego-lifts")
    assert (
        b"Choose an exercise" in blank.data
        and b"disabled" in blank.data
        and b'name="weight"' not in blank.data
    )
    page = client.get(f"/people/{person}/ego-lifts?exercise={exercise}")
    assert page.data.count(b'class="ego-recent"') == 5 and b"999.0" not in page.data
    positions = [page.data.index(f"{value}.0 lb".encode()) for value in (6, 5, 4, 3, 2)]
    assert positions == sorted(positions)
    assert b"M0 0L10 10" in page.data and b'data-icon-position="end"' in page.data
    history = client.get(f"/people/{person}/ego-history")
    assert history.data.count(b'class="ego-history-row"') == 7
    assert b"History and Progress" in history.data
    remembered = client.get(f"/people/{person}/ego-history?progress_range=12m")
    assert b"range=12m" in remembered.data
    with database_session(root110, write=True) as db:
        db.execute(
            "DELETE FROM routine_exercises WHERE routine_id=? AND exercise_id=?",
            (routine, exercise),
        )
        c.update_definition(db, person, exercise, "", "archive")
    archived = client.get(f"/people/{person}/ego-history?exercise={exercise}")
    assert archived.status_code == 200 and exercise.encode() in archived.data
