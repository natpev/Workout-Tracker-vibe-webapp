# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""Opt-in Docker smoke tests run only against the managed local daemon.

pytest creates disposable host metadata and mounts it read-only into test
containers. No host ports or network are enabled; HTTP checks run inside them.
Set WORKOUT_CONTAINER_TESTS=1 after building workout-tracker:phase1-review.
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


def start_container(root):
    """Start one local-only disposable process with retained read-only storage."""
    return docker(
        "run", "-d", "--network=none", "--read-only", "--tmpfs", "/tmp",
        "--cap-drop=ALL", "--security-opt=no-new-privileges",
        "--user", f"{os.getuid()}:{os.getgid()}",
        "--mount", f"type=bind,src={root},dst=/var/lib/workout-tracker,readonly",
        "-e", "WORKOUT_DATA_ROOT=/var/lib/workout-tracker",
        "workout-tracker:phase1-review",
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
    assert service["volumes"][0]["read_only"] is True
    # Compose omits false values in normalized output; absence also means false.
    assert service["volumes"][0]["bind"].get("create_host_path", False) is False
    assert service["read_only"] is True
