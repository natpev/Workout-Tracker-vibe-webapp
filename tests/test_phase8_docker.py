# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Actual v4/host-service/Compose rehearsal with real disposable schema-5 storage.

Git source fetching and the host-specific Docker storage path probe are simulated. Docker build, backup, schema-6 migration,
container replacement, Unix peer checks and independent HTTP progress are real.
No published workout port, external status listener, or real user data is used.
"""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

import pytest
from test_phase8_updater import fixture,REPO
from workout_tracker import APP_VERSION, TARGET_SCHEMA_VERSION

pytestmark=pytest.mark.skipif(os.environ.get('WORKOUT_CONTAINER_TESTS')!='1',reason='Opt-in isolated Docker rehearsal')


@pytest.mark.parametrize('source_schema,fault',[(9,None),(10,None),(11,'code-only'),(6,'unclassified'),(7,'unclassified'),(8,'unclassified'),(6,'shutdown'),(7,'shutdown'),(9,'shutdown'),(9,'startup')])
def test_actual_v4_host_service_and_docker_migration(tmp_path,source_schema,fault):
    """CLI updates actual containers while independent LAN-style HTTP/Unix survive."""
    short=tempfile.TemporaryDirectory(prefix='p8-',dir='/tmp')
    initial_schema=source_schema
    if fault=='code-only':fault=None
    root,env=fixture(Path(short.name),initial_schema);env.update(MODE='ok',METADATA_VERSION=APP_VERSION,METADATA_SCHEMA=str(TARGET_SCHEMA_VERSION))
    adapter=Path(short.name)/'bin/docker'
    real_docker=shutil.which('docker')
    # The cloud test UID cannot traverse the rootless daemon user's private
    # directory. Simulate only that path probe; every Docker operation is real.
    adapter.write_text('#!/usr/bin/env python3\n# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.\nimport os,sys\nfrom pathlib import Path\na=sys.argv[1:]\nif "info" in a and "{{.DockerRootDir}}" in a: print(os.environ["FIXTURE"])\nelse: os.execv('+repr(real_docker)+', ['+repr(real_docker)+',*a])\n')
    source=adapter.read_text().replace('import os,sys','import os,sys,subprocess')
    source=source.replace('a=sys.argv[1:]',"""a=sys.argv[1:]
fault=os.environ.get('DOCKER_FAULT','')
marker=Path(os.environ['FIXTURE'])/'shutdown-failed-once'
if fault=='shutdown' and 'compose' in a and 'stop' in a and not marker.exists():
 marker.touch();subprocess.run([REAL_DOCKER,*a]);sys.exit(1)
