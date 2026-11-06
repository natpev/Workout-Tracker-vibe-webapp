# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""Workout-service and schema tests use only disposable migrated fixtures.

Services run inside real SQLite transactions; failure tests assert committed
state survives bad input and stale revisions. No real workouts are accessed.
"""

from datetime import datetime, timezone
import sqlite3
from unittest.mock import patch

import pytest

from workout_tracker import catalog as c, workouts as w
from workout_tracker.storage import database_session


def seed(db):
    """Build two synthetic people and a mixed Weight/Time routine with fixed identity."""
    a, b = c.create_person(db, 'A'), c.create_person(db, 'B')
    routine = c.create_routine(db, a, 'Strength')
    first = c.add_entry(db, a, routine, dict(name='Bench',measurement_type='weight',target_sets='3',target_reps='12',notes='Slow'))
    c.add_entry(db, a, routine, dict(name='Plank',measurement_type='time',target_sets='3',minutes='0',seconds='45'))
    return a, b, routine, first


def data(db, person, identity, **values):
    """Build a valid blank-entry update at the current persisted revision."""
    parent = w.session(db, person, identity)
    rows = w.entries(db, person, identity)
    return dict(revision=str(parent['revision']),entry_id=rows[0]['id'],current_position='0',weight='',minutes='',seconds='',increase='', **values)


@pytest.mark.parametrize('raw,expected', [('40.99',409),('42.56',425),('40',400),('0',0),('0.09',0),('.5',5),('',None),('40.99999999999999',409)])
def test_weight_exact_truncation(raw, expected):
    """Extra digits truncate without float rounding; explicit zero differs from NULL."""
    assert w.weight_tenths(raw) == expected


@pytest.mark.parametrize('raw', ['-1','NaN','Infinity','1e3','1,2','abc','..5', '922337203685477581'])
def test_weight_rejects_malformed_and_out_of_range(raw):
    """Only finite nonnegative decimal text within SQLite's integer range is valid."""
    with pytest.raises(c.ValidationError):
        w.weight_tenths(raw)


@pytest.mark.parametrize('minutes,seconds,expected', [('','',None),('0','1',1),('0','45',45),('1','5',65),('2','0',120)])
def test_duration_conversion(minutes, seconds, expected):
    """One duration is stored in seconds regardless of set count."""
    assert w.duration_seconds(minutes, seconds) == expected


@pytest.mark.parametrize('minutes,seconds', [('0','0'),('','1'),('1',''),('-1','1'),('1','60'),('1','1.5'),('x','0')])
def test_duration_partial_zero_and_invalid(minutes, seconds):
    """Partially blank, zero and malformed durations must never become skips."""
    with pytest.raises(c.ValidationError):
        w.duration_seconds(minutes, seconds)


def test_start_snapshot_one_draft_timezone_and_independent_users(phase3_root):
    """Start records server-local date, snapshots and blank values; retry resumes."""
    with database_session(phase3_root, write=True) as db:
        a,b,r,item = seed(db)
        with patch.object(w, 'now', return_value=datetime(2026,1,2,2,0,tzinfo=timezone.utc)):
            identity, created = w.start(db,a,r,'America/Indiana/Indianapolis')
        assert created and w.session(db,a,identity)['workout_date'] == '2026-01-01'
        rows = w.entries(db,a,identity)
        assert w.count_performed(rows) == 0
        assert len(rows) == 2 and rows[0]['name'] == 'Bench' and rows[1]['target_duration_seconds'] == 45
        assert w.start(db,a,r,'UTC') == (identity,False)
        c.update_entry(db,a,r,item,dict(measurement_type='time',target_sets='5',minutes='1',seconds='0'))
        c.update_definition(db,a,rows[0]['exercise_id'],'Renamed','rename')
        db.execute('DELETE FROM routine_exercises WHERE id=?',(item,))
        db.execute('UPDATE routines SET archived=1 WHERE id=?',(r,))
        assert w.entries(db,a,identity)[0]['name'] == 'Bench'
        assert w.entries(db,a,identity)[0]['measurement_type'] == 'weight'
        copied = c.create_routine(db,b,'Independent')
        c.add_entry(db,b,copied,dict(name='Time',measurement_type='time',target_sets='1',minutes='0',seconds='1'))
        other,_ = w.start(db,b,copied,'UTC')
        assert other != identity and w.active(db,b)['id'] == other


