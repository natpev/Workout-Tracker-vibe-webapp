# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Pure exact-arithmetic regressions for effective snapshots and imperial units.

Synthetic dictionaries represent history-reader output; no household data or
database connections are used by these tests.
"""
from fractions import Fraction
import pytest
from workout_tracker import weight_statistics as stats


def entry(**changes):
    """Make one captured legacy prescription, independent of Library defaults."""
    return dict(dict(actual_weight_tenths_lb=400, measurement_type='weight',
                     target_sets=3, target_reps=12, weight_basis='per_side'), **changes)


@pytest.mark.parametrize('changes,expected', [
    ({}, 2880),
    ({'actual_reps': [12, 12, 10]}, 2720),
    ({'weight_basis': 'total', 'actual_reps': [12, 12, 10]}, 1360),
    ({'actual_reps': [12, 10, 0]}, 1760),
    ({'actual_reps': [0, 0, 0]}, 0),
    ({'actual_weight_tenths_lb': 0}, 0),
    ({'actual_weight_tenths_lb': None}, 0),
    ({'measurement_type': 'time', 'weight_basis': 'not_configured'}, 0),
    ({'measurement_type': 'weight_duration', 'target_reps': None}, 240),
    ({'measurement_type': 'weight_duration', 'weight_basis': 'total'}, 120),
    ({'actual_weight_tenths_lb': 1, 'target_sets': 1, 'target_reps': 1}, Fraction(1, 5)),
])
def test_snapshot_totals(changes, expected):
    assert stats.entry_total(entry(**changes)) == expected


@pytest.mark.parametrize('value,expected', [
    (0, '0 lb'), (1, '1 lb'), (Fraction(1, 10), '0.1 lb'),
    (Fraction(1234567, 10), '123,456.7 lb'),
])
def test_pounds(value, expected):
    assert stats.pounds(value) == expected


@pytest.mark.parametrize('value,expected', [
    (0, '0 tons'), (2000, '1 ton'), (1000, '0.5 tons'),
    (50000, '25 tons'), (1998000, '999 tons'),
    (1999999, '999.9995 tons'), (2000000, '1.00 kilotons'),
    (51000000, '25.50 kilotons'), (2000000000, '1.00 megatons'),
    (2000000000000, '1.00 gigatons'), (2000000000000000, '1.00 teratons'),
    (2000000000000000000, '1.00 petatons'),
    (2000000000000000000000, '1.00 exatons'),
])
def test_imperial_short_tons(value, expected):
    assert stats.tons(value) == expected


def workout(identity, day, weight=400, routine='routine', person='person', clock=None):
    """Build a completed effective snapshot with an optional aware instant."""
    return dict(id=identity, workout_date=day, occurred_at=clock,
                routine_id=routine, person_id=person), [entry(actual_weight_tenths_lb=weight)]


@pytest.mark.parametrize('weight,expected', [(440, '+10.0%'), (360, '−10.0%'), (400, '0.0%')])
def test_comparison_scope_boundary_and_sign(weight, expected):
    current = workout('current', '2026-10-31', weight)
    history = [current, workout('previous', '2026-10-01'),
               workout('too old', '2026-09-30', 10000),
               workout('future', '2026-11-01', 10000),
               workout('other routine', '2026-10-15', 10000, routine='other'),
               workout('other person', '2026-10-15', 10000, person='other')]
    assert stats.comparison(current, history) == expected


def test_comparison_without_positive_denominator():
    current = workout('current', '2026-10-31')
    assert stats.comparison(current, [current]) == 'Not enough data'
    assert stats.comparison(current, [workout('zero', '2026-10-30', 0)]) == 'Not enough data'


def test_daylight_saving_instant_boundary():
    current = workout('current', '2026-11-02', clock='2026-11-02T06:30:00+00:00')
    previous = workout('previous', '2026-10-03', clock='2026-10-03T02:30:00-04:00')
    too_old = workout('old', '2026-10-03', 9000, clock='2026-10-03T02:29:59-04:00')
    assert stats.comparison(current, [current, previous, too_old]) == '0.0%'


def test_exact_accumulation_and_effective_corrected_weight():
    rows = [entry(actual_weight_tenths_lb=125, actual_reps=[1, 1, 1]) for _ in range(100)]
    assert stats.workout_total(rows) == 7500
    assert stats.workout_total([entry(actual_weight_tenths_lb=125)]) == 900


def test_unknown_basis_refuses_to_guess():
    with pytest.raises(ValueError, match='Update 1'):
        stats.entry_total(entry(weight_basis='not_configured'))


@pytest.mark.parametrize('power,unit',[(7,'zettatons'),(8,'yottatons'),(9,'ronnatons'),(10,'quettatons')])
def test_larger_standard_prefixes(power,unit):
    assert stats.tons(2000*1000**power)=='1.00 '+unit


def test_no_rounding_driven_prefix_transition_and_no_negative_zero():
    assert stats.tons(2000*999999)=='1,000.00 kilotons'
    current=workout('current','2026-10-31',999999)
    assert stats.comparison(current,[workout('previous','2026-10-30',1000000)])=='0.0%'
