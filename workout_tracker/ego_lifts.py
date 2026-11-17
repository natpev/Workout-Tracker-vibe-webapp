# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Separate person-owned strength attempts; never query or write normal workout totals.

Callers own the existing locked transaction. Exact weight tenths and immutable
name/basis snapshots survive edits; corrections/deletions append complete audits.
"""
from datetime import datetime
from fractions import Fraction
from uuid import uuid4
import json
from . import catalog as c, workouts as w, history as h
from .storage import StorageError


def record(db, person, identity):
    """Always qualify lookup by person, including deliberate correction requests."""
    c.person(db, person, archived=True)
    row = db.execute(
        "SELECT * FROM ego_lifts WHERE id=? AND person_id=? AND deleted=0",
        (identity, person),
    ).fetchone()
    if row is None:
        raise c.MissingRecord("Ego Lift not found for this person.")
    return dict(row)


def history(db, person, exercise=""):
    """Latest recorded attempts first; deleted attempts remain only in the audit."""
    c.person(db, person)
    return [
        dict(r)
        for r in db.execute(
            "SELECT * FROM ego_lifts WHERE person_id=? AND deleted=0 AND (?='' OR exercise_id=?) ORDER BY occurred_at DESC,id DESC",
            (person, exercise, exercise),
        )
    ]


def measurements(values):
    """Use the same nonnegative/truncated weight parser as workouts, with positive reps."""
    weight = w.weight_tenths(w.field(values, "weight"))
    if weight is None:
        raise c.ValidationError("Enter a weight; explicitly entered zero is valid.")
    return weight, c.integer(values.get("repetitions", ""), "Repetitions", 1, 10000)


def audit(db, before, after):
    """Append immutable original/corrected values instead of losing prior attempts."""
    revision = db.execute(
        "SELECT coalesce(max(revision),0)+1 FROM ego_lift_audit WHERE lift_id=?",
        (after["id"],),
    ).fetchone()[0]
    db.execute(
        "INSERT INTO ego_lift_audit VALUES (?,?,?,?,?,?,?)",
        (
            uuid4().hex,
            after["id"],
            after["person_id"],
            revision,
            w.now().isoformat(),
            h.json_text(before) if before else None,
            h.json_text(after),
        ),
    )


def weight_basis(db, exercise):
    """A permanently assigned convention also applies when Weight is currently disabled."""
    assigned = db.execute(
        "SELECT basis FROM exercise_weight_basis WHERE exercise_id=?", (exercise,)
    ).fetchone()
    return assigned[0] if assigned else "total"


def save(db, person, exercise, values):
    """A signed form's unique submission ID makes retries return the original attempt."""
    import re

    c.person(db, person)
    submission = values.get("submission_id", "")
    if not isinstance(submission, str) or not re.fullmatch("[0-9a-f]{32}", submission):
        raise c.ValidationError("Reload the form before saving this lift.")
    old = db.execute(
        "SELECT * FROM ego_lifts WHERE person_id=? AND submission_id=?",
        (person, submission),
    ).fetchone()
    if old:
        if old["exercise_id"] != exercise:
            raise w.RevisionConflict("This form was already used for another exercise.")
        return old["id"]
    definition = c.definition(db, person, exercise)
    defaults = c.exercise_defaults(db, person, exercise)
    weight, reps = measurements(values)
    # A dormant permanent assignment still applies; unweighted/unclassified
    # library definitions use total only for this attempt, without editing defaults.
    basis = weight_basis(db, exercise)
    identity = uuid4().hex
    stamp = w.now().isoformat()
    db.execute(
        "INSERT INTO ego_lifts(id,person_id,exercise_id,exercise_name,weight_basis,weight_meaning,weight_tenths_lb,repetitions,occurred_at,created_at,updated_at,submission_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            identity,
            person,
            exercise,
            definition["name"],
            basis,
            defaults["weight_meaning"],
            weight,
            reps,
            stamp,
            stamp,
            stamp,
            submission,
        ),
    )
    audit(db, None, record(db, person, identity))
    return identity


