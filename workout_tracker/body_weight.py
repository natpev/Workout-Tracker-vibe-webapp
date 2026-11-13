# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Person-owned local weigh-ins and exact daily-average moving trends.

Routes/importers own the transaction. Weight uses integer thousandths of a pound,
never binary floating point. Credentials are never passed to this SQLite layer.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from uuid import uuid4
from zoneinfo import ZoneInfo
from . import catalog as c, workouts as w, history as h


def amount(value):
    """Parse positive pounds with at most three decimal places, retaining exact integers."""
    raw = w.field({"weight": value}, "weight")
    try:
        number = Decimal(raw)
        if (
            not number.is_finite()
            or number <= 0
            or number * 1000 != (number * 1000).to_integral_value()
        ):
            raise ValueError()
        result = int(number * 1000)
        if result > w.MAX_INTEGER:
            raise ValueError()
        return result
    except (InvalidOperation, ValueError, OverflowError) as error:
        raise c.ValidationError(
            "Enter a positive body weight with at most three decimal places."
        ) from error


def timestamp(day, clock, zone, fold=""):
    """Use existing local-calendar/DST validation; body-weight time is required."""
    if not clock:
        raise c.ValidationError("Choose the measurement time.")
    _, _, instant = h.occurrence(day, clock, zone, fold)
    return (
        datetime.fromisoformat(instant)
        .astimezone(timezone.utc)
        .isoformat(timespec="microseconds")
    )


def record(db, person, identity):
    """Read by person AND permanent record ID; never fall back to another household member."""
    c.person(db, person, archived=True)
    row = db.execute(
        "SELECT * FROM body_weights WHERE id=? AND person_id=?", (identity, person)
    ).fetchone()
    if row is None:
        raise c.MissingRecord("Body-weight record not found for this person.")
    return dict(row)


def audit(db, person, identity, before, after):
    """Retain before/after records for deliberate edits, removals and Garmin updates."""
    revision = db.execute(
        "SELECT coalesce(max(revision),0)+1 FROM body_weight_audit WHERE record_id=?",
        (identity,),
    ).fetchone()[0]
    db.execute(
        "INSERT INTO body_weight_audit VALUES (?,?,?,?,?,?,?)",
        (
            uuid4().hex,
            identity,
            person,
            w.now().isoformat(),
            revision,
            h.json_text(before) if before else None,
            h.json_text(after) if after else None,
        ),
    )


def manual(db, person, values, zone, identity=None):
    """Create or deliberately revise only Manual data, checking stale-browser revisions."""
    c.person(db, person)
    weight = amount(values.get("weight", ""))
    instant = timestamp(
        w.field(values, "date"), w.field(values, "time"), zone, w.field(values, "fold")
    )
    stamp = w.now().isoformat()
    before = record(db, person, identity) if identity else None
    if before:
        if before["source"] != "manual":
            raise c.ValidationError(
                "Garmin measurements retain their source; edit them in Garmin."
            )
        if values.get("revision") != str(before["revision"]):
            raise w.RevisionConflict("This weigh-in changed. Reload before editing.")
        db.execute(
            "UPDATE body_weights SET weight_milli_lb=?,measured_at=?,updated_at=?,revision=revision+1 WHERE id=? AND person_id=?",
            (weight, instant, stamp, identity, person),
        )
    else:
        identity = uuid4().hex
        db.execute(
            "INSERT INTO body_weights(id,person_id,weight_milli_lb,measured_at,source,created_at,updated_at) VALUES (?,?,?,?,?,?,?)",
            (identity, person, weight, instant, "manual", stamp, stamp),
        )
    audit(db, person, identity, before, record(db, person, identity))
    return identity


def remove(db, person, identity, values):
    """Delete only an acknowledged Manual record and append its retained audit."""
    before = record(db, person, identity)
    if before["source"] != "manual":
        raise c.ValidationError(
            "Garmin records cannot be removed as manual measurements."
        )
    if values.get("confirm") != "yes":
        raise c.ValidationError("Confirm removing this body-weight measurement.")
    if values.get("revision") != str(before["revision"]):
        raise w.RevisionConflict("This weigh-in changed. Reload before removing.")
    audit(db, person, identity, before, None)
    db.execute(
        "DELETE FROM body_weights WHERE id=? AND person_id=?", (identity, person)
    )


def records(db, person, zone, values=None):
    """Sort/filter real readings by local calendar; multiple same-day measurements remain."""
    c.person(db, person, archived=True)
    values = values or {}
    start, end = values.get("from", ""), values.get("to", "")
    if start:
        h.parse_date(start)
    if end:
        h.parse_date(end)
    if start and end and start > end:
        raise c.ValidationError("From date must not follow To date.")
    source = values.get("source", "")
    if source not in ("", "manual", "garmin"):
        raise c.ValidationError("Choose Manual, Garmin or all sources.")
    result = []
    for row in db.execute(
        "SELECT * FROM body_weights WHERE person_id=? ORDER BY measured_at,id",
        (person,),
    ):
        row = dict(row)
        local = datetime.fromisoformat(row["measured_at"]).astimezone(ZoneInfo(zone))
        row.update(
            day=local.date().isoformat(),
            clock=local.strftime("%H:%M"),
            weight=display(row["weight_milli_lb"]),
        )
        if (
            (not start or row["day"] >= start)
            and (not end or row["day"] <= end)
            and (not source or row["source"] == source)
        ):
            result.append(row)
    return result if values.get("order") == "oldest" else list(reversed(result))


def display(value):
    """Readable exact pounds without exposing storage scaling or float artifacts."""
    return f"{value//1000}.{value%1000:03d}".rstrip("0").rstrip(".")


def today_exists(db, person, zone):
    """Local data only: Garmin availability can never block the workout-start check."""
    day = w.now().astimezone(ZoneInfo(zone)).date().isoformat()
    return bool(records(db, person, zone, {"from": day, "to": day}))


def trends(rows):
    """Average readings within each day first, then observed daily means in 7/30 days.

    Missing days are omitted rather than treated as zero. Each observed day gets
    equal weight; individual readings stay intact and visible separately.
    """
    daily = {}
    for row in rows:
        daily.setdefault(row["day"], []).append(row["weight_milli_lb"])
    means = {
        day: Fraction(sum(weights), len(weights)) for day, weights in daily.items()
    }
    result = []
    for day in sorted(means):
        date = h.parse_date(day)
        point = {"day": day, "daily": means[day]}
        for window in (7, 30):
            chosen = [
                value
                for other, value in means.items()
                if date - timedelta(days=window - 1) <= h.parse_date(other) <= date
            ]
            point[f"ma{window}"] = sum(chosen, Fraction(0)) / len(chosen)
        result.append(point)
    return result
