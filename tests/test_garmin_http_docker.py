# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""The built release image exercises Garmin token/JSON headers without network or storage."""
import os
import pytest
from test_container import docker

pytestmark=pytest.mark.skipif(os.environ.get('WORKOUT_CONTAINER_TESTS')!='1',reason='Opt-in isolated Docker check')


def test_release_image_garmin_plain_token_and_safe_406():
    """Use the packaged HTTP adapter, synthetic JWT and hostile upstream error fields."""
    script='''
import base64,json,time
from io import BytesIO
from unittest.mock import patch
from urllib.error import HTTPError
from workout_tracker import APP_VERSION,TARGET_SCHEMA_VERSION,garmin as g
assert APP_VERSION=='1.0.2' and TARGET_SCHEMA_VERSION==13
payload=base64.urlsafe_b64encode(json.dumps({'exp':int(time.time()+43200)}).encode()).decode().rstrip('=')
jwt='synthetic.'+payload+'.signature'
def opened(req,timeout):
    if req.full_url==g.BASE+g.TOKEN:
        assert req.get_header('Accept')=='*/*'
        return BytesIO(jwt.encode())
    assert req.get_header('Accept')=='application/json'
    return BytesIO(b'[]')
with patch.object(g,'build_opener') as factory:
    factory.return_value.open.side_effect=opened
    assert g.obtain('synthetic-key')[0]==jwt
    assert g.request('/weight-service/weight/all/2020-01-01/2020-01-02','Bearer '+jwt)=='[]'
with patch.object(g,'build_opener') as factory:
    factory.return_value.open.side_effect=HTTPError(g.BASE+g.TOKEN,406,'secret-key',{},BytesIO(jwt.encode()))
    try:g.obtain('synthetic-key')
    except g.GarminError as error:
        assert 'HTTP 406' in str(error) and 'secret-key' not in str(error) and jwt not in str(error)
    else:raise AssertionError('HTTP 406 was not reported')
'''
    docker('run','--rm','--network=none','--read-only','--tmpfs','/tmp','--entrypoint','python','workout-tracker:phase8-review','-c',script)


def test_release_image_garmin_grams_timestamp_and_exception_recovery():
    """Packaged services use real disposable SQLite, with no external network or real credentials."""
    script = '''
import json,tempfile
from pathlib import Path
from unittest.mock import patch
from workout_tracker import garmin as g,catalog as c,body_weight as b
from workout_tracker.storage import initialize_storage,database_session
from workout_tracker.migrations import migrate_storage
from workout_tracker.maintenance import logical_check_connection
root=Path(tempfile.mkdtemp())/'synthetic-storage'
initialize_storage(root);migrate_storage(root,13)
with database_session(root,write=True) as db:
    person=c.create_person(db,'Synthetic Docker person')
with patch.object(g,'obtain',return_value=('synthetic-token',g.w.now().timestamp()+43200)):
    g.connect(root,person,'synthetic-key')
payload=json.dumps([dict(timestampGMT=1577865600000,weight=100000),dict(timestampGMT='2020-01-01T18:00:00Z',weight=85000)])
with patch.object(g,'request',return_value=payload):
    assert g.sync(root,person,'UTC')==2
    assert g.sync(root,person,'UTC')==0
with patch.object(g,'request',side_effect=AttributeError('synthetic-key private-payload')):
    try:g.sync(root,person,'UTC')
    except g.GarminError as error:
        assert 'stopped unexpectedly' in str(error)
        assert 'synthetic-key' not in str(error) and 'private-payload' not in str(error)
    else:raise AssertionError('Unexpected exception escaped cleanup')
with g.storage_lock(root) as locked:
    state=g.read(locked)['people'][person]
    assert state['claim'] is None and state['connected'] and state['key']=='synthetic-key'
with database_session(root) as db:
    values={r[0] for r in db.execute('SELECT weight_milli_lb FROM body_weights')}
    assert values=={220462,187393}
    logical_check_connection(db,13)
'''
    docker('run','--rm','--network=none','--read-only','--tmpfs','/tmp','--entrypoint','python','workout-tracker:phase8-review','-c',script)