if fault=='startup' and 'compose' in a and 'up' in a:sys.exit(1)""".replace('REAL_DOCKER',repr(real_docker)))
    adapter.write_text(source);adapter.chmod(0o700)
    env['DOCKER_FAULT']=fault or ''
    for name in ('Dockerfile','.dockerignore','requirements.txt'):
        shutil.copy2(REPO/name,root/'app'/name)
    shutil.copytree(REPO/'workout_tracker',root/'app/workout_tracker',ignore=shutil.ignore_patterns('__pycache__'))
    compose=(REPO/'compose.yaml').read_text().replace('    ports:\n      - "${WORKOUT_BIND_ADDRESS:-127.0.0.1}:${WORKOUT_PORT:-8000}:8000"','    network_mode: none')
    compose=compose.replace('services:\n','name: phase8-'+tmp_path.name[:40].replace('_','-').lower()+'\nservices:\n',1)
    (root/'app/compose.yaml').write_text(compose)
    (root/'.env').write_text(f'WORKOUT_DATA_ROOT={root}/data/storage\nWORKOUT_UID={os.getuid()}\nWORKOUT_GID={os.getgid()}\n')
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    state=root/'updater';config=dict(root=str(root),uid=os.getuid(),gid=os.getgid(),status_url=f'http://127.0.0.1:{port}/status',app_url='http://127.0.0.1:8000')
    (state/'config.json').write_text(json.dumps(config))
    bridge=root/'data/storage/config/updater-bridge';bridge.mkdir()
    (bridge/'client.json').write_text(json.dumps({'status_url':config['status_url']}))
    service_env={**env,'PYTHONPATH':str(REPO)}
    service_log=(root/'updater/service-test.log').open('w')
    service=subprocess.Popen([sys.executable,'-m','workout_updater','serve','--root',str(root)],env=service_env,stdout=service_log,stderr=service_log)
    docker=shutil.which('docker');prefix=[docker,'--host=unix:///var/run/docker.sock','compose','--project-directory',str(root/'app'),'--env-file',str(root/'.env'),'-f',str(root/'app/compose.yaml')]
    clean_env={k:v for k,v in env.items() if k not in ('DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH')}
    manifest=root/'data/storage/config/active.json';original=root/'data/storage/data'/json.loads(manifest.read_text())['database'];before=original.read_bytes()
    try:
        deadline=time.monotonic()+15
        while True:
            try:
                with urllib.request.urlopen(config['status_url'],timeout=1) as response:assert response.status==200
                break
            except OSError:
                if time.monotonic()>deadline:
                    service_log.flush();pytest.fail('Independent host status did not start: '+(root/'updater/service-test.log').read_text()[-4000:])
                time.sleep(.1)
        # Rehearse recovery from an actually running application, not a fake
        # successful restart response. Docker exec verifies its real health.
        initial=subprocess.run([*prefix,'up','-d','--no-build'],env=clean_env,text=True,capture_output=True,timeout=30)
        assert initial.returncode==0,initial.stderr
        result=subprocess.run(['bash',str(REPO/'deployment/update_workout_tracker_v4.sh'),'--root',str(root),'--confirm','--allow-migration'],
                              env=clean_env,text=True,capture_output=True,timeout=180)
        assert (result.returncode==0)==(fault is None),result.stdout+result.stderr+'\n'+''.join(p.read_text()[-5000:] for p in state.glob('*.private.log'))
        assert original.read_bytes()==before
        assert (json.loads(manifest.read_text())['database']!=original.name)==(initial_schema<TARGET_SCHEMA_VERSION and fault not in ('shutdown','unclassified'))
        assert service.poll() is None
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/status.json',timeout=5) as response:status=json.load(response)
        if fault is None:
            assert status['status']=='Completed' and status['installed_schema']==TARGET_SCHEMA_VERSION and status['installed_version']==APP_VERSION
            assert status['backup_id']
        else:
            if status['status']!='Failed' or status['recovered']!=(fault in ('shutdown','unclassified')):
                pytest.fail(''.join(p.read_text() for p in state.glob('*.private.log')))
            assert list(state.glob('*.recovery.json')) and list(state.glob('*.private.log'))
            if fault=='startup':
                stopped=subprocess.run([*prefix,'ps','--status','running','--services'],env=clean_env,text=True,capture_output=True,check=True)
                assert not stopped.stdout.strip()
                return  # The schema-10 selection must never roll back to the older source.
            if fault=='unclassified':
                assert json.loads(manifest.read_text())['database']==original.name
            health=f"import json,urllib.request; r=json.load(urllib.request.urlopen('http://127.0.0.1:8000/health/ready')); assert r==dict(status='ready',app_version='{APP_VERSION}',schema_version={initial_schema})"
            checked=subprocess.run([*prefix,'exec','-T','web','python','-c',health],env=clean_env,text=True,capture_output=True)
            assert checked.returncode==0,checked.stderr
            return
        # The actual replacement web container can reach the host Unix socket
        # through the existing data mount, with its real configured writer UID.
        probe="import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8000/settings/updates').read(); assert b'Application Updates' in r and b'Completed' in r and b'password' not in r"
        response=subprocess.run([*prefix,'exec','-T','web','python','-c',probe],env=clean_env,text=True,capture_output=True)
        assert response.returncode==0,response.stderr
        assert (root/'app/.env').read_bytes()==(root/'.env').read_bytes()
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/console.json?operation='+status['operation'],timeout=5) as response:console=json.load(response)
        text='\n'.join(row['text'] for row in console['lines'])
        assert 'Database backup verified:' in text and 'Completed' in text
        assert 'WORKOUT_SECRET_KEY' not in text and status['console_protocol']==1
        for event in ('Backing up database','Starting services','Verifying health')+ (('Migrating database',) if initial_schema<TARGET_SCHEMA_VERSION else ()):
            assert any(row['status']==event for row in status['events'])
    finally:
        service.terminate()
        try:service.wait(timeout=5)
        except subprocess.TimeoutExpired:service.kill();service.wait()
        subprocess.run([*prefix,'down'],env=clean_env,text=True,capture_output=True,check=False,timeout=30)
        service_log.close();short.cleanup()
