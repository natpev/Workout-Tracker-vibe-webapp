# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Synthetic schema-8 display fixtures and unchanged IANA/DST/correction semantics.

No production paths are read. Services retain full timestamps even though normal
HTML omits zone names; deliberate diagnostics still expose them for inspection.
"""
import pytest
from workout_tracker import create_app,catalog as c,history as h
from workout_tracker.storage import database_session
from test_combined import phase11_root,phase9_root
from test_history import correction_payload
ZONE='America/Indiana/Indianapolis'


@pytest.fixture
def ui_data(phase11_root):
    """Freeze all three prescriptions plus a known repeated-hour occurrence."""
    root=phase11_root
    with database_session(root,write=True) as db:
        a=c.create_person(db,'UI fixture');b=c.create_person(db,'Separate person')
        r=c.create_routine(db,a,'Three modes')
        for values in (dict(name='Bench',measurement_type='weight',target_sets='3',target_reps='12',weight_meaning='per hand'),
                       dict(name='Plank',measurement_type='time',target_sets='2',seconds='45'),
                       dict(name='Carry',measurement_type='weight_duration',target_sets='1',seconds='360',weight_meaning='total weight')):
            c.add_entry(db,a,r,values)
        c.add_entry(db,a,r,dict(name='Cooldown',measurement_type='time',target_sets='1',seconds='30'))
        form=h.prepare(db,a,r,dict(workout_date='2020-11-01',workout_time='01:30',fold='1'),ZONE)
        saved=h.complete_historical(db,a,form,dict(weight_0='40.99',increase_0='1',seconds_1='45',increase_1='1',weight_2='20',seconds_2='360',increase_2='1'))
        review=h.prepare(db,a,r,dict(workout_date='2020-11-02',workout_time='05:30'),ZONE)
    return root,a,b,r,saved,review


def test_hidden_history_zones_preserve_all_stored_values_and_diagnostics(ui_data):
    """GET-only presentation changes keep exact originals, NULLs, instants and IDs."""
    root,a,b,r,saved,review=ui_data
    client=create_app({'TESTING':True,'WORKOUT_DATA_ROOT':root,'WORKOUT_TIMEZONE':ZONE}).test_client()
    with database_session(root) as db:before='\n'.join(db.iterdump())
    for path in (f'/people/{a}/history',f'/people/{a}/history/{saved}/correct',f'/people/{a}/historical/{review}',f'/people/{a}/historical'):
        response=client.get(path);assert response.status_code==200 and ZONE.encode() not in response.data
    detail=client.get(f'/people/{a}/history/{saved}')
    assert b'Timing diagnostics</summary>' in detail.data and ZONE.encode() in detail.data
    assert b'01:30' in detail.data and b'01:30:00' not in detail.data
    assert b'Three modes' not in client.get(f'/people/{b}/history').data
    with database_session(root) as db:assert '\n'.join(db.iterdump())==before


def test_corrections_and_dst_keep_original_zone_and_occurrence(ui_data):
    """A measurement correction keeps the repeated-hour instant and append-only audit."""
    root,a,b,r,saved,review=ui_data
    with database_session(root,write=True) as db:
        original=h.original(db,a,saved)
        parent,_=h.effective(db,a,saved);stamp=parent['occurred_at']
        h.correct(db,a,saved,correction_payload(db,a,saved,weight_0='42.56',fold='1'))
        corrected,rows=h.effective(db,a,saved)
        assert corrected['timezone']==ZONE and corrected['occurred_at']==stamp
        assert rows[0]['actual_weight_tenths_lb']==425
        assert h.original(db,a,saved)==original
        assert db.execute('SELECT count(*) FROM workout_corrections').fetchone()[0]==1
    early=h.occurrence('2020-11-01','01:30',ZONE,'0')[2]
    late=h.occurrence('2020-11-01','01:30',ZONE,'1')[2]
    assert early!=late and '06:30' in late
    with pytest.raises(c.ValidationError):h.occurrence('2020-03-08','02:30',ZONE,'')
