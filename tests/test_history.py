# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""History/correction services tested against disposable schema-4 databases.

Fixtures exercise native/historical chronology, append-only audit, effective
queries, NULL/zero semantics and independence from active drafts and definitions.
"""

from datetime import datetime, timezone
import sqlite3
from unittest.mock import patch

import pytest

from workout_tracker import catalog as c, history as h, workouts as w
from workout_tracker.storage import database_session


def seed(db):
    """Create two synthetic people and a mixed routine with permanent exercise IDs."""
    a,b=c.create_person(db,'A'),c.create_person(db,'B')
    r=c.create_routine(db,a,'Mixed')
    item=c.add_entry(db,a,r,dict(name='Bench',measurement_type='weight',target_sets='3',target_reps='12',weight_meaning='per dumbbell',notes='Original note'))
    c.add_entry(db,a,r,dict(name='Plank',measurement_type='time',target_sets='3',minutes='0',seconds='45'))
    return a,b,r,item


def manual(db,a,r,day,**measurements):
    """Prepare/save an independent synthetic past workout, no active-draft mutation."""
    form=h.prepare(db,a,r,dict(workout_date=day,workout_time=''), 'UTC')
    return h.complete_historical(db,a,form,measurements),form


def correction_payload(db,a,identity,**changes):
    """Build a complete current form for deliberate, revision-checked correction."""
    parent,rows=h.effective(db,a,identity)
    values=dict(workout_date=parent['workout_date'],workout_time=parent['workout_time'] or '',correction_revision=str(parent['correction_revision']),confirm='yes')
    for i,row in enumerate(rows):
        if row['actual_weight_tenths_lb'] is not None:
            value=row['actual_weight_tenths_lb'];values[f'weight_{i}']=f'{value//10}.{value%10}'
        if row['actual_duration_seconds'] is not None:
            value=row['actual_duration_seconds'];values.update({f'minutes_{i}':str(value//60),f'seconds_{i}':str(value%60)})
        if row['increase_next_time']: values[f'increase_{i}']='1'
    values.update(changes)
    return values


def test_manual_entry_preserves_draft_zero_null_and_snapshots(phase4_root):
    """Historical completion does not compete with the active draft or lose skipped rows."""
    with database_session(phase4_root,write=True) as db:
        a,b,r,item=seed(db);draft,_=w.start(db,a,r,'UTC')
        original_draft=[dict(row) for row in w.entries(db,a,draft)]
        form=h.prepare(db,a,r,dict(workout_date='2020-01-02',workout_time=''), 'UTC')
        c.update_definition(db,a,original_draft[0]['exercise_id'],'Changed','rename')
        c.update_entry(db,a,r,item,dict(measurement_type='time',target_sets='9',minutes='1',seconds='0'))
        db.execute('UPDATE routines SET archived=1 WHERE id=?',(r,))
        identity=h.complete_historical(db,a,form,{'weight_0':'0','increase_0':'1'})
        assert h.complete_historical(db,a,form,{'weight_0':'99'})==identity
        parent,rows=h.effective(db,a,identity)
        assert parent['workout_time'] is None and parent['occurred_at'] is None
        assert parent['workout_date']=='2020-01-02' and parent['entered_at']>parent['workout_date']
        assert rows[0]['name']=='Bench' and rows[0]['target_reps']==12 and rows[0]['notes']=='Original note'
        assert rows[0]['actual_weight_tenths_lb']==0 and rows[1]['actual_duration_seconds'] is None
        assert w.active(db,a)['id']==draft and [dict(row) for row in w.entries(db,a,draft)]==original_draft
        assert len(h.all_completed(db,a))==1 and h.all_completed(db,b)==[]
        with pytest.raises(c.MissingRecord): h.effective(db,b,identity)
        with pytest.raises(c.MissingRecord): h.complete_historical(db,b,form,{})
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]


def test_chronology_filters_series_separation_and_zero_records(phase4_root):
    """Date chronology ignores entry time; charts separate permanent ID/type/meaning."""
    with database_session(phase4_root,write=True) as db:
        a,b,r,item=seed(db)
        recent,_=manual(db,a,r,'2022-02-02',weight_0='0',minutes_1='0',seconds_1='45')
        old,_=manual(db,a,r,'2020-01-01',weight_0='40.99',minutes_1='1',seconds_1='5')
        skipped,_=manual(db,a,r,'2021-01-01',confirm_all_skipped='yes')
        assert [pair[0]['id'] for pair in h.listing(db,a,{})]==[recent,skipped,old]
        assert [pair[0]['id'] for pair in h.listing(db,a,{'from':'2021-01-01','to':'2021-12-31'})]==[skipped]
        groups=h.chart_series(db,a,{})
        weights=next(group for group in groups if group['kind']=='weight')
        times=next(group for group in groups if group['kind']=='time')
        assert [point['raw'] for point in weights['points']]==[409,0]
        assert weights['highest']['label']=='40.9 lb' and len(weights['records'])==3
        assert [point['raw'] for point in times['points']]==[65,45]
        assert times['highest']['label']=='1:05'
        c.update_entry(db,a,r,item,dict(measurement_type='weight',target_sets='3',target_reps='12',weight_meaning='total barbell'))
        manual(db,a,r,'2023-01-01',weight_0='100')
        assert len([g for g in h.chart_series(db,a,{}) if g['kind']=='weight'])==2
        c.update_entry(db,a,r,item,dict(measurement_type='time',target_sets='3',minutes='0',seconds='45'))
        manual(db,a,r,'2024-01-01',minutes_0='0',seconds_0='1')
        assert len(h.chart_series(db,a,{}))==4
        exercise=weights['exercise_id']
        assert all(g['exercise_id']==exercise for g in h.chart_series(db,a,{'exercise':exercise}))
        with pytest.raises(c.ValidationError): h.listing(db,a,{'from':'2022-01-01','to':'2020-01-01'})


def test_append_only_correction_audit_effective_readers_and_previous(phase4_root):
    """Original rows stay intact; all readers use corrected measures and occurrence."""
    with database_session(phase4_root,write=True) as db:
        a,b,r,_=seed(db)
        identity,_=manual(db,a,r,'2020-01-01',weight_0='40',minutes_1='0',seconds_1='45')
        original=h.original(db,a,identity)
        payload=correction_payload(db,a,identity,weight_0='42.56',workout_date='2021-01-01',increase_0='1')
        with pytest.raises(c.ValidationError): h.correct(db,a,identity,{**payload,'confirm':''})
        assert h.correct(db,a,identity,payload)==1
        with pytest.raises(w.RevisionConflict): h.correct(db,a,identity,payload)
        assert h.original(db,a,identity)==original
        parent,rows=h.effective(db,a,identity)
        assert parent['workout_date']=='2021-01-01' and rows[0]['actual_weight_tenths_lb']==425
        logs=h.audit(db,a,identity)
        assert logs[0]['before']['entries'][0]['actual_weight_tenths_lb']==400
        assert logs[0]['after']['entries'][0]['actual_weight_tenths_lb']==425
        draft,_=w.start(db,a,r,'UTC');entry=w.entries(db,a,draft)[0]
        previous,performed=w.previous(db,a,w.session(db,a,draft),entry)
        assert previous['actual_weight_tenths_lb']==425 and previous['increase_next_time']==1
        assert h.chart_series(db,a,{'exercise':entry['exercise_id']})[0]['highest']['raw']==425
        payload2=correction_payload(db,a,identity,weight_0='',minutes_1='',seconds_1='',confirm_all_skipped='yes')
        assert h.correct(db,a,identity,payload2)==2
        assert h.effective(db,a,identity)[1][0]['actual_weight_tenths_lb'] is None
        assert h.audit(db,a,identity)[1]['before']==h.audit(db,a,identity)[0]['after']
        with pytest.raises(sqlite3.IntegrityError): db.execute("UPDATE workout_corrections SET before_json='{}'")
        with pytest.raises(sqlite3.IntegrityError): db.execute('DELETE FROM historical_entries')
        with pytest.raises(c.MissingRecord): h.correct(db,b,identity,payload)


def test_native_completed_protection_and_correction_registry(phase4_root):
    """Phase 3 triggers remain active; native completion registers an owned correction target."""
    with database_session(phase4_root,write=True) as db:
        a,_,r,_=seed(db);identity,_=w.start(db,a,r,'UTC');entry=w.entries(db,a,identity)[0]
        w.finish(db,a,identity,dict(revision='0',entry_id=entry['id'],current_position='0',weight='0'))
        base=tuple(db.execute('SELECT * FROM workout_entries WHERE id=?',(entry['id'],)).fetchone())
        payload=correction_payload(db,a,identity,weight_0='40.99')
        h.correct(db,a,identity,payload)
        assert tuple(db.execute('SELECT * FROM workout_entries WHERE id=?',(entry['id'],)).fetchone())==base
        assert h.effective(db,a,identity)[1][0]['actual_weight_tenths_lb']==409
        with pytest.raises(sqlite3.IntegrityError): db.execute('UPDATE workout_entries SET actual_weight_tenths_lb=100 WHERE id=?',(entry['id'],))
        with pytest.raises(sqlite3.IntegrityError): db.execute("UPDATE workout_sessions SET workout_date='2020-01-01' WHERE id=?",(identity,))


@pytest.mark.parametrize('values',[{'minutes_1':'0','seconds_1':'0'},{'minutes_1':'1','seconds_1':''},{'weight_0':'-1'},{'weight_0':'NaN'}])
def test_invalid_manual_entry_rolls_back_and_keeps_current_draft(phase4_root,values):
    """Invalid form data cannot leave a partial historical completion."""
    with database_session(phase4_root,write=True) as db:
        a,_,r,_=seed(db);draft,_=w.start(db,a,r,'UTC')
        form=h.prepare(db,a,r,dict(workout_date='2020-01-01',workout_time=''),'UTC')
    with pytest.raises(c.ValidationError):
        with database_session(phase4_root,write=True) as db:
            h.complete_historical(db,a,form,values)
    with database_session(phase4_root) as db:
        assert db.execute('SELECT count(*) FROM historical_workouts').fetchone()[0]==0
        assert w.active(db,a)['id']==draft


def test_dates_unknown_time_dst_validation_and_backdated_reference(phase4_root):
    """Unknown times stay NULL; future/gap/ambiguous times fail rather than guessing."""
    assert h.occurrence('2020-01-01','','UTC')==('2020-01-01',None,None)
    for day,clock in [('2020-02-30',''),('2999-01-01',''),('2026-03-08','02:30')]:
        with pytest.raises(c.ValidationError): h.occurrence(day,clock,'America/Indiana/Indianapolis')
    with pytest.raises(c.ValidationError): h.occurrence('2026-11-01','01:30','America/Indiana/Indianapolis')
    early=h.occurrence('2026-11-01','01:30','America/Indiana/Indianapolis','0')
    late=h.occurrence('2026-11-01','01:30','America/Indiana/Indianapolis','1')
    assert early[2]!=late[2]


def test_atomic_manual_failure_and_concurrent_corrections(phase4_root):
    """Failed insertion rolls back every row; two stale correction forms cannot both win."""
    from concurrent.futures import ThreadPoolExecutor
    from uuid import UUID
    from workout_tracker.storage import StorageError
    with database_session(phase4_root,write=True) as db:
        a,_,r,_=seed(db)
        form=h.prepare(db,a,r,dict(workout_date='2020-01-01',workout_time=''),'UTC')
    with pytest.raises(StorageError):
        with database_session(phase4_root,write=True) as db:
            # A duplicate synthetic entry ID fails only after parent/first entry
            # insertion, proving the whole write rolls back, including registry.
            with patch.object(h,'uuid4',return_value=UUID(int=1)):
                h.complete_historical(db,a,form,{'weight_0':'40'})
    with database_session(phase4_root,write=True) as db:
        assert db.execute('SELECT count(*) FROM historical_workouts').fetchone()[0]==0
        assert db.execute('SELECT count(*) FROM workout_registry').fetchone()[0]==0
        identity=h.complete_historical(db,a,form,{'weight_0':'40'})
        payload=correction_payload(db,a,identity,weight_0='42.56')

    def apply(_):
        """Use separate locked connections like independent browser workers."""
        try:
            with database_session(phase4_root,write=True) as db:
                h.correct(db,a,identity,payload)
            return 'saved'
        except w.RevisionConflict:
            return 'conflict'

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(apply,range(2)))==['conflict','saved']
    with database_session(phase4_root) as db:
        assert db.execute('SELECT count(*) FROM workout_corrections').fetchone()[0]==1
        assert h.effective(db,a,identity)[1][0]['actual_weight_tenths_lb']==425


def test_corrected_date_changes_previous_performance_reference(phase4_root):
    """Effective occurrence, not entry/correction time, determines comparison eligibility."""
    with database_session(phase4_root,write=True) as db:
        a,_,r,_=seed(db)
        with patch.object(w,'now',return_value=datetime(2021,6,1,12,tzinfo=timezone.utc)):
            draft,_=w.start(db,a,r,'UTC')
        identity,_=manual(db,a,r,'2022-01-01',weight_0='50')
        parent=w.session(db,a,draft);entry=w.entries(db,a,draft)[0]
        assert w.previous(db,a,parent,entry)==(None,None)
        h.correct(db,a,identity,correction_payload(db,a,identity,workout_date='2020-01-01'))
        assert w.previous(db,a,parent,entry)[0]['actual_weight_tenths_lb']==500
        h.correct(db,a,identity,correction_payload(db,a,identity,workout_date='2023-01-01'))
        assert w.previous(db,a,parent,entry)==(None,None)


def test_known_times_filters_and_archived_sources_keep_history(phase4_root):
    """History orders actual times and retains snapshots after every definition is archived."""
    with database_session(phase4_root,write=True) as db:
        a,_,r,_=seed(db)
        ids=[]
        for clock in ('17:30','08:30',''):
            form=h.prepare(db,a,r,dict(workout_date='2020-01-01',workout_time=clock),'UTC')
            ids.append(h.complete_historical(db,a,form,{'weight_0':'0'}))
        assert [parent['id'] for parent,_ in h.all_completed(db,a)]==[ids[0],ids[1],ids[2]]
        exercise=h.effective(db,a,ids[0])[1][0]['exercise_id']
        assert len(h.listing(db,a,{'routine':r,'exercise':exercise}))==3
        assert h.listing(db,a,{'exercise':'another-person-exercise'})==[]
        db.execute('UPDATE routines SET archived=1 WHERE id=?',(r,))
        c.update_definition(db,a,exercise,'Changed name','rename')
        c.update_definition(db,a,exercise,None,'archive')
        c.update_person(db,a,None,'archive')
        parent,rows=h.effective(db,a,ids[0])
        assert parent['routine_name']=='Mixed' and rows[0]['name']=='Bench'
        assert exercise in h.choices(db,a)[1] and r in h.choices(db,a)[0]
        assert len(h.chart_series(db,a,{}))==2


def test_repeated_hour_order_and_fold_only_correction(phase4_root):
    """Actual UTC order distinguishes repeated times; changing only fold is audited."""
    with patch.object(w,'now',return_value=datetime(2026,11,6,12,tzinfo=timezone.utc)):
        with database_session(phase4_root,write=True) as db:
            a,_,r,_=seed(db)
            late_form=h.prepare(db,a,r,dict(workout_date='2026-11-01',workout_time='01:30',fold='1'),'America/Indiana/Indianapolis')
            late=h.complete_historical(db,a,late_form,{'weight_0':'40'})
            early_form=h.prepare(db,a,r,dict(workout_date='2026-11-01',workout_time='01:30',fold='0'),'America/Indiana/Indianapolis')
            early=h.complete_historical(db,a,early_form,{'weight_0':'40'})
            assert [parent['id'] for parent,_ in h.all_completed(db,a)]==[late,early]
            before=h.effective(db,a,early)[0]['occurred_at']
            payload=correction_payload(db,a,early,fold='1')
            assert h.correct(db,a,early,payload)==1
            after=h.effective(db,a,early)[0]['occurred_at']
            assert before!=after
            assert datetime.fromisoformat(after).hour==6
            assert h.audit(db,a,early)[0]['before']['occurred_at']==before
            assert h.audit(db,a,early)[0]['after']['occurred_at']==after
