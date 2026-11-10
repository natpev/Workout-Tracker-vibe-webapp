# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Navigation-only progress persists in the existing cursor, without schema changes."""
import pytest
from workout_tracker import catalog as c, workouts as w, create_app
from workout_tracker.storage import database_session
from test_workouts import seed


def payload(db,person,session,index=0,**values):
    """Build a current revision payload for one immutable snapshot entry."""
    parent=w.session(db,person,session);row=w.entries(db,person,session)[index]
    return dict(revision=str(parent['revision']),entry_id=row['id'],current_position=str(parent['current_position']),**values)


def test_saves_flags_skip_next_back_revisit_restart_and_completion(phase3_root):
    """Only validated Next destinations change the checkpoint, regardless of actuals."""
    root=phase3_root
    with database_session(root,write=True) as db:
        a,b,r,_=seed(db);session,_=w.start(db,a,r,'UTC')
        for values in ({'weight':'40.99'},{'weight':'42','increase':'1'},{'weight':''}):
            w.update(db,a,session,payload(db,a,session,**values))
            assert w.session(db,a,session)['current_position']==0
        values=payload(db,a,session,navigation_action='next');values['current_position']='1'
        w.update(db,a,session,values)
        assert w.session(db,a,session)['current_position']==1
        w.update(db,a,session,payload(db,a,session,1,seconds='45',increase='1'))
        assert w.session(db,a,session)['current_position']==1
        values=payload(db,a,session,1,navigation_action='back',seconds='45');values['current_position']='0'
        w.update(db,a,session,values)
        values=payload(db,a,session,navigation_action='next');values['current_position']='1'
        w.update(db,a,session,values)
        assert w.session(db,a,session)['current_position']==1
    with database_session(root,write=True) as db:
        assert w.session(db,a,session)['current_position']==1
        values=payload(db,a,session,1,seconds='45')
        w.finish(db,a,session,values)
        assert w.session(db,a,session)['status']=='completed'
        assert w.entries(db,a,session)[0]['actual_weight_tenths_lb'] is None


def test_jump_and_failed_navigation_do_not_fabricate_progress(phase3_root):
    """Jump is view-only; invalid/stale navigation cannot partially commit actuals."""
    root=phase3_root
    with database_session(root,write=True) as db:
        a,b,r,_=seed(db);session,_=w.start(db,a,r,'UTC')
        values=payload(db,a,session,navigation_action='jump');values['current_position']='1'
        w.update(db,a,session,values)
        assert w.session(db,a,session)['current_position']==0
    with pytest.raises(c.ValidationError):
        with database_session(root,write=True) as db:
            values=payload(db,a,session,navigation_action='back',weight='99');values['current_position']='1'
            w.update(db,a,session,values)
    with database_session(root) as db:
        assert w.session(db,a,session)['current_position']==0
        assert w.entries(db,a,session)[0]['actual_weight_tenths_lb'] is None


def test_each_sequential_next_advances_once_even_when_every_measurement_is_null(phase3_root):
    """Three blank exercises still navigate and complete only with skipped confirmation."""
    with database_session(phase3_root,write=True) as db:
        a,b,r,_=seed(db)
        c.add_entry(db,a,r,dict(name='Third',measurement_type='weight',target_sets='2',target_reps='10'))
        session,_=w.start(db,a,r,'UTC')
        for index in (0,1):
            values=payload(db,a,session,index,navigation_action='next')
            values['current_position']=str(index+1)
            w.update(db,a,session,values)
            assert w.session(db,a,session)['current_position']==index+1
            assert w.count_performed(w.entries(db,a,session))==0
        w.finish(db,a,session,payload(db,a,session,2,confirm_all_skipped='yes'))
        assert w.session(db,a,session)['status']=='completed'
        assert all(row['actual_weight_tenths_lb'] is None and row['actual_duration_seconds'] is None for row in w.entries(db,a,session))
