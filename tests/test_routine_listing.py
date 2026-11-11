# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Disposable routine-card ordering tests, including effective corrected history.

Only synthetic data is written through existing services. Read-only listing and
HTTP GET tests compare complete SQL dumps, keeping positions/audits unchanged.
"""
from datetime import datetime, timezone
import json
import re
import subprocess
from unittest.mock import patch

import pytest
from workout_tracker import APP_VERSION, create_app, catalog as c, history as h, workouts as w
from workout_tracker.routine_listing import selectable_routines
from workout_tracker.storage import database_session
from test_phase9 import phase9_root
from test_history import correction_payload
from test_phase8_deletion import approval
from workout_tracker import deletions


def routine(db, person, name):
    """Add a one-exercise synthetic routine using an existing global definition."""
    identity = c.create_routine(db, person, name)
    exercise = db.execute('SELECT id FROM exercises LIMIT 1').fetchone()
    exercise_id = exercise[0] if exercise else c.create_definition(db, person, 'Fixture exercise')
    c.add_entry(db, person, identity, dict(exercise_id=exercise_id, measurement_type='weight', target_sets='3', target_reps='12'))
    return identity


def historical(db, person, identity, day, clock=''):
    """Complete a past occurrence now; entry time must never determine its rank."""
    form = h.prepare(db, person, identity, dict(workout_date=day, workout_time=clock), 'UTC')
    return h.complete_historical(db, person, form, {'weight_0': '0'})


def order(db, person):
    """Read the permanent IDs in card order, without changing any row."""
    return [row['id'] for row in selectable_routines(db, person)]


def test_recent_old_and_alphabetical_never_completed_with_read_only_get(phase9_root):
    """Latest actual occurrence wins even when older history is entered afterward."""
    with database_session(phase9_root, write=True) as db:
        person = c.create_person(db, 'Person')
        never_z = routine(db, person, 'Zulu')
        old = routine(db, person, 'Older')
        recent = routine(db, person, 'Recent')
        never_a = routine(db, person, 'alpha')
        historical(db, person, recent, '2022-02-02')
        historical(db, person, old, '2021-01-01')
        historical(db, person, recent, '2020-01-01')
        h.prepare(db, person, never_z, dict(workout_date='2023-01-01', workout_time=''), 'UTC')
        before = '\n'.join(db.iterdump())
        expected = [recent, old, never_a, never_z]
        assert order(db, person) == expected
        assert '\n'.join(db.iterdump()) == before
    client = create_app({'TESTING': True, 'WORKOUT_DATA_ROOT': phase9_root}).test_client()
    page = client.get('/people/' + person)
    assert page.status_code == 200
    names = re.findall(r'<section class="routine-card"><div><h2>(.*?)</h2>', page.get_data(as_text=True))
    assert names == ['Recent', 'Older', 'alpha', 'Zulu']
    with database_session(phase9_root) as db:
        assert '\n'.join(db.iterdump()) == before


def test_completed_live_counts_but_drafts_and_discards_do_not(phase9_root):
    """Finishing counts; autosaving, discarding and unfinished preparations do not."""
    with database_session(phase9_root, write=True) as db:
        person = c.create_person(db, 'Person')
        discarded = routine(db, person, 'Discarded')
        live = routine(db, person, 'Live')
        draft_routine = routine(db, person, 'Active')
        past = routine(db, person, 'Past')
        historical(db, person, past, '2020-01-01')
        with patch.object(w, 'now', return_value=datetime(2021, 1, 1, 12, tzinfo=timezone.utc)):
            identity, _ = w.start(db, person, live, 'UTC')
            row = w.entries(db, person, identity)[0]
            w.finish(db, person, identity, dict(revision='0', entry_id=row['id'], current_position='0', weight='0'))
        identity, _ = w.start(db, person, discarded, 'UTC')
        w.discard(db, person, identity, {'revision': '0', 'confirm': 'yes'})
        identity, _ = w.start(db, person, draft_routine, 'UTC')
        row = w.entries(db, person, identity)[0]
        w.update(db, person, identity, dict(revision='0', entry_id=row['id'], current_position='0', weight='99'))
        assert order(db, person) == [live, past, draft_routine, discarded]


def test_owned_ids_and_independent_same_person_and_cross_person_copies(phase9_root):
    """Copies share exercise IDs, never completion rank; names cannot join history."""
    with database_session(phase9_root, write=True) as db:
        a, b = c.create_person(db, 'A'), c.create_person(db, 'B')
        original = routine(db, a, 'Same name')
        historical(db, a, original, '2022-01-01')
        duplicate = c.copy_routine(db, a, original, a, 'Same name')
        cross_copy = c.copy_routine(db, a, original, b, 'Same name')
        b_old = routine(db, b, 'B completed')
        historical(db, b, b_old, '2020-01-01')
        assert order(db, a) == [original, duplicate]
        assert order(db, b) == [b_old, cross_copy]
        historical(db, b, cross_copy, '2023-01-01')
        assert order(db, a) == [original, duplicate]
        assert order(db, b) == [cross_copy, b_old]
        db.execute('UPDATE routines SET name=? WHERE id=?', ('Renamed', original))
        assert order(db, a) == [original, duplicate]


def test_identical_dates_use_known_occurrences_then_names_not_entry_time(phase9_root):
    """Clock precision resolves a date tie; equal/unknown times sort alphabetically."""
    with database_session(phase9_root, write=True) as db:
        person = c.create_person(db, 'Person')
        z = routine(db, person, 'Zulu')
        a = routine(db, person, 'alpha')
        late = routine(db, person, 'Late')
        early = routine(db, person, 'Early')
        unknown_z = routine(db, person, 'Unknown Z')
        unknown_a = routine(db, person, 'Unknown A')
        for identity, clock in ((z, '12:00:01'), (a, '12:00:01'), (late, '12:00:02'), (early, '12:00:00'), (unknown_z, ''), (unknown_a, '')):
            historical(db, person, identity, '2020-01-01', clock)
        expected = [late, a, z, early, unknown_a, unknown_z]
        for _ in range(3):
            assert order(db, person) == expected


def test_corrections_change_effective_rank_without_rewriting_history(phase9_root):
    """Use the latest appended occurrence, and retain every original date and audit."""
    with database_session(phase9_root, write=True) as db:
        person = c.create_person(db, 'Person')
        a, b = routine(db, person, 'A'), routine(db, person, 'B')
        saved = historical(db, person, a, '2022-01-01')
        historical(db, person, b, '2021-01-01')
        original = h.original(db, person, saved)
        assert order(db, person) == [a, b]
        h.correct(db, person, saved, correction_payload(db, person, saved, workout_date='2020-01-01'))
        before = '\n'.join(db.iterdump())
        assert order(db, person) == [b, a]
        assert h.original(db, person, saved) == original and len(h.audit(db, person, saved)) == 1
        assert '\n'.join(db.iterdump()) == before


def test_deleted_and_archived_routines_never_appear(phase9_root):
    """Retained snapshots do not resurrect missing or archived routine cards."""
    with database_session(phase9_root, write=True) as db:
        person = c.create_person(db, 'Person')
        deleted = routine(db, person, 'Deleted')
        archived = routine(db, person, 'Archived')
        active = routine(db, person, 'Active')
        saved = historical(db, person, deleted, '2023-01-01')
        historical(db, person, archived, '2022-01-01')
        deletions.delete_routine(db, person, deleted, approval(db, 'routine', deleted, person))
        db.execute('UPDATE routines SET archived=1 WHERE id=?', (archived,))
        assert order(db, person) == [active]
        assert h.effective(db, person, saved)[0]['routine_deleted']


def test_retained_schema2_lists_alphabetically_without_new_tables(phase2_root):
    """Old management-only installations stay readable and are never migrated."""
    with database_session(phase2_root, write=True) as db:
        person = c.create_person(db, 'Person')
        z = c.create_routine(db, person, 'Z')
        a = c.create_routine(db, person, 'a')
        before = '\n'.join(db.iterdump())
        assert order(db, person) == [a, z] and '\n'.join(db.iterdump()) == before


def test_retained_schema3_counts_live_completion_without_history_tables(phase3_root):
    """The schema-3 fallback reads completed sessions, not missing historical tables."""
    with database_session(phase3_root, write=True) as db:
        person = c.create_person(db, 'Person')
        a, z = routine(db, person, 'A'), routine(db, person, 'Z')
        identity, _ = w.start(db, person, z, 'UTC')
        row = w.entries(db, person, identity)[0]
        w.finish(db, person, identity, dict(revision='0', entry_id=row['id'], current_position='0', weight='0'))
        before = '\n'.join(db.iterdump())
        assert order(db, person) == [z, a] and '\n'.join(db.iterdump()) == before


def test_patch_release_works_with_existing_updater_without_schema_migration(tmp_path):
    """Use the real v4/host engine with fixed synthetic commands and disposable DB."""
    from test_phase8_updater import fixture, REPO
    from test_shared_library import selected
    root, env = fixture(tmp_path, 7)
    env.update(MODE='ok', METADATA_VERSION=APP_VERSION, METADATA_SCHEMA='7')
    storage = root / 'data/storage'
    original = selected(storage)
    before = original.read_bytes()
    manifest = (storage / 'config/active.json').read_bytes()
    result = subprocess.run(['bash', str(REPO / 'deployment/update_workout_tracker_v4.sh'), '--root', str(root), '--confirm'], env=env, text=True, capture_output=True, timeout=70)
    assert result.returncode == 0, result.stdout + result.stderr
    state = json.loads((root / 'updater/status.json').read_text())
    assert state['installed_version'] == '0.13.0' and state['installed_schema'] == 7 and state['status'] == 'Completed'
    assert original.read_bytes() == before and (storage / 'config/active.json').read_bytes() == manifest
    assert 'migrate-storage' not in (root / 'calls.jsonl').read_text()


def test_same_day_live_finish_timestamp_and_corrected_occurrence(phase9_root):
    """Finish time resolves native ties; corrected clocks supersede original stamps."""
    with database_session(phase9_root, write=True) as db:
        person = c.create_person(db, 'Person')
        a, z, manual_routine = routine(db, person, 'A'), routine(db, person, 'Z'), routine(db, person, 'Manual')
        saved = None
        for identity, start_hour, finish_hour, finish_minute in ((a, 10, 12, 0), (z, 11, 11, 30)):
            with patch.object(w, 'now', return_value=datetime(2020, 1, 1, start_hour, tzinfo=timezone.utc)):
                session, _ = w.start(db, person, identity, 'UTC')
            row = w.entries(db, person, session)[0]
            with patch.object(w, 'now', return_value=datetime(2020, 1, 1, finish_hour, finish_minute, tzinfo=timezone.utc)):
                w.finish(db, person, session, dict(revision='0', entry_id=row['id'], current_position='0', weight='0'))
            if identity == a:
                saved = session
        historical(db, person, manual_routine, '2020-01-01', '11:45')
        assert order(db, person) == [a, manual_routine, z]
        h.correct(db, person, saved, correction_payload(db, person, saved, workout_time='09:00'))
        assert order(db, person) == [manual_routine, z, a]
