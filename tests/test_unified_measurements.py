# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Seven capability combinations share exact per-set validation and real SQLite writes."""
import pytest
from workout_tracker import catalog as c, workouts as w, measurements as m
from workout_tracker.storage import initialize_storage, database_session
from workout_tracker.migrations import migrate_storage


@pytest.fixture
def unified_root(tmp_path):
    """Only a new synthetic tree is explicitly initialized and migrated."""
    root = tmp_path / "unified"
    initialize_storage(root)
    migrate_storage(root, 13)
    return root


@pytest.mark.parametrize("caps", range(1, 8))
def test_all_capabilities_one_weight_per_exercise_and_three_set_states(
    unified_root, caps
):
    """Zero reps/weight are real; a skipped row has SQL NULLs; incomplete blocks Next."""
    with database_session(unified_root, write=True) as db:
        person = c.create_person(db, "Synthetic person")
        routine = c.create_routine(db, person, "Flexible")
        values = dict(
            name="Example",
            capabilities=caps,
            measurement_type="flex",
            target_sets="3",
            target_reps="12",
            seconds="45",
            weight_basis="total",
        )
        item = c.add_entry(db, person, routine, values)
        session, _ = w.start(db, person, routine, "UTC")
        row = w.entries(db, person, session)[0]
        assert row["capabilities"] == caps and row["measurement_type"] == "flex"
        assert (
            row["sets"]
            == [
                dict(
                    status="incomplete", actual_reps=None, actual_duration_seconds=None
                )
            ]
            * 3
        )
        fields = dict(
            revision="0",
            entry_id=row["id"],
            current_position="0",
            weight="0" if caps & 1 else "",
            status_0="completed",
            status_1="skipped",
            status_2="incomplete",
        )
        if caps & 2:
            fields["reps_0"] = "0"
        if caps & 4:
            fields["seconds_0"] = "90"
        w.update(db, person, session, fields)
        stored = w.entries(db, person, session)[0]
        assert stored["actual_weight_tenths_lb"] == (0 if caps & 1 else None)
        assert stored["sets"][0]["actual_duration_seconds"] == (
            90 if caps & 4 else None
        )
        assert stored["sets"][1] == dict(
            status="skipped", actual_reps=None, actual_duration_seconds=None
        )
        assert stored["sets"][2]["status"] == "incomplete"
        with pytest.raises(c.ValidationError, match="Set 3"):
            w.finish(db, person, session, dict(fields, revision="1"))
        fields.update(revision="1", status_2="skipped")
        w.finish(db, person, session, fields)
        assert w.session(db, person, session)["status"] == "completed"


@pytest.mark.parametrize("caps", range(1, 8))
def test_historical_sets_and_append_only_corrections(unified_root, caps):
    """Manual history and corrections retain immutable originals for every combination."""
    from workout_tracker import history as h
    from workout_tracker.maintenance import logical_check_connection

    with database_session(unified_root, write=True) as db:
        person = c.create_person(db, "Past person")
        routine = c.create_routine(db, person, "Past")
        c.add_entry(
            db,
            person,
            routine,
            dict(
                name="Past example",
                measurement_type="flex",
                capabilities=caps,
                target_sets="2",
                target_reps="12",
                seconds="45",
                weight_basis="total",
            ),
        )
        form = h.prepare(
            db, person, routine, dict(workout_date="2020-01-02", workout_time=""), "UTC"
        )
        raw = dict(
            weight_0="40" if caps & 1 else "",
            status_0_0="completed",
            status_0_1="skipped",
        )
        if caps & 2:
            raw["reps_0_0"] = "10"
        if caps & 4:
            raw["seconds_0_0"] = "45"
        identity = h.complete_historical(db, person, form, raw)
        parent, rows = h.effective(db, person, identity)
        original = h.original(db, person, identity)
        assert len(rows[0]["sets"]) == 2 and rows[0]["sets"][1]["status"] == "skipped"
        corrected = dict(
            raw,
            workout_date="2020-01-02",
            workout_time="",
            confirm="yes",
            correction_revision="0",
            increase_0="1",
        )
        h.correct(db, person, identity, corrected)
        assert h.original(db, person, identity) == original
        assert h.effective(db, person, identity)[1][0]["increase_next_time"] == 1
        logical_check_connection(db, 13)


@pytest.mark.parametrize("caps", range(1, 8))
def test_effective_set_corrections_are_atomic_and_feed_every_reader(unified_root, caps):
    """Real changed set values reach reports/charts without touching immutable originals."""
    from workout_tracker import history as h, reports
    from workout_tracker.maintenance import logical_check_connection

    with database_session(unified_root, write=True) as db:
        person = c.create_person(db, "Corrections")
        routine = c.create_routine(db, person, "Routine")
        c.add_entry(
            db,
            person,
            routine,
            dict(
                name="Exercise",
                capabilities=caps,
                target_sets="2",
                target_reps="12",
                seconds="45",
                weight_basis="total",
            ),
        )
        form = h.prepare(
            db,
            person,
            routine,
            dict(workout_date="2020-01-02", workout_time="08:30"),
            "UTC",
        )
        raw = dict(
            weight_0="40" if caps & 1 else "",
            status_0_0="completed",
            status_0_1="skipped",
            reps_0_0="10" if caps & 2 else "",
            seconds_0_0="45" if caps & 4 else "",
        )
        identity = h.complete_historical(db, person, form, raw)
        original = h.original(db, person, identity)
        changed = dict(
            raw,
            weight_0="50" if caps & 1 else "",
            reps_0_0="9" if caps & 2 else "",
            seconds_0_0="90" if caps & 4 else "",
            workout_date="2020-01-02",
            workout_time="08:30",
            confirm="yes",
            correction_revision="0",
        )
        h.correct(db, person, identity, changed)
        assert h.original(db, person, identity) == original
        parent, rows = h.effective(db, person, identity)
        row = rows[0]
        assert row["actual_weight_tenths_lb"] == (500 if caps & 1 else None)
        assert row["sets"][0]["actual_reps"] == (9 if caps & 2 else None)
        assert row["sets"][0]["actual_duration_seconds"] == (90 if caps & 4 else None)
        with pytest.raises(w.RevisionConflict):
            h.correct(db, person, identity, changed)
        report = reports.build(
            dict(c.person(db, person)),
            h.all_completed(db, person),
            "2020-01-01",
            "2020-01-31",
            "UTC",
        )
        expected = 50 * (9 if caps & 2 else 1) if caps & 1 else 0
        assert report["total"] == expected
        logical_check_connection(db, 13)


