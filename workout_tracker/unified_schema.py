# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Schema 13 candidate-only capability, set and body-weight storage.

Released DDL stays frozen. Legacy entry cells remain unchanged and have NULL
capabilities: their single historical durations are never guessed into sets.
"""
import re
from .icon_size_schema import ICON_SIZE_OBJECTS


def flexible_table(sql):
    """Allow the new flex model while retaining every constraint for legacy rows."""
    sql = sql.replace(
        "measurement_type TEXT",
        "capabilities INTEGER CHECK(capabilities BETWEEN 1 AND 7),\n        measurement_type TEXT",
        1,
    )
    # Wrap only the old type/actual cross-field checks, using balanced SQL
    # parentheses rather than changing released legacy schema definitions.
    cursor = 0
    while True:
        match = re.search(r"CHECK\(", sql[cursor:])
        if match is None:
            break
        begin = cursor + match.start()
        position = begin + 6
        depth = 1
        quoted = False
        while depth:
            char = sql[position]
            if char == "'":
                quoted = not quoted
            elif not quoted:
                if char == "(":
                    depth += 1
                elif char == ")":
                    depth -= 1
            position += 1
        inside = sql[begin + 6 : position - 1]
        if "measurement_type" in inside or "actual_weight_tenths_lb IS NULL" in inside:
            replacement = "CHECK(measurement_type='flex' OR (" + inside + "))"
            sql = sql[:begin] + replacement + sql[position:]
            cursor = begin + len(replacement)
        else:
            cursor = position
    offset = sql.rfind(") STRICT")
    extra = """,
        CHECK(measurement_type!='flex' OR (capabilities IS NOT NULL
          AND ((capabilities & 1)=0 OR (unit='lb' AND weight_basis IN ('total','per_side')))
          AND ((capabilities & 2)=0 OR (target_reps IS NOT NULL AND target_reps BETWEEN 1 AND 10000))
          AND ((capabilities & 4)=0 OR (target_duration_seconds IS NOT NULL AND target_duration_seconds BETWEEN 1 AND 359999))))
    """
    if "actual_weight_tenths_lb" in sql:
        extra += """,
        CHECK((measurement_type='flex')=(capabilities IS NOT NULL)),
        CHECK(measurement_type!='flex' OR (actual_duration_seconds IS NULL AND actual_reps_json IS NULL)),
        CHECK(measurement_type!='flex' OR (capabilities & 1)!=0 OR actual_weight_tenths_lb IS NULL)
        """
    return sql[:offset] + extra + sql[offset:]


UNIFIED_OBJECTS = dict(ICON_SIZE_OBJECTS)
CHANGED = (
    "exercise_defaults",
    "routine_exercises",
    "workout_entries",
    "historical_entries",
)
for table in CHANGED:
    UNIFIED_OBJECTS[table] = flexible_table(UNIFIED_OBJECTS[table])
for table in ("exercise_defaults", "routine_exercises"):
    for operation in ("insert", "update"):
        name = table + "_basis_" + operation
        UNIFIED_OBJECTS[name] = UNIFIED_OBJECTS[name].replace(
            "NEW.measurement_type!='time'",
            "(NEW.measurement_type!='time' AND (NEW.capabilities IS NULL OR (NEW.capabilities & 1)!=0))",
        )
ADDITIONS = {}
for table, parent in (
    ("workout_sets", "workout_entries"),
    ("historical_sets", "historical_entries"),
):
    ADDITIONS[
        table
    ] = f"""CREATE TABLE {table} (
        entry_id TEXT NOT NULL REFERENCES {parent}(id) ON DELETE CASCADE,
        set_index INTEGER NOT NULL CHECK(set_index BETWEEN 0 AND 999),
        status TEXT NOT NULL CHECK(status IN ('incomplete','completed','skipped')),
        actual_reps INTEGER CHECK(actual_reps BETWEEN 0 AND 10000),
        actual_duration_seconds INTEGER CHECK(actual_duration_seconds>0),
        PRIMARY KEY(entry_id,set_index),
        CHECK(status!='skipped' OR (actual_reps IS NULL AND actual_duration_seconds IS NULL))
    ) STRICT"""
    for operation in ("INSERT", "UPDATE"):
        name = f"{table}_{operation.lower()}_valid"
        ADDITIONS[
            name
        ] = f"""CREATE TRIGGER {name} BEFORE {operation} ON {table}
          WHEN NOT EXISTS(SELECT 1 FROM {parent} e WHERE e.id=NEW.entry_id
            AND e.capabilities IS NOT NULL AND e.measurement_type='flex' AND NEW.set_index<e.target_sets
            AND ((e.capabilities & 2)!=0 OR NEW.actual_reps IS NULL)
            AND ((e.capabilities & 4)!=0 OR NEW.actual_duration_seconds IS NULL)
            AND (NEW.status!='completed' OR (((e.capabilities & 1)=0 OR e.actual_weight_tenths_lb IS NOT NULL)
              AND ((e.capabilities & 2)=0 OR NEW.actual_reps IS NOT NULL)
              AND ((e.capabilities & 4)=0 OR NEW.actual_duration_seconds IS NOT NULL))))
          BEGIN SELECT RAISE(ABORT,'Invalid capability set result'); END"""
    condition = (
        "(SELECT s.status FROM workout_entries e JOIN workout_sessions s ON s.id=e.session_id WHERE e.id=OLD.entry_id)!='draft'"
        if table == "workout_sets"
        else "1"
    )
    for operation in ("UPDATE", "DELETE"):
        name = f"{table}_{operation.lower()}_immutable"
        ADDITIONS[name] = (
            f"CREATE TRIGGER {name} BEFORE {operation} ON {table} WHEN deletion_in_progress()=0 AND ({condition}) BEGIN SELECT RAISE(ABORT,'Completed set results are immutable'); END"
        )
    ADDITIONS[table + "_identity_immutable"] = (
        f"CREATE TRIGGER {table}_identity_immutable BEFORE UPDATE ON {table} WHEN NEW.entry_id!=OLD.entry_id OR NEW.set_index!=OLD.set_index BEGIN SELECT RAISE(ABORT,'Set identity is immutable'); END"
    )
    if table == "workout_sets":
        ADDITIONS["workout_sets_insert_draft"] = (
            "CREATE TRIGGER workout_sets_insert_draft BEFORE INSERT ON workout_sets WHEN (SELECT s.status FROM workout_entries e JOIN workout_sessions s ON s.id=e.session_id WHERE e.id=NEW.entry_id)!='draft' BEGIN SELECT RAISE(ABORT,'Cannot add completed sets'); END"
        )
for table in ("workout_entries", "historical_entries"):
    name = table + "_capabilities_immutable"
    ADDITIONS[name] = (
        f"CREATE TRIGGER {name} BEFORE UPDATE OF capabilities ON {table} BEGIN SELECT RAISE(ABORT,'Immutable measurement capabilities'); END"
    )
ADDITIONS[
    "unified_completion_validated"
] = """CREATE TRIGGER unified_completion_validated BEFORE UPDATE OF status ON workout_sessions
  WHEN NEW.status='completed' AND EXISTS(SELECT 1 FROM workout_entries e WHERE e.session_id=NEW.id AND e.measurement_type='flex' AND
    ((SELECT count(*) FROM workout_sets r WHERE r.entry_id=e.id)!=e.target_sets
      OR EXISTS(SELECT 1 FROM workout_sets r WHERE r.entry_id=e.id AND r.status='incomplete')
      OR (e.actual_weight_tenths_lb IS NOT NULL AND NOT EXISTS(SELECT 1 FROM workout_sets r WHERE r.entry_id=e.id AND r.status='completed'))
      OR ((e.capabilities & 1)!=0 AND e.actual_weight_tenths_lb IS NULL AND EXISTS(SELECT 1 FROM workout_sets r WHERE r.entry_id=e.id AND r.status='completed'))))
  BEGIN SELECT RAISE(ABORT,'Resolve all required sets before completion'); END"""
ADDITIONS[
    "body_weights"
] = """CREATE TABLE body_weights (
    id TEXT PRIMARY KEY NOT NULL,
    person_id TEXT NOT NULL REFERENCES people(id) ON DELETE RESTRICT,
    weight_milli_lb INTEGER NOT NULL CHECK(weight_milli_lb>0),
    measured_at TEXT NOT NULL,
    source TEXT NOT NULL CHECK(source IN ('manual','garmin')),
    external_id TEXT,
    source_value TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    revision INTEGER NOT NULL DEFAULT 0 CHECK(revision>=0),
    UNIQUE(person_id,source,external_id),
    CHECK((source='manual' AND external_id IS NULL) OR (source='garmin' AND external_id IS NOT NULL))
) STRICT"""
ADDITIONS["body_weights_person_time"] = (
    "CREATE INDEX body_weights_person_time ON body_weights(person_id,measured_at,id)"
)
ADDITIONS[
    "body_weight_audit"
] = """CREATE TABLE body_weight_audit (
    id TEXT PRIMARY KEY NOT NULL,
    record_id TEXT NOT NULL,
    person_id TEXT NOT NULL REFERENCES people(id) ON DELETE RESTRICT,
    changed_at TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK(revision>0),
    before_json TEXT,
    after_json TEXT,
    UNIQUE(record_id,revision),
    CHECK(before_json IS NOT NULL OR after_json IS NOT NULL)
) STRICT"""
for operation in ("UPDATE", "DELETE"):
    name = "body_weight_audit_" + operation.lower() + "_protected"
    ADDITIONS[name] = (
        f"CREATE TRIGGER {name} BEFORE {operation} ON body_weight_audit BEGIN SELECT RAISE(ABORT,'Append-only body-weight audit'); END"
    )
ADDITIONS[
    "workout_weighin_prompts"
] = """CREATE TABLE workout_weighin_prompts (
    session_id TEXT PRIMARY KEY NOT NULL REFERENCES workout_sessions(id) ON DELETE CASCADE,
    acknowledged_at TEXT NOT NULL
) STRICT"""
UNIFIED_OBJECTS.update(ADDITIONS)


def upgrade_unified(db):
    """Change only a copied candidate; preserve old snapshots, values and audit JSON."""
    triggers = db.execute(
        "SELECT name FROM sqlite_schema WHERE type='trigger'"
    ).fetchall()
    for (name,) in triggers:
        db.execute(f'DROP TRIGGER "{name}"')
    for table in CHANGED:
        columns = ",".join(
            '"' + r[1] + '"' for r in db.execute(f"PRAGMA table_info({table})")
        )
        db.execute(f"CREATE TEMP TABLE preserved_{table} AS SELECT * FROM {table}")
        db.execute(f"DROP TABLE {table}")
        db.execute(UNIFIED_OBJECTS[table])
        db.execute(
            f"INSERT INTO {table}({columns}) SELECT {columns} FROM preserved_{table}"
        )
        db.execute(f"DROP TABLE preserved_{table}")
    # Current configurations gain capabilities; original historical entries do
    # not, so old one-value durations and unknown sets stay explicitly legacy.
    for table in ("exercise_defaults", "routine_exercises"):
        db.execute(
            f"UPDATE {table} SET capabilities=CASE measurement_type WHEN 'weight' THEN 3 WHEN 'time' THEN 4 ELSE 5 END"
        )
    for name, sql in UNIFIED_OBJECTS.items():
        if name in ADDITIONS or sql.startswith("CREATE TRIGGER"):
            db.execute(sql)
