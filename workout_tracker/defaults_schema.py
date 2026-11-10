# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Schema 7 adds global defaults without rebuilding any existing table or history.

Explicit migration creates this table on a candidate and initializes conservative
3x12 weight defaults. Existing per-routine configurations are never inferred or
rewritten. Deleting the global identity cascades only its editable defaults.
"""
from .deletion_schema import DELETION_OBJECTS

DEFAULT_TABLE="""CREATE TABLE exercise_defaults (
    exercise_id TEXT PRIMARY KEY NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
    measurement_type TEXT NOT NULL CHECK(measurement_type IN ('weight','time')),
    target_sets INTEGER NOT NULL CHECK(target_sets BETWEEN 1 AND 1000),
    target_reps INTEGER,
    target_duration_seconds INTEGER,
    unit TEXT,
    weight_meaning TEXT NOT NULL DEFAULT '' CHECK(length(weight_meaning)<=200),
    notes TEXT NOT NULL DEFAULT '' CHECK(length(notes)<=2000),
    CHECK((measurement_type='weight' AND target_reps IS NOT NULL AND target_reps BETWEEN 1 AND 10000
           AND target_duration_seconds IS NULL AND unit IS NOT NULL AND unit='lb')
       OR (measurement_type='time' AND target_reps IS NULL AND target_duration_seconds IS NOT NULL
           AND target_duration_seconds BETWEEN 1 AND 359999 AND unit IS NULL AND weight_meaning=''))
) STRICT"""
DEFAULT_OBJECTS=DELETION_OBJECTS | {'exercise_defaults':DEFAULT_TABLE}


def upgrade_defaults(db):
    """Add one default row per identity on the candidate; preserve every old cell."""
    db.execute(DEFAULT_TABLE)
    db.execute("INSERT INTO exercise_defaults SELECT id,'weight',3,12,NULL,'lb','','' FROM exercises")
