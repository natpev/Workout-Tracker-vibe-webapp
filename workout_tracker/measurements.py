# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""One capability model and per-set validator for every new exercise combination.

Bit flags describe enabled measurements, not seven separate workout types. Legacy
snapshots keep their original parser; new results store real SQL NULLs per set.
"""
from . import catalog as c

WEIGHT, REPETITIONS, DURATION = 1, 2, 4
LEGACY = {"weight": 3, "time": 4, "weight_duration": 5}


def mask(values):
    """Read bounded capability flags or an existing configuration's explicit mask."""
    if values.get("capabilities_form") == "yes":
        result = sum(
            bit
            for key, bit in (
                ("enable_weight", 1),
                ("enable_reps", 2),
                ("enable_duration", 4),
            )
            if values.get(key) == "yes"
        )
    elif values.get("capabilities") is not None:
        raw = str(values["capabilities"])
        if raw not in tuple(str(i) for i in range(1, 8)):
            raise c.ValidationError("Choose at least one measurement capability.")
        result = int(raw)
    else:
        result = LEGACY.get(values.get("measurement_type"), 0)
    if result not in range(1, 8):
        raise c.ValidationError("Choose at least one measurement capability.")
    return result


def adapt(db, values):
    """All schema-13 configuration writes use the same flex representation."""
    if db.execute("PRAGMA user_version").fetchone()[0] < 13:
        return values
    return dict(values, measurement_type="flex", capabilities=mask(values))


def configuration(values):
    """Return legacy-compatible target columns for the independently enabled fields."""
    caps = mask(values)
    sets = c.integer(values.get("target_sets", ""), "Sets", 1, 1000)
    notes = str(values.get("notes", "")).strip()
    if len(notes) > 2000:
        raise c.ValidationError("Notes must contain at most 2000 characters.")
    reps = (
        c.integer(values.get("target_reps", ""), "Target reps", 1, 10000)
        if caps & 2
        else None
    )
    duration = None
    if caps & 4:
        from .durations import parse_duration

        try:
            duration = parse_duration(
                values.get("minutes", ""), values.get("seconds", ""), 359999
            )
        except ValueError as error:
            raise c.ValidationError(str(error)) from error
        if duration is None:
            raise c.ValidationError("Specify a positive target duration.")
    if caps & 1 and values.get("unit", "lb") != "lb":
        raise c.ValidationError("Weight unit must be pounds (lb).")
    meaning = str(values.get("weight_meaning", "")).strip() if caps & 1 else ""
    if len(meaning) > 200:
        raise c.ValidationError("Weight meaning must contain at most 200 characters.")
    return "flex", sets, reps, duration, "lb" if caps & 1 else None, meaning, notes


def label(caps):
    """Human names come from enabled bits, not an exercise's equipment or name."""
    return " + ".join(
        name
        for bit, name in ((1, "Weight"), (2, "Repetitions"), (4, "Duration"))
        if caps & bit
    )


def validate(entry, weight, sets, *, complete=False):
    """Validate a complete result or a resumable partial draft without coercing NULL."""
    from .workouts import MAX_INTEGER

    caps = entry["capabilities"]
    if type(caps) is not int or caps not in range(1, 8):
        raise c.ValidationError("Invalid measurement capabilities.")
    if weight is not None and (
        not caps & 1 or type(weight) is not int or not 0 <= weight <= MAX_INTEGER
    ):
        raise c.ValidationError("Invalid exercise weight.")
    if not isinstance(sets, list) or len(sets) != entry["target_sets"]:
        raise c.ValidationError("Every configured set must retain a result.")
    for index, row in enumerate(sets):
        if set(row) != {"status", "actual_reps", "actual_duration_seconds"}:
            raise c.ValidationError("Invalid set fields.")
        state = row["status"]
        reps = row["actual_reps"]
        duration = row["actual_duration_seconds"]
        if state not in ("incomplete", "completed", "skipped"):
            raise c.ValidationError("Choose a valid set status.")
        if reps is not None and (
            not caps & 2 or type(reps) is not int or not 0 <= reps <= 10000
        ):
            raise c.ValidationError(f"Set {index+1}: invalid actual repetitions.")
        if duration is not None and (
            not caps & 4
            or type(duration) is not int
            or not 1 <= duration <= MAX_INTEGER
        ):
            raise c.ValidationError(f"Set {index+1}: duration must be positive.")
        if state == "skipped" and (reps is not None or duration is not None):
            raise c.ValidationError("Skipped set measurements must be NULL.")
        if state == "completed" and (
            (caps & 1 and weight is None)
            or (caps & 2 and reps is None)
            or (caps & 4 and duration is None)
        ):
            raise c.ValidationError(
                f"Set {index+1}: enter every enabled measurement before marking Completed."
            )
        if complete and state == "incomplete":
            raise c.ValidationError(
                f"Set {index+1}: record measurements or explicitly choose Skipped."
            )
    if complete and all(r["status"] == "skipped" for r in sets) and weight is not None:
        raise c.ValidationError("An entirely skipped exercise must retain NULL weight.")
    return sets


