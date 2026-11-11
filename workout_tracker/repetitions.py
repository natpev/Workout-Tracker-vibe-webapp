# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Per-set repetitions shared by live entry, corrections and integrity checks.

SQLite stores an ordered nullable JSON array on its exercise occurrence. NULL is
legacy/unknown, never zero. Browser strings validate before any transaction write.
"""
import json
from .catalog import ValidationError, integer

MAX_REPS = 10000


def validate(row, actual):
    """Validate a complete ordered array, including legitimate zero repetitions."""
    if actual is None:
        return None
    if row['measurement_type'] != 'weight' or not isinstance(actual, list) or len(actual) != row['target_sets']:
        raise ValueError('Actual repetition count does not match the captured sets.')
    if any(type(value) is not int or not 0 <= value <= MAX_REPS for value in actual):
        raise ValueError('Actual repetitions must be whole numbers from 0 to 10000.')
    return actual


def decode(row):
    """Expose an array alongside SQL columns; old schemas remain unchanged."""
    result = dict(row)
    if 'actual_reps_json' in result:
        result['actual_reps'] = validate(result, json.loads(result['actual_reps_json']) if result['actual_reps_json'] is not None else None)
    return result


def inputs(row, values, prefix='reps_', *, legacy=False):
    """Read all configured set fields; empty is incomplete, not zero.

    Legacy correction forms may leave every field blank to retain unknown reps.
    Incomplete draft input remains visible but is never acknowledged as saved.
    """
    if row['measurement_type'] != 'weight':
        return None
    raw = [values.get(prefix + str(index), '') for index in range(row['target_sets'])]
    if legacy and all(value == '' for value in raw):
        return None
    actual = []
    for index, value in enumerate(raw):
        if not isinstance(value, str) or len(value) > 100:
            raise ValidationError(f'Set {index+1}: enter whole repetitions from 0 to {MAX_REPS}.')
        if value == '':
            raise ValidationError(f'Set {index+1}: repetitions are incomplete.')
        actual.append(integer(value, f'Set {index+1} repetitions', 0, MAX_REPS))
    return actual


def encode(actual):
    """Store no duplicated totals; exact ordered values or SQL NULL only."""
    return json.dumps(actual, separators=(',', ':')) if actual is not None else None
