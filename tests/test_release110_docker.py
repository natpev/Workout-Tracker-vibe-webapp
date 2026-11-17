# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Real image/CLI/SQLite rehearsals; only disposable mounted synthetic records."""
import os
import json
import pytest
from test_container import docker

pytestmark = pytest.mark.skipif(
    os.environ.get("WORKOUT_CONTAINER_TESTS") != "1",
    reason="Opt-in isolated Docker checks",
)


def run(root, script):
    """Run the packaged image with no network and only this temporary test mount."""
    return docker(
        "run",
        "--rm",
        "--network=none",
        "--read-only",
        "--tmpfs",
        "/tmp",
        "--user",
        f"{os.getuid()}:{os.getgid()}",
        "--mount",
        f"type=bind,src={root},dst=/fixture",
        "--entrypoint",
        "python",
        "workout-tracker:phase8-review",
        "-c",
        script,
    )


def seed(tmp_path):
    """Use actual released schema 13 and non-generic settings, not a version-marker fake."""
    run(
        tmp_path,
        """
from pathlib import Path
import json
from workout_tracker.storage import initialize_storage,database_session
from workout_tracker.migrations import migrate_storage
from workout_tracker import catalog as c,history as h,workouts as w,garmin as g,body_weight as b
root=Path('/fixture/storage');initialize_storage(root);migrate_storage(root,13)
with database_session(root,write=True) as db:
    person=c.create_person(db,'Container person');routine=c.create_routine(db,person,'Container routine')
    entry=c.add_entry(db,person,routine,dict(name='Preserved exercise',measurement_type='flex',capabilities=3,target_sets='2',target_reps='15',weight_basis='per_side'))
    exercise=c.entry(db,person,routine,entry)['exercise_id']
    form=h.prepare(db,person,routine,dict(workout_date='2020-01-01',workout_time='08:00'),'UTC')
    h.complete_historical(db,person,form,dict(weight_0='40',reps_0_0='15',status_0_0='completed',status_0_1='skipped'))
    draft,_=w.start(db,person,routine,'UTC')
    b.manual(db,person,dict(date='2020-01-01',time='09:00',weight='219.123'),'UTC')
    g.import_weights(db,person,[dict(measured_at='2020-01-01T10:00:00.000000+00:00',weight_milli_lb=220462,source_value='{"unit":"g","value":"100000"}')])
with g.storage_lock(root,exclusive=True) as locked:
    g.write(locked,dict(version=1,people={person:dict(connected=False,key='synthetic-private-key',token='synthetic-private-token')}))
Path('/fixture/ids.json').write_text(json.dumps(dict(person=person,exercise=exercise,draft=draft)))
""",
    )


def test_real_schema13_cli_upgrade_preserves_settings_credentials_and_ego_recovery(
    tmp_path,
):
    """Candidate upgrade, app read, new data, verified restore and secret-free download."""
    seed(tmp_path)
    root = tmp_path / "storage"
    selection = json.loads((root / "config/active.json").read_text())
    original = root / "data" / selection["database"]
    before = original.read_bytes()
    secret = (root / "config/garmin-private.json").read_bytes()
    docker(
        "run",
        "--rm",
        "--network=none",
        "--read-only",
        "--tmpfs",
        "/tmp",
        "--user",
        f"{os.getuid()}:{os.getgid()}",
        "--mount",
        f"type=bind,src={tmp_path},dst=/fixture",
        "--entrypoint",
        "python",
        "workout-tracker:phase8-review",
        "-m",
        "workout_tracker",
        "migrate-storage",
        "--data-root",
        "/fixture/storage",
        "--confirm-upgrade",
        "--target-version",
        "14",
    )
    assert (
        original.read_bytes() == before
        and (root / "config/garmin-private.json").read_bytes() == secret
    )
    assert json.loads((root / "config/active.json").read_text()) != selection
    run(
        tmp_path,
        """
import json
from pathlib import Path
from uuid import uuid4
from workout_tracker import create_app,catalog as c,ego_lifts as e,workouts as w,history as h
from workout_tracker.storage import database_session
from workout_tracker.maintenance import backup,restore,logical_check_connection
from workout_tracker.database_download import snapshot
root=Path('/fixture/storage');ids=json.loads(Path('/fixture/ids.json').read_text())
with database_session(root,write=True) as db:
    settings=c.exercise_defaults(db,ids['person'],ids['exercise'])
    assert (settings['target_sets'],settings['target_reps'],settings['weight_basis'])==(2,15,'per_side')
    assert w.session(db,ids['person'],ids['draft'])['status']=='draft'
    assert len(h.all_completed(db,ids['person']))==1
    assert db.execute("SELECT weight_milli_lb FROM body_weights WHERE source='garmin'").fetchone()[0]==220500
    assert db.execute("SELECT weight_milli_lb FROM body_weights WHERE source='manual'").fetchone()[0]==219123
    lift=e.save(db,ids['person'],ids['exercise'],dict(weight='55',repetitions='1',submission_id=uuid4().hex))
    logical_check_connection(db,14)
app=create_app(dict(TESTING=True,WORKOUT_DATA_ROOT=root,WORKOUT_TIMEZONE='America/Indiana/Indianapolis'))
client=app.test_client();assert client.get('/people/'+ids['person']+'/ego-lifts').status_code==200
saved=backup(root,uuid4().hex);assert saved['status']=='verified'
with database_session(root,write=True) as db:e.correct(db,ids['person'],lift,dict(action='delete',confirm='yes',revision='0'))
assert restore(root,saved['id'],uuid4().hex,confirm=True)['status']=='succeeded'
with database_session(root) as db:
    assert e.record(db,ids['person'],lift)['weight_tenths_lb']==550
    assert len(h.all_completed(db,ids['person']))==1
with snapshot(root) as handle:
    data=handle.read();assert data.startswith(b'SQLite format 3')
    assert b'synthetic-private-key' not in data and b'synthetic-private-token' not in data
""",
    )


def test_ordinary_startup_never_migrates_old_storage_for_ego_page(tmp_path):
    """An older installed schema is preserved even when a new feature is requested."""
    seed(tmp_path)
    root = tmp_path / "storage"
    manifest = (root / "config/active.json").read_bytes()
    original = root / "data" / json.loads(manifest)["database"]
    before = original.read_bytes()
    run(
        tmp_path,
        """
from pathlib import Path
import json
from workout_tracker import create_app
root=Path('/fixture/storage');person=json.loads(Path('/fixture/ids.json').read_text())['person']
app=create_app(dict(TESTING=True,WORKOUT_DATA_ROOT=root))
response=app.test_client().get('/people/'+person+'/ego-lifts')
assert response.status_code==503
""",
    )
    assert (
        original.read_bytes() == before
        and (root / "config/active.json").read_bytes() == manifest
    )
