# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Schema 8 permits paired weight/duration without adding result columns.

Only the explicit migrator rebuilds these four tables on its private candidate.
Old schema constants stay intact so retained databases are still exactly verified.
All original cells and protection triggers are copied without reinterpretation.
"""
import re
from .defaults_schema import DEFAULT_OBJECTS

CHANGED_TABLES = ('routine_exercises', 'workout_entries', 'historical_entries', 'exercise_defaults')


def combined_table(sql, actual):
    """Extend the balanced type CHECK; preserve every unrelated column/constraint."""
    sql = re.sub(r"IN \('weight',\s*'time'\)", "IN ('weight','time','weight_duration')", sql)
    start = sql.index('CHECK((measurement_type')
    depth = 0
    for end in range(start + len('CHECK'), len(sql)):
        depth += (sql[end] == '(') - (sql[end] == ')')
        if depth == 0:
            break
    clause = """ OR (measurement_type='weight_duration' AND target_reps IS NULL
        AND target_duration_seconds IS NOT NULL AND target_duration_seconds BETWEEN 1 AND 359999
        AND unit IS NOT NULL AND unit='lb'"""
    if actual:
        # Explicit NULL tests avoid SQLite's rule that CHECK(NULL) passes.
        clause += """ AND ((actual_weight_tenths_lb IS NULL AND actual_duration_seconds IS NULL)
          OR (actual_weight_tenths_lb IS NOT NULL AND actual_duration_seconds IS NOT NULL))"""
    return sql[:end] + clause + ')' + sql[end:]


COMBINED_OBJECTS = dict(DEFAULT_OBJECTS)
for name in CHANGED_TABLES:
    COMBINED_OBJECTS[name] = combined_table(DEFAULT_OBJECTS[name], name in ('workout_entries', 'historical_entries'))


def upgrade_combined(db):
    """Rebuild only candidate tables; reinstall identical immutable/ownership guards.

    The caller holds the root lock, disabled candidate FKs before BEGIN, and
    will compare all cells, integrity, FKs, exact DDL and audit chains before
    activation. No application connection can observe this intermediate state.
    """
    triggers = db.execute("SELECT name,sql FROM sqlite_schema WHERE type='trigger'").fetchall()
    for name, _ in triggers:
        db.execute(f'DROP TRIGGER "{name}"')
    for name in CHANGED_TABLES:
        db.execute(f'CREATE TEMP TABLE preserved_{name} AS SELECT * FROM {name}')
        db.execute(f'DROP TABLE {name}')
        db.execute(COMBINED_OBJECTS[name])
        db.execute(f'INSERT INTO {name} SELECT * FROM preserved_{name}')
        db.execute(f'DROP TABLE preserved_{name}')
    for _, sql in triggers:
        db.execute(sql)
