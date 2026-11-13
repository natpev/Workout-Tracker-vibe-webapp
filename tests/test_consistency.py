# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Calendar buckets use effective completed identities and include zero periods."""
from datetime import date
from workout_tracker.analytics import consistency


def test_twelve_calendar_buckets_deduplicate_and_keep_zero_periods():
    """Date-only legacy workouts remain unknown-time records with real calendar dates."""
    parent = dict(id="one", workout_date="2026-11-09", occurred_at=None)
    result = consistency(
        [(parent, []), (parent, [])], "America/Indiana/Indianapolis", date(2026, 11, 13)
    )
    assert len(result["weekly"]) == len(result["monthly"]) == 12
    assert sum(p["count"] for p in result["weekly"]) == 1
    assert result["weekly"][-1]["label"] == "2026-11-09"
    assert result["monthly"][-1]["label"] == "2026-11"
    assert sum(p["count"] == 0 for p in result["weekly"]) == 11
