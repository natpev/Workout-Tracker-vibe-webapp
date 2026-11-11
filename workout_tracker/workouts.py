# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Workout rules called by routes with a locked schema-3 transaction.

Browser -> Flask -> these services -> SQLite. Starts copy complete snapshots;
updates require the last revision; finish saves pending input and status in the
same transaction. Callers own commit/rollback, so failed changes never erase a
previously saved draft. Actual values are integers or SQL NULL, never floats.
"""

from datetime import datetime, timezone
from pathlib import Path
import re
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from . import catalog
from .storage import StorageError

MAX_INTEGER = 9223372036854775807


class RevisionConflict(catalog.ValidationError):
    """Another browser saved first; the stale page must reload before writing."""


class AllSkipped(catalog.ValidationError):
    """An entirely skipped workout needs an additional explicit acknowledgment."""


def configured_timezone(value=None):
    """Use explicit IANA config or the server's local zone, with UTC fallback.

    Linux /etc/timezone or /etc/localtime supplies a stable zone name including
    DST rules. Do not infer the household server's zone from a browser's zone.
    """
    if not value:
        local = Path('/etc/localtime').resolve().as_posix()
        if '/zoneinfo/' in local:
            value = local.split('/zoneinfo/', 1)[1]
        elif Path('/etc/timezone').is_file():
            value = Path('/etc/timezone').read_text().strip()
        else:
            value = 'UTC'
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError, TypeError) as error:
        raise StorageError("WORKOUT_TIMEZONE must name an installed IANA timezone.") from error
    return value


def now():
    """Return an aware UTC instant; tests may freeze this without real data."""
    return datetime.now(timezone.utc)


def field(values, name):
    """Accept bounded plain strings from form/JSON data, never implicit coercion."""
    result = values.get(name, '')
    if not isinstance(result, str) or len(result) > 100:
        raise catalog.ValidationError(f"Invalid {name} input.")
    return result.strip()


def weight_tenths(value):
    """Convert exact decimal pounds to tenths by truncation; blank is SQL NULL."""
    if value == '':
        return None
    if not re.fullmatch(r'(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)', value):
        raise catalog.ValidationError("Enter a nonnegative weight in pounds.")
    whole, _, fraction = value.partition('.')
    result = int(whole or '0') * 10 + int((fraction + '0')[0])
    if result > MAX_INTEGER:
        raise catalog.ValidationError("Weight exceeds the supported integer-tenths storage limit.")
    return result


def duration_seconds(minutes, seconds):
    """Normalize optional minute/second parts while preserving two-blank skips."""
    from .durations import parse_duration
    try:return parse_duration(minutes,seconds,MAX_INTEGER)
    except ValueError as error:raise catalog.ValidationError(str(error)) from error


class MeasurementError(catalog.ValidationError):
    """Expose safe field messages while leaving invalid pairs uncommitted."""
    def __init__(self, fields):
        """Carry input names for live and historical inline error rendering."""
        self.fields = fields
        super().__init__(' '.join(dict.fromkeys(fields.values())))


def measurement(entry, values):
    """Validate typed actuals atomically; combined entries need both or neither.

    A half-entered pair remains visible in the browser but cannot be committed
    as performed or skipped. No historical/default measurement is substituted.
    """
    kind = entry['measurement_type']; errors = {}; weight = duration = None
    if kind in ('weight','weight_duration'):
        try:weight = weight_tenths(field(values,'weight'))
        except catalog.ValidationError as error:errors['weight'] = str(error)
    if kind in ('time','weight_duration'):
        try:duration = duration_seconds(field(values,'minutes'),field(values,'seconds'))
        except catalog.ValidationError as error:
            errors.update(minutes=str(error),seconds=str(error))
    if kind == 'weight_duration' and (weight is None) != (duration is None):
        message = 'Enter both weight and a positive duration, or leave both blank to skip.'
        if weight is None:errors.setdefault('weight',message)
        if duration is None:
            errors.setdefault('minutes',message);errors.setdefault('seconds',message)
    flag = field(values,'increase')
    if flag not in ('','0','1'):errors['increase'] = 'Invalid increase recommendation.'
    if errors:raise MeasurementError(errors)
    increase = None if weight is None and duration is None else int(flag == '1')
    return weight,duration,increase


def active(db, person_id):
    """Find this person's one draft; the unique partial index is the final guard."""
    return db.execute("SELECT * FROM workout_sessions WHERE person_id=? AND status='draft'", (person_id,)).fetchone()


def session(db, person_id, session_id):
    """Read owned sessions even if a person was archived; never cross owners."""
    catalog.person(db, person_id, archived=True)
    row = db.execute("SELECT * FROM workout_sessions WHERE id=? AND person_id=?", (session_id, person_id)).fetchone()
    if row is None:
        raise catalog.MissingRecord("Workout not found for this person.")
    return row