def test_invalid_sets_roll_back_and_completed_sql_rows_stay_immutable(unified_root):
    """Validation rejects partial completion and direct SQL cannot bypass saved set guards."""
    import sqlite3

    with database_session(unified_root, write=True) as db:
        person = c.create_person(db, "Guard")
        routine = c.create_routine(db, person, "Routine")
        c.add_entry(
            db,
            person,
            routine,
            dict(
                name="Exercise",
                capabilities=7,
                target_sets="1",
                target_reps="12",
                seconds="45",
                weight_basis="total",
            ),
        )
        session, _ = w.start(db, person, routine, "UTC")
        entry = w.entries(db, person, session)[0]
        fields = dict(
            revision="0",
            current_position="0",
            entry_id=entry["id"],
            weight="0",
            status_0="completed",
            reps_0="0",
            seconds_0="",
        )
        with pytest.raises(c.ValidationError):
            w.update(db, person, session, fields)
        assert w.session(db, person, session)["revision"] == 0
        fields["seconds_0"] = "60"
        w.finish(db, person, session, fields)
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "UPDATE workout_sets SET actual_reps=1 WHERE entry_id=?", (entry["id"],)
            )
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("DELETE FROM workout_sets WHERE entry_id=?", (entry["id"],))


def test_permanent_exercise_deletion_projects_new_set_audits_without_touching_body_history(unified_root):
    """Existing deliberate deletion can cascade new sets while retaining unrelated history."""
    from workout_tracker import history as h,deletions as d,body_weight as b
    from workout_tracker.maintenance import logical_check_connection
    from test_phase8_deletion import approval
    with database_session(unified_root,write=True) as db:
        person=c.create_person(db,'Deletion');routine=c.create_routine(db,person,'Routine')
        items=[c.add_entry(db,person,routine,dict(name=name,capabilities=7,target_sets='2',target_reps='12',seconds='45',weight_basis='total')) for name in ('Remove','Keep')]
        exercise=c.entry(db,person,routine,items[0])['exercise_id']
        form=h.prepare(db,person,routine,dict(workout_date='2020-01-02',workout_time=''),'UTC')
        values={}
        for index in range(2):values.update({f'weight_{index}':'40',f'reps_{index}_0':'10',f'seconds_{index}_0':'45',f'status_{index}_0':'completed',f'status_{index}_1':'skipped'})
        identity=h.complete_historical(db,person,form,values)
        h.correct(db,person,identity,dict(values,workout_date='2020-01-02',workout_time='',confirm='yes',correction_revision='0',weight_1='50'))
        b.manual(db,person,dict(date='2020-01-02',time='08:00',weight='220'),'UTC')
        d.delete_exercise(db,person,exercise,approval(db,'exercise',exercise,person))
        parent,rows=h.effective(db,person,identity)
        assert len(rows)==1 and rows[0]['name']=='Keep' and rows[0]['actual_weight_tenths_lb']==500
        assert db.execute('SELECT count(*) FROM historical_sets').fetchone()[0]==2
        assert len(b.records(db,person,'UTC'))==1
        logical_check_connection(db,13)


def test_sql_capability_guards_reject_duplicate_actual_storage_and_false_completion(unified_root):
    """The database itself rejects duplicate legacy actuals and weightless completed sets."""
    import sqlite3
    with database_session(unified_root,write=True) as db:
        person=c.create_person(db,'SQL guards');routine=c.create_routine(db,person,'Routine')
        c.add_entry(db,person,routine,dict(name='Weight',capabilities=1,target_sets='1',weight_basis='total'))
        session,_=w.start(db,person,routine,'UTC');row=w.entries(db,person,session)[0]
        with pytest.raises(sqlite3.IntegrityError):db.execute('UPDATE workout_entries SET actual_duration_seconds=1 WHERE id=?',(row['id'],))
        with pytest.raises(sqlite3.IntegrityError):db.execute("UPDATE workout_sets SET status='completed' WHERE entry_id=?",(row['id'],))
        db.execute("UPDATE workout_sets SET status='skipped' WHERE entry_id=?",(row['id'],))
        db.execute('UPDATE workout_entries SET actual_weight_tenths_lb=0 WHERE id=?',(row['id'],))
        with pytest.raises(sqlite3.IntegrityError):db.execute("UPDATE workout_sessions SET status='completed',finished_at=? WHERE id=?",(w.now().isoformat(),session))
        # Leave the disposable draft in a logically valid skipped state.
        db.execute('UPDATE workout_entries SET actual_weight_tenths_lb=NULL WHERE id=?',(row['id'],))
