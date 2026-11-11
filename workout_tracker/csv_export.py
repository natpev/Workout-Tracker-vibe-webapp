# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Read-only paper-style CSV from validated, person-owned effective history.

The caller supplies its locked connection and validated date bounds. This module
writes only an in-memory CSV; no workout, prescription or identity is changed.
"""
import csv
from io import StringIO
from collections import Counter
from . import catalog as c, history as h


def spreadsheet_text(value):
    """Quote formula-like user text with an apostrophe before CSV escaping."""
    text = str(value)
    if text.startswith(('\t', '\r', '\n')) or text.lstrip().startswith(('=', '+', '-', '@')):
        return "'" + text
    return text


def duration(value):
    """Render integer seconds as total minutes:two-digit seconds, never set totals."""
    return f'{value // 60}:{value % 60:02d}'


def weight(value):
    """Render exact stored tenths; retain zero and avoid floating-point rounding."""
    return str(value // 10) if value % 10 == 0 else f'{value // 10}.{value % 10}'


def wide_csv(db, person_id, filters, selected):
    """Return UTF-8 CSV text for selected IDs, with one row per completed workout.

    Column groups separate identity/type/unit/meaning, plus occurrence number when
    a routine contains the same exercise more than once. Missing actuals stay
    blank; a present skipped row retains its historical target prescription.
    Ordinary groups have actual/target pairs; combined groups have a weight,
    duration and historical-target triple.
    """
    modern=db.execute('PRAGMA user_version').fetchone()[0]>=10
    completed=h.all_completed(db,person_id)
    if db.execute('PRAGMA user_version').fetchone()[0]>=11:
        from .exercise_listing import ordering
        _,names,_=ordering(db,person_id,completed)
    else:
        _,names=h.choices(db,person_id)
    selected = list(dict.fromkeys(selected))
    if not selected:
        raise c.ValidationError('Select at least one exercise to export.')
    if any(identity not in names for identity in selected):
        raise c.ValidationError('Choose recorded exercises belonging to this person.')
    bounds = {key: filters.get(key, '') for key in ('from', 'to')}
    workouts = sorted(h.listing(db, person_id, bounds,completed=completed), key=lambda pair: h.chronology(pair[0]))
    keys = set(); records = []
    for parent, rows in workouts:
        cells = {}; repeats = Counter()
        for row in rows:
            if row['exercise_id'] not in selected:
                continue
            group = (row['exercise_id'], row['measurement_type'], row['unit'], row['weight_meaning'], row.get('weight_basis','not_configured'))
            repeats[group] += 1
            key = (*group, repeats[group])
            kind = row['measurement_type']
            actual_weight, actual_duration = row['actual_weight_tenths_lb'], row['actual_duration_seconds']
            weight_cell = '' if actual_weight is None else weight(actual_weight)
            duration_cell = '' if actual_duration is None else duration(actual_duration)
            target = str(row['target_reps']) if kind == 'weight' else duration(row['target_duration_seconds'])
            prescription = f"{row['target_sets']} × {target}"
            cells[key] = ((weight_cell,duration_cell,prescription) if kind == 'weight_duration'
                          else (weight_cell if kind == 'weight' else duration_cell,prescription))
            if modern and kind=='weight':
                actual=row.get('actual_reps')
                cells[key]+=('; '.join(str(value) for value in actual) if actual is not None else '',)
            keys.add(key)
        if cells:
            records.append((parent, cells))
    if not records:
        raise c.ValidationError('No completed workouts match these exercises and dates. Choose another range or selection.')
    # Keep selected exercises as blank column pairs even when none of this
    # range's workouts included them. Prefer captured configurations; a never-
    # recorded ID gets headings only from its defaults, never fabricated values.
    # No out-of-range data rows are added.
    absent = set(selected) - {key[0] for key in keys}
    if absent:
        for _, rows in completed:
            repeats = Counter()
            for row in rows:
                if row['exercise_id'] not in absent:
                    continue
                group = (row['exercise_id'], row['measurement_type'], row['unit'], row['weight_meaning'], row.get('weight_basis','not_configured'))
                repeats[group] += 1
                keys.add((*group, repeats[group]))
    if db.execute('PRAGMA user_version').fetchone()[0]>=11:
        for identity in set(selected)-{key[0] for key in keys}:
            preset=db.execute('SELECT * FROM exercise_defaults WHERE exercise_id=?',(identity,)).fetchone()
            if preset:keys.add((identity,preset['measurement_type'],preset['unit'],preset['weight_meaning'],preset['weight_basis'],1))
    # Names label columns only; full IDs disambiguate matching names without
    # merging or repairing any definitions. Measurements use captured groups.
    duplicates = Counter(names[identity].casefold() for identity in selected)
    rank = {identity: index for index, identity in enumerate(selected)}
    ordered = sorted(keys, key=lambda key: (rank[key[0]], key[1], key[2] or '', key[3] or '', key[4],key[5]))
    header = ['Date', 'Time', 'Routine', 'Workout ID']
    for identity, kind, unit, meaning, basis, slot in ordered:
        label = names[identity]
        if duplicates[label.casefold()] > 1:
            label += ' [' + identity + ']'
        if meaning:
            label += ' (' + meaning + ')'
        if basis!='not_configured':
            from .basis import label as basis_label
            label += ' ('+basis_label(basis)+')'
        if slot > 1:
            label += f' [occurrence {slot}]'
        labels = (('Weight (lb)', 'Duration', 'Sets × Target Duration') if kind == 'weight_duration'
                  else ('Weight (lb)', 'Sets × Reps') if kind == 'weight' else ('Duration', 'Sets × Target Duration'))
        if modern and kind=='weight':labels+=('Actual Repetitions by Set',)
        header.extend(label + ' — ' + part for part in labels)
    buffer = StringIO(newline=''); writer = csv.writer(buffer, lineterminator='\r\n')
    writer.writerow([spreadsheet_text(cell) for cell in header])
    for parent, cells in records:
        row = [parent['workout_date'], (parent['workout_time'] or '')[:5], parent['routine_name'], parent['id']]
        for key in ordered:
            row.extend(cells.get(key, ('',) * (3 if key[1]=='weight_duration' or (modern and key[1]=='weight') else 2)))
        writer.writerow([spreadsheet_text(cell) for cell in row])
    return buffer.getvalue()
