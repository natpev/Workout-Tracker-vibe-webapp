# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""Opt-in Docker smoke tests run only against the managed local daemon.

pytest creates disposable host metadata and mounts it read-only into test
containers. No host ports or network are enabled; HTTP checks run inside them.
Set WORKOUT_CONTAINER_TESTS=1 after building workout-tracker:phase3-review.
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
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.rglob("*") if path.is_file()}


def start_container(root, *, writable=False):
    """Start one local-only disposable process with retained read-only storage."""
    return docker(
        "run", "-d", "--network=none", "--read-only", "--tmpfs", "/tmp",
        "--cap-drop=ALL", "--security-opt=no-new-privileges",
        "--user", f"{os.getuid()}:{os.getgid()}",
        "--mount", f"type=bind,src={root},dst=/var/lib/workout-tracker" + ("" if writable else ",readonly"),
        "-e", "WORKOUT_DATA_ROOT=/var/lib/workout-tracker",
        "workout-tracker:phase3-review",
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
    result = subprocess.run(["docker", "compose", "config", "--format", "json"],
                            env=environment, capture_output=True, text=True, check=True, timeout=15)
    service = json.loads(result.stdout)["services"]["web"]
    assert service["ports"][0]["host_ip"] == "127.0.0.1"
    assert service["volumes"][0].get("read_only", False) is False
    # Compose omits false values in normalized output; absence also means false.
    assert service["volumes"][0]["bind"].get("create_host_path", False) is False
    assert service["read_only"] is True


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
