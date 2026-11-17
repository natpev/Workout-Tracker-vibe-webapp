# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Schema 14 adds separate Ego Lifts; every released schema-13 object stays frozen."""
from .unified_schema import UNIFIED_OBJECTS

ADDITIONS = {
    "ego_lifts": """CREATE TABLE ego_lifts (
        id TEXT PRIMARY KEY, person_id TEXT NOT NULL REFERENCES people(id) ON DELETE RESTRICT,
        exercise_id TEXT NOT NULL REFERENCES exercises(id) ON DELETE RESTRICT,
        exercise_name TEXT NOT NULL, weight_basis TEXT NOT NULL CHECK(weight_basis IN ('total','per_side')),
        weight_meaning TEXT NOT NULL, weight_tenths_lb INTEGER NOT NULL CHECK(weight_tenths_lb>=0),
        repetitions INTEGER NOT NULL CHECK(repetitions BETWEEN 1 AND 10000),
        occurred_at TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        submission_id TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 0 CHECK(revision>=0),
        deleted INTEGER NOT NULL DEFAULT 0 CHECK(deleted IN (0,1)),
        UNIQUE(person_id,submission_id)
    ) STRICT""",
    "ego_lifts_person_exercise": "CREATE INDEX ego_lifts_person_exercise ON ego_lifts(person_id,exercise_id,occurred_at)",
    "ego_lift_audit": """CREATE TABLE ego_lift_audit (
        id TEXT PRIMARY KEY, lift_id TEXT NOT NULL REFERENCES ego_lifts(id) ON DELETE CASCADE,
        person_id TEXT NOT NULL REFERENCES people(id) ON DELETE RESTRICT,
        revision INTEGER NOT NULL CHECK(revision>0), changed_at TEXT NOT NULL,
        before_json TEXT, after_json TEXT NOT NULL, UNIQUE(lift_id,revision)
    ) STRICT""",
}
for operation in ("INSERT", "UPDATE"):
    name = "garmin_precision_" + operation.lower()
    ADDITIONS[
        name
    ] = f"""CREATE TRIGGER {name} BEFORE {operation} ON body_weights
      WHEN NEW.source='garmin' AND NEW.weight_milli_lb%100!=0
      BEGIN SELECT RAISE(ABORT,'Garmin weights require one decimal place'); END"""
ADDITIONS[
    "workout_set_checks"
] = """CREATE TABLE workout_set_checks (
    entry_id TEXT NOT NULL REFERENCES workout_entries(id) ON DELETE CASCADE,
    set_index INTEGER NOT NULL CHECK(set_index BETWEEN 0 AND 999),
    done INTEGER NOT NULL CHECK(done IN (0,1)), PRIMARY KEY(entry_id,set_index)
) STRICT"""
for operation in ("INSERT", "UPDATE"):
    name = "workout_set_checks_" + operation.lower()
    ADDITIONS[
        name
    ] = f"""CREATE TRIGGER {name} BEFORE {operation} ON workout_set_checks
      WHEN NOT EXISTS(SELECT 1 FROM workout_entries e JOIN workout_sessions s ON s.id=e.session_id
        WHERE e.id=NEW.entry_id AND e.capabilities=1 AND NEW.set_index<e.target_sets AND s.status='draft')
      BEGIN SELECT RAISE(ABORT,'Invalid weight-only draft checkbox'); END"""
ADDITIONS[
    "workout_set_checks_delete"
] = """CREATE TRIGGER workout_set_checks_delete BEFORE DELETE ON workout_set_checks
    WHEN deletion_in_progress()=0 AND EXISTS(SELECT 1 FROM workout_entries e JOIN workout_sessions s
      ON s.id=e.session_id WHERE e.id=OLD.entry_id AND s.status='completed')
    BEGIN SELECT RAISE(ABORT,'Completed draft checkbox is immutable'); END"""
for operation in ("UPDATE", "DELETE"):
    name = "ego_audit_no_" + operation.lower()
    ADDITIONS[
        name
    ] = f"""CREATE TRIGGER {name} BEFORE {operation} ON ego_lift_audit
        WHEN deletion_in_progress()=0 BEGIN SELECT RAISE(ABORT,'Ego audit is append-only'); END"""
ADDITIONS[
    "ego_identity_immutable"
] = """CREATE TRIGGER ego_identity_immutable BEFORE UPDATE ON ego_lifts
    WHEN NEW.id!=OLD.id OR NEW.person_id!=OLD.person_id OR NEW.exercise_id!=OLD.exercise_id
      OR NEW.exercise_name!=OLD.exercise_name OR NEW.weight_basis!=OLD.weight_basis
      OR NEW.weight_meaning!=OLD.weight_meaning OR NEW.occurred_at!=OLD.occurred_at
      OR NEW.created_at!=OLD.created_at OR NEW.submission_id!=OLD.submission_id
    BEGIN SELECT RAISE(ABORT,'Immutable Ego Lift identity'); END"""
ADDITIONS[
    "ego_delete_guard"
] = """CREATE TRIGGER ego_delete_guard BEFORE DELETE ON ego_lifts
    WHEN deletion_in_progress()=0 BEGIN SELECT RAISE(ABORT,'Use audited Ego deletion'); END"""
EGO_OBJECTS = UNIFIED_OBJECTS | ADDITIONS


def upgrade_ego(db):
    """Apply only to a disposable candidate, including the explicitly authorized Garmin rounding."""
    for sql in ADDITIONS.values():
        db.execute(sql)
    from .garmin import round_existing

    round_existing(db)
