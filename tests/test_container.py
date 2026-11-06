# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""Opt-in Docker smoke tests run only against the managed local daemon.

pytest creates disposable host metadata and mounts it read-only into test
containers. No host ports or network are enabled; HTTP checks run inside them.
Set WORKOUT_CONTAINER_TESTS=1 after building workout-tracker:phase5-review.
"""

import hashlib
import json
import os
import sqlite3
import subprocess
import time

import pytest

from workout_tracker.storage import initialize_storage

pytestmark = pytest.mark.skipif(
    os.environ.get("WORKOUT_CONTAINER_TESTS") != "1", reason="Opt-in isolated Docker checks"
)


def docker(*arguments, check=True):
    """Invoke only the local daemon; capture output without dumping credentials."""
    environment = os.environ.copy()
    for name in ("DOCKER_HOST", "DOCKER_CONTEXT", "DOCKER_TLS", "DOCKER_TLS_VERIFY", "DOCKER_CERT_PATH"):
        environment.pop(name, None)
    return subprocess.run(
        ["docker", "--host=unix:///var/run/docker.sock", *arguments],
        env=environment, capture_output=True, text=True, check=check, timeout=30,
    )


def storage_bytes(root):
    """Hash files to detect any container-triggered copies, migrations or writes."""
    # Phase 5 may append diagnostics; all database/config/archive bytes remain protected.
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.rglob("*") if path.is_file() and "logs" not in path.relative_to(root).parts}


def start_container(root, *, writable=False):
    """Start one local-only disposable process with retained read-only storage."""
    return docker(
        "run", "-d", "--network=none", "--read-only", "--tmpfs", "/tmp",
        "--cap-drop=ALL", "--security-opt=no-new-privileges",
        "--user", f"{os.getuid()}:{os.getgid()}",
        "--mount", f"type=bind,src={root},dst=/var/lib/workout-tracker" + ("" if writable else ",readonly"),
        "-e", "WORKOUT_DATA_ROOT=/var/lib/workout-tracker",
        "workout-tracker:phase5-review",
    ).stdout.strip()


def test_container_replacement_and_schema_refusal(tmp_path):
    """Real Gunicorn requests survive replacement; incompatible storage stops boot."""
    root = tmp_path / "container-storage"
    initialize_storage(root)
    original = storage_bytes(root)
    for _ in range(2):
        container = start_container(root)
        try:
            deadline = time.monotonic() + 15
            while True:
                result = docker("exec", container, "python", "-c",
                    "import json, urllib.request; "
                    "r=urllib.request.urlopen('http://127.0.0.1:8000/health/ready',timeout=2); "
                    "assert json.load(r)['status']=='ready'; "
                    "r=urllib.request.urlopen('http://127.0.0.1:8000/',timeout=2); "
                    "assert b'Foundation ready for review' in r.read()", check=False)
                if result.returncode == 0:
                    break
                if time.monotonic() >= deadline:
                    logs = docker("logs", container)
                    pytest.fail("Container readiness failed: " + result.stdout + result.stderr
                                + logs.stdout + logs.stderr)
                time.sleep(.2)
            state = json.loads(docker("inspect", container).stdout)[0]
            assert state["HostConfig"]["NetworkMode"] == "none"
            assert state["HostConfig"]["ReadonlyRootfs"] is True
            assert state["NetworkSettings"]["Ports"] == {}
            assert storage_bytes(root) == original
        finally:
            docker("rm", "-f", container)

    # Change only this disposable fixture to simulate a newer schema release.
    manifest = json.loads((root / "config" / "active.json").read_text())
    with sqlite3.connect(root / "data" / manifest["database"]) as connection:
        connection.execute("PRAGMA user_version=999")
    incompatible = storage_bytes(root)
    container = start_container(root)
    try:
        result = docker("wait", container)
        assert int(result.stdout.strip()) != 0
        logs = docker("logs", container)
        assert "Unsupported schema version" in logs.stdout + logs.stderr
        assert storage_bytes(root) == incompatible
    finally:
        docker("rm", "-f", container)


def test_compose_configuration_is_loopback_and_external(tmp_path):
    """Validate actual Compose interpolation without starting deployment services."""
    environment = os.environ.copy()
    environment["WORKOUT_DATA_ROOT"] = str(tmp_path / "external")
    environment["WORKOUT_BIND_ADDRESS"] = "127.0.0.1"
    result = subprocess.run(["docker", "compose", "config", "--format", "json"],
                            env=environment, capture_output=True, text=True, check=True, timeout=15)
    service = json.loads(result.stdout)["services"]["web"]
    assert service["ports"][0]["host_ip"] == "127.0.0.1"
    assert service["volumes"][0].get("read_only", False) is False
    # Compose omits false values in normalized output; absence also means false.
    assert service["volumes"][0]["bind"].get("create_host_path", False) is False
    assert service["read_only"] is True
    assert service['image']=='workout-tracker:local'
    assert service['restart']=='unless-stopped'
    assert service['environment']['WORKOUT_SECRET_KEY']==environment.get('WORKOUT_SECRET_KEY','')
    scheduler=json.loads(result.stdout)['services']['scheduler']
    assert scheduler['image']==service['image'] and scheduler['restart']=='unless-stopped'
    assert scheduler['command']==['python','-m','workout_tracker','scheduler']
    assert scheduler['network_mode']=='none' and scheduler['read_only'] is True
    assert not scheduler.get('ports') and scheduler['user']==service['user']
    assert scheduler['volumes'][0]['source']==service['volumes'][0]['source']


def test_phase2_container_writes_persist_and_original_is_untouched(phase2_root):
    """Exercise actual CSRF writes through Gunicorn, replace container, read data."""
    root = phase2_root
    original = next((root / "data").glob("schema-1-*.sqlite3"))
    original_bytes = original.read_bytes()
    retained = None
    for iteration in range(2):
        container = start_container(root, writable=True)
        try:
            deadline = time.monotonic() + 15
            while True:
                probe = docker("exec", container, "python", "-c",
                    "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready',timeout=2)", check=False)
                if probe.returncode == 0:
                    break
                if time.monotonic() >= deadline:
                    pytest.fail("Phase 2 container failed readiness: " + probe.stderr)
                time.sleep(.2)
            if iteration == 0:
                # Actual browser-like form submission with signed cookies and the
                # rendered CSRF token. Only synthetic fixture names are sent.
                script = """
