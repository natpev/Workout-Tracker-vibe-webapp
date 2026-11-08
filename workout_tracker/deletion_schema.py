# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""Schema 6 candidate DDL: detached routine snapshots and explicit deletion guards.

Storage validates this exact DDL. Normal connections register a deny-by-default
capability; only the confirmed deletion service enables it temporarily within
one locked transaction. No permanent flag or startup schema edit is used.
"""
import re
from .library_schema import LIBRARY_OBJECTS


def guarded(sql):
    """Retain each original trigger predicate with a connection-local capability gate."""
    prefix, body = re.split(r'\bBEGIN\b', sql, maxsplit=1)
    parts = re.split(r'\bWHEN\b', prefix, maxsplit=1)
    condition = f' AND ({parts[1].strip()})' if len(parts) == 2 else ''
    return parts[0].rstrip() + ' WHEN deletion_in_progress()=0' + condition + ' BEGIN' + body


DELETION_OBJECTS = dict(LIBRARY_OBJECTS)
for name in ('workout_sessions', 'historical_forms', 'historical_workouts'):
    DELETION_OBJECTS[name] = DELETION_OBJECTS[name].replace(
        '        FOREIGN KEY(routine_id,person_id) REFERENCES routines(id,person_id) ON DELETE RESTRICT,\n', ''
    ).replace(',\n        FOREIGN KEY(routine_id,person_id) REFERENCES routines(id,person_id) ON DELETE RESTRICT', '')
for name, sql in list(DELETION_OBJECTS.items()):
    if sql.startswith('CREATE TRIGGER') and ('RAISE(ABORT' in sql):
        DELETION_OBJECTS[name] = guarded(sql)

# Detaching historical routine references must not permit cross-person writes.
# New live sessions/forms still need an existing owned routine; a historical
# completion may outlive its routine but must match its owned prepared snapshot.
DELETION_OBJECTS.update({
    'live_routine_owner_guard': """CREATE TRIGGER live_routine_owner_guard BEFORE INSERT ON workout_sessions
        WHEN NOT EXISTS(SELECT 1 FROM routines WHERE id=NEW.routine_id AND person_id=NEW.person_id)
        BEGIN SELECT RAISE(ABORT,'Routine ownership mismatch'); END""",
    'prepared_routine_owner_guard': """CREATE TRIGGER prepared_routine_owner_guard BEFORE INSERT ON historical_forms
        WHEN NOT EXISTS(SELECT 1 FROM routines WHERE id=NEW.routine_id AND person_id=NEW.person_id)
        BEGIN SELECT RAISE(ABORT,'Routine ownership mismatch'); END""",
    'historical_preparation_owner_guard': """CREATE TRIGGER historical_preparation_owner_guard BEFORE INSERT ON historical_workouts
        WHEN NOT EXISTS(SELECT 1 FROM historical_forms WHERE id=NEW.form_id AND person_id=NEW.person_id AND routine_id=NEW.routine_id)
        BEGIN SELECT RAISE(ABORT,'Historical preparation ownership mismatch'); END""",
})


def upgrade_deletion(connection):
    """Rebuild three candidate tables with exact cells; recreate all indexes/guards."""
    for name, in connection.execute("SELECT name FROM sqlite_schema WHERE type='trigger'").fetchall():
        connection.execute(f'DROP TRIGGER "{name}"')
    for name in ('workout_sessions', 'historical_forms', 'historical_workouts'):
        connection.execute(f'CREATE TEMP TABLE saved_{name} AS SELECT * FROM {name}')
        connection.execute(f'DROP TABLE {name}')
        connection.execute(DELETION_OBJECTS[name])
        connection.execute(f'INSERT INTO {name} SELECT * FROM saved_{name}')
        connection.execute(f'DROP TABLE saved_{name}')
    for name, sql in DELETION_OBJECTS.items():
        if sql.startswith('CREATE TRIGGER') or name == 'one_active_workout':
            connection.execute(sql)
