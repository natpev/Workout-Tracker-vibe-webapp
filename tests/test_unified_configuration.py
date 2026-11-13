# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Shared capabilities/defaults copy independently; permanent basis cannot be bypassed."""
import pytest
from workout_tracker import catalog as c,defaults_views as defaults
from workout_tracker.storage import database_session
from test_unified_measurements import unified_root


@pytest.mark.parametrize('caps',range(1,8))
def test_defaults_copies_and_personal_apply_keep_settings_independent(unified_root,caps):
    """Copying reuses identity/capabilities, not configuration objects or measurements."""
    with database_session(unified_root,write=True) as db:
        a=c.create_person(db,'A');other=c.create_person(db,'B');routine=c.create_routine(db,a,'Source')
        item=c.add_entry(db,a,routine,dict(name='Shared',capabilities=caps,target_sets='2',target_reps='12',seconds='45',weight_basis='per_side'))
        exercise=c.entry(db,a,routine,item)['exercise_id']
        copied=c.copy_routine(db,a,routine,other,'Copy')
        foreign=db.execute('SELECT * FROM routine_exercises WHERE routine_id=?',(copied,)).fetchone()
        assert foreign['exercise_id']==exercise and foreign['capabilities']==caps and foreign['target_sets']==2
        values=dict(c.default_values(c.exercise_defaults(db,a,exercise)),name='Renamed',target_sets='3',target_reps='9',seconds='60')
        defaults.save(db,a,exercise,values,confirmed_type_change=True)
        assert c.entry(db,a,routine,item)['target_sets']==2
        assert c.entry(db,other,copied,foreign['id'])['target_sets']==2
        defaults.save(db,a,exercise,values,True,confirmed_type_change=True)
        assert c.entry(db,a,routine,item)['target_sets']==3
        assert c.entry(db,other,copied,foreign['id'])['target_sets']==2
        assert c.definition(db,a,exercise)['name']=='Renamed'
        assert not db.execute('SELECT 1 FROM workout_sessions').fetchone()
        if caps&1:
            disabled=dict(values,capabilities=2,measurement_type='flex',weight_basis='per_side')
            c.update_defaults(db,a,exercise,disabled,confirmed_type_change=True)
            bad=dict(values,weight_basis='total')
            with pytest.raises(c.ValidationError,match='permanent'):c.update_defaults(db,a,exercise,bad,confirmed_type_change=True)
            assert db.execute('SELECT basis FROM exercise_weight_basis WHERE exercise_id=?',(exercise,)).fetchone()[0]=='per_side'


def test_copy_nonweighted_routine_after_shared_exercise_first_gains_permanent_basis(unified_root):
    """A dormant old configuration can copy after defaults gain Weight, without unlocking basis."""
    with database_session(unified_root,write=True) as db:
        a=c.create_person(db,'A');other=c.create_person(db,'B');routine=c.create_routine(db,a,'Repetitions')
        item=c.add_entry(db,a,routine,dict(name='Push-up',capabilities=2,target_sets='2',target_reps='12'))
        exercise=c.entry(db,a,routine,item)['exercise_id']
        from workout_tracker import history as h,workouts as w
        form=h.prepare(db,a,routine,dict(workout_date='2020-01-01',workout_time=''),'UTC')
        h.complete_historical(db,a,form,dict(status_0_0='completed',reps_0_0='25',status_0_1='skipped'))
        c.update_defaults(db,a,exercise,dict(capabilities=3,target_sets='3',target_reps='10',weight_basis='total'),confirmed_type_change=True)
        assert c.entry(db,a,routine,item)['weight_basis']=='not_configured'
        copied=c.copy_routine(db,a,routine,other,'Copied original')
        row=db.execute('SELECT * FROM routine_exercises WHERE routine_id=?',(copied,)).fetchone()
        assert row['exercise_id']==exercise and row['capabilities']==2 and row['target_sets']==2
        assert row['weight_basis']=='total'
        own_copy=c.copy_routine(db,a,routine,a,'Own copy')
        session,_=w.start(db,a,own_copy,'UTC');entry=w.entries(db,a,session)[0]
        previous,last=w.previous(db,a,w.session(db,a,session),entry)
        assert previous is not None and previous['sets'][0]['actual_reps']==25
        assert last is not None
        with pytest.raises(c.ValidationError,match='permanent'):
            c.update_entry(db,other,copied,row['id'],dict(capabilities=2,target_sets='2',target_reps='12',weight_basis='per_side'),confirmed_type_change=True)