def entries(db, person_id, session_id):
    """Read the whole ordered snapshot and verify no exercises are missing."""
    parent = session(db, person_id, session_id)
    rows = db.execute("SELECT * FROM workout_entries WHERE session_id=? AND person_id=? ORDER BY position",
                      (session_id, person_id)).fetchall()
    if len(rows) != parent['entry_count'] or [r['position'] for r in rows] != list(range(len(rows))):
        raise StorageError("Workout snapshot consistency verification failed.")
    from .repetitions import decode
    return [decode(row) for row in rows]


def start(db, person_id, routine_id, zone):
    """Start once, copying every configuration with blank actual measurements.

    A retry or second start while a draft exists returns that same draft for
    explicit resume/discard. No routine edit can later change copied fields.
    """
    catalog.person(db, person_id)
    routine = catalog.routine(db, person_id, routine_id)
    existing = active(db, person_id)
    if existing:
        return existing['id'], False
    rows = db.execute("SELECT re.*,e.name FROM routine_exercises re JOIN exercises e ON e.id=re.exercise_id "
                      "WHERE re.routine_id=? ORDER BY re.position", (routine_id,)).fetchall()
    if not rows:
        raise catalog.ValidationError("Add at least one exercise before starting this routine.")
    stamp = now()
    identity = uuid4().hex
    db.execute("INSERT INTO workout_sessions(id,person_id,routine_id,routine_name,timezone,workout_date,"
               "started_at,updated_at,entry_count) VALUES (?,?,?,?,?,?,?,?,?)",
               (identity, person_id, routine_id, routine['name'], zone, stamp.astimezone(ZoneInfo(zone)).date().isoformat(),
                stamp.isoformat(), stamp.isoformat(), len(rows)))
    modern=db.execute('PRAGMA user_version').fetchone()[0]>=9
    for position, row in enumerate(rows):
        columns="id,session_id,person_id,exercise_id,name,position,measurement_type,target_sets,target_reps,target_duration_seconds,unit,weight_meaning,notes"
        values=(uuid4().hex,identity,person_id,row['exercise_id'],row['name'],position,row['measurement_type'],row['target_sets'],row['target_reps'],row['target_duration_seconds'],row['unit'],row['weight_meaning'],row['notes'])
        if modern:columns+=",weight_basis";values+= (row['weight_basis'],)
        if db.execute('PRAGMA user_version').fetchone()[0]>=10 and row['measurement_type']=='weight':
            from .repetitions import encode
            columns+=',actual_reps_json';values+=(encode([row['target_reps']]*row['target_sets']),)
        db.execute(f"INSERT INTO workout_entries({columns}) VALUES ({','.join('?' for _ in values)})",values)
    return identity, True


def revision(parent, value):
    """Reject stale tabs before writes; revisions advance only on committed saves."""
    if not isinstance(value, str) or not re.fullmatch('[0-9]{1,19}', value) or int(value) != parent['revision']:
        raise RevisionConflict("This workout changed in another tab. Reload before saving; your unsaved input is still visible.")


def update(db, person_id, session_id, values):
    """Persist actuals and a Next-only navigation checkpoint with revision protection."""
    parent = session(db, person_id, session_id)
    if parent['status'] != 'draft':
        raise RevisionConflict("This workout is no longer a draft. Reload to view its final state.")
    revision(parent, field(values, 'revision'))
    rows = entries(db, person_id, session_id)
    entry_id = field(values, 'entry_id')
    current = next((row for row in rows if row['id'] == entry_id), None)
    if current is None:
        raise catalog.MissingRecord("Workout exercise not found in this person's snapshot.")
    position = catalog.integer(field(values, 'current_position'), 'Exercise position', 0, len(rows) - 1)
    action = field(values, 'navigation_action')
    if action not in ('', 'next', 'back', 'jump'):
        raise catalog.ValidationError('Choose a valid workout navigation action.')
    if action == 'next' and position != current['position'] + 1:
        raise catalog.ValidationError('Next must move to the following exercise.')
    if action == 'back' and position != current['position'] - 1:
        raise catalog.ValidationError('Back must move to the previous exercise.')
    # This existing column is the furthest acknowledged Next destination, not
    # a measurement count. Repeated/revisited Next requests cannot count twice.
    checkpoint = max(parent['current_position'], position) if action == 'next' else parent['current_position']
    weight, duration, increase = measurement(current, values)
    db.execute("UPDATE workout_entries SET actual_weight_tenths_lb=?,actual_duration_seconds=?,increase_next_time=? "
               "WHERE id=? AND session_id=? AND person_id=?", (weight, duration, increase, entry_id, session_id, person_id))
    if db.execute('PRAGMA user_version').fetchone()[0]>=10:
        from .repetitions import inputs, encode
        try:
            actual=inputs(current,values)
        except catalog.ValidationError as error:
            raise MeasurementError({'actual_reps':str(error)}) from error
        db.execute('UPDATE workout_entries SET actual_reps_json=? WHERE id=?',(encode(actual),entry_id))
    db.execute("UPDATE workout_sessions SET revision=revision+1,current_position=?,updated_at=? WHERE id=? AND person_id=?",
               (checkpoint, now().isoformat(), session_id, person_id))
    return session(db, person_id, session_id)