import http.cookiejar, re, urllib.parse, urllib.request
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
base = 'http://127.0.0.1:8000'
page = opener.open(base + '/people').read().decode()
token = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
page = opener.open(base + '/people', urllib.parse.urlencode({'name':'Container Fixture','csrf_token':token}).encode()).read().decode()
assert 'Container Fixture' in page
"""
                docker("exec", container, "python", "-c", script)
                retained = storage_bytes(root)
            else:
                docker("exec", container, "python", "-c",
                       "import urllib.request; assert b'Container Fixture' in urllib.request.urlopen('http://127.0.0.1:8000/people').read()")
                assert storage_bytes(root) == retained
            assert original.read_bytes() == original_bytes
        finally:
            docker("rm", "-f", container)


def test_schema3_draft_survives_container_replacement(phase3_root):
    """Actual Gunicorn draft POST persists across isolated container replacement."""
    from workout_tracker import catalog as c
    from workout_tracker.storage import database_session
    with database_session(phase3_root,write=True) as db:
        person=c.create_person(db,'Workout container fixture')
        routine=c.create_routine(db,person,'Fixture routine')
        c.add_entry(db,person,routine,dict(name='Bench',measurement_type='weight',target_sets='3',target_reps='12'))
    originals={p:p.read_bytes() for p in (phase3_root/'data').glob('schema-[12]-*.sqlite3')}
    session_path=None
    for iteration in range(2):
        container=start_container(phase3_root,writable=True)
        try:
            deadline=time.monotonic()+15
            while True:
                probe=docker('exec',container,'python','-c',
                    "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready',timeout=2)",check=False)
                if probe.returncode==0: break
                if time.monotonic()>=deadline: pytest.fail('Schema 3 container readiness failed: '+probe.stderr)
                time.sleep(.2)
            if iteration==0:
                script=f"""
