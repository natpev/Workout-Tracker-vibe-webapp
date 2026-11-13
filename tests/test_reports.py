# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""PDF/CSV/download checks use real generated files and disposable effective history."""
from io import BytesIO
from unittest.mock import patch
import csv
import json
import sqlite3
from pypdf import PdfReader
from workout_tracker import (
    catalog as c,
    history as h,
    reports,
    body_weight as b,
    garmin as g,
    workouts as w,
)
from workout_tracker.storage import database_session
from workout_tracker.database_download import snapshot
from workout_tracker.maintenance import backup, restore
from test_unified_measurements import unified_root


def seed(root):
    """Shared seven-capability completed workout with explicit skipped sets and notes."""
    with database_session(root, write=True) as db:
        person = c.create_person(db, 'Example, "household"')
        routine = c.create_routine(db, person, "Routine")
        for caps in range(1, 8):
            c.add_entry(
                db,
                person,
                routine,
                dict(
                    name=("=SUM(1,2)" if caps == 1 else f"Exercise {caps}"),
                    measurement_type="flex",
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
        values = {}
        for index, caps in enumerate(range(1, 8)):
            values.update(
                {f"status_{index}_0": "completed", f"status_{index}_1": "skipped"}
            )
            if caps & 1:
                values[f"weight_{index}"] = "40"
            if caps & 2:
                values[f"reps_{index}_0"] = "10"
            if caps & 4:
                values[f"seconds_{index}_0"] = "45"
        identity = h.complete_historical(db, person, form, values)
    return person, routine, identity


def test_pdf_csv_actual_sets_statistics_and_formula_safety(unified_root):
    """PDFs parse, names/columns escape, explicit set totals agree with shared statistics."""
    person, _, identity = seed(unified_root)
    with database_session(unified_root) as db:
        report = reports.build(
            dict(c.person(db, person)),
            h.all_completed(db, person),
            "2020-01-01",
            "2020-01-31",
            "UTC",
        )
    assert report["completed_sets"] == report["skipped_sets"] == 7
    assert (
        report["total"] == 880
    )  # weight-only + combined hold each 40; weighted reps each 400.
    data = list(
        csv.DictReader(reports.csv_bytes(report).decode("utf-8-sig").splitlines())
    )
    assert len(data) == 14 and data[0]["exercise_name"].startswith("'=")
    assert (
        data[1]["set_status"] == "skipped"
        and data[1]["actual_repetitions"] == ""
        and data[1]["actual_duration_seconds"] == ""
    )
    pdf = reports.pdf_bytes(report)
    reader = PdfReader(BytesIO(pdf))
    text = "\n".join(page.extract_text() for page in reader.pages)
    assert pdf.startswith(b"%PDF") and len(reader.pages) >= 1
    assert "Workout Summary" in text and "Detailed workouts" in text
    assert "unknown individual status" in text and "880 lb" in text


def test_database_download_excludes_private_garmin_and_backup_restore_keeps_weights(
    unified_root,
):
    """Snapshot is SQLite-consistent; all body/icon data restores while secrets stay external."""
    person, _, _ = seed(unified_root)
    with database_session(unified_root, write=True) as db:
        b.manual(
            db, person, dict(date="2020-01-02", time="10:00", weight="220.125"), "UTC"
        )
        exercise = db.execute("SELECT id FROM exercises LIMIT 1").fetchone()[0]
        from workout_tracker.exercise_icons import update

        update(
            db, exercise, "start", '<svg><circle r="10" fill="var(--accent)"/></svg>'
        )
    with g.storage_lock(unified_root, exclusive=True) as root:
        g.write(
            root,
            dict(
                version=1,
                people={
                    person: dict(
                        key="SYNTHETIC-SECRET-NEVER-IN-SQLITE", connected=False
                    )
                },
            ),
        )
    handle = snapshot(unified_root)
    try:
        content = handle.read()
    finally:
        handle.close()
    assert (
        content.startswith(b"SQLite format 3")
        and b"SYNTHETIC-SECRET-NEVER-IN-SQLITE" not in content
    )
    db = sqlite3.connect(":memory:")
    db.deserialize(content)
    assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert not db.execute("PRAGMA foreign_key_check").fetchall()
    assert (
        db.execute("SELECT weight_milli_lb FROM body_weights").fetchone()[0] == 220125
    )
    db.close()
    record = backup(unified_root, "a" * 32)
    assert record["status"] == "verified"
    with database_session(unified_root, write=True) as db:
        row = db.execute("SELECT id FROM body_weights").fetchone()[0]
        b.remove(db, person, row, dict(confirm="yes", revision="0"))
    assert (
        restore(unified_root, record["id"], "b" * 32, confirm=True)["status"]
        == "succeeded"
    )
    with database_session(unified_root) as db:
        assert db.execute("SELECT count(*) FROM body_weights").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM exercise_icons").fetchone()[0] == 1
