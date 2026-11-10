# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Read-only routine selection for the selected person's dashboard.

The route supplies its locked SQLite connection. Existing effective history
provides completed live/manual occurrences, including date/time corrections.
Only card order and display metadata change; no positions, snapshots or dates are written.
"""
from datetime import date, datetime, timezone

from . import catalog, history


MONTHS = ('January', 'February', 'March', 'April', 'May', 'June',
          'July', 'August', 'September', 'October', 'November', 'December')


def completion_label(day):
    """Format an ISO workout date in English, without locale or leading-zero days."""
    chosen = date.fromisoformat(day)
    return f'{MONTHS[chosen.month - 1]} {chosen.day}, {chosen.year}'


def selectable_routines(db, person_id):
    """Return active owned cards with their last date, newest first, then name for ties.

    Use actual workout dates and live completion/historical occurrence times,
    never historical entry/audit timestamps. An
    unknown time sorts below a known time on the same date. Stable name sorting
    breaks equal occurrences and places never-completed routines alphabetically
    at the bottom. Permanent IDs distinguish copies and same-named routines.
    """
    catalog.person(db, person_id)
    routines = db.execute(
        'SELECT * FROM routines WHERE person_id=? AND archived=0', (person_id,)
    ).fetchall()
    version = db.execute('PRAGMA user_version').fetchone()[0]
    if version >= 4:
        # Reuse the validated read layer so append-only corrections are honored;
        # it already excludes drafts, discards and unsaved historical preparations.
        completed = [parent for parent, _ in history.all_completed(db, person_id)]
    elif version == 3:
        # Retained schema 3 has live sessions but no historical/audit tables.
        completed = db.execute(
            "SELECT routine_id,workout_date,finished_at AS occurred_at FROM workout_sessions "
            "WHERE person_id=? AND status='completed'", (person_id,)
        ).fetchall()
    else:
        completed = []  # Schema 2 has routine definitions only; never migrate here.
    latest = {}
    for workout in completed:
        instant = workout['occurred_at']
        if version >= 4 and workout['source'] == 'live' and instant == workout['started_at']:
            # A normal live workout has a genuine Finish timestamp. A corrected
            # occurrence takes precedence when its date/time differs from Start.
            instant = workout['finished_at']
        clock = datetime.fromisoformat(instant).astimezone(timezone.utc).isoformat(timespec='microseconds') if instant else ''
        occurrence = (workout['workout_date'], clock)
        identity = workout['routine_id']
        latest[identity] = max(latest.get(identity, ('', '')), occurrence)
    # Attach display-only metadata from the exact maximum used by sorting.
    # Copies/people without a completion keep None; no extra query or DB write.
    cards = []
    for row in routines:
        day = latest[row['id']][0] if row['id'] in latest else None
        cards.append(dict(row, last_completed_date=day,
                          last_completed_label=completion_label(day) if day else None))
    # Python's stable second sort retains the alphabetical order for equal keys.
    # The ID is a final deterministic fallback when names also match exactly.
    alphabetical = sorted(cards, key=lambda row: (row['name'].casefold(), row['name'], row['id']))
    return sorted(alphabetical, key=lambda row: latest.get(row['id'], ('', '')), reverse=True)