def count_performed(rows):
    """Count non-NULL actual values; explicit zero weight counts, navigation does not."""
    return sum(row['actual_weight_tenths_lb'] is not None or row['actual_duration_seconds'] is not None for row in rows)


def finish(db, person_id, session_id, values):
    """Atomically persist pending input and complete once, retaining every NULL row.

    Completed retry requests return the existing confirmation without another
    session or write. Stale or invalid pending data roll back as a whole.
    """
    parent = session(db, person_id, session_id)
    if parent['status'] == 'completed':
        return parent
    parent = update(db, person_id, session_id, values)
    rows = entries(db, person_id, session_id)
    if count_performed(rows) == 0 and values.get('confirm_all_skipped') != 'yes':
        raise AllSkipped("Confirm that you want to save an entirely skipped workout.")
    if db.execute('PRAGMA user_version').fetchone()[0]>=10:
        from .repetitions import encode
        for row in rows:
            actual=row.get('actual_reps')
            if row['measurement_type']=='weight' and row['actual_weight_tenths_lb'] is not None and actual is None:
                actual=[row['target_reps']]*row['target_sets']
            if row['actual_weight_tenths_lb'] is None:
                actual=None
            db.execute('UPDATE workout_entries SET actual_reps_json=? WHERE id=?',(encode(actual),row['id']))
    stamp = now().isoformat()
    db.execute("UPDATE workout_sessions SET status='completed',finished_at=?,updated_at=? WHERE id=? AND person_id=?",
               (stamp, stamp, session_id, person_id))
    return session(db, person_id, session_id)


def discard(db, person_id, session_id, values):
    """Discard only an active draft after acknowledgment and a matching revision."""
    parent = session(db, person_id, session_id)
    if parent['status'] != 'draft':
        raise RevisionConflict("Only an unfinished workout may be discarded.")
    revision(parent, field(values, 'revision'))
    if values.get('confirm') != 'yes':
        raise catalog.ValidationError("Acknowledge the discard warning before choosing OK.")
    stamp = now().isoformat()
    db.execute("UPDATE workout_sessions SET status='discarded',discarded_at=?,updated_at=?,revision=revision+1 "
               "WHERE id=? AND person_id=?", (stamp, stamp, session_id, person_id))


def previous(db, person_id, parent, entry):
    """Find comparable completed entries only, before this session's start.

    Permanent exercise ID, type, unit and weight meaning prevent pounds/time or
    cross-person comparisons. An immediately previous skip and last performed
    result are kept separate; previous values never become today's defaults.
    """
    if db.execute('PRAGMA user_version').fetchone()[0] >= 4:
        from .history import previous_comparable
        return previous_comparable(db, person_id, parent, entry)
    rows = db.execute("SELECT e.*,s.workout_date,s.started_at FROM workout_entries e "
                      "JOIN workout_sessions s ON s.id=e.session_id WHERE e.person_id=? AND e.exercise_id=? "
                      "AND e.measurement_type=? AND e.unit IS ? AND e.weight_meaning=? AND s.status='completed' "
                      "AND s.started_at < ? ORDER BY s.started_at DESC,s.id DESC,e.position DESC",
                      (person_id, entry['exercise_id'], entry['measurement_type'], entry['unit'],
                       entry['weight_meaning'], parent['started_at'])).fetchall()
    return (rows[0] if rows else None,
            next((row for row in rows if count_performed([row])), None))


def display_measurement(entry):
    """Format exact stored integers for the browser, including zero and skips."""
    if entry is None:
        return 'No previous performance'
    weight, duration = entry['actual_weight_tenths_lb'], entry['actual_duration_seconds']
    if weight is not None and duration is not None:
        meaning = entry['weight_meaning'] if 'weight_meaning' in entry.keys() else ''
        return f"{weight // 10}.{weight % 10} lb{(' ' + meaning) if meaning else ''} · {duration // 60}:{duration % 60:02d}"
    if weight is not None:
        return f"{weight // 10}.{weight % 10} lb"
    if duration is not None:
        return f"{duration // 60:02d}:{duration % 60:02d}"
    return 'Skipped'
