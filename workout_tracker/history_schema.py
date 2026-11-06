# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""Schema 4 additions executed only on separate migration candidates.

Phase 3 tables/triggers stay unchanged. Historical sessions have their own
immutable tables; a registry links both sources for ownership-safe, append-only
corrections. Prepared snapshots/submission IDs give manual entry retry safety.
"""

from .workout_schema import WORKOUT_TABLES

HISTORY_TABLES = {
    'historical_forms': """CREATE TABLE historical_forms (
        id TEXT PRIMARY KEY NOT NULL,
        person_id TEXT NOT NULL REFERENCES people(id) ON DELETE RESTRICT,
        routine_id TEXT NOT NULL,
        routine_name TEXT NOT NULL,
        timezone TEXT NOT NULL,
        workout_date TEXT NOT NULL,
        workout_time TEXT,
        occurred_at TEXT,
        prepared_at TEXT NOT NULL,
        snapshots_json TEXT NOT NULL,
        UNIQUE(id,person_id),
        FOREIGN KEY(routine_id,person_id) REFERENCES routines(id,person_id) ON DELETE RESTRICT
    ) STRICT""",
    'historical_workouts': """CREATE TABLE historical_workouts (
        id TEXT PRIMARY KEY NOT NULL,
        person_id TEXT NOT NULL,
        routine_id TEXT NOT NULL,
        routine_name TEXT NOT NULL,
        timezone TEXT NOT NULL,
        workout_date TEXT NOT NULL,
        workout_time TEXT,
        occurred_at TEXT,
        entered_at TEXT NOT NULL,
        form_id TEXT NOT NULL UNIQUE,
        entry_count INTEGER NOT NULL CHECK(entry_count > 0),
        UNIQUE(id,person_id),
        FOREIGN KEY(person_id) REFERENCES people(id) ON DELETE RESTRICT,
        FOREIGN KEY(routine_id,person_id) REFERENCES routines(id,person_id) ON DELETE RESTRICT,
        FOREIGN KEY(form_id,person_id) REFERENCES historical_forms(id,person_id) ON DELETE RESTRICT,
        CHECK((workout_time IS NULL AND occurred_at IS NULL) OR (workout_time IS NOT NULL AND occurred_at IS NOT NULL))
    ) STRICT""",
    'historical_entries': WORKOUT_TABLES['workout_entries'].replace('CREATE TABLE workout_entries', 'CREATE TABLE historical_entries').replace('REFERENCES workout_sessions(id,person_id)', 'REFERENCES historical_workouts(id,person_id)'),
    'workout_registry': """CREATE TABLE workout_registry (
        id TEXT PRIMARY KEY NOT NULL,
        person_id TEXT NOT NULL,
        live_session_id TEXT,
        historical_session_id TEXT,
        UNIQUE(id,person_id),
        FOREIGN KEY(live_session_id,person_id) REFERENCES workout_sessions(id,person_id) ON DELETE RESTRICT,
        FOREIGN KEY(historical_session_id,person_id) REFERENCES historical_workouts(id,person_id) ON DELETE RESTRICT,
        CHECK((live_session_id IS NOT NULL AND historical_session_id IS NULL AND id=live_session_id)
           OR (historical_session_id IS NOT NULL AND live_session_id IS NULL AND id=historical_session_id))
    ) STRICT""",
    'workout_corrections': """CREATE TABLE workout_corrections (
        id TEXT PRIMARY KEY NOT NULL,
        workout_id TEXT NOT NULL,
        person_id TEXT NOT NULL,
        revision INTEGER NOT NULL CHECK(revision >= 1),
        corrected_at TEXT NOT NULL,
        before_json TEXT NOT NULL,
        after_json TEXT NOT NULL,
        UNIQUE(workout_id,revision),
        FOREIGN KEY(workout_id,person_id) REFERENCES workout_registry(id,person_id) ON DELETE RESTRICT
    ) STRICT""",
}
HISTORY_OBJECTS = HISTORY_TABLES | {
    'register_completed_workout': """CREATE TRIGGER register_completed_workout AFTER UPDATE OF status ON workout_sessions
        WHEN NEW.status='completed' BEGIN
        INSERT INTO workout_registry(id,person_id,live_session_id) VALUES (NEW.id,NEW.person_id,NEW.id); END""",
    'register_historical_workout': """CREATE TRIGGER register_historical_workout AFTER INSERT ON historical_workouts BEGIN
        INSERT INTO workout_registry(id,person_id,historical_session_id) VALUES (NEW.id,NEW.person_id,NEW.id); END""",
    'correction_revision_guard': """CREATE TRIGGER correction_revision_guard BEFORE INSERT ON workout_corrections
        WHEN NEW.revision != (SELECT coalesce(max(revision),0)+1 FROM workout_corrections WHERE workout_id=NEW.workout_id)
        BEGIN SELECT RAISE(ABORT,'Correction revision must append the next version'); END""",
    'registry_completed_guard': """CREATE TRIGGER registry_completed_guard BEFORE INSERT ON workout_registry
        WHEN NEW.live_session_id IS NOT NULL AND (SELECT status FROM workout_sessions WHERE id=NEW.live_session_id) != 'completed'
        BEGIN SELECT RAISE(ABORT,'Only completed workouts may have corrections'); END""",
    'historical_entry_insert_guard': """CREATE TRIGGER historical_entry_insert_guard BEFORE INSERT ON historical_entries
        WHEN NEW.position >= (SELECT entry_count FROM historical_workouts WHERE id=NEW.session_id)
          OR EXISTS(SELECT 1 FROM workout_corrections WHERE workout_id=NEW.session_id)
        BEGIN SELECT RAISE(ABORT,'Historical snapshot is finalized'); END""",
}
# Updates/deletions are forbidden for every append-only record, including audit
# records themselves. No existing Phase 3 immutability trigger is removed.
for table in HISTORY_TABLES:
    for operation in ('UPDATE', 'DELETE'):
        name = f'{table}_{operation.lower()}_protected'
        HISTORY_OBJECTS[name] = f"CREATE TRIGGER {name} BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT,'Append-only history record'); END"
