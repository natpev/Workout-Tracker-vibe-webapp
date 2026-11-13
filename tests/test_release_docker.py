# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Real clean Compose/bootstrap/browser/restart and schema-12 candidate acceptance.

Only temporary host trees and loopback ports are used. Docker images are built
before this suite. No server credentials, live mounts or real Garmin calls exist.
"""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time
import pytest
from workout_tracker.storage import database_session, inspect_storage
from workout_tracker import history as h, weight_statistics as stats, workouts as w
from test_basis import basis_data
from test_container import docker

pytestmark = pytest.mark.skipif(
    os.environ.get("WORKOUT_CONTAINER_TESTS") != "1",
    reason="Opt-in isolated Docker acceptance",
)
REPO = Path(__file__).resolve().parents[1]


def wait_url(url):
    """Bounded local health polling, never a remote application deployment."""
    import urllib.request

    deadline = time.monotonic() + 30
    while True:
        try:
            with urllib.request.urlopen(url + "/health/ready", timeout=2) as response:
                info = json.load(response)
            assert info == dict(status="ready", app_version="1.0.2", schema_version=13)
            return
        except OSError:
            if time.monotonic() > deadline:
                raise
            time.sleep(0.2)


def test_documented_clean_install_real_browser_and_compose_restart(tmp_path):
    """Documented bootstrap commands create fresh storage; UI data survives both services restarting."""
    root = tmp_path / "WorkoutTracker"
    app = root / "app"
    parent = root / "data"
    app.mkdir(parents=True)
    parent.mkdir(mode=0o700)
    shutil.copy2(REPO / "compose.yaml", app / "compose.yaml")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    envfile = root / ".env"
    envfile.write_text(
        f"WORKOUT_DATA_ROOT={parent}/storage\nWORKOUT_UID={os.getuid()}\nWORKOUT_GID={os.getgid()}\nWORKOUT_BIND_ADDRESS=127.0.0.1\nWORKOUT_PORT={port}\nWORKOUT_TIMEZONE=UTC\nWORKOUT_TRUSTED_HOSTS=localhost,127.0.0.1,[::1]\n"
    )
    project = "release-" + tmp_path.name.lower().replace("_", "-")[:40]
    env = {
        k: v
        for k, v in os.environ.items()
        if k
        not in (
            "DOCKER_HOST",
            "DOCKER_CONTEXT",
            "DOCKER_TLS",
            "DOCKER_TLS_VERIFY",
            "DOCKER_CERT_PATH",
        )
    }

    def compose(*args):
        """The same checked-in Compose configuration with temporary bind paths only."""
        return subprocess.run(
            [
                "docker",
                "--host=unix:///var/run/docker.sock",
                "compose",
                "-p",
                project,
                "--project-directory",
                str(app),
                "--env-file",
                str(envfile),
                "-f",
                str(app / "compose.yaml"),
                *args,
            ],
            env=env,
            text=True,
            capture_output=True,
            check=True,
            timeout=90,
        )

    docker(
        "run",
        "--rm",
        "--network=none",
        "--read-only",
        "--tmpfs",
        "/tmp",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges:true",
        "--user",
        f"{os.getuid()}:{os.getgid()}",
        "--mount",
        f"type=bind,src={parent},dst=/bootstrap",
        "--entrypoint",
        "python",
        "workout-tracker:local",
        "-m",
        "workout_tracker",
        "init-storage",
        "--data-root",
        "/bootstrap/storage",
        "--confirm-new-storage",
    )
    compose("config", "--quiet")
    compose(
        "run",
        "--rm",
        "--no-deps",
        "web",
        "python",
        "-m",
        "workout_tracker",
        "migrate-storage",
        "--data-root",
        "/var/lib/workout-tracker",
        "--confirm-upgrade",
        "--target-version",
        "13",
    )
    assert (
        "schema version 13"
        in compose(
            "run",
            "--rm",
            "--no-deps",
            "web",
            "python",
            "-m",
            "workout_tracker",
            "check-storage",
            "--data-root",
            "/var/lib/workout-tracker",
        ).stdout
    )
    base = f"http://127.0.0.1:{port}"
    try:
        compose("up", "-d", "--no-build")
        wait_url(base)
        from playwright.sync_api import sync_playwright, expect

        with sync_playwright() as manager:
            browser = manager.chromium.launch(
                headless=True, executable_path=shutil.which("chromium")
            )
            try:
                page = browser.new_page(viewport=dict(width=1280, height=900))
                page.goto(base + "/people")
                for name in ("Alex", "Blair"):
                    page.goto(base + "/people")
                    page.locator(".add-person [name=name]").fill(name)
                    page.get_by_role("button", name="Add person", exact=True).click()
                page.goto(base + "/people")
                page.locator(".person-name").filter(has_text="Alex").click()
                person = page.url.rsplit("/", 1)[-1]
                page.get_by_role("textbox", name="Routine name", exact=True).fill(
                    "All combinations"
                )
                page.get_by_role("button", name="Create routine", exact=True).click()
                # Creation returns the dashboard; edit the newly created routine.
                if "/routines/" not in page.url:
                    page.get_by_role(
                        "link", name="Edit All combinations", exact=True
                    ).click()
                routine = page.url.rsplit("/", 1)[-1]
                for caps in range(1, 8):
                    form = page.locator("form[data-configuration]").last
                    form.locator("[name=name]").fill(f"Exercise {caps}")
                    for key, bit in (("weight", 1), ("reps", 2), ("duration", 4)):
                        form.locator(f"[name=enable_{key}]").set_checked(
                            bool(caps & bit)
                        )
                    form.locator("[name=target_sets]").fill("3")
                    if caps & 1:
                        form.locator("[name=weight_basis][value=total]").check()
                    form.get_by_role("button", name="Add exercise", exact=True).click()
                    expect(
                        page.get_by_role("heading", name=f"Exercise {caps}", exact=True)
                    ).to_be_visible()
                # Copy through the other person's real UI; identities stay shared,
                # settings independent and no workout history is inherited.
                page.goto(base+'/people')
                page.locator('.person-name').filter(has_text='Blair').click()
                page.get_by_label('Name for the copy',exact=True).fill('Independent copy')
                page.get_by_role('button',name='Copy routine',exact=True).click()
                with database_session(parent/'storage') as db:
                    copied=db.execute("SELECT id FROM routines WHERE name='Independent copy'").fetchone()[0]
                    assert copied!=routine
                    assert [r[0] for r in db.execute('SELECT exercise_id FROM routine_exercises WHERE routine_id=? ORDER BY position',(copied,))]==[r[0] for r in db.execute('SELECT exercise_id FROM routine_exercises WHERE routine_id=? ORDER BY position',(routine,))]
                # Exercise the same seven-combination workflow on actual Gunicorn.
                with database_session(parent / "storage") as db:
                    exercise_ids = [
                        r[0]
                        for r in db.execute(
                            "SELECT exercise_id FROM routine_exercises WHERE routine_id=? ORDER BY position",
                            (routine,),
                        )
                    ]
                from test_release_browser import (
                    test_seven_combinations_autosave_skip_resume_and_complete,
                )

                test_seven_combinations_autosave_skip_resume_and_complete(
                    (
                        page,
                        base,
                        dict(
                            root=parent / "storage",
                            person=person,
                            routine=routine,
                            exercises=exercise_ids,
                        ),
                    ),
                    (1280, 900),
                    "light",
                )
                page.goto(base + f"/people/{person}/weight")
                page.locator("[name=weight]").fill("220.125")
                page.get_by_role("button", name="Save body weight", exact=True).click()
                expect(page.get_by_role("link", name="Edit weigh-in")).to_have_count(1)
                page.goto(base + f"/settings/administration?person_id={person}")
                with page.expect_download() as download:
                    page.get_by_role(
                        "button", name="Download Database", exact=True
                    ).click()
                assert (
                    Path(download.value.path())
                    .read_bytes()
                    .startswith(b"SQLite format 3")
                )
                compose("restart")
                wait_url(base)
                page.goto(base + f"/people/{person}/history")
                expect(
                    page.get_by_role("link", name="All combinations", exact=False).first
                ).to_be_visible()
                page.goto(base + f"/people/{person}/weight")
                expect(page.get_by_role("link", name="Edit weigh-in")).to_have_count(1)
                with database_session(parent / "storage") as db:
                    assert db.execute("SELECT count(*) FROM people").fetchone()[0] == 2
                    assert (
                        db.execute("SELECT count(*) FROM workout_sets").fetchone()[0]
                        == 21
                    )
                    assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            finally:
                browser.close()
    finally:
        compose("down", "--remove-orphans")


def test_schema12_real_cli_upgrade_preserves_legacy_history_drafts_icons_and_audits(
    basis_data,
):
    """Actual container migration retains every old field and interpreted lifetime total."""
    from workout_tracker.migrations import migrate_storage
    from workout_tracker.exercise_icons import update
    from workout_tracker import preferences

    x = basis_data
    root = x["root"]
    migrate_storage(root, 12)
    with database_session(root, write=True) as db:
        update(db, x["e"], "start", '<svg><circle r="10" fill="var(--accent)"/></svg>')
    # Extend the archived conversion household with actual schema-12 reps and a
    # combined duration occurrence; all are genuine legacy snapshots after upgrade.
    from workout_tracker import catalog as c
    with database_session(root,write=True) as db:
        routine=c.create_routine(db,x['a'],'Schema 12 measurements')
        c.add_entry(db,x['a'],routine,dict(name='Legacy actual reps',measurement_type='weight',target_sets='2',target_reps='12',weight_basis='total'))
        c.add_entry(db,x['a'],routine,dict(name='Legacy weighted hold',measurement_type='weight_duration',target_sets='3',seconds='45',weight_basis='per_side'))
        form=h.prepare(db,x['a'],routine,dict(workout_date='2020-05-01',workout_time='09:00'),'UTC')
        saved=h.complete_historical(db,x['a'],form,dict(weight_0='40',reps_0_0='12',reps_0_1='9',weight_1='20',seconds_1='90'))
        h.correct(db,x['a'],saved,dict(weight_0='42.5',reps_0_0='11',reps_0_1='8',weight_1='25',seconds_1='95',workout_date='2020-05-01',workout_time='09:00',confirm='yes',correction_revision='0'))
    preferences.set_color(root, x["a"], "purple")
    source = (
        root
        / "data"
        / json.loads((root / "config/active.json").read_text())["database"]
    )
    original = source.read_bytes()
    with database_session(root) as db:
        before = h.all_completed(db, x["a"])
        total = sum(stats.workout_total(rows) for _, rows in before)
        draft = w.active(db, x["a"])
        draft_rows = w.entries(db, x["a"], draft["id"])
        audit = [
            tuple(r)
            for r in db.execute("SELECT * FROM workout_corrections ORDER BY id")
        ]
    docker(
        "run",
        "--rm",
        "--network=none",
        "--user",
        f"{os.getuid()}:{os.getgid()}",
        "--mount",
        f"type=bind,src={root},dst=/storage",
        "workout-tracker:local",
        "python",
        "-m",
        "workout_tracker",
        "migrate-storage",
        "--data-root",
        "/storage",
        "--target-version",
        "13",
        "--confirm-upgrade",
    )
    assert (
        source.read_bytes() == original
        and inspect_storage(root)["schema_version"] == 13
    )
    with database_session(root) as db:
        after = h.all_completed(db, x["a"])
        assert [
            (p, [{k: v for k, v in row.items() if k != "capabilities"} for row in rows])
            for p, rows in after
        ] == before
        assert sum(stats.workout_total(rows) for _, rows in after) == total
        assert [
            tuple(r)
            for r in db.execute("SELECT * FROM workout_corrections ORDER BY id")
        ] == audit
        assert [
            {k: v for k, v in row.items() if k != "capabilities"}
            for row in w.entries(db, x["a"], draft["id"])
        ] == draft_rows
        assert db.execute("SELECT count(*) FROM exercise_icons").fetchone()[0] == 1
        assert not db.execute("PRAGMA foreign_key_check").fetchall()
    assert preferences.colors(root)[x["a"]] == "purple"
