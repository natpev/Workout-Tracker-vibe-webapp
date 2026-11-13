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
assert APP_VERSION=='1.0.1' and TARGET_SCHEMA_VERSION==13
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
