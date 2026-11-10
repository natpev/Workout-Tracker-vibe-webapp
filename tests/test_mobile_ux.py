# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Disposable HTTP/storage checks for person preferences and deliberate workout exit.

No schema migration is introduced. Tests assert original database bytes remain
unchanged by appearance and failed/stale exits never replace confirmed drafts.
"""
import json
import re
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from workout_tracker import catalog as c,workouts as w,preferences as p,create_app
from workout_tracker.storage import database_session,storage_lock,_inspect_unlocked,StorageError


def seed(root):
    """Create two synthetic people and a mixed routine without household config."""
    with database_session(root,write=True) as db:
        a,b=c.create_person(db,'Alex'),c.create_person(db,'Sam');routine=c.create_routine(db,a,'Strength')
        c.add_entry(db,a,routine,dict(name='Bench press',measurement_type='weight',target_sets='3',target_reps='12'))
        c.add_entry(db,a,routine,dict(name='Plank',measurement_type='time',target_sets='3',minutes='0',seconds='45'))
    return a,b,routine


def fields(page):
    """Take real signed CSRF/revision fields from rendered HTML."""
    return dict(re.findall(r'name="(csrf_token|revision|entry_id|current_position)" value="([^"]*)"',page.get_data(as_text=True)))


def test_preferences_persist_independently_without_database_changes(phase4_root):
    """All colors, independent people and restart reads change only private JSON."""
    root=phase4_root;a,b,_=seed(root)
    with storage_lock(root): database=_inspect_unlocked(root)['database']
    before=database.read_bytes();mtime=database.stat().st_mtime_ns
    assert p.colors(root)=={} and not (root/'config'/'person-preferences.json').exists()
    with ThreadPoolExecutor(2) as pool:
        list(pool.map(lambda args:p.set_color(root,*args),[(a,'purple'),(b,'orange')]))
    assert p.colors(root)=={a:'purple',b:'orange'}
    replacement=create_app({'WORKOUT_DATA_ROOT':root,'TESTING':True}).test_client()
    assert b'data-accent="purple"' in replacement.get('/people/'+a).data
    assert b'data-accent="orange"' in replacement.get('/people/'+b).data
    assert database.read_bytes()==before and database.stat().st_mtime_ns==mtime
    assert (root/'config'/'person-preferences.json').stat().st_mode & 0o777==0o600
    for color in p.PALETTE: p.set_color(root,a,color)
    with pytest.raises(c.ValidationError): p.set_color(root,a,'url(evil)')
    with pytest.raises(c.MissingRecord): p.set_color(root,uuid4().hex,'blue')


def test_corrupt_preferences_preserved_and_no_startup_initialization(phase4_root):
    """Malformed preferences fail writes; they cannot create replacement storage or alter SQL."""
    root=phase4_root;a,_,_=seed(root);path=root/'config'/'person-preferences.json';path.write_text('bad');path.chmod(0o600)
    with pytest.raises(StorageError): p.set_color(root,a,'green')
    assert path.read_text()=='bad'
    assert create_app({'WORKOUT_DATA_ROOT':root,'TESTING':True}).test_client().get('/people').status_code==200
    assert path.read_text()=='bad'


def test_accent_form_csrf_owner_archive_and_no_arbitrary_css(phase4_app,phase4_root):
    """Preference actions remain protected even for archived retained people."""
    client=phase4_app.test_client();a,_,_=seed(phase4_root);url=f'/settings/people/{a}/accent'
    assert client.post(url,data={'accent':'purple'}).status_code==400
    payload=fields(client.get('/settings?person_id='+a))
    assert client.post(url,data=dict(payload,accent='purple')).status_code==303
    assert client.post(url,data=dict(payload,accent='bad')).status_code==400
    assert client.post('/settings/people/'+uuid4().hex+'/accent',data=dict(payload,accent='blue')).status_code==404
    with database_session(phase4_root,write=True) as db: c.update_person(db,a,None,'archive')
    assert client.post(url,data=dict(payload,accent='teal')).status_code==303
    assert p.colors(phase4_root)[a]=='teal'


def test_exit_saves_current_input_and_rejects_stale_invalid_requests(phase4_app,phase4_root):
    """Explicit exit atomically saves pending input, preserving the one resumable draft."""
    client=phase4_app.test_client();a,_,routine=seed(phase4_root)
    with database_session(phase4_root,write=True) as db: identity,_=w.start(db,a,routine,'UTC')
    url=f'/people/{a}/workouts/{identity}';payload=fields(client.get(url))
    assert client.post(url+'/exit',data=dict(payload,weight='bad')).status_code==400
    response=client.post(url+'/exit',data=dict(payload,weight='42.56'))
    assert response.status_code==303 and 'exited='+identity in response.location
    assert client.post(url+'/exit',data=dict(payload,weight='99')).status_code==409
    with database_session(phase4_root) as db:
        assert w.active(db,a)['id']==identity and w.entries(db,a,identity)[0]['actual_weight_tenths_lb']==425
    page=client.get(url);assert b'Open navigation' not in page.data and b'Switch person' not in page.data
    assert b'Exit Workout' in page.data and b'Workout details' in page.data


def test_preference_publication_failure_preserves_previous_file(phase4_root,monkeypatch):
    """A failed rename preserves the previous complete preference selection and SQL bytes."""
    root=phase4_root;a,_,_=seed(root);p.set_color(root,a,'blue')
    path=root/'config'/'person-preferences.json';before=path.read_bytes()
    def fail(*args):
        """Reject only preference publication to simulate an interrupted config save."""
        raise OSError('synthetic publication failure')
    monkeypatch.setattr(p.os,'replace',fail)
    with pytest.raises(StorageError): p.set_color(root,a,'red')
    assert path.read_bytes()==before
