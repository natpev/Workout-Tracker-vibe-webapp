# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""History HTTP integration tests use signed cookies and disposable schema 4.

Browser forms -> CSRF/ownership -> prepared snapshots/atomic completion/audit.
Tests inspect actual saved rows, filtering, charts and native protection triggers.
"""

import re

from workout_tracker import catalog as c, workouts as w
from workout_tracker.storage import database_session


def token(response):
    """Read an actual server-issued CSRF field, retaining the client's signed cookie."""
    match=re.search(r'name="csrf_token" value="([^"]+)"',response.get_data(as_text=True))
    assert match
    return match.group(1)


def setup(root):
    """Build a synthetic mixed routine and another household person."""
    with database_session(root,write=True) as db:
        a,b=c.create_person(db,'Fixture'),c.create_person(db,'Other')
        r=c.create_routine(db,a,'Mixed')
        c.add_entry(db,a,r,dict(name='Bench',measurement_type='weight',target_sets='3',target_reps='12',notes='Snapshot note'))
        c.add_entry(db,a,r,dict(name='Plank',measurement_type='time',target_sets='3',minutes='0',seconds='45'))
    return a,b,r


def test_historical_history_charts_corrections_and_ownership(phase4_app,phase4_root):
    """Complete backdated form, filter/open it, append a correction and read effective views."""
    client=phase4_app.test_client();a,b,r=setup(phase4_root)
    start=f'/people/{a}/historical'
    response=client.post(start,data=dict(csrf_token=token(client.get(start)),routine_id=r,workout_date='2020-01-01',workout_time=''))
    assert response.status_code==303
    review=response.location;form=client.get(review)
    assert b'Review historical workout' in form.data and b'Time unknown' in form.data
    payload=dict(csrf_token=token(form),weight_0='40.99',minutes_1='0',seconds_1='45')
    saved=client.post(review,data=payload)
    assert saved.status_code==303
    assert client.post(review,data=payload).location==saved.location
    detail=saved.location
    assert b'40.9 lb' in client.get(detail).data and b'Snapshot note' in client.get(detail).data
    assert client.get(detail.replace(a,b)).status_code==404
    history=client.get(f'/people/{a}/history?from=2020-01-01&to=2020-12-31')
    assert b'class="history-record"' in history.data
    assert b'class="history-record"' not in client.get(f'/people/{b}/history').data
    assert b'class="history-record"' not in client.get(f'/people/{a}/history?from=2021-01-01').data
    assert client.get(f'/people/{a}/history?from=bad').status_code==400
    charts=client.get(f'/people/{a}/progress?range=all')
    assert charts.status_code==200 and charts.data.count(b'<svg ')==2
    assert b'Highest logged weight' in charts.data and b'Longest logged duration' in charts.data
    assert b'40.9 lb' in charts.data and b'0:45' in charts.data
    correction=detail+'/correct';page=client.get(correction)
    values=dict(csrf_token=token(page),correction_revision='0',workout_date='2021-02-03',workout_time='',weight_0='42.56',minutes_1='1',seconds_1='5')
    assert client.post(correction,data=values).status_code==400
    values['confirm']='yes'
    assert client.post(correction,data=values).status_code==303
    assert client.post(correction,data=values).status_code==409
    changed=client.get(detail)
    assert b'42.5 lb' in changed.data and b'1:05' in changed.data and b'Correction 1' in changed.data
    assert b'40.9 lb' in changed.data  # Retained original/audit, not overwritten.
    assert b'class="history-record"' not in client.get(f'/people/{a}/history?to=2020-12-31').data
    assert b'42.5 lb' in client.get(f'/people/{a}/progress?from=2021-01-01').data


def test_manual_does_not_replace_draft_and_completed_bookmark_uses_corrections(phase4_app,phase4_root):
    """Native completion remains protected while its legacy confirmation shows effective values."""
    client=phase4_app.test_client();a,_,r=setup(phase4_root)
    with database_session(phase4_root,write=True) as db:
        identity,_=w.start(db,a,r,'UTC');entry=w.entries(db,a,identity)[0]
        w.finish(db,a,identity,dict(revision='0',entry_id=entry['id'],current_position='0',weight='0'))
        draft,_=w.start(db,a,r,'UTC')
    correct=f'/people/{a}/history/{identity}/correct'
    page=client.get(correct)
    with database_session(phase4_root) as db:
        from workout_tracker.history import effective
        parent,_=effective(db,a,identity)
    payload=dict(csrf_token=token(page),correction_revision='0',confirm='yes',workout_date=parent['workout_date'],workout_time=parent['workout_time'],weight_0='50')
    assert client.post(correct,data=payload).status_code==303
    assert b'50.0 lb' in client.get(f'/people/{a}/workouts/{identity}').data
    start=f'/people/{a}/historical';page=client.get(start)
    response=client.post(start,data=dict(csrf_token=token(page),routine_id=r,workout_date='2020-01-01'))
    page=client.get(response.location)
    skipped=client.post(response.location,data=dict(csrf_token=token(page)))
    assert skipped.status_code==400
    result=client.post(response.location,data=dict(csrf_token=token(page),confirm_all_skipped='yes'))
    assert result.status_code==303
    with database_session(phase4_root) as db:
        assert w.active(db,a)['id']==draft
        assert len(w.entries(db,a,draft))==2