import http.cookiejar,json,re,urllib.parse,urllib.request
opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
base='http://127.0.0.1:8000'
routine='/people/{person}/routines/{routine}'
page=opener.open(base+routine).read().decode()
token=re.search(r'name="csrf_token" value="([^"]+)"',page).group(1)
response=opener.open(base+routine+'/start',urllib.parse.urlencode({{'csrf_token':token}}).encode())
path=urllib.parse.urlsplit(response.url).path
page=response.read().decode()
fields=dict(re.findall(r'name="(csrf_token|revision|entry_id|current_position)" value="([^"]*)"',page))
fields.update(weight='40.99',increase='1')
result=json.load(opener.open(base+path+'/draft',urllib.parse.urlencode(fields).encode()))
assert result['weight']=='40.9' and result['completed']==1
print(path)
"""
                session_path=docker('exec',container,'python','-c',script).stdout.strip()
            else:
                docker('exec',container,'python','-c',
                    f"import urllib.request; page=urllib.request.urlopen('http://127.0.0.1:8000{session_path}').read(); assert b'value=\"40.9\"' in page; assert b'Increase weight next time' in page")
            assert all(path.read_bytes()==content for path,content in originals.items())
        finally:
            docker('rm','-f',container)


def test_history_correction_survives_container_replacement(phase4_root):
    """Actual HTTP correction appends an audit row; effective charts persist after replacement."""
    from workout_tracker import catalog as c, history as h
    from workout_tracker.storage import database_session
    with database_session(phase4_root,write=True) as db:
        person=c.create_person(db,'History container fixture');routine=c.create_routine(db,person,'Past workout')
        c.add_entry(db,person,routine,dict(name='Bench',measurement_type='weight',target_sets='3',target_reps='12'))
        form=h.prepare(db,person,routine,dict(workout_date='2020-01-01',workout_time=''),'UTC')
        identity=h.complete_historical(db,person,form,{'weight_0':'40.99'})
    originals={path:path.read_bytes() for path in (phase4_root/'data').glob('schema-[123]-*.sqlite3')}
    for iteration in range(2):
        container=start_container(phase4_root,writable=True)
        try:
            deadline=time.monotonic()+15
            while True:
                probe=docker('exec',container,'python','-c',
                    "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready',timeout=2)",check=False)
                if probe.returncode==0: break
                if time.monotonic()>=deadline: pytest.fail('History container readiness failed: '+probe.stderr)
                time.sleep(.2)
            if iteration==0:
                script=f"""
import http.cookiejar,re,urllib.parse,urllib.request
opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
base='http://127.0.0.1:8000'
path='/people/{person}/history/{identity}/correct'
page=opener.open(base+path).read().decode()
fields=dict(re.findall(r'name="(csrf_token|correction_revision)" value="([^"]*)"',page))
fields.update(workout_date='2021-02-03',workout_time='',weight_0='42.56',confirm='yes')
page=opener.open(base+path,urllib.parse.urlencode(fields).encode()).read()
assert b'42.5 lb' in page and b'Correction 1' in page
"""
                docker('exec',container,'python','-c',script)
            docker('exec',container,'python','-c',
                f"import urllib.request; page=urllib.request.urlopen('http://127.0.0.1:8000/people/{person}/progress').read(); assert b'42.5 lb' in page and b'<svg ' in page")
            assert all(path.read_bytes()==content for path,content in originals.items())
        finally: docker('rm','-f',container)
    with database_session(phase4_root) as db:
        assert db.execute('SELECT count(*) FROM workout_corrections').fetchone()[0]==1
        assert db.execute('SELECT actual_weight_tenths_lb FROM historical_entries').fetchone()[0]==409


def test_phase5_backup_restore_metadata_and_logs_survive_replacement(phase4_root):
    """Actual Gunicorn forms preserve backup/restore audit and logs outside the image."""
    from workout_tracker import maintenance as m,operations as o
    root=phase4_root
    for iteration in range(2):
        container=start_container(root,writable=True)
        try:
            deadline=time.monotonic()+15
            while True:
                probe=docker('exec',container,'python','-c',"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready',timeout=2)",check=False)
                if probe.returncode==0: break
                if time.monotonic()>=deadline: pytest.fail('Phase 5 container readiness failed: '+probe.stderr)
                time.sleep(.2)
            if iteration==0:
                script="""
