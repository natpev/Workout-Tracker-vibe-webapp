# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Combined schema-8 results survive real container replacement on disposable data.

No published port/network or real database is used. HTTP inside the container
verifies paired draft autosaves and corrected history/chart/CSV after replacement.
"""
import os
import time
import pytest
from workout_tracker import catalog as c, history as h, workouts as w
from workout_tracker.storage import database_session
from test_combined import phase11_root,phase9_root,seed
from test_phase8_deletion import manual
from test_history import correction_payload
from test_container import docker,start_container
pytestmark=pytest.mark.skipif(os.environ.get('WORKOUT_CONTAINER_TESTS')!='1',reason='Opt-in isolated Docker checks')


def test_combined_draft_and_corrected_history_survive_replacement(phase11_root):
    """Real image reads schema 8, saves paired zero and exports effective corrections."""
    root=phase11_root
    with database_session(root,write=True) as db:
        a,b,r,e,item=seed(db)
        saved,_=manual(db,a,r,'2020-01-01',weight_0='20',seconds_0='360')
        h.correct(db,a,saved,correction_payload(db,a,saved,weight_0='25.99',minutes_0='4',seconds_0='45'))
        session,_=w.start(db,a,r,'UTC')
    originals={p:p.read_bytes() for p in (root/'data').glob('schema-[1-7]-*.sqlite3')}
    for iteration in range(2):
        container=start_container(root,writable=True)
        try:
            deadline=time.monotonic()+20
            while True:
                result=docker('exec',container,'python','-c',"import json,urllib.request; d=json.load(urllib.request.urlopen('http://127.0.0.1:8000/health/ready',timeout=2)); assert d['schema_version']==8",check=False)
                if not result.returncode:break
                if time.monotonic()>deadline:pytest.fail('Combined container readiness failed: '+result.stderr)
                time.sleep(.2)
            if iteration==0:
                script=f"""
import http.cookiejar,re,urllib.parse,urllib.request,json
opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
base='http://127.0.0.1:8000';path='/people/{a}/workouts/{session}'
page=opener.open(base+path).read().decode()
fields=dict(re.findall(r'name="(csrf_token|revision|entry_id|current_position)" value="([^"]*)"',page))
fields.update(weight='0',seconds='90',increase='1')
result=json.load(opener.open(base+path+'/draft',urllib.parse.urlencode(fields).encode()))
assert result['weight']=='0.0' and result['minutes']=='1' and result['seconds']=='30' and result['navigation_progress']==0
"""
                docker('exec',container,'python','-c',script)
            probe=f"""
import csv,io,urllib.request
base='http://127.0.0.1:8000'
page=urllib.request.urlopen(base+'/people/{a}/workouts/{session}').read().decode()
assert 'value="0.0"' in page and 'value="30"' in page
progress=urllib.request.urlopen(base+'/people/{a}/progress?range=all').read().decode()
assert progress.count('class="progress-chart"')==2 and '25.9 lb' in progress
response=urllib.request.urlopen(base+'/people/{a}/progress.csv?range=all&export_exercise={e}')
data=list(csv.reader(io.StringIO(response.read().decode('utf-8-sig'))))
assert data[1][4:]==['25.9','4:45','1 × 6:00']
"""
            docker('exec',container,'python','-c',probe)
            assert all(p.read_bytes()==before for p,before in originals.items())
        finally:docker('rm','-f',container)
