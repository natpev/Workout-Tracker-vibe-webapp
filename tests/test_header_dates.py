# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Read-only card-date regression on synthetic completed/corrected workout data.

The card date and its sort key share one history calculation. HTTP assertions
check visible labels and semantic dates; SQL dumps detect accidental writes.
"""
import re
import pytest
from workout_tracker import create_app, catalog as c, history as h, workouts as w, deletions
from workout_tracker.routine_listing import selectable_routines, completion_label
from workout_tracker.storage import database_session
from test_phase9 import phase9_root
from test_routine_listing import routine, historical
from test_history import correction_payload
from test_phase8_deletion import approval


def test_card_dates_match_sorting_and_ignore_unsaved_workouts(phase9_root):
    """Late-entered older dates, drafts and discarded/prepared sessions never win."""
    root = phase9_root
    with database_session(root, write=True) as db:
        person = c.create_person(db, 'Dates')
        recent, old, never = [routine(db, person, name) for name in ('Recent', 'Old', 'Never')]
        historical(db, person, recent, '2026-11-06')
        historical(db, person, old, '2026-11-04')
        historical(db, person, recent, '2020-01-01')
        h.prepare(db, person, never, dict(workout_date='2026-11-07', workout_time=''), 'UTC')
        identity, _ = w.start(db, person, never, 'UTC')
        w.discard(db, person, identity, {'revision': '0', 'confirm': 'yes'})
        w.start(db, person, old, 'UTC')
        before = '\n'.join(db.iterdump())
        cards = selectable_routines(db, person)
        assert [r['id'] for r in cards] == [recent, old, never]
        assert [r['last_completed_date'] for r in cards] == ['2026-11-06', '2026-11-04', None]
        assert [r['last_completed_label'] for r in cards] == ['November 6, 2026', 'November 4, 2026', None]
        assert '\n'.join(db.iterdump()) == before
    page = create_app({'TESTING': True, 'WORKOUT_DATA_ROOT': root}).test_client().get('/people/' + person)
    assert page.status_code == 200
    cards = re.findall(r'<section class="routine-card">(.*?)</section>', page.get_data(as_text=True), re.S)
    assert len(cards) == 3 and 'November 6, 2026' in cards[0] and 'November 4, 2026' in cards[1]
    assert 'datetime="2026-11-06"' in cards[0] and 'Never completed' in cards[2] and '<time ' not in cards[2]
    with database_session(root) as db:
        assert '\n'.join(db.iterdump()) == before


def test_person_copies_and_deleted_routine_dates_are_independent(phase9_root):
    """Same names/shared exercise IDs cannot transfer dates to a new routine ID."""
    with database_session(phase9_root, write=True) as db:
        a, b = c.create_person(db, 'A'), c.create_person(db, 'B')
        original = routine(db, a, 'Shared name')
        historical(db, a, original, '2026-11-06')
        same_copy = c.copy_routine(db, a, original, a, 'Shared name')
        other_copy = c.copy_routine(db, a, original, b, 'Shared name')
        assert [row['last_completed_date'] for row in selectable_routines(db, a)] == ['2026-11-06', None]
        assert selectable_routines(db, b)[0]['last_completed_date'] is None
        historical(db, b, other_copy, '2026-11-04')
        assert selectable_routines(db, b)[0]['last_completed_date'] == '2026-11-04'
        assert selectable_routines(db, a)[0]['last_completed_date'] == '2026-11-06'
        deletions.delete_routine(db, a, original, approval(db, 'routine', original, a))
        cards = selectable_routines(db, a)
        assert len(cards) == 1 and cards[0]['id'] == same_copy and cards[0]['last_completed_date'] is None


def test_corrected_date_and_multiple_completions_use_same_winning_record(phase9_root):
    """Moving one workout earlier exposes the routine's next latest completion."""
    with database_session(phase9_root, write=True) as db:
        person = c.create_person(db, 'Dates')
        a, b = routine(db, person, 'A'), routine(db, person, 'B')
        saved = historical(db, person, a, '2026-11-06', '12:00')
        historical(db, person, a, '2026-11-02')
        historical(db, person, b, '2026-11-04')
        original = h.original(db, person, saved)
        h.correct(db, person, saved, correction_payload(db, person, saved, workout_date='2026-11-01'))
        cards = selectable_routines(db, person)
        assert [(r['id'], r['last_completed_date']) for r in cards] == [(b, '2026-11-04'), (a, '2026-11-02')]
        assert h.original(db, person, saved) == original


@pytest.mark.parametrize('day,label', [('2026-11-06','November 6, 2026'), ('2024-02-09','February 9, 2024'), ('2000-01-01','January 1, 2000'), ('2026-12-31','December 31, 2026')])
def test_date_format_has_english_month_and_no_leading_zero(day, label):
    """Formatting is deterministic regardless of the host locale."""
    assert completion_label(day) == label
