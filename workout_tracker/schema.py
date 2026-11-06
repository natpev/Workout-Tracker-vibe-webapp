# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""Phase 2 DDL imported by storage validation and candidate-only migration.

These constants describe people, permanent exercise definitions and routine
configuration. There are deliberately no workout/result tables. sqlite3 executes
these statements only in a newly copied candidate, never the selected original.
"""

PHASE2_TABLES = {
    "people": """CREATE TABLE people (
        id TEXT PRIMARY KEY NOT NULL,
        name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 100),
        archived INTEGER NOT NULL DEFAULT 0 CHECK(archived IN (0, 1))
    ) STRICT""",
    "exercises": """CREATE TABLE exercises (
        id TEXT PRIMARY KEY NOT NULL,
        person_id TEXT NOT NULL REFERENCES people(id) ON DELETE RESTRICT,
        name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 100),
        archived INTEGER NOT NULL DEFAULT 0 CHECK(archived IN (0, 1)),
        UNIQUE(id, person_id)
    ) STRICT""",
    "routines": """CREATE TABLE routines (
        id TEXT PRIMARY KEY NOT NULL,
        person_id TEXT NOT NULL REFERENCES people(id) ON DELETE RESTRICT,
        name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 100),
        position INTEGER NOT NULL CHECK(position >= 0),
        archived INTEGER NOT NULL DEFAULT 0 CHECK(archived IN (0, 1)),
        UNIQUE(id, person_id),
        UNIQUE(person_id, position)
    ) STRICT""",
    "routine_exercises": """CREATE TABLE routine_exercises (
        id TEXT PRIMARY KEY NOT NULL,
        person_id TEXT NOT NULL,
        routine_id TEXT NOT NULL,
        exercise_id TEXT NOT NULL,
        position INTEGER NOT NULL CHECK(position >= 0),
        measurement_type TEXT NOT NULL CHECK(measurement_type IN ('weight', 'time')),
        target_sets INTEGER NOT NULL CHECK(target_sets BETWEEN 1 AND 1000),
        target_reps INTEGER,
        target_duration_seconds INTEGER,
        unit TEXT,
        weight_meaning TEXT NOT NULL DEFAULT '' CHECK(length(weight_meaning) <= 200),
        notes TEXT NOT NULL DEFAULT '' CHECK(length(notes) <= 2000),
        FOREIGN KEY(routine_id, person_id) REFERENCES routines(id, person_id) ON DELETE RESTRICT,
        FOREIGN KEY(exercise_id, person_id) REFERENCES exercises(id, person_id) ON DELETE RESTRICT,
        UNIQUE(routine_id, position),
        CHECK((measurement_type = 'weight' AND target_reps IS NOT NULL
               AND target_reps BETWEEN 1 AND 10000 AND target_duration_seconds IS NULL
               AND unit IS NOT NULL AND unit = 'lb')
           OR (measurement_type = 'time' AND target_reps IS NULL
               AND target_duration_seconds IS NOT NULL
               AND target_duration_seconds BETWEEN 1 AND 359999 AND unit IS NULL
               AND weight_meaning = ''))
    ) STRICT""",
}
