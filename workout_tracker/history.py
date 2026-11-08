# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""History services called by routes with an existing locked SQLite connection.

Completed Phase 3 records remain immutable. Historical records and correction
revisions are appended separately; all readers apply the latest correction in
memory. Actual occurrence and entry timestamps are distinct. Chart series use
permanent exercise/type/unit/meaning keys and never replace NULL with zero.
"""

from datetime import date, datetime, time, timezone
import json
import re
from uuid import uuid4
from zoneinfo import ZoneInfo

from . import catalog as c, workouts as w
from .storage import StorageError


def schema4(db):
    """Require explicit schema 4 without automatically upgrading existing storage."""
    if db.execute('PRAGMA user_version').fetchone()[0] < 4:
        raise StorageError('History requires an explicit target-4 migration.')


def json_text(value):
    """Serialize exact integers and NULLs deterministically for audit comparisons."""
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)


def parse_date(value):
    """Validate canonical ISO calendar dates from untrusted browser fields."""
    if not isinstance(value,str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}',value):
        raise c.ValidationError('Choose a valid workout date.')
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise c.ValidationError('Choose a valid workout date.') from error


def occurrence(day, clock, zone, fold=''):
    """Validate a past local date and optional time; never invent an unknown time.

    DST gaps are rejected. Repeated-hour times require an explicit earlier/later
    choice. Return local date/time plus an aware UTC instant only when known.
    """
    chosen=parse_date(day);local_now=w.now().astimezone(ZoneInfo(zone))
    if chosen>local_now.date():
        raise c.ValidationError('Workout date cannot be in the future.')
    if not clock:
        return day,None,None
    if not re.fullmatch(r'[0-9]{2}:[0-9]{2}(?::[0-9]{2})?',clock):
        raise c.ValidationError('Enter a valid time, or leave it blank if unknown.')
    try:
        naive=datetime.combine(chosen,time.fromisoformat(clock))
    except ValueError as error:
        raise c.ValidationError('Enter a valid workout time.') from error
    z=ZoneInfo(zone)
    candidates=[]
    for f in (0,1):
        candidate=naive.replace(tzinfo=z,fold=f)
        if candidate.astimezone(timezone.utc).astimezone(z).replace(tzinfo=None)==naive:
            candidates.append(candidate)
    if not candidates:
        raise c.ValidationError('That local time does not exist because clocks changed. Choose another time.')
    ambiguous=len({item.utcoffset() for item in candidates})>1
    if ambiguous and fold not in ('0','1'):
        raise c.ValidationError('This time occurred twice. Choose the earlier or later occurrence.')
    stamp=naive.replace(tzinfo=z,fold=int(fold) if ambiguous else 0)
    if stamp.astimezone(timezone.utc)>w.now().astimezone(timezone.utc):
        raise c.ValidationError('Workout time cannot be in the future.')
    return day,stamp.strftime('%H:%M:%S'),stamp.astimezone(timezone.utc).isoformat()


def original(db, person_id, identity):
    """Read one completed source and its snapshotted entries under owner checks."""
    schema4(db);c.person(db,person_id,archived=True)
    parent=db.execute("SELECT * FROM workout_sessions WHERE id=? AND person_id=? AND status='completed'",(identity,person_id)).fetchone()
    if parent:
        parent=dict(parent)
        local=datetime.fromisoformat(parent['started_at']).astimezone(ZoneInfo(parent['timezone']))
        parent.update(source='live',workout_time=local.strftime('%H:%M:%S'),occurred_at=parent['started_at'],entered_at=parent['finished_at'])
        rows=[dict(row) for row in w.entries(db,person_id,identity)]
    else:
        found=db.execute('SELECT * FROM historical_workouts WHERE id=? AND person_id=?',(identity,person_id)).fetchone()
        if not found:
            raise c.MissingRecord('Completed workout not found for this person.')
        parent=dict(found)
        parent.update(source='historical',status='completed',finished_at=parent['entered_at'],started_at=parent['occurred_at'])
        rows=[dict(row) for row in db.execute('SELECT * FROM historical_entries WHERE session_id=? AND person_id=? ORDER BY position',(identity,person_id))]
        if len(rows)!=parent['entry_count'] or [r['position'] for r in rows]!=list(range(len(rows))):
            raise StorageError('Historical snapshot consistency failed.')
    parent['routine_deleted'] = db.execute('SELECT 1 FROM routines WHERE id=? AND person_id=?',(parent['routine_id'],person_id)).fetchone() is None
    return parent,rows


def value_state(parent, rows):
    """Capture only correctable occurrence/measurement fields, not snapshot metadata."""
    return dict(workout_date=parent['workout_date'],workout_time=parent['workout_time'],occurred_at=parent['occurred_at'],
                entries=[{key:row[key] for key in ('id','actual_weight_tenths_lb','actual_duration_seconds','increase_next_time')} for row in rows])


def validate_state(parent, rows, values):
    """Reject malformed audit payloads before chart/history readers use any values.

    Snapshot IDs and fields are fixed. Only bounded integer actual values and
    consistent local date/optional aware time may pass the effective-value layer.
    """
    if set(values)!= {'workout_date','workout_time','occurred_at','entries'} or [r['id'] for r in values['entries']]!=[r['id'] for r in rows]:
        raise ValueError('Correction shape mismatch')
    parse_date(values['workout_date'])
    clock,instant=values['workout_time'],values['occurred_at']
    if (clock is None)!=(instant is None):
        raise ValueError('Correction date/time mismatch')
    if instant is not None:
        parsed=datetime.fromisoformat(instant)
        if parsed.tzinfo is None: raise ValueError('Correction time is not aware')
        local=parsed.astimezone(ZoneInfo(parent['timezone']))
        if local.date().isoformat()!=values['workout_date'] or local.strftime('%H:%M:%S')!=clock:
            raise ValueError('Correction date/time mismatch')
    for row,value in zip(rows,values['entries']):
        if set(value)!= {'id','actual_weight_tenths_lb','actual_duration_seconds','increase_next_time'}:
            raise ValueError('Correction fields mismatch')
        weight,duration,flag=(value[key] for key in ('actual_weight_tenths_lb','actual_duration_seconds','increase_next_time'))
        if weight is not None and (type(weight) is not int or not 0<=weight<=w.MAX_INTEGER):
            raise ValueError('Invalid audit weight')
        if duration is not None and (type(duration) is not int or not 1<=duration<=w.MAX_INTEGER):
            raise ValueError('Invalid audit duration')
        if row['measurement_type']=='weight' and duration is not None or row['measurement_type']=='time' and weight is not None:
            raise ValueError('Incompatible audit measurement')
        if weight is None and duration is None:
            if flag is not None: raise ValueError('Skipped audit flag')
        elif type(flag) is not int or flag not in (0,1):
            raise ValueError('Invalid audit flag')


def effective(db, person_id, identity):
    """Overlay latest appended values; original records and immutable fields stay intact."""
    parent,rows=original(db,person_id,identity)
    latest=db.execute('SELECT * FROM workout_corrections WHERE workout_id=? AND person_id=? ORDER BY revision DESC LIMIT 1',(identity,person_id)).fetchone()
    parent['correction_revision']=0
    if latest:
        try:
            values=json.loads(latest['after_json'])
            validate_state(parent,rows,values)
            for row,measurement in zip(rows,values['entries']):
                if set(measurement)!= {'id','actual_weight_tenths_lb','actual_duration_seconds','increase_next_time'}:
                    raise ValueError('Correction fields mismatch')
                row.update(measurement)
            parent.update({key:values[key] for key in ('workout_date','workout_time','occurred_at')})
            parent['correction_revision']=latest['revision']
        except (ValueError,TypeError,KeyError) as error:
            raise StorageError('Correction audit validation failed.') from error
    return parent,rows


def audit(db, person_id, identity):
    """Read immutable before/after values, ordered by correction sequence."""
    original(db,person_id,identity)
    return [dict(row, before=json.loads(row['before_json']),after=json.loads(row['after_json']))
            for row in db.execute('SELECT * FROM workout_corrections WHERE person_id=? AND workout_id=? ORDER BY revision',(person_id,identity))]


def chronology(parent):
    """Order by occurrence, not entry time; unknown times sort before known times that day."""
    clock=datetime.fromisoformat(parent['occurred_at']).astimezone(timezone.utc).isoformat(timespec='microseconds') if parent['occurred_at'] else ''
    return parent['workout_date'],clock,parent['entered_at'],parent['id']


def all_completed(db, person_id):
    """Unify completed native/manual sources; discarded and active drafts are excluded."""
    schema4(db);c.person(db,person_id,archived=True)
    identities=[row[0] for row in db.execute("SELECT id FROM workout_sessions WHERE person_id=? AND status='completed' UNION ALL SELECT id FROM historical_workouts WHERE person_id=?",(person_id,person_id))]
    return sorted([effective(db,person_id,identity) for identity in identities],key=lambda pair:chronology(pair[0]),reverse=True)


def filters(values):
    """Validate date filters once; lexical comparisons are safe for ISO dates."""
    start=values.get('from','');end=values.get('to','')
    if start: parse_date(start)
    if end: parse_date(end)
    if start and end and start>end:
        raise c.ValidationError('Start date must not be after end date.')
    return start,end,values.get('routine',''),values.get('exercise','')


def listing(db, person_id, values):
    """Filter effective sessions by date, original routine identity and exercise identity."""
    start,end,routine,exercise=filters(values)
    return [(parent,rows) for parent,rows in all_completed(db,person_id)
            if (not start or parent['workout_date']>=start) and (not end or parent['workout_date']<=end)
            and (not routine or parent['routine_id']==routine)
            and (not exercise or any(row['exercise_id']==exercise for row in rows))]


def choices(db, person_id):
    """Build filter options from retained snapshots, including removed definitions."""
    routines={};exercises={}
    for parent,rows in all_completed(db,person_id):
        routines.setdefault(parent['routine_id'],parent['routine_name'])
        for row in rows:
            exercises.setdefault(row['exercise_id'],row['name'])
    return routines,exercises


def chart_series(db, person_id, values):
    """Prepare separate series per permanent ID/type/unit/meaning, including zero.

    NULL rows are retained as skipped table records and excluded from numerical
    points and maxima. Target sets never multiply actual performance.
    """
    groups={}
    for parent,rows in reversed(listing(db,person_id,values)):
        for row in rows:
            if values.get('exercise') and row['exercise_id']!=values['exercise']:
                continue
            key=(row['exercise_id'],row['measurement_type'],row['unit'],row['weight_meaning'])
            series=groups.setdefault(key,dict(name=row['name'],kind=row['measurement_type'],meaning=row['weight_meaning'],exercise_id=row['exercise_id'],points=[],records=[],highest=None))
            value=row['actual_weight_tenths_lb'] if row['measurement_type']=='weight' else row['actual_duration_seconds']
            label=w.display_measurement(row)
            series['records'].append(dict(date=parent['workout_date'],time=parent['workout_time'],label=label,workout_id=parent['id']))
            if value is not None:
                point=dict(date=parent['workout_date'],time=parent['workout_time'],raw=value,label=label,
                           xday=date.fromisoformat(parent['workout_date']).toordinal()+_day_fraction(parent['workout_time']))
                series['points'].append(point)
                series['highest']=point if series['highest'] is None or value>series['highest']['raw'] else series['highest']
    for series in groups.values():
        points=series['points']
        if not points: continue
        low=min(p['xday'] for p in points);high=max(p['xday'] for p in points)
        top=max(p['raw'] for p in points) or 1
        for point in points:
            point['x']=130+(point['xday']-low)/(high-low or 1)*530
            point['y']=220-point['raw']/top*180
        series['line']=' '.join(f"{p['x']:.2f},{p['y']:.2f}" for p in points)
        series['top_label']=w.display_measurement({
            'actual_weight_tenths_lb':top if series['kind']=='weight' else None,
            'actual_duration_seconds':top if series['kind']=='time' else None})
    return list(groups.values())


def _day_fraction(clock):
    """Place known clock times within a day; unknown times are labeled as unknown."""
    if not clock: return 0
    parts=[int(part) for part in clock.split(':')]
    return (parts[0]*3600+parts[1]*60+(parts[2] if len(parts)>2 else 0))/86400


def prepare(db, person_id, routine_id, values, zone):
    """Append a fixed routine snapshot for historical review, without creating a draft."""
    schema4(db);routine=c.routine(db,person_id,routine_id)
    day,clock,stamp=occurrence(w.field(values,'workout_date'),w.field(values,'workout_time'),zone,w.field(values,'fold'))
    rows=[dict(row) for row in db.execute('SELECT re.*,e.name FROM routine_exercises re JOIN exercises e ON e.id=re.exercise_id WHERE re.routine_id=? ORDER BY re.position',(routine_id,))]
    if not rows: raise c.ValidationError('Choose a routine with at least one exercise.')
    identity=uuid4().hex
    db.execute('INSERT INTO historical_forms VALUES (?,?,?,?,?,?,?,?,?,?)',
               (identity,person_id,routine_id,routine['name'],zone,day,clock,stamp,w.now().isoformat(),json_text(rows)))
    return identity


def prepared(db, person_id, form_id):
    """Read an owned immutable preparation, independent of subsequent routine editing."""
    schema4(db);c.person(db,person_id,archived=True)
    row=db.execute('SELECT * FROM historical_forms WHERE id=? AND person_id=?',(form_id,person_id)).fetchone()
    if row is None: raise c.MissingRecord('Historical form not found for this person.')
    return dict(row),json.loads(row['snapshots_json'])


def entered_measurements(rows, values):
    """Validate every typed row before any completion/correction SQL is issued."""
    results=[]
    for index,row in enumerate(rows):
        fields={key:values.get(f'{key}_{index}','') for key in ('weight','minutes','seconds','increase')}
        weight,duration,flag=w.measurement(row,fields)
        results.append(dict(id=row['id'],actual_weight_tenths_lb=weight,actual_duration_seconds=duration,increase_next_time=flag))
    if not any(row['actual_weight_tenths_lb'] is not None or row['actual_duration_seconds'] is not None for row in results) and values.get('confirm_all_skipped')!='yes':
        raise w.AllSkipped('Confirm saving an entirely skipped workout.')
    return results


def complete_historical(db, person_id, form_id, values):
    """Create a complete historical session/entries atomically; retries reuse its ID.

    These tables do not use the one-active-draft index. The routine and original
    workout tables are never changed. The caller commits everything or nothing.
    """
    form,rows=prepared(db,person_id,form_id)
    existing=db.execute('SELECT id FROM historical_workouts WHERE form_id=? AND person_id=?',(form_id,person_id)).fetchone()
    if existing: return existing[0]
    measurements=entered_measurements(rows,values)
    identity=uuid4().hex
    db.execute('INSERT INTO historical_workouts VALUES (?,?,?,?,?,?,?,?,?,?,?)',
               (identity,person_id,form['routine_id'],form['routine_name'],form['timezone'],form['workout_date'],form['workout_time'],form['occurred_at'],w.now().isoformat(),form_id,len(rows)))
    for position,(row,result) in enumerate(zip(rows,measurements)):
        db.execute('INSERT INTO historical_entries(id,session_id,person_id,exercise_id,name,position,measurement_type,target_sets,target_reps,target_duration_seconds,unit,weight_meaning,notes,actual_weight_tenths_lb,actual_duration_seconds,increase_next_time) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                   (uuid4().hex,identity,person_id,row['exercise_id'],row['name'],position,row['measurement_type'],row['target_sets'],row['target_reps'],row['target_duration_seconds'],row['unit'],row['weight_meaning'],row['notes'],result['actual_weight_tenths_lb'],result['actual_duration_seconds'],result['increase_next_time']))
    return identity


def correct(db, person_id, identity, values):
    """Append before/after values after confirmation and compare-and-swap revision."""
    parent,rows=effective(db,person_id,identity)
    if values.get('confirm')!='yes':
        raise c.ValidationError('Confirm the correction before applying it.')
    if values.get('correction_revision')!=str(parent['correction_revision']):
        raise w.RevisionConflict('This workout was corrected in another page. Reload before applying changes.')
    day,clock,stamp=occurrence(w.field(values,'workout_date'),w.field(values,'workout_time'),parent['timezone'],w.field(values,'fold'))
    # The UI edits clock minutes only. An unchanged displayed minute must not
    # erase original seconds/microseconds during a measurement-only correction.
    if len(w.field(values,'workout_time'))==5 and day==parent['workout_date'] and clock and parent['workout_time'] and clock[:5]==parent['workout_time'][:5] and stamp and parent['occurred_at']:
        if datetime.fromisoformat(stamp).replace(second=0,microsecond=0)==datetime.fromisoformat(parent['occurred_at']).replace(second=0,microsecond=0):
            clock,stamp=parent['workout_time'],parent['occurred_at']
    same_instant = (stamp is None and parent['occurred_at'] is None) or (stamp is not None and parent['occurred_at'] is not None and datetime.fromisoformat(stamp).replace(microsecond=0)==datetime.fromisoformat(parent['occurred_at']).replace(microsecond=0))
    if day==parent['workout_date'] and clock==parent['workout_time'] and same_instant:
        # Preserve native fractional seconds only when the chosen instant is
        # unchanged. A repeated-hour fold change must retain its new UTC instant.
        stamp=parent['occurred_at']
    after=dict(workout_date=day,workout_time=clock,occurred_at=stamp,entries=entered_measurements(rows,values))
    before=value_state(parent,rows)
    if after==before:
        raise c.ValidationError('No corrected values were changed.')
    db.execute('INSERT INTO workout_corrections VALUES (?,?,?,?,?,?,?)',
               (uuid4().hex,identity,person_id,parent['correction_revision']+1,w.now().isoformat(),json_text(before),json_text(after)))
    return parent['correction_revision']+1


def previous_comparable(db, person_id, parent, entry):
    """Use effective chronology for backdated/corrected reference performance."""
    local=datetime.fromisoformat(parent['started_at']).astimezone(ZoneInfo(parent['timezone']))
    cutoff=(parent['workout_date'],local.strftime('%H:%M:%S'))
    matches=[]
    for workout,rows in all_completed(db,person_id):
        if workout['id']==parent['id']:
            continue
        if workout['occurred_at']:
            if datetime.fromisoformat(workout['occurred_at']) >= datetime.fromisoformat(parent['started_at']):
                continue
        elif (workout['workout_date'],'')>=cutoff:
            continue
        for row in reversed(rows):
            if all(row[key]==entry[key] for key in ('exercise_id','measurement_type','unit','weight_meaning')):
                matches.append(dict(row,workout_date=workout['workout_date']))
    return (matches[0] if matches else None,next((row for row in matches if w.count_performed([row])),None))