def parse(entry, values, *, complete=False):
    """Browser fields -> exact exercise weight and independent status/reps/duration."""
    from . import workouts as w

    caps = entry["capabilities"]
    rows = []
    errors = {}
    weight = None
    if caps & 1:
        try:
            weight = w.weight_tenths(w.field(values, "weight"))
        except c.ValidationError as error:
            errors["weight"] = str(error)
    for index in range(entry["target_sets"]):
        status = w.field(values, f"status_{index}") or "incomplete"
        result = dict(status=status, actual_reps=None, actual_duration_seconds=None)
        if status != "skipped":
            for bit, key in ((2, "reps"), (4, "duration")):
                if not caps & bit:
                    continue
                try:
                    if bit == 2:
                        raw = w.field(values, f"reps_{index}")
                        result["actual_reps"] = (
                            c.integer(raw, "Actual repetitions", 0, 10000)
                            if raw
                            else None
                        )
                    else:
                        result["actual_duration_seconds"] = w.duration_seconds(
                            w.field(values, f"minutes_{index}"),
                            w.field(values, f"seconds_{index}"),
                        )
                except c.ValidationError as error:
                    errors[f"{key}_{index}"] = str(error)
        rows.append(result)
    if errors:
        raise w.MeasurementError(errors)
    if all(row["status"] == "skipped" for row in rows):
        weight = None
    try:
        validate(entry, weight, rows, complete=complete)
    except c.ValidationError as error:
        raise w.MeasurementError({"sets": str(error)}) from error
    flag = w.field(values, "increase")
    if flag not in ("", "0", "1"):
        raise w.MeasurementError({"increase": "Invalid increase recommendation."})
    increase = (
        int(flag == "1") if any(r["status"] == "completed" for r in rows) else None
    )
    return dict(
        actual_weight_tenths_lb=weight,
        actual_duration_seconds=None,
        increase_next_time=increase,
        sets=rows,
    )


def read(db, entry, source="live"):
    """Load immutable or draft SQL set rows; legacy values are deliberately not expanded."""
    row = dict(entry)
    if row.get("capabilities") is None:
        return row
    table = "workout_sets" if source == "live" else "historical_sets"
    row["sets"] = [
        dict(
            status=r["status"],
            actual_reps=r["actual_reps"],
            actual_duration_seconds=r["actual_duration_seconds"],
        )
        for r in db.execute(
            f"SELECT * FROM {table} WHERE entry_id=? ORDER BY set_index", (row["id"],)
        )
    ]
    return row


def insert_sets(db, entry_id, rows, source="live"):
    """Write one SQL row per set; skipped measurements are actual SQL NULL values."""
    table = "workout_sets" if source == "live" else "historical_sets"
    for index, row in enumerate(rows):
        db.execute(
            f"INSERT INTO {table} VALUES (?,?,?,?,?)",
            (
                entry_id,
                index,
                row["status"],
                row["actual_reps"],
                row["actual_duration_seconds"],
            ),
        )


def validate_storage(db):
    """Read-only invariants shared by startup, candidate verification and backup/restore."""
    from datetime import datetime
    import json
    from .storage import StorageError

    try:
        for table in ("exercise_defaults", "routine_exercises"):
            for row in db.execute(f"SELECT * FROM {table}"):
                if row["capabilities"] is None:
                    raise ValueError("Missing current capabilities")
                if row["measurement_type"] != "flex":
                    if row["capabilities"] != LEGACY.get(row["measurement_type"]):
                        raise ValueError("Legacy configuration mismatch")
                else:
                    configured = configuration(c.default_values(row))
                    if configured != tuple(
                        row[k]
                        for k in (
                            "measurement_type",
                            "target_sets",
                            "target_reps",
                            "target_duration_seconds",
                            "unit",
                            "weight_meaning",
                            "notes",
                        )
                    ):
                        raise ValueError("Invalid flex configuration")
        for source, table in (
            ("live", "workout_entries"),
            ("historical", "historical_entries"),
        ):
            for stored in db.execute(
                f"SELECT * FROM {table} WHERE capabilities IS NOT NULL"
            ):
                row = read(db, stored, source)
                complete = (
                    source == "historical"
                    or db.execute(
                        "SELECT status FROM workout_sessions WHERE id=?",
                        (row["session_id"],),
                    ).fetchone()[0]
                    == "completed"
                )
                validate(
                    row, row["actual_weight_tenths_lb"], row["sets"], complete=complete
                )
        chains = {}
        for audit in db.execute(
            "SELECT * FROM body_weight_audit ORDER BY record_id,revision"
        ):
            before = json.loads(audit["before_json"]) if audit["before_json"] else None
            after = json.loads(audit["after_json"]) if audit["after_json"] else None
            previous, revision = chains.get(audit["record_id"], (None, 0))
            if audit["revision"] != revision + 1 or before != previous:
                raise ValueError("Body-weight audit chain mismatch")
            if datetime.fromisoformat(audit["changed_at"]).tzinfo is None:
                raise ValueError("Unaware body-weight audit")
            for record in (before, after):
                if record:
                    if (
                        record["id"] != audit["record_id"]
                        or record["person_id"] != audit["person_id"]
                    ):
                        raise ValueError("Body-weight audit ownership")
                    if (
                        datetime.fromisoformat(record["measured_at"]).tzinfo is None
                        or type(record["weight_milli_lb"]) is not int
                        or record["weight_milli_lb"] <= 0
                    ):
                        raise ValueError("Invalid body-weight value")
            chains[audit["record_id"]] = (after, audit["revision"])
        for identity, (last, _) in chains.items():
            actual = db.execute(
                "SELECT * FROM body_weights WHERE id=?", (identity,)
            ).fetchone()
            if (dict(actual) if actual else None) != last:
                raise ValueError("Body-weight effective value differs from audit")
        for record in db.execute("SELECT * FROM body_weights"):
            if record["id"] not in chains:
                raise ValueError("Missing body-weight audit")
    except (ValueError, TypeError, KeyError, c.ValidationError) as error:
        raise StorageError(
            "Unified set/body-weight consistency validation failed."
        ) from error
