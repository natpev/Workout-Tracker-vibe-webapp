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


def kind_for(row):
    """Keep every old export format; new captured capabilities get explicit columns."""
    row=dict(row)
    return 'flex:'+str(row['capabilities']) if row.get('capabilities') is not None else row['measurement_type']


def column_labels(kind,modern):
    """Stable wide-column labels separate exercise weight from independent set results."""
    if kind.startswith('flex:'):
        caps=int(kind[5:]);labels=[]
        if caps&1:labels.append('Weight (lb)')
        labels.append('Historical Prescription')
        if caps&2:labels.append('Actual Repetitions by Set')
        if caps&4:labels.append('Actual Durations by Set')
        labels.append('Set Statuses')
        return tuple(labels)
    labels=(('Weight (lb)','Duration','Sets × Target Duration') if kind=='weight_duration' else ('Weight (lb)','Sets × Reps') if kind=='weight' else ('Duration','Sets × Target Duration'))
    return labels+('Actual Repetitions by Set',) if modern and kind=='weight' else labels


def flex_cells(row):
    """Blank actual cells remain blank for skipped sets; statuses retain the distinction."""
    caps=row['capabilities'];cells=[]
    if caps&1:cells.append('' if row['actual_weight_tenths_lb'] is None else weight(row['actual_weight_tenths_lb']))
    target=str(row['target_sets'])+' sets'
    if caps&2:target+=' × '+str(row['target_reps'])+' reps'
    if caps&4:target+=' · '+duration(row['target_duration_seconds'])+' per set'
    cells.append(target)
    if caps&2:cells.append('; '.join('' if s['actual_reps'] is None else str(s['actual_reps']) for s in row['sets']))
    if caps&4:cells.append('; '.join('' if s['actual_duration_seconds'] is None else duration(s['actual_duration_seconds']) for s in row['sets']))
    cells.append('; '.join(s['status'] for s in row['sets']))
    return tuple(cells)


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
            group = (row['exercise_id'], kind_for(row), row['unit'], row['weight_meaning'], row.get('weight_basis','not_configured'))
            repeats[group] += 1
            key = (*group, repeats[group])
            kind = kind_for(row)
            if kind.startswith('flex:'):
                cells[key]=flex_cells(row);keys.add(key);continue
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
                group = (row['exercise_id'], kind_for(row), row['unit'], row['weight_meaning'], row.get('weight_basis','not_configured'))
                repeats[group] += 1
                keys.add((*group, repeats[group]))
    if db.execute('PRAGMA user_version').fetchone()[0]>=11:
        for identity in set(selected)-{key[0] for key in keys}:
            preset=db.execute('SELECT * FROM exercise_defaults WHERE exercise_id=?',(identity,)).fetchone()
            if preset:keys.add((identity,kind_for(preset),preset['unit'],preset['weight_meaning'],preset['weight_basis'],1))
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
        if kind.startswith('flex:'):
            from .measurements import label as capability_label
            label+=' ('+capability_label(int(kind[5:]))+'; per-set)'
        if slot > 1:
            label += f' [occurrence {slot}]'
        labels=column_labels(kind,modern)
        header.extend(label + ' — ' + part for part in labels)
    buffer = StringIO(newline=''); writer = csv.writer(buffer, lineterminator='\r\n')
    writer.writerow([spreadsheet_text(cell) for cell in header])
    for parent, cells in records:
        row = [parent['workout_date'], (parent['workout_time'] or '')[:5], parent['routine_name'], parent['id']]
        for key in ordered:
            row.extend(cells.get(key, ('',) * len(column_labels(key[1],modern))))
        writer.writerow([spreadsheet_text(cell) for cell in row])
    return buffer.getvalue()
