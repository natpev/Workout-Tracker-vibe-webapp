# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""History-derived lifting estimates and imperial formatting for Flask pages.

Callers supply effective snapshots from history.py under the storage read lock.
Integer tenths and fractions avoid cumulative rounding; this module writes no
database rows and never applies historical conversions a second time.
"""
from datetime import date, datetime, timedelta
from decimal import Decimal, localcontext
from fractions import Fraction


def entry_total(row):
    """Return estimated pounds as an exact Fraction using captured prescriptions."""
    weight = row['actual_weight_tenths_lb']
    kind = row['measurement_type']
    if kind == 'time' or weight is None:
        return Fraction(0)
    basis = row['weight_basis']
    if basis not in ('total', 'per_side'):
        raise ValueError('Weight Basis must be classified using Update 1 first.')
    if kind == 'weight_duration':
        repetitions = row['target_sets']
    else:
        actual = row.get('actual_reps')
        repetitions = sum(actual) if actual is not None else row['target_sets'] * row['target_reps']
    return Fraction(weight * repetitions * (2 if basis == 'per_side' else 1), 10)


def workout_total(rows):
    """Sum effective entry estimates without rounding intermediate values."""
    return sum((entry_total(row) for row in rows), Fraction(0))


def number(value, places=None):
    """Format exact rational values with separators; round only for presentation."""
    value = Fraction(value)
    with localcontext() as context:
        context.prec = max(50, len(str(abs(value.numerator))) + 20)
        decimal = Decimal(value.numerator) / Decimal(value.denominator)
        if places is not None:
            return f'{decimal:,.{places}f}'
        return f'{decimal:,.10f}'.rstrip('0').rstrip('.')


def pounds(value):
    """Primary display always uses pounds, preserving fractional pounds."""
    return number(value) + ' lb'


def tons(value):
    """Scale imperial short tons by unrounded thresholds; one ton is 2,000 lb."""
    amount = Fraction(value) / 2000
    units = ('ton', 'kiloton', 'megaton', 'gigaton', 'teraton', 'petaton', 'exaton',
             'zettaton', 'yottaton', 'ronnaton', 'quettaton')
    index = 0
    while amount >= 1000 and index < len(units) - 1:
        amount /= 1000
        index += 1
    unit = units[index]
    return number(amount, 2 if index else None) + ' ' + unit + ('' if not index and amount == 1 else 's')


def comparison(current, workouts):
    """Compare with this routine's prior 30 days, using effective occurrence.

    Date-only records retain calendar-date semantics; known instants compare in
    UTC through aware datetimes, including timezone and daylight-saving changes.
    """
    parent, rows = current
    instant = datetime.fromisoformat(parent['occurred_at']) if parent['occurred_at'] else None
    day = date.fromisoformat(parent['workout_date'])
    previous = []
    for other, entries in workouts:
        if other['id'] == parent['id'] or other['routine_id'] != parent['routine_id'] or other['person_id'] != parent['person_id']:
            continue
        if instant and other['occurred_at']:
            occurred = datetime.fromisoformat(other['occurred_at'])
            included = instant - timedelta(days=30) <= occurred < instant
        else:
            occurred = date.fromisoformat(other['workout_date'])
            included = day - timedelta(days=30) <= occurred < day
        if included:
            previous.append(workout_total(entries))
    if not previous or sum(previous) == 0:
        return 'Not enough data'
    average = sum(previous, Fraction(0)) / len(previous)
    change = (workout_total(rows) - average) * 100 / average
    formatted = number(abs(change), 1)
    sign='' if formatted=='0.0' else '+' if change>0 else '−'
    return sign+formatted+'%'


def summary(workouts, identity=None):
    """Build compact display values directly from completed effective history."""
    total=sum((workout_total(rows) for _, rows in workouts), Fraction(0))
    result=dict(lifetime=pounds(total),lifetime_tons=tons(total))
    if identity is not None:
        current = next(pair for pair in workouts if pair[0]['id'] == identity)
        result.update(workout=pounds(workout_total(current[1])), comparison=comparison(current, workouts))
    return result
