# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""HTTP workflow tests use temporary schema-3 data and signed CSRF cookies.

Browser-like form helpers exercise real routes, rollback and post-commit API
acknowledgments. There are no production DBs, history explorers or backdating.
"""

import html
import re

import pytest

from workout_tracker import create_app, catalog as c, workouts as w
from workout_tracker.storage import database_session


def fields(response):
    """Extract actual server-issued security/entry state from a rendered page."""
    text=response.get_data(as_text=True)
    return {name:html.unescape(value) for name,value in re.findall(r'name="(csrf_token|revision|entry_id|current_position)" value="([^"]*)"',text)}


def start(client,root):
    """Seed one synthetic routine and start it through a protected HTTP POST."""
    with database_session(root,write=True) as db:
        person=c.create_person(db,'Fixture'); other=c.create_person(db,'Other')
        routine=c.create_routine(db,person,'Mixed')
        c.add_entry(db,person,routine,dict(name='Bench',measurement_type='weight',target_sets='3',target_reps='12'))
        c.add_entry(db,person,routine,dict(name='Plank',measurement_type='time',target_sets='3',minutes='0',seconds='45'))
    routine_path=f'/people/{person}/routines/{routine}'
    response=client.post(routine_path+'/start',data=fields(client.get(routine_path)))
    assert response.status_code==303
    return person,other,routine_path,response.location


def test_start_resume_autosave_restart_cursor_and_atomic_finish(phase3_app,phase3_root):
    """Full request flow saves current state, recovers after restart, completes once."""
    client=phase3_app.test_client()
    person,other,routine_path,path=start(client,phase3_root)
    page=client.get(path)
    assert b'name="weight"' in page.data
    assert b'Previous session:' in page.data and b'No previous performance' in page.data
    assert client.get(path.replace(person,other)).status_code==404
    retry=client.post(routine_path+'/start',data=fields(client.get(routine_path)))
    assert retry.location==path+'/resume'
    assert b'Resume workout' in client.get(retry.location).data
    payload=fields(page);payload.update(weight='40.99',increase='1',current_position='1')
    assert client.post(path+'/draft',data={}).status_code==400
    saved=client.post(path+'/draft',data=payload)
    assert saved.status_code==200 and saved.json['weight']=='40.9'
    assert saved.json['completed']==1 and saved.json['current_position']==1
    assert client.post(path+'/draft',data=payload).status_code==409
    restarted=create_app({'WORKOUT_DATA_ROOT':phase3_root,'TESTING':True}).test_client()
    recovered=restarted.get(path)
    assert b'Today\xe2\x80\x99s seconds' in recovered.data
    payload=fields(recovered);payload.update(minutes='1',seconds='5')
    result=restarted.post(path+'/finish',data=payload)
    assert result.status_code==303
    assert b'Workout saved' in restarted.get(result.location).data
    assert restarted.post(path+'/finish',data=payload).status_code==303
    assert restarted.post(path+'/discard',data={**payload,'confirm':'yes'}).status_code==409
    with database_session(phase3_root) as db:
        assert db.execute('SELECT count(*) FROM workout_sessions').fetchone()[0]==1
        rows=db.execute('SELECT * FROM workout_entries ORDER BY position').fetchall()
        assert rows[0]['actual_weight_tenths_lb']==409 and rows[1]['actual_duration_seconds']==65
        assert rows[0]['increase_next_time']==1 and rows[1]['increase_next_time']==0


def test_all_skipped_and_discard_confirmation_cancellation(phase3_app,phase3_root):
    """All-skipped completion and discard require explicit acknowledgment."""
    client=phase3_app.test_client()
    person,_,routine_path,path=start(client,phase3_root)
    payload=fields(client.get(path));payload['weight']=''
    denied=client.post(path+'/finish',data=payload)
    assert denied.status_code==400 and b'Confirm that you want' in denied.data
    payload['confirm_all_skipped']='yes'
    assert client.post(path+'/finish',data=payload).status_code==303
    response=client.post(routine_path+'/start',data=fields(client.get(routine_path)))
    draft=response.location
    page=client.get(draft+'/discard')
    assert b'Are you sure?' in page.data and b'id="discard-ok" disabled' in page.data
    # Cancel is a GET back to the draft and cannot mutate state.
    assert client.get(draft).status_code==200
    payload=fields(page)
    assert client.post(draft+'/discard',data=payload).status_code==400
    assert client.post(draft+'/discard',data={**payload,'confirm':'yes'}).status_code==303
    with database_session(phase3_root) as db:
        sessions=db.execute('SELECT status FROM workout_sessions ORDER BY started_at').fetchall()
        assert [row[0] for row in sessions]==['completed','discarded']
        assert db.execute('SELECT count(*) FROM workout_entries WHERE actual_weight_tenths_lb IS NULL AND actual_duration_seconds IS NULL').fetchone()[0]==4


def test_invalid_autosave_keeps_confirmed_values_and_hides_cross_user_items(phase3_app,phase3_root):
    """Bad updates return errors without mutating any previously committed entry."""
    client=phase3_app.test_client()
    person,_,_,path=start(client,phase3_root)
    payload=fields(client.get(path));payload.update(weight='0',increase='1')
    assert client.post(path+'/draft',data=payload).json['completed']==1
    page=client.get(path+'?position=1')
    payload=fields(page);payload.update(minutes='1',seconds='')
    response=client.post(path+'/draft',data=payload)
    assert response.status_code==400 and 'both' in response.json['error']
    payload.update(minutes='0',seconds='1',entry_id='unknown')
    assert client.post(path+'/draft',data=payload).status_code==404
    with database_session(phase3_root) as db:
        parent=w.active(db,person)
        rows=w.entries(db,person,parent['id'])
        assert parent['revision']==1
        assert rows[0]['actual_weight_tenths_lb']==0 and rows[1]['actual_duration_seconds'] is None