def correct(db, person, identity, values):
    """Confirmed revision checks protect newer edits; deletion is audited soft deletion."""
    before = record(db, person, identity)
    if values.get("confirm") != "yes":
        raise c.ValidationError("Confirm this correction or deletion before saving.")
    if values.get("revision") != str(before["revision"]):
        raise w.RevisionConflict("This Ego Lift changed. Reload before editing.")
    deleted = values.get("action") == "delete"
    weight, reps = (
        (before["weight_tenths_lb"], before["repetitions"])
        if deleted
        else measurements(values)
    )
    db.execute(
        "UPDATE ego_lifts SET weight_tenths_lb=?,repetitions=?,deleted=?,updated_at=?,revision=revision+1 WHERE id=? AND person_id=?",
        (weight, reps, int(deleted), w.now().isoformat(), identity, person),
    )
    after = dict(
        db.execute("SELECT * FROM ego_lifts WHERE id=?", (identity,)).fetchone()
    )
    audit(db, before, after)


def records(rows):
    """Compare only compatible exercise/basis/meaning groups; 1RM uses exact Epley fractions."""
    groups = {}
    for row in rows:
        key = (row["exercise_id"], row["weight_basis"], row["weight_meaning"])
        group = groups.setdefault(
            key,
            dict(
                name=row["exercise_name"],
                basis=row["weight_basis"],
                meaning=row["weight_meaning"],
                heaviest=None,
                estimate=None,
            ),
        )
        if group["heaviest"] is None or (
            row["weight_tenths_lb"],
            row["repetitions"],
        ) > (group["heaviest"]["weight_tenths_lb"], group["heaviest"]["repetitions"]):
            group["heaviest"] = row
        if row["repetitions"] <= 10:
            estimate = Fraction(row["weight_tenths_lb"], 10) * (
                1 if row["repetitions"] == 1 else Fraction(30 + row["repetitions"], 30)
            )
            if group["estimate"] is None or estimate > group["estimate"]:
                group["estimate"] = estimate
    return list(groups.values())


def validate_storage(db):
    """Validate audit continuity/current state, ownership, immutable snapshots and aware dates."""
    chains = {}
    try:
        if db.execute(
            "SELECT 1 FROM body_weights WHERE source='garmin' AND weight_milli_lb%100!=0"
        ).fetchone():
            raise ValueError()
        for row in db.execute("SELECT * FROM ego_lift_audit ORDER BY lift_id,revision"):
            before = json.loads(row["before_json"]) if row["before_json"] else None
            after = json.loads(row["after_json"])
            last, revision = chains.get(row["lift_id"], (None, 0))
            if (
                before != last
                or row["revision"] != revision + 1
                or after["id"] != row["lift_id"]
                or after["person_id"] != row["person_id"]
            ):
                raise ValueError()
            if (
                after["revision"] != revision
                or datetime.fromisoformat(row["changed_at"]).tzinfo is None
            ):
                raise ValueError()
            if (
                type(after["weight_tenths_lb"]) is not int
                or not 0 <= after["weight_tenths_lb"] <= w.MAX_INTEGER
                or type(after["repetitions"]) is not int
                or not 1 <= after["repetitions"] <= 10000
                or after["deleted"] not in (0, 1)
                or after["weight_basis"] not in ("total", "per_side")
            ):
                raise ValueError()
            if any(
                datetime.fromisoformat(after[k]).tzinfo is None
                for k in ("occurred_at", "created_at", "updated_at")
            ):
                raise ValueError()
            if before and any(
                before[k] != after[k]
                for k in (
                    "id",
                    "person_id",
                    "exercise_id",
                    "exercise_name",
                    "weight_basis",
                    "weight_meaning",
                    "occurred_at",
                    "created_at",
                    "submission_id",
                )
            ):
                raise ValueError()
            if before and before["deleted"]:
                raise ValueError()
            chains[row["lift_id"]] = (after, revision + 1)
        actual = {r["id"]: dict(r) for r in db.execute("SELECT * FROM ego_lifts")}
        if actual != {identity: pair[0] for identity, pair in chains.items()}:
            raise ValueError()
    except (ValueError, TypeError, KeyError):
        raise StorageError("Ego Lift audit consistency validation failed.") from None
