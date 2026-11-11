# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Schema 9 is installed only on an explicitly copied migration candidate.

Four existing tables gain an independent basis column. Original cells, free-text
meanings and all immutable guards remain. New append-only transition/entry audits
link to ordinary correction revisions, avoiding a second numerical read layer.
"""
from .combined_schema import COMBINED_OBJECTS,CHANGED_TABLES

BASIS_OBJECTS=dict(COMBINED_OBJECTS)
for name in CHANGED_TABLES:
    BASIS_OBJECTS[name]=COMBINED_OBJECTS[name].replace('measurement_type TEXT',"weight_basis TEXT NOT NULL DEFAULT 'not_configured' CHECK(weight_basis IN ('not_configured','total','per_side')) CHECK(measurement_type!='time' OR weight_basis='not_configured'),\n        measurement_type TEXT")
BASIS_TABLES={
 'basis_transitions':'''CREATE TABLE basis_transitions (
    id TEXT PRIMARY KEY NOT NULL CHECK(length(id)=32),
    person_id TEXT NOT NULL REFERENCES people(id) ON DELETE RESTRICT,
    exercise_id TEXT NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
    revision INTEGER NOT NULL CHECK(revision>0),
    old_basis TEXT NOT NULL CHECK(old_basis IN ('not_configured','total','per_side')),
    new_basis TEXT NOT NULL CHECK(new_basis IN ('not_configured','total','per_side')),
    created_at TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    payload_hash TEXT NOT NULL CHECK(length(payload_hash)=64),
    effects_json TEXT NOT NULL,
    UNIQUE(person_id,exercise_id,revision),
    CHECK(old_basis='not_configured' OR new_basis!='not_configured')
 ) STRICT''',
 'basis_assignments':'''CREATE TABLE basis_assignments (
    transition_id TEXT NOT NULL REFERENCES basis_transitions(id) ON DELETE CASCADE,
    workout_id TEXT NOT NULL,
    person_id TEXT NOT NULL,
    exercise_id TEXT NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
    entry_id TEXT NOT NULL,
    before_basis TEXT NOT NULL CHECK(before_basis IN ('not_configured','total','per_side')),
    after_basis TEXT NOT NULL CHECK(after_basis IN ('total','per_side')),
    before_weight INTEGER CHECK(before_weight IS NULL OR before_weight>=0),
    after_weight INTEGER CHECK(after_weight IS NULL OR after_weight>=0),
    correction_id TEXT NOT NULL REFERENCES workout_corrections(id) ON DELETE CASCADE,
    PRIMARY KEY(transition_id,workout_id,entry_id),
    FOREIGN KEY(workout_id,person_id) REFERENCES workout_registry(id,person_id) ON DELETE CASCADE,
    CHECK((before_weight IS NULL)=(after_weight IS NULL)),
    CHECK(before_basis!=after_basis)
 ) STRICT''',
 'historical_basis_immutable':"CREATE TRIGGER historical_basis_immutable BEFORE UPDATE OF weight_basis ON historical_entries BEGIN SELECT RAISE(ABORT,'Immutable original basis'); END",
 'workout_basis_immutable':"CREATE TRIGGER workout_basis_immutable BEFORE UPDATE OF weight_basis ON workout_entries BEGIN SELECT RAISE(ABORT,'Immutable original basis'); END",
 'basis_entry_lookup': 'CREATE INDEX basis_entry_lookup ON basis_assignments(person_id,workout_id,entry_id)',
 'basis_transition_order':'''CREATE TRIGGER basis_transition_order BEFORE INSERT ON basis_transitions
    WHEN NEW.revision!=(SELECT coalesce(max(revision),0)+1 FROM basis_transitions WHERE person_id=NEW.person_id AND exercise_id=NEW.exercise_id)
    OR NEW.old_basis!=coalesce((SELECT new_basis FROM basis_transitions WHERE person_id=NEW.person_id AND exercise_id=NEW.exercise_id ORDER BY revision DESC LIMIT 1),'not_configured')
    BEGIN SELECT RAISE(ABORT,'Basis revisions must append from the actual baseline'); END''',
 'basis_assignment_identity':'''CREATE TRIGGER basis_assignment_identity BEFORE INSERT ON basis_assignments
    WHEN NOT EXISTS(SELECT 1 FROM basis_transitions WHERE id=NEW.transition_id AND person_id=NEW.person_id AND exercise_id=NEW.exercise_id)
      OR NOT EXISTS(SELECT 1 FROM workout_corrections WHERE id=NEW.correction_id AND workout_id=NEW.workout_id AND person_id=NEW.person_id)
      OR (NOT EXISTS(SELECT 1 FROM workout_entries e JOIN workout_sessions s ON s.id=e.session_id WHERE e.id=NEW.entry_id AND e.session_id=NEW.workout_id AND e.person_id=NEW.person_id AND e.exercise_id=NEW.exercise_id AND e.measurement_type IN ('weight','weight_duration') AND s.status='completed')
          AND NOT EXISTS(SELECT 1 FROM historical_entries WHERE id=NEW.entry_id AND session_id=NEW.workout_id AND person_id=NEW.person_id AND exercise_id=NEW.exercise_id AND measurement_type IN ('weight','weight_duration')))
    BEGIN SELECT RAISE(ABORT,'Basis assignment ownership or completed identity mismatch'); END''',
}
for table in ('basis_transitions','basis_assignments'):
    for operation in ('UPDATE','DELETE'):
        name=f'{table}_{operation.lower()}_protected'
        condition=' WHEN deletion_in_progress()=0' if operation=='DELETE' else ''
        BASIS_TABLES[name]=f"CREATE TRIGGER {name} BEFORE {operation} ON {table}{condition} BEGIN SELECT RAISE(ABORT,'Append-only basis audit'); END"
BASIS_OBJECTS.update(BASIS_TABLES)


def upgrade_basis(db):
    """Rebuild candidate tables with explicit original-column copying, then restore guards."""
    triggers=db.execute("SELECT name,sql FROM sqlite_schema WHERE type='trigger'").fetchall()
    for name,_ in triggers:db.execute(f'DROP TRIGGER "{name}"')
    for name in CHANGED_TABLES:
        columns=','.join('"'+r[1]+'"' for r in db.execute(f'PRAGMA table_info({name})'))
        db.execute(f'CREATE TEMP TABLE preserved_{name} AS SELECT * FROM {name}')
        db.execute(f'DROP TABLE {name}')
        db.execute(BASIS_OBJECTS[name])
        db.execute(f'INSERT INTO {name}({columns}) SELECT {columns} FROM preserved_{name}')
        db.execute(f'DROP TABLE preserved_{name}')
    for _,sql in triggers:db.execute(sql)
    for sql in BASIS_TABLES.values():db.execute(sql)
