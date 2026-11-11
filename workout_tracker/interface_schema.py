# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Schema 11 candidate migration: durable artwork, dormant basis and partial drafts.

Only the explicit migrator rebuilds candidate tables. Every original cell/audit is
copied by name. New guards keep completed repetitions strict and basis immutable.
"""
from .final_schema import FINAL_OBJECTS

INTERFACE_OBJECTS=dict(FINAL_OBJECTS)
for name in ('exercise_defaults','routine_exercises'):
    INTERFACE_OBJECTS[name]=FINAL_OBJECTS[name].replace(" CHECK(measurement_type!='time' OR weight_basis='not_configured')",'')
for name in ('workout_entries','historical_entries'):
    INTERFACE_OBJECTS[name]=FINAL_OBJECTS[name].replace('measurement_type TEXT',"reps_required INTEGER NOT NULL DEFAULT 0 CHECK(reps_required IN (0,1)),\n        measurement_type TEXT",1)

ADDITIONS={
 'exercise_weight_basis':'''CREATE TABLE exercise_weight_basis (
    exercise_id TEXT PRIMARY KEY NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
    basis TEXT NOT NULL CHECK(basis IN ('total','per_side'))
 ) STRICT''',
 'exercise_icons':'''CREATE TABLE exercise_icons (
    exercise_id TEXT NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
    position TEXT NOT NULL CHECK(position IN ('start','end')),
    svg TEXT NOT NULL CHECK(length(svg) BETWEEN 1 AND 65536),
    PRIMARY KEY(exercise_id,position)
 ) STRICT''',
 'permanent_basis_update':"CREATE TRIGGER permanent_basis_update BEFORE UPDATE ON exercise_weight_basis BEGIN SELECT RAISE(ABORT,'Permanent Weight Basis cannot change'); END",
 'permanent_basis_delete':"CREATE TRIGGER permanent_basis_delete BEFORE DELETE ON exercise_weight_basis WHEN deletion_in_progress()=0 BEGIN SELECT RAISE(ABORT,'Permanent Weight Basis must be retained'); END",
}
for table in ('exercise_defaults','routine_exercises'):
    name=table+'_basis_locked'
    ADDITIONS[name]=f"""CREATE TRIGGER {name} BEFORE UPDATE ON {table}
       WHEN OLD.weight_basis IN ('total','per_side') AND NEW.weight_basis!=OLD.weight_basis
       BEGIN SELECT RAISE(ABORT,'Weight Basis is permanent'); END"""
    for operation in ('INSERT','UPDATE'):
        name=table+'_basis_'+operation.lower()
        ADDITIONS[name]=f"""CREATE TRIGGER {name} BEFORE {operation} ON {table}
          WHEN (NEW.measurement_type!='time' AND NOT EXISTS(SELECT 1 FROM exercise_weight_basis b WHERE b.exercise_id=NEW.exercise_id AND b.basis=NEW.weight_basis))
            OR (NEW.weight_basis IN ('total','per_side') AND NOT EXISTS(SELECT 1 FROM exercise_weight_basis b WHERE b.exercise_id=NEW.exercise_id AND b.basis=NEW.weight_basis))
          BEGIN SELECT RAISE(ABORT,'Use the permanent exercise Weight Basis'); END"""
# Null elements represent unentered sets in live drafts only. Completed values
# remain bounded integers, including explicit zero, with no target substitution.
for operation in ('INSERT','UPDATE'):
    name='workout_entries_repetitions_'+operation.lower()
    ADDITIONS[name]=f"""CREATE TRIGGER {name} BEFORE {operation} ON workout_entries
      WHEN NEW.actual_reps_json IS NOT NULL AND
        (json_array_length(NEW.actual_reps_json)!=NEW.target_sets OR
         EXISTS(SELECT 1 FROM json_each(NEW.actual_reps_json) WHERE type NOT IN ('integer','null') OR (type='integer' AND (value<0 OR value>10000))))
      BEGIN SELECT RAISE(ABORT,'Invalid draft repetitions'); END"""
ADDITIONS['final_completion_repetitions']="""CREATE TRIGGER final_completion_repetitions BEFORE UPDATE OF status ON workout_sessions
  WHEN NEW.status='completed' AND EXISTS(SELECT 1 FROM workout_entries e WHERE e.session_id=NEW.id AND
    ((e.actual_weight_tenths_lb IS NULL AND e.actual_reps_json IS NOT NULL) OR
     (e.measurement_type='weight' AND e.actual_weight_tenths_lb IS NOT NULL AND
       (e.actual_reps_json IS NULL OR EXISTS(SELECT 1 FROM json_each(e.actual_reps_json) WHERE type!='integer')))))
  BEGIN SELECT RAISE(ABORT,'Record every performed set before completing'); END"""
for table in ('workout_entries','historical_entries'):
    ADDITIONS[table+'_rep_mode_immutable']=f"CREATE TRIGGER {table}_rep_mode_immutable BEFORE UPDATE OF reps_required ON {table} WHEN NEW.reps_required!=OLD.reps_required BEGIN SELECT RAISE(ABORT,'Immutable repetition mode'); END"
    ADDITIONS[table+'_rep_mode_insert']=f"CREATE TRIGGER {table}_rep_mode_insert BEFORE INSERT ON {table} WHEN NEW.reps_required!=(NEW.measurement_type='weight') BEGIN SELECT RAISE(ABORT,'New weight entries require actual repetitions'); END"
INTERFACE_OBJECTS.update(ADDITIONS)


def upgrade_interface(db):
    """Rebuild only four candidate tables; leave history, arrays and IDs unchanged."""
    triggers=db.execute("SELECT name,sql FROM sqlite_schema WHERE type='trigger'").fetchall()
    for name,_ in triggers:db.execute(f'DROP TRIGGER "{name}"')
    for table in ('exercise_defaults','routine_exercises','workout_entries','historical_entries'):
        columns=','.join('"'+row[1]+'"' for row in db.execute(f'PRAGMA table_info({table})'))
        db.execute(f'CREATE TEMP TABLE preserved_{table} AS SELECT * FROM {table}')
        db.execute(f'DROP TABLE {table}')
        db.execute(INTERFACE_OBJECTS[table])
        db.execute(f'INSERT INTO {table}({columns}) SELECT {columns} FROM preserved_{table}')
        db.execute(f'DROP TABLE preserved_{table}')
    db.execute(ADDITIONS['exercise_weight_basis']);db.execute(ADDITIONS['exercise_icons'])
    db.execute("INSERT INTO exercise_weight_basis SELECT exercise_id,weight_basis FROM exercise_defaults WHERE weight_basis IN ('total','per_side')")
    db.execute("UPDATE workout_entries SET reps_required=1 WHERE measurement_type='weight' AND session_id IN (SELECT id FROM workout_sessions WHERE status='draft')")
    for name,sql in triggers:
        if name not in ADDITIONS:db.execute(sql)
    for name,sql in ADDITIONS.items():
        if name not in ('exercise_weight_basis','exercise_icons'):db.execute(sql)


def validate_interface(db):
    """Read-only invariants reused by startup, candidate verification and backups."""
    from .storage import StorageError
    from .repetitions import decode
    from .exercise_icons import sanitize
    try:
        for table in ('exercise_defaults','routine_exercises'):
            for row in db.execute(f'SELECT c.*,b.basis FROM {table} c LEFT JOIN exercise_weight_basis b ON b.exercise_id=c.exercise_id'):
                if row['measurement_type']!='time' and row['weight_basis']!=row['basis']:
                    raise ValueError('Missing permanent basis')
                if row['weight_basis']!='not_configured' and row['weight_basis']!=row['basis']:
                    raise ValueError('Changed permanent basis')
        for row in db.execute('SELECT e.*,s.status FROM workout_entries e JOIN workout_sessions s ON s.id=e.session_id'):
            decoded=decode(row,partial=row['status']!='completed')
            if row['status']=='completed' and row['reps_required'] and row['actual_weight_tenths_lb'] is not None and decoded['actual_reps'] is None:
                raise ValueError('New completed weight entries require repetitions')
            if row['status']=='completed' and row['actual_weight_tenths_lb'] is None and row['actual_reps_json'] is not None:
                raise ValueError('Skipped repetitions must be NULL')
        for row in db.execute('SELECT * FROM historical_entries'):
            decoded=decode(row)
            if row['reps_required'] and row['actual_weight_tenths_lb'] is not None and decoded['actual_reps'] is None:
                raise ValueError('New historical weight entries require repetitions')
        for row in db.execute('SELECT svg FROM exercise_icons'):
            if sanitize(row['svg'])!=row['svg']:raise ValueError('Noncanonical artwork')
    except (ValueError,TypeError,KeyError) as error:
        raise StorageError('Exercise artwork, basis or repetition integrity failed.') from error
