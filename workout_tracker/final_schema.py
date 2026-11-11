# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Schema 10: permanent Library conventions and nullable ordered actual reps.

Only explicit migration executes DDL on a separate candidate. Immutable original
basis, meanings and conversion audits remain for verification and recovery.
"""
from .basis_schema import BASIS_OBJECTS

FINAL_OBJECTS = dict(BASIS_OBJECTS)
for table in ('workout_entries', 'historical_entries'):
    FINAL_OBJECTS[table] = BASIS_OBJECTS[table].replace('measurement_type TEXT',
        'actual_reps_json TEXT CHECK(actual_reps_json IS NULL OR (measurement_type=\'weight\' AND json_valid(actual_reps_json) AND json_type(actual_reps_json)=\'array\')),\n        measurement_type TEXT', 1)

LOCKS = {}
for table in ('exercise_defaults', 'routine_exercises'):
    name = table + '_basis_locked'
    LOCKS[name] = f"""CREATE TRIGGER {name} BEFORE UPDATE ON {table}
        WHEN NEW.weight_basis IS NOT OLD.weight_basis
          OR (NEW.measurement_type='time') != (OLD.measurement_type='time')
        BEGIN SELECT RAISE(ABORT,'Weight Basis is permanent; create a new exercise'); END"""
    for operation in ('INSERT', 'UPDATE'):
        name = table + '_basis_' + operation.lower()
        predicate = "EXISTS(SELECT 1 FROM exercise_defaults d WHERE d.exercise_id=NEW.exercise_id AND d.weight_basis=NEW.weight_basis AND (d.measurement_type='time')=(NEW.measurement_type='time'))"
        invalid = "(NEW.measurement_type!='time' AND NEW.weight_basis NOT IN ('total','per_side'))" if table=='exercise_defaults' else f'NOT ({predicate})'
        LOCKS[name] = f"CREATE TRIGGER {name} BEFORE {operation} ON {table} WHEN {invalid} BEGIN SELECT RAISE(ABORT,'Choose the permanent Library Weight Basis'); END"
for table in ('basis_transitions', 'basis_assignments'):
    name = table + '_closed'
    LOCKS[name] = f"CREATE TRIGGER {name} BEFORE INSERT ON {table} BEGIN SELECT RAISE(ABORT,'Historical conversions are closed'); END"
for table in ('workout_entries', 'historical_entries'):
    for operation in ('INSERT', 'UPDATE'):
        name=table+'_repetitions_'+operation.lower()
        LOCKS[name]=f"""CREATE TRIGGER {name} BEFORE {operation} ON {table}
          WHEN NEW.actual_reps_json IS NOT NULL AND
            (json_array_length(NEW.actual_reps_json)!=NEW.target_sets OR
             EXISTS(SELECT 1 FROM json_each(NEW.actual_reps_json) WHERE type!='integer' OR value<0 OR value>10000))
          BEGIN SELECT RAISE(ABORT,'Invalid actual repetitions'); END"""
LOCKS['final_completion_repetitions']="""CREATE TRIGGER final_completion_repetitions BEFORE UPDATE OF status ON workout_sessions
  WHEN NEW.status='completed' AND EXISTS(SELECT 1 FROM workout_entries WHERE session_id=NEW.id AND
    ((actual_weight_tenths_lb IS NULL AND actual_reps_json IS NOT NULL) OR
     (measurement_type='weight' AND actual_weight_tenths_lb IS NOT NULL AND actual_reps_json IS NULL)))
  BEGIN SELECT RAISE(ABORT,'Completed repetitions must match performed or skipped state'); END"""
LOCKS['final_historical_repetitions']="""CREATE TRIGGER final_historical_repetitions BEFORE INSERT ON historical_entries
  WHEN (NEW.actual_weight_tenths_lb IS NULL AND NEW.actual_reps_json IS NOT NULL) OR
       (NEW.measurement_type='weight' AND NEW.actual_weight_tenths_lb IS NOT NULL AND NEW.actual_reps_json IS NULL)
  BEGIN SELECT RAISE(ABORT,'Historical repetitions must match performed or skipped state'); END"""
FINAL_OBJECTS.update(LOCKS)


def classifications(db):
    """Refuse unclassified configurations/drafts/effective history without guessing.

    Library defaults take precedence for conflicts in current routines. Historical
    snapshots keep their own effective bases, including archived conversions.
    """
    from .storage import StorageError
    from .history import all_completed
    for table in ('exercise_defaults', 'routine_exercises'):
        row=db.execute(f"SELECT exercise_id FROM {table} WHERE measurement_type!='time' AND weight_basis='not_configured' LIMIT 1").fetchone()
        if row:
            raise StorageError(f'Exercise {row[0]} must be classified using Update 1 first ({table}).')
    row=db.execute("SELECT e.exercise_id FROM workout_entries e JOIN workout_sessions s ON s.id=e.session_id WHERE s.status='draft' AND e.measurement_type!='time' AND e.weight_basis='not_configured' LIMIT 1").fetchone()
    if row:
        raise StorageError(f'Exercise {row[0]} has an unclassified draft; finish it and classify using Update 1 first.')
    for person, in db.execute('SELECT id FROM people'):
        for parent, rows in all_completed(db, person):
            for row in rows:
                if row['measurement_type']!='time' and row['weight_basis']=='not_configured':
                    raise StorageError(f"Exercise {row['exercise_id']} in workout {parent['id']} must be classified using Update 1 first.")
    # A duration-only Library definition cannot supply a permanent basis for a
    # weighted routine. No convention is inferred for incompatible mode families.
    bad=db.execute("SELECT r.exercise_id FROM routine_exercises r JOIN exercise_defaults d ON d.exercise_id=r.exercise_id WHERE (r.measurement_type='time')!=(d.measurement_type='time') LIMIT 1").fetchone()
    if bad:
        raise StorageError(f'Exercise {bad[0]} has incompatible Library/routine measurement types. Resolve in Update 1 first.')


def upgrade_final(db):
    """Preserve old cells on a candidate, align routine bases, install final guards."""
    previous=db.row_factory
    import sqlite3
    db.row_factory=sqlite3.Row
    # Earlier migration stages run in this same transaction; enable their reader.
    db.execute('PRAGMA user_version=9')
    classifications(db)
    triggers=db.execute("SELECT name,sql FROM sqlite_schema WHERE type='trigger'").fetchall()
    for name,_ in triggers:
        db.execute(f'DROP TRIGGER "{name}"')
    for table in ('workout_entries','historical_entries'):
        columns=','.join('"'+r[1]+'"' for r in db.execute(f'PRAGMA table_info({table})'))
        db.execute(f'CREATE TEMP TABLE preserved_{table} AS SELECT * FROM {table}')
        db.execute(f'DROP TABLE {table}')
        db.execute(FINAL_OBJECTS[table])
        db.execute(f'INSERT INTO {table}({columns}) SELECT {columns} FROM preserved_{table}')
        db.execute(f'DROP TABLE preserved_{table}')
    db.execute('UPDATE routine_exercises SET weight_basis=(SELECT weight_basis FROM exercise_defaults WHERE exercise_id=routine_exercises.exercise_id)')
    for _,sql in triggers:
        db.execute(sql)
    for sql in LOCKS.values():
        db.execute(sql)
    db.row_factory=previous


def validate_final(db):
    """Verify final configuration and repetition invariants during storage checks."""
    from .storage import StorageError
    from .repetitions import decode
    try:
        for table in ('workout_entries','historical_entries'):
            for row in db.execute(f'SELECT * FROM {table}'):
                decoded=decode(row)
                if table=='historical_entries' and row['actual_weight_tenths_lb'] is None and decoded['actual_reps'] is not None:
                    raise ValueError('Skipped historical repetitions must be NULL')
        for table in ('exercise_defaults','routine_exercises'):
            if db.execute(f"SELECT 1 FROM {table} WHERE measurement_type!='time' AND weight_basis='not_configured'").fetchone():
                raise ValueError('Unclassified configuration')
        if db.execute('SELECT 1 FROM routine_exercises r JOIN exercise_defaults d ON d.exercise_id=r.exercise_id WHERE r.weight_basis!=d.weight_basis OR (r.measurement_type=\'time\')!=(d.measurement_type=\'time\')').fetchone():
            raise ValueError('Conflicting Library basis')
    except (ValueError,TypeError,KeyError) as error:
        raise StorageError('Permanent basis or actual repetition validation failed.') from error
