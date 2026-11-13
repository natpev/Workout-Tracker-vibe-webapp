# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Exercise the real Garmin HTTP adapter with synthetic responses, never live accounts."""
from io import BytesIO
from urllib.error import HTTPError
from unittest.mock import patch
import json
import pytest
from workout_tracker import garmin as g, catalog as c, body_weight as b
from workout_tracker.storage import database_session
from test_garmin import token
from test_unified_measurements import unified_root


def test_token_exchange_accepts_plain_jwt_and_weight_requests_accept_json():
    """Inspect actual urllib headers; mocking g.request itself would miss this bug."""
    jwt=token();seen=[]
    def opened(request,timeout):
        """Return the official endpoint's response format without any external traffic."""
        seen.append(request)
        assert timeout==10
        if request.full_url==g.BASE+g.TOKEN:return BytesIO(jwt.encode())
        return BytesIO(b'[]')
    with patch.object(g,'build_opener') as factory:
        factory.return_value.open.side_effect=opened
        received,expires=g.obtain('synthetic-private-key')
        assert received==jwt and expires>g.w.now().timestamp()
        assert g.request(g.WEIGHTS.format(start='2020-01-01',end='2020-01-02'),'Bearer '+jwt)=='[]'
    assert seen[0].get_header('Accept')=='*/*' and seen[0].method=='POST'
    assert seen[0].get_header('Authorization')=='ApiKey synthetic-private-key'
    assert seen[1].get_header('Accept')=='application/json'
    assert seen[1].get_header('Authorization')=='Bearer '+jwt


@pytest.mark.parametrize('code',[401,403,404,406,429,500,503])
def test_http_status_is_diagnostic_without_echoing_remote_secrets(code):
    """An upstream reason/body/URL/header may echo secrets; only its status is displayed."""
    secret='synthetic-private-key';jwt=token()
    error=HTTPError(g.BASE+g.TOKEN+'?key='+secret,code,secret+jwt,{'X-Private':secret,'Retry-After':'3600'},BytesIO((secret+jwt).encode()))
    with patch.object(g,'build_opener') as factory:
        factory.return_value.open.side_effect=error
        with pytest.raises(g.GarminError) as caught:g.obtain(secret)
    message=str(caught.value)
    assert f'HTTP {code}' in message
    assert secret not in message and jwt not in message and g.BASE not in message
    assert caught.value.unauthorized==(code in (401,403))
    if code==429:assert caught.value.retry_after==3600
    if code==406:assert 'response format' in message


def test_http_transport_connection_cache_and_406_preserve_settings_and_local_records(unified_root):
    """Connect/sync through the HTTP adapter, then reject a new key without resetting state."""
    with database_session(unified_root,write=True) as db:
        person=c.create_person(db,'Synthetic Garmin person')
        b.manual(db,person,dict(date='2020-01-01',time='08:00',weight='220'),'UTC')
    seen=[];jwt=token()
    def opened(request,timeout):
        """Model token exchange and real individual weight DTOs with header checks."""
        seen.append(request)
        if request.full_url==g.BASE+g.TOKEN:
            assert request.get_header('Accept')=='*/*'
            return BytesIO(jwt.encode())
        assert request.get_header('Accept')=='application/json'
        return BytesIO(json.dumps([dict(timestampGMT='2020-01-01T18:00:00Z',weight=100)]).encode())
    with patch.object(g,'build_opener') as factory:
        factory.return_value.open.side_effect=opened
        g.connect(unified_root,person,'synthetic-original-key','UTC')
        g.schedule(unified_root,person,True,'12')
        assert g.sync(unified_root,person,'UTC')==1
        assert g.sync(unified_root,person,'UTC')==0
    assert len([r for r in seen if r.full_url==g.BASE+g.TOKEN])==1
    with g.storage_lock(unified_root) as root:before=dict(g.read(root)['people'][person])
    with database_session(unified_root) as db:records=b.records(db,person,'UTC')
    with patch.object(g,'build_opener') as factory:
        factory.return_value.open.side_effect=HTTPError(g.BASE+g.TOKEN,406,'secret remote reason',{},BytesIO(b'secret remote body'))
        with pytest.raises(g.GarminError,match='HTTP 406'):g.connect(unified_root,person,'synthetic-rejected-key','UTC')
    with g.storage_lock(unified_root) as root:after=g.read(root)['people'][person]
    for key in ('key','token','expires','generation','connected','automatic','interval_hours','timezone','last_success'):assert after[key]==before[key]
    with database_session(unified_root) as db:assert b.records(db,person,'UTC')==records
    status=json.dumps(g.public(unified_root,person))
    assert 'HTTP 406' in status and 'synthetic-' not in status and 'secret remote' not in status and jwt not in status