def test_saves_progress_conflicts_and_completion_retries(phase3_root):
    """Zero counts; a stale revision cannot erase saved data; finish is idempotent."""
    with database_session(phase3_root,write=True) as db:
        a,b,r,_ = seed(db)
        identity,_ = w.start(db,a,r,'UTC')
        payload = data(db,a,identity)
        payload['weight']='0'
        payload['increase']='1'
        w.update(db,a,identity,payload)
        with pytest.raises(w.RevisionConflict):
            w.update(db,a,identity,payload)
        rows=w.entries(db,a,identity)
        assert rows[0]['actual_weight_tenths_lb'] == 0 and rows[0]['increase_next_time'] == 1
        assert w.count_performed(rows) == 1
        with pytest.raises(c.MissingRecord):
            w.session(db,b,identity)
        current=data(db,a,identity)
        current['weight']='40.99'
        w.finish(db,a,identity,current)
        assert w.session(db,a,identity)['status']=='completed'
        assert w.entries(db,a,identity)[1]['actual_duration_seconds'] is None
        assert len(w.entries(db,a,identity))==2
        assert w.finish(db,a,identity,payload)['status']=='completed'
        assert db.execute('SELECT count(*) FROM workout_sessions').fetchone()[0]==1
        with pytest.raises(w.RevisionConflict):
            w.discard(db,a,identity,{'revision':'0','confirm':'yes'})


def test_failed_later_update_keeps_previous_commit(phase3_root):
    """A malformed timed update rolls back while previously saved weight survives."""
    with database_session(phase3_root,write=True) as db:
        a,_,r,_=seed(db)
        identity,_=w.start(db,a,r,'UTC')
        payload=data(db,a,identity); payload['weight']='42.56'
        w.update(db,a,identity,payload)
    with pytest.raises(c.ValidationError):
        with database_session(phase3_root,write=True) as db:
            payload=data(db,a,identity)
            payload.update(entry_id=w.entries(db,a,identity)[1]['id'],minutes='1',seconds='')
            w.update(db,a,identity,payload)
    with database_session(phase3_root) as db:
        assert w.entries(db,a,identity)[0]['actual_weight_tenths_lb']==425
        assert w.session(db,a,identity)['revision']==1


def test_all_skipped_confirmation_and_discard_retain_rows(phase3_root):
    """Unconfirmed finish rolls back; confirmed discard changes status, not rows."""
    with database_session(phase3_root,write=True) as db:
        a,_,r,_=seed(db); identity,_=w.start(db,a,r,'UTC')
    with pytest.raises(w.AllSkipped):
        with database_session(phase3_root,write=True) as db:
            w.finish(db,a,identity,data(db,a,identity))
    with database_session(phase3_root,write=True) as db:
        assert w.session(db,a,identity)['revision']==0
        with pytest.raises(c.ValidationError):
            w.discard(db,a,identity,{'revision':'0'})
        w.discard(db,a,identity,{'revision':'0','confirm':'yes'})
        assert len(w.entries(db,a,identity))==2
        assert w.active(db,a) is None
        next_id,_=w.start(db,a,r,'UTC')
        payload=data(db,a,next_id);payload['confirm_all_skipped']='yes'
        w.finish(db,a,next_id,payload)
        assert all(row['actual_weight_tenths_lb'] is None and row['actual_duration_seconds'] is None for row in w.entries(db,a,next_id))


def test_previous_matching_skip_and_increase_no_prefill(phase3_root):
    """Reference lookups isolate owner/type and retain last performed after a skip."""
    with database_session(phase3_root,write=True) as db:
        a,_,r,_=seed(db)
        first,_=w.start(db,a,r,'UTC')
        payload=data(db,a,first);payload.update(weight='40.99',increase='1')
        w.finish(db,a,first,payload)
        second,_=w.start(db,a,r,'UTC')
        payload=data(db,a,second);payload['confirm_all_skipped']='yes'
        w.finish(db,a,second,payload)
        third,_=w.start(db,a,r,'UTC')
        row=w.entries(db,a,third)[0]
        prior,performed=w.previous(db,a,w.session(db,a,third),row)
        assert w.display_measurement(prior)=='Skipped'
        assert w.display_measurement(performed)=='40.9 lb' and performed['increase_next_time']==1
        assert row['actual_weight_tenths_lb'] is None
        with pytest.raises(sqlite3.IntegrityError):
            db.execute('UPDATE workout_entries SET actual_weight_tenths_lb=999 WHERE session_id=?',(first,))
        with pytest.raises(sqlite3.IntegrityError):
            db.execute('DELETE FROM workout_entries WHERE session_id=?',(first,))


@pytest.mark.parametrize('change', ['actual_weight_tenths_lb=-1','actual_weight_tenths_lb=1.5',
                                 'actual_duration_seconds=1','actual_weight_tenths_lb=10,increase_next_time=NULL'])
def test_database_rejects_invalid_measurement_combinations(phase3_root,change):
    """Constraints protect types and NULL rules even if service validation is bypassed."""
    with database_session(phase3_root,write=True) as db:
        a,_,r,_=seed(db);identity,_=w.start(db,a,r,'UTC')
        row=w.entries(db,a,identity)[0]
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(f'UPDATE workout_entries SET {change} WHERE id=?',(row['id'],))
