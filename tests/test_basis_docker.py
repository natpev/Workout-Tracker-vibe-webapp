# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Real isolated schema-8 -> 9 CLI, failure preservation and restart/read integration.

All mounts point at pytest storage, never an installed database. The image has no
published ports or external network; HTTP probes execute inside the container.
"""
import json
import os
import time
import pytest
from test_basis import legacy_fixture
from test_container import docker,start_container
pytestmark=pytest.mark.skipif(os.environ.get('WORKOUT_CONTAINER_TESTS')!='1',reason='Opt-in disposable Docker verification')


def run_storage(root,*args):
    """Execute the actual app CLI as the fixture's writer UID with explicit storage."""
    return docker('run','--rm','--network=none','--read-only','--tmpfs','/tmp','--user',f'{os.getuid()}:{os.getgid()}',
                  '--mount',f'type=bind,src={root},dst=/var/lib/workout-tracker','--entrypoint','python','workout-tracker:phase8-review',*args)


def test_schema9_to10_original_candidate_failure_audits_and_restart(tmp_path):
    """Actual image upgrades only candidates and reads converted values after restart."""
    x=legacy_fixture(tmp_path);root=x['root'];manifest=(root/'config/active.json').read_bytes()
    release=json.loads(docker('run','--rm','--network=none','--read-only','--entrypoint','python','workout-tracker:phase8-review','-m','workout_tracker','release-info').stdout)
    assert release==dict(app_version='1.0.1',target_schema_version=13)
    assert 'schema version 9.' in run_storage(root,'-m','workout_tracker','check-storage','--data-root','/var/lib/workout-tracker').stdout
    failure="""
from unittest.mock import patch
from workout_tracker.migrations import migrate_storage
from workout_tracker.storage import StorageError
with patch('workout_tracker.final_schema.upgrade_final',side_effect=RuntimeError('Synthetic candidate failure')):
 try:migrate_storage('/var/lib/workout-tracker',10)
 except StorageError:pass
 else:raise AssertionError('Failure was not reported')
"""
    run_storage(root,'-c',failure)
    assert (root/'config/active.json').read_bytes()==manifest and x['original'].read_bytes()==x['source']
    run_storage(root,'-m','workout_tracker','migrate-storage','--data-root','/var/lib/workout-tracker','--target-version','10','--confirm-upgrade')
    assert (root/'config/active.json').read_bytes()!=manifest and x['original'].read_bytes()==x['source']
    script=f"""
from uuid import uuid4
from workout_tracker.storage import database_session
from workout_tracker import basis as b,catalog as c
from workout_tracker.maintenance import backup
root='/var/lib/workout-tracker'
with database_session(root,write=True) as db:
 copied=c.copy_routine(db,{x['a']!r},{x['r']!r},{x['other']!r},'Final image copy')
 assert db.execute('SELECT count(*) FROM routine_exercises WHERE routine_id=?',(copied,)).fetchone()[0]==2
 assert not db.execute('PRAGMA foreign_key_check').fetchall()
 assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
assert backup(root,uuid4().hex)['status']=='verified'
"""
    run_storage(root,'-c',script)
    for _ in range(2):
        container=start_container(root,writable=True)
        try:
            deadline=time.monotonic()+20
            while True:
                result=docker('exec',container,'python','-c',"import json,urllib.request; r=json.load(urllib.request.urlopen('http://127.0.0.1:8000/health/ready',timeout=2)); assert r==dict(status='ready',app_version='1.0.1',schema_version=10)",check=False)
                if not result.returncode:break
                if time.monotonic()>deadline:pytest.fail('Schema-10 image did not become ready: '+result.stderr)
                time.sleep(.2)
            probe=f"""
import urllib.request,csv,io
base='http://127.0.0.1:8000'
page=urllib.request.urlopen(base+'/people/{x['a']}/history/{x['first']}').read().decode()
assert '25.0 lb' in page and 'Per Hand / Side' in page and 'Weight Basis transition' in page
page=urllib.request.urlopen(base+'/people/{x['other']}/history/{x['foreign']}').read().decode()
assert '20.0 lb' in page
page=urllib.request.urlopen(base+'/people/{x['a']}/progress?range=all').read().decode()
assert '25.0 lb' in page
csv_text=urllib.request.urlopen(base+'/people/{x['a']}/progress.csv?range=all&export_exercise={x['e']}').read().decode('utf-8-sig')
assert 'Per Hand / Side' in csv_text and any('25' in row for row in csv.reader(io.StringIO(csv_text)))
"""
            docker('exec',container,'python','-c',probe)
            assert x['original'].read_bytes()==x['source']
        finally:docker('rm','-f',container)
