# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""Schema 3 constants imported by candidate migration and exact validation.

Only migration executes this DDL on a separate candidate. Sessions own complete
exercise snapshots; constraints protect NULL skips, ownership and typed values.
Completed/discarded snapshots cannot be edited through ordinary SQL operations.
"""

WORKOUT_TABLES = {
    "workout_sessions": """CREATE TABLE workout_sessions (
        id TEXT PRIMARY KEY NOT NULL,
        person_id TEXT NOT NULL REFERENCES people(id) ON DELETE RESTRICT,
        routine_id TEXT NOT NULL,
        routine_name TEXT NOT NULL,
        timezone TEXT NOT NULL,
        workout_date TEXT NOT NULL,
        started_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        finished_at TEXT,
        discarded_at TEXT,
        status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','completed','discarded')),
        revision INTEGER NOT NULL DEFAULT 0 CHECK(revision >= 0),
        entry_count INTEGER NOT NULL CHECK(entry_count > 0),
        current_position INTEGER NOT NULL DEFAULT 0 CHECK(current_position >= 0 AND current_position < entry_count),
        FOREIGN KEY(routine_id,person_id) REFERENCES routines(id,person_id) ON DELETE RESTRICT,
        UNIQUE(id,person_id),
        CHECK((status='draft' AND finished_at IS NULL AND discarded_at IS NULL)
           OR (status='completed' AND finished_at IS NOT NULL AND discarded_at IS NULL)
           OR (status='discarded' AND finished_at IS NULL AND discarded_at IS NOT NULL))
    ) STRICT""",
    "workout_entries": """CREATE TABLE workout_entries (
        id TEXT PRIMARY KEY NOT NULL,
        session_id TEXT NOT NULL,
        person_id TEXT NOT NULL,
        exercise_id TEXT NOT NULL,
        name TEXT NOT NULL,
        position INTEGER NOT NULL CHECK(position >= 0),
        measurement_type TEXT NOT NULL CHECK(measurement_type IN ('weight','time')),
        target_sets INTEGER NOT NULL CHECK(target_sets BETWEEN 1 AND 1000),
        target_reps INTEGER,
        target_duration_seconds INTEGER,
        unit TEXT,
        weight_meaning TEXT NOT NULL,
        notes TEXT NOT NULL,
        actual_weight_tenths_lb INTEGER CHECK(actual_weight_tenths_lb >= 0),
        actual_duration_seconds INTEGER CHECK(actual_duration_seconds >= 1),
        increase_next_time INTEGER CHECK(increase_next_time IN (0,1)),
        FOREIGN KEY(session_id,person_id) REFERENCES workout_sessions(id,person_id) ON DELETE RESTRICT,
        FOREIGN KEY(exercise_id,person_id) REFERENCES exercises(id,person_id) ON DELETE RESTRICT,
        UNIQUE(session_id,position),
        CHECK((measurement_type='weight' AND target_reps IS NOT NULL AND target_reps BETWEEN 1 AND 10000
                AND target_duration_seconds IS NULL AND unit IS NOT NULL AND unit='lb' AND actual_duration_seconds IS NULL)
           OR (measurement_type='time' AND target_reps IS NULL AND target_duration_seconds IS NOT NULL
                AND target_duration_seconds BETWEEN 1 AND 359999 AND unit IS NULL AND weight_meaning=''
                AND actual_weight_tenths_lb IS NULL)),
        CHECK((actual_weight_tenths_lb IS NULL AND actual_duration_seconds IS NULL AND increase_next_time IS NULL)
           OR ((actual_weight_tenths_lb IS NOT NULL OR actual_duration_seconds IS NOT NULL) AND increase_next_time IS NOT NULL))
    ) STRICT""",
}
WORKOUT_OBJECTS = WORKOUT_TABLES | {
    "one_active_workout": "CREATE UNIQUE INDEX one_active_workout ON workout_sessions(person_id) WHERE status='draft'",
    "finished_session_immutable": """CREATE TRIGGER finished_session_immutable BEFORE UPDATE ON workout_sessions
        WHEN OLD.status != 'draft' BEGIN SELECT RAISE(ABORT,'Finished session is immutable'); END""",
    "session_delete_protected": """CREATE TRIGGER session_delete_protected BEFORE DELETE ON workout_sessions
        BEGIN SELECT RAISE(ABORT,'Sessions must be retained'); END""",
    "entry_snapshot_immutable": """CREATE TRIGGER entry_snapshot_immutable BEFORE UPDATE ON workout_entries
        WHEN OLD.id IS NOT NEW.id OR OLD.session_id IS NOT NEW.session_id OR OLD.person_id IS NOT NEW.person_id
          OR OLD.exercise_id IS NOT NEW.exercise_id OR OLD.name IS NOT NEW.name OR OLD.position IS NOT NEW.position
          OR OLD.measurement_type IS NOT NEW.measurement_type OR OLD.target_sets IS NOT NEW.target_sets
          OR OLD.target_reps IS NOT NEW.target_reps OR OLD.target_duration_seconds IS NOT NEW.target_duration_seconds
          OR OLD.unit IS NOT NEW.unit OR OLD.weight_meaning IS NOT NEW.weight_meaning OR OLD.notes IS NOT NEW.notes
          OR (SELECT status FROM workout_sessions WHERE id=OLD.session_id) != 'draft'
        BEGIN SELECT RAISE(ABORT,'Workout snapshot is immutable'); END""",
    "entry_delete_protected": """CREATE TRIGGER entry_delete_protected BEFORE DELETE ON workout_entries
        BEGIN SELECT RAISE(ABORT,'Snapshot entries must be retained'); END""",
    "entry_insert_protected": """CREATE TRIGGER entry_insert_protected BEFORE INSERT ON workout_entries
        WHEN (SELECT status FROM workout_sessions WHERE id=NEW.session_id) != 'draft'
          OR NEW.position >= (SELECT entry_count FROM workout_sessions WHERE id=NEW.session_id)
        BEGIN SELECT RAISE(ABORT,'Invalid snapshot insertion'); END""",
    "session_completion_validated": """CREATE TRIGGER session_completion_validated BEFORE UPDATE OF status ON workout_sessions
        WHEN NEW.status='completed' AND (SELECT count(*) FROM workout_entries WHERE session_id=OLD.id) != OLD.entry_count
        BEGIN SELECT RAISE(ABORT,'Incomplete workout snapshot'); END""",
}