import http.cookiejar,re,urllib.parse,urllib.request
opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
base='http://127.0.0.1:8000'
page=opener.open(base+'/settings').read().decode()
fields=dict(re.findall(r'name="(csrf_token|operation_id)" value="([^"]*)"',page))
response=opener.open(base+'/settings/backup',urllib.parse.urlencode(fields).encode())
path=urllib.parse.urlsplit(response.url).path;page=response.read().decode()
assert 'id="backup-status">verified' in page
fields=dict(re.findall(r'name="(csrf_token|operation_id)" value="([^"]*)"',page));fields.update(confirm='yes',confirmation='RESTORE')
page=opener.open(base+path+'/restore',urllib.parse.urlencode(fields).encode()).read()
assert b'succeeded' in page
"""
                docker('exec',container,'python','-c',script)
            docker('exec',container,'python','-c',"import urllib.request; page=urllib.request.urlopen('http://127.0.0.1:8000/settings').read(); assert b'verified' in page and b'succeeded' in page; assert b'Restore completed' in urllib.request.urlopen('http://127.0.0.1:8000/settings/logs').read()")
        finally: docker('rm','-f',container)
    state=o.read_state(root);assert len(state['backups'])==len(state['restores'])==1
    record=next(iter(state['backups'].values()));assert m.backup_path(root,record).exists()


def test_dedicated_scheduler_container_due_slot_and_restart(phase4_root):
    """Independent non-web containers share durable claims, producing one missed backup."""
    from workout_tracker import operations as o
    from workout_tracker.storage import storage_lock
    root=phase4_root
    with storage_lock(root,exclusive=True):
        state=o.read_state(root);state['schedule'].update(enabled=True,anchor='2020-01-01',next='2020-01-01T02:00:00+00:00',revision=1)
        o.write_state(root,state)
    for _ in range(2):
        docker('run','--rm','--network=none','--read-only','--tmpfs','/tmp','--cap-drop=ALL','--security-opt=no-new-privileges',
               '--user',f'{os.getuid()}:{os.getgid()}','--mount',f'type=bind,src={root},dst=/var/lib/workout-tracker',
               '-e','WORKOUT_DATA_ROOT=/var/lib/workout-tracker','workout-tracker:phase5-review','python','-m','workout_tracker','scheduler','--once')
    current=o.read_state(root)
    assert len(current['backups'])==1 and current['schedule']['result']=='Verified'
    assert next(iter(current['backups'].values()))['source']=='automatic'


def test_scheduler_long_running_service_needs_no_browser_and_stops_cleanly(phase4_root):
    """Actual scheduler daemon claims a due slot without Gunicorn and logs orderly exit."""
    from workout_tracker import operations as o
    from workout_tracker.storage import storage_lock
    root=phase4_root
    with storage_lock(root,exclusive=True):
        state=o.read_state(root);state['schedule'].update(enabled=True,anchor='2020-01-01',next='2020-01-01T02:00:00+00:00',revision=1)
        o.write_state(root,state)
    container=docker('run','-d','--network=none','--read-only','--tmpfs','/tmp','--cap-drop=ALL','--security-opt=no-new-privileges',
                     '--user',f'{os.getuid()}:{os.getgid()}','--mount',f'type=bind,src={root},dst=/var/lib/workout-tracker',
                     '-e','WORKOUT_DATA_ROOT=/var/lib/workout-tracker','workout-tracker:phase5-review','python','-m','workout_tracker','scheduler').stdout.strip()
    try:
        deadline=time.monotonic()+10
        while True:
            with storage_lock(root): current=o.read_state(root)
            if current['schedule']['result']=='Verified': break
            if time.monotonic()>=deadline: pytest.fail('Dedicated scheduler did not run its due backup')
            time.sleep(.1)
        assert len(current['backups'])==1
        docker('stop','--time','5',container)
        assert any('Scheduler process stopped' in path.read_text() for path in (root/'logs').glob('events-*.jsonl'))
    finally: docker('rm','-f',container)


def test_documented_parent_bootstrap_and_compose_installation(tmp_path,monkeypatch):
    """Exercise README's parent mount, schema-4 CLI and both real Compose services.

    Paths are temporary. A test-only override removes ports and networking;
    production bind addresses are checked separately without exposing anything.
    """
    from pathlib import Path
    from uuid import uuid4
    for name in ('WORKOUT_DATA_ROOT','WORKOUT_UID','WORKOUT_GID','WORKOUT_PORT',
                 'WORKOUT_BIND_ADDRESS','WORKOUT_TIMEZONE','WORKOUT_TRUSTED_HOSTS',
                 'WORKOUT_SECRET_KEY','WORKOUT_BUILD_CA_BUNDLE'):
        monkeypatch.delenv(name,raising=False)
    parent=tmp_path/'install-parent';parent.mkdir(mode=0o700)
    root=parent/'storage';project='workout-doc-'+uuid4().hex[:12]
    envfile=tmp_path/'install.env'
    envfile.write_text(f'WORKOUT_DATA_ROOT={root}\nWORKOUT_UID={os.getuid()}\nWORKOUT_GID={os.getgid()}\nWORKOUT_PORT=8000\nWORKOUT_BIND_ADDRESS=127.0.0.1\nWORKOUT_TIMEZONE=America/Indiana/Indianapolis\nWORKOUT_TRUSTED_HOSTS=localhost,127.0.0.1,[::1]\nWORKOUT_BUILD_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt\n')
    envfile.chmod(0o600)
    override=tmp_path/'isolated.yaml'
    override.write_text('# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.\n# Test isolation only; no published services.\nservices:\n  web:\n    ports: !reset []\n    network_mode: none\n')
    base=Path(__file__).resolve().parents[1]/'compose.yaml'
    prefix=('compose','--project-name',project,'--env-file',str(envfile),'-f',str(base))
    isolated=(*prefix,'-f',str(override))
    bootstrap=('run','--rm','--network=none','--read-only','--tmpfs','/tmp','--cap-drop=ALL',
               '--security-opt=no-new-privileges:true','--user',f'{os.getuid()}:{os.getgid()}',
               '--mount',f'type=bind,src={parent},dst=/bootstrap','--entrypoint','python',
               'workout-tracker:local','-m','workout_tracker','init-storage','--data-root','/bootstrap/storage','--confirm-new-storage')
    try:
        # The production .env interpolates loopback; an explicit LAN address only
        # changes publishing/allowed hosts, not container identity or schema.
        config=json.loads(docker(*prefix,'config','--format','json').stdout)
        assert config['services']['web']['ports'][0]['host_ip']=='127.0.0.1'
        envfile.write_text(envfile.read_text().replace('WORKOUT_BIND_ADDRESS=127.0.0.1','WORKOUT_BIND_ADDRESS=192.168.1.100').replace('WORKOUT_TRUSTED_HOSTS=localhost,127.0.0.1,[::1]','WORKOUT_TRUSTED_HOSTS=localhost,127.0.0.1,[::1],192.168.1.100'))
        lan=json.loads(docker(*prefix,'config','--format','json').stdout)
        assert lan['services']['web']['ports'][0]['host_ip']=='192.168.1.100'
        assert '192.168.1.100' in lan['services']['web']['environment']['WORKOUT_TRUSTED_HOSTS']
        # An explicit test value proves forwarding; no actual signing secret is printed.
        envfile.write_text(envfile.read_text()+'WORKOUT_SECRET_KEY=fixture-only-forwarding-check\n')
        assert json.loads(docker(*prefix,'config','--format','json').stdout)['services']['web']['environment']['WORKOUT_SECRET_KEY']=='fixture-only-forwarding-check'
        envfile.write_text(envfile.read_text().replace('WORKOUT_SECRET_KEY=fixture-only-forwarding-check\n',''))
        docker(*isolated,'config','--quiet')
        docker(*isolated,'build')
        assert not root.exists()
        assert 'foundation storage initialized' in docker(*bootstrap).stdout
        before=storage_bytes(root)
        refused=docker(*bootstrap,check=False)
        assert refused.returncode!=0 and storage_bytes(root)==before
        docker(*isolated,'run','--rm','--no-deps','web','python','-m','workout_tracker','migrate-storage',
               '--data-root','/var/lib/workout-tracker','--confirm-upgrade','--target-version','4')
        checked=docker(*isolated,'run','--rm','--no-deps','web','python','-m','workout_tracker','check-storage','--data-root','/var/lib/workout-tracker')
        assert 'schema version 4' in checked.stdout
        assert root.stat().st_uid==os.getuid() and (root/'config'/'session.key').stat().st_mode & 0o777==0o600
        for iteration in range(2):
            docker(*isolated,'up','-d','--no-build')
            ids={service:docker(*isolated,'ps','-q',service).stdout.strip() for service in ('web','scheduler')}
            deadline=time.monotonic()+45
            while True:
                web=json.loads(docker('inspect',ids['web']).stdout)[0]
                if web['State']['Health']['Status']=='healthy': break
                if time.monotonic()>=deadline: pytest.fail('Documented Compose web did not become healthy')
                time.sleep(.2)
            docker(*isolated,'exec','-T','web','python','-c',
                   "import json,urllib.request; d=json.load(urllib.request.urlopen('http://127.0.0.1:8000/health/ready',timeout=10)); assert d==dict(status='ready',app_version='0.5.0',schema_version=4)")
            for identity in ids.values():
                inspected=json.loads(docker('inspect',identity).stdout)[0]
                assert inspected['State']['Running'] and inspected['HostConfig']['RestartPolicy']['Name']=='unless-stopped'
                assert inspected['Config']['User']==f'{os.getuid()}:{os.getgid()}'
                assert inspected['HostConfig']['ReadonlyRootfs'] and inspected['HostConfig']['NetworkMode']=='none'
                assert inspected['NetworkSettings']['Ports']=={}
            if iteration==0:
                # A browser-like synthetic write must survive the documented
                # restart and stop/start without implicit DB migration/copy.
                script="""
import http.cookiejar,re,urllib.parse,urllib.request
opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
base='http://127.0.0.1:8000'
page=opener.open(base+'/people').read().decode()
token=re.search(r'name="csrf_token" value="([^"]+)"',page).group(1)
page=opener.open(base+'/people',urllib.parse.urlencode(dict(csrf_token=token,name='Installation fixture')).encode()).read()
assert b'Installation fixture' in page
"""
                docker(*isolated,'exec','-T','web','python','-c',script)
                retained=storage_bytes(root)
                docker(*isolated,'restart')
            else:
                docker(*isolated,'exec','-T','web','python','-c',"import urllib.request; assert b'Installation fixture' in urllib.request.urlopen('http://127.0.0.1:8000/people').read()")
                assert storage_bytes(root)==retained
            docker(*isolated,'stop')
        assert any('Scheduler process started' in path.read_text() for path in (root/'logs').glob('events-*.jsonl'))
    finally:
        docker(*isolated,'down',check=False)
