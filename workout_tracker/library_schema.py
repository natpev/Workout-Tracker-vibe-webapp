# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Schema 5 shared references used by exact validation and candidate migration.

Exercise person_id remains registration provenance, preserving every old value;
it is no longer an ownership boundary. Routine and workout owners stay unchanged.
Only the three exercise foreign keys change; immutable snapshot triggers remain.
"""
from .schema import PHASE2_TABLES
from .workout_schema import WORKOUT_OBJECTS
from .history_schema import HISTORY_OBJECTS

LOCAL_REFERENCE = "FOREIGN KEY(exercise_id,person_id) REFERENCES exercises(id,person_id) ON DELETE RESTRICT"
GLOBAL_REFERENCE = "FOREIGN KEY(exercise_id) REFERENCES exercises(id) ON DELETE RESTRICT"
LIBRARY_OBJECTS = {
    name: sql.replace("FOREIGN KEY(exercise_id, person_id) REFERENCES exercises(id, person_id) ON DELETE RESTRICT", GLOBAL_REFERENCE).replace(LOCAL_REFERENCE, GLOBAL_REFERENCE)
    for name, sql in (PHASE2_TABLES | WORKOUT_OBJECTS | HISTORY_OBJECTS).items()
}
CHANGED_TABLES = ('routine_exercises', 'workout_entries', 'historical_entries')


def upgrade_library(connection):
    """Rebuild candidate tables only, copying every column without conversion.

    Caller disabled foreign keys before BEGIN, while holding the root lock.
    Trigger DDL is retained exactly and reinstalled after the copied snapshots;
    this does not expose any unprotected connection to application requests.
    """
    triggers = connection.execute("SELECT name,sql FROM sqlite_schema WHERE type='trigger'").fetchall()
    for name, _ in triggers:
        connection.execute(f'DROP TRIGGER "{name}"')
    for name in CHANGED_TABLES:
        connection.execute(f'CREATE TEMP TABLE preserved_{name} AS SELECT * FROM {name}')
        connection.execute(f'DROP TABLE {name}')
        connection.execute(LIBRARY_OBJECTS[name])
        connection.execute(f'INSERT INTO {name} SELECT * FROM preserved_{name}')
        connection.execute(f'DROP TABLE preserved_{name}')
    for _, sql in triggers:
        connection.execute(sql)
