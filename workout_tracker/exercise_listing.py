# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""One all-time effective-history pass supplies person-specific exercise ordering.

Global identities stay distinct. Zero measurements count; NULL skips do not.
Callers may reuse completed snapshots for charts rather than rescanning per ID.
"""
from . import catalog as c,history as h


def ordering(db,person,completed=None):
    """Return ordered shared definitions, names and all-time performed IDs."""
    version=db.execute('PRAGMA user_version').fetchone()[0]
    rows=[dict(row) for row in (db.execute('SELECT * FROM exercises') if version>=6 else c.definitions(db,person))]
    completed=h.all_completed(db,person) if completed is None and version>=4 else completed or []
    recorded={row['exercise_id'] for _,entries in completed for row in entries if row['actual_weight_tenths_lb'] is not None or row['actual_duration_seconds'] is not None}
    names={row['id']:row['name'] for row in rows}
    for _,entries in completed:
        for row in entries:names.setdefault(row['exercise_id'],row['name'])
    key=lambda identity:(identity not in recorded,names[identity].casefold(),names[identity],identity)
    rows.sort(key=lambda row:key(row['id']))
    return rows,{identity:names[identity] for identity in sorted(names,key=key)},recorded


def chart_order(db,person,filters,completed,names):
    """Sort current charts and retain empty exercise choices using captured modes."""
    series=h.chart_series(db,person,filters,completed=completed)
    present={chart['exercise_id'] for chart in series}
    all_series=h.chart_series(db,person,{},completed=completed)
    missing=set(names)-present
    if filters.get('exercise'):missing&={filters['exercise']}
    for chart in all_series:
        if chart['exercise_id'] in missing:
            series.append(dict(chart,points=[],records=[],highest=None))
    captured={chart['exercise_id'] for chart in all_series}
    for identity in missing-captured:
        row=db.execute('SELECT * FROM exercise_defaults WHERE exercise_id=?',(identity,)).fetchone() if db.execute('PRAGMA user_version').fetchone()[0]>=7 else None
        kind=row['measurement_type'] if row else 'weight'
        for axis in (('weight','time') if kind=='weight_duration' else (kind,)):
            series.append(dict(exercise_id=identity,name=names[identity],kind=axis,combined=kind=='weight_duration',meaning='',weight_basis=row['weight_basis'] if row and 'weight_basis' in row.keys() else 'not_configured',points=[],records=[],highest=None,targets=set()))
    rank={identity:index for index,identity in enumerate(names)}
    for chart in series:chart['name']=names.get(chart['exercise_id'],chart['name'])
    series.sort(key=lambda chart:(rank.get(chart['exercise_id'],len(rank)),'weight_duration' if chart['combined'] else chart['kind'],chart['meaning'],chart.get('weight_basis',''),0 if chart['kind']=='weight' else 1))
    return series
