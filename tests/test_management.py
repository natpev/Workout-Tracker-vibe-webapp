# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""HTTP integration tests: signed CSRF form -> route -> catalog -> SQLite.

All clients and data come from migrated disposable fixtures. Requests prove
ownership, form validation, escaped output and complete routine-management flow.
"""

import html
import re

from workout_tracker import catalog as c
from workout_tracker.storage import database_session


def form_values(response):
    """Extract only security fields from actual rendered server forms."""
    text = response.get_data(as_text=True)
    fields = {}
    for name in ("csrf_token", "revision"):
        match = re.search(r'name="' + name + r'" value="([^"]+)"', text)
        if match:
            fields[name] = html.unescape(match.group(1))
    return fields


def submit(client, path, values, *, page=None):
    """Visit a form, preserving signed cookies, then send its current tokens."""
    response = client.get(page or path, follow_redirects=True)
    assert response.status_code == 200, response.get_data(as_text=True)
    return client.post(path, data={**form_values(response), **values})


def seed(root):
    """Create two owned routines to test HTTP separation without real records."""
    with database_session(root, write=True) as db:
        a, b = c.create_person(db, "A"), c.create_person(db, "B")
        r = c.create_routine(db, a, "Strength")
    return a, b, r


def test_full_person_and_routine_http_flow(phase2_client, phase2_root):
    """Create/rename users/routines, add/edit/remove typed items and delete routine."""
    client = phase2_client
    assert client.get("/").status_code == 302
    response = submit(client, "/people", {"name": "Alex"})
    assert response.status_code == 303
    person_path = response.location
    person_id = person_path.rsplit("/", 1)[1]
    response = submit(client, person_path, {"action": "create", "name": "Strength"})
    assert response.status_code == 303
    routine_path = response.location
    response = submit(client, routine_path, {"action": "add", "name": "Bench", "measurement_type": "weight",
                                           "target_sets": "3", "target_reps": "12", "notes": "Easy"})
    assert response.status_code == 303
    with database_session(phase2_root) as db:
        item = dict(db.execute("SELECT * FROM routine_exercises").fetchone())
    item_path = routine_path + "/items/" + item["id"]
    response = submit(client, item_path, {"action": "save", "measurement_type": "time", "target_sets": "3",
                                        "minutes": "1", "seconds": "5", "target_reps": "12"})
    assert response.status_code == 303
    with database_session(phase2_root) as db:
        saved = db.execute("SELECT * FROM routine_exercises").fetchone()
        assert saved["target_duration_seconds"] == 65
        assert saved["target_reps"] is None
        assert saved["exercise_id"] == item["exercise_id"]
    assert b"1 min 5 sec" in client.get(routine_path).data
    assert submit(client, routine_path, {"action": "rename", "name": "New routine"}).status_code == 303
    assert submit(client, item_path, {"action": "remove", "confirm": "yes"}).status_code == 303
    assert submit(client, routine_path, {"action": "delete", "confirm": "yes"}).status_code == 303
    assert client.get(routine_path).status_code == 404
    with database_session(phase2_root) as db:
        assert db.execute("SELECT archived FROM routines").fetchone()[0] == 1
        assert db.execute("SELECT id FROM exercises").fetchone()[0] == item["exercise_id"]
    manage = person_path + "/manage"
    assert submit(client, manage, {"action": "archive", "confirm": "yes"}, page="/people").status_code == 303
    assert client.get(person_path).status_code == 404
    assert submit(client, manage, {"action": "reactivate"}, page="/people").status_code == 303
    assert submit(client, manage, {"action": "rename", "name": "Renamed"}, page="/people").status_code == 303
    assert b"Renamed" in client.get("/people").data


def test_csrf_ownership_conflicts_and_validation(phase2_client, phase2_root):
    """Invalid requests cannot mutate data, including forged IDs and stale forms."""
    client = phase2_client
    a, b, r = seed(phase2_root)
    path = f"/people/{a}/routines/{r}"
    assert client.post(path, data={"action": "delete", "confirm": "yes"}).status_code == 400
    assert client.get(f"/people/{b}/routines/{r}").status_code == 404
    token = form_values(client.get(path))
    assert client.post(f"/people/{b}/routines/{r}", data={**token, "action": "delete", "confirm": "yes"}).status_code == 404
    assert client.post(path, data={**token, "action": "rename", "name": "Updated"}).status_code == 303
    assert client.post(path, data={**token, "action": "rename", "name": "Stale"}).status_code == 409
    assert submit(client, path, {"action": "delete"}).status_code == 400
    assert submit(client, path, {"action": "add", "name": "Bad", "measurement_type": "time", "target_sets": "3",
                                 "minutes": "0", "seconds": "-60"}).status_code == 400
    with database_session(phase2_root) as db:
        assert db.execute("SELECT name FROM routines WHERE id=?", (r,)).fetchone()[0] == "Updated"
        assert db.execute("SELECT count(*) FROM exercises").fetchone()[0] == 0


def test_copy_duplicate_and_exercise_library_routes(phase2_client, phase2_root):
    """Cross-person copying and own duplication are explicit independent actions."""
    client = phase2_client
    a, b, r = seed(phase2_root)
    source_path = f"/people/{a}/routines/{r}"
    with database_session(phase2_root, write=True) as db:
        c.add_entry(db, a, r, {"name": "Plank", "measurement_type": "time", "target_sets": "3", "minutes": "0", "seconds": "45"})
    response = submit(client, f"/people/{b}", {"action": "copy", "name": "Copy", "source": f"{a}:{r}"})
    assert response.status_code == 303
    copy_path = response.location
    assert b"0 min 45 sec" in client.get(copy_path).data
    assert submit(client, source_path, {"action": "duplicate", "name": "Duplicate"}).status_code == 303
    library = f"/people/{b}/exercises"
    with database_session(phase2_root) as db:
        identity = db.execute("SELECT id FROM exercises WHERE person_id=?", (b,)).fetchone()[0]
    assert submit(client, library, {"action": "rename", "exercise_id": identity, "name": "Copied Plank"}).status_code == 303
    assert b"Copied Plank" not in client.get(source_path).data
    assert submit(client, f"/people/{a}/exercises", {"action": "rename", "exercise_id": identity, "name": "Forbidden"}).status_code == 404
    assert submit(client, library, {"action": "create", "name": "<script>alert(1)</script>"}).status_code == 303
    response = client.get(library)
    assert b"&lt;script&gt;alert(1)&lt;/script&gt;" in response.data
    assert b"<script>alert(1)</script>" not in response.data


def test_schema1_readonly_fallback_and_upgrade_required(tmp_path):
    """New app code must not auto-migrate a still-compatible Phase 1 foundation."""
    from workout_tracker import create_app
    from workout_tracker.storage import initialize_storage, inspect_storage
    root = tmp_path / "old"
    initialize_storage(root)
    client = create_app({"WORKOUT_DATA_ROOT": root, "TESTING": True}).test_client()
    assert client.get("/").status_code == 200
    assert client.get("/people").status_code == 503
    assert inspect_storage(root)["schema_version"] == 1


def test_non_ascii_security_fields_fail_cleanly(phase2_client, phase2_root):
    """Forged Unicode tokens/revisions are errors, never uncaught TypeErrors."""
    client = phase2_client
    a, _, r = seed(phase2_root)
    assert submit(client, "/people", {"name": "No insert", "csrf_token": "☃"}).status_code == 400
    path = f"/people/{a}/routines/{r}"
    assert submit(client, path, {"action": "rename", "name": "No edit", "revision": "☃"}).status_code == 409


def test_missing_session_key_never_regenerated(phase2_root):
    """Removing a key blocks startup and leaves config unchanged for inspection."""
    from workout_tracker import create_app
    from workout_tracker.storage import StorageError
    import pytest
    key = phase2_root / "config" / "session.key"
    key.unlink()
    with pytest.raises(StorageError):
        create_app({"WORKOUT_DATA_ROOT": phase2_root})
    assert not key.exists()


def test_schema1_process_requires_restart_after_offline_migration(tmp_path):
    """An old process without a key fails safely rather than serving broken forms."""
    from workout_tracker import create_app
    from workout_tracker.storage import initialize_storage
    from workout_tracker.migrations import migrate_storage
    root = tmp_path / "restart-review"
    initialize_storage(root)
    old = create_app({"WORKOUT_DATA_ROOT": root, "TESTING": True}).test_client()
    migrate_storage(root)
    assert old.get("/people").status_code == 503
    assert old.get("/health/ready").status_code == 503
    restarted = create_app({"WORKOUT_DATA_ROOT": root, "TESTING": True}).test_client()
    assert restarted.get("/people").status_code == 200
    assert restarted.get("/health/ready").status_code == 200
