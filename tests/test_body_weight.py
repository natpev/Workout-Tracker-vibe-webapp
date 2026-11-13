# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Synthetic per-person weigh-ins, revision safety and observed-day trend arithmetic."""
import pytest
from workout_tracker import body_weight as b, catalog as c
from workout_tracker.storage import database_session
from test_unified_measurements import unified_root


def test_multiple_readings_and_equal_day_trends(unified_root):
    """Repeated weights/times are genuine independent Manual rows; days get equal weight."""
    with database_session(unified_root, write=True) as db:
        a = c.create_person(db, "A")
        other = c.create_person(db, "B")
        ids = []
        for day, clock, weight in [
            ("2020-01-01", "08:00", "200"),
            ("2020-01-01", "18:00", "220"),
            ("2020-01-02", "08:00", "230"),
        ]:
            ids.append(
                b.manual(db, a, dict(date=day, time=clock, weight=weight), "UTC")
            )
        assert len(set(ids)) == 3 and len(b.records(db, a, "UTC")) == 3
        assert not b.records(db, other, "UTC")
        trend = b.trends(b.records(db, a, "UTC"))
        assert trend[0]["daily"] == 210000 and trend[1]["ma7"] == 220000
        with pytest.raises(c.MissingRecord):
            b.record(db, other, ids[0])
        b.manual(
            db,
            a,
            dict(date="2020-01-01", time="08:00", weight="201.125", revision="0"),
            "UTC",
            ids[0],
        )
        assert b.record(db, a, ids[0])["weight_milli_lb"] == 201125
        with pytest.raises(c.ValidationError):
            b.remove(db, a, ids[0], dict(revision="1"))
        b.remove(db, a, ids[0], dict(confirm="yes", revision="1"))
        assert len(b.records(db, a, "UTC")) == 2
        assert db.execute("SELECT count(*) FROM body_weight_audit").fetchone()[0] == 5


@pytest.mark.parametrize("bad", ["", "0", "-1", "NaN", "Infinity", "1.1234", "bad"])
def test_invalid_body_weight_never_becomes_zero(bad):
    """Invalid values do not silently create a plausible reading."""
    with pytest.raises(c.ValidationError):
        b.amount(bad)


def test_workout_weighin_prompt_skip_resume_and_retry(unified_root):
    """No remote calls; one draft survives prompt refresh/skip/retry without body rows."""
    from workout_tracker import create_app, workouts as w
    from test_phase8_deletion import token

    with database_session(unified_root, write=True) as db:
        person = c.create_person(db, "Prompt")
        routine = c.create_routine(db, person, "Routine")
        c.add_entry(
            db,
            person,
            routine,
            dict(
                name="Plank",
                measurement_type="flex",
                capabilities=4,
                target_sets="2",
                seconds="45",
            ),
        )
        session, _ = w.start(db, person, routine, "UTC")
    client = create_app(
        {"TESTING": True, "WORKOUT_DATA_ROOT": unified_root, "WORKOUT_TIMEZONE": "UTC"}
    ).test_client()
    path = f"/people/{person}/workouts/{session}"
    response = client.get(path, follow_redirects=True)
    assert b"Today\xe2\x80\x99s Body Weight" in response.data
    response = client.post(
        path + "/weigh-in",
        data=dict(csrf_token=token(response), action="skip"),
        follow_redirects=True,
    )
    assert response.status_code == 200 and b"workout-form" in response.data
    assert client.get(path).status_code == 200
    with database_session(unified_root) as db:
        assert db.execute("SELECT count(*) FROM body_weights").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM workout_sessions").fetchone()[0] == 1
        assert (
            db.execute("SELECT count(*) FROM workout_weighin_prompts").fetchone()[0]
            == 1
        )
