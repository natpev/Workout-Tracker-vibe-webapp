# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Shared 24-hour presentation filters; stored timestamps retain full precision.

Templates use clock for workout HH:mm and timestamp for UTC diagnostics with
seconds. Duration formatting is separate and never interprets exercise seconds
as a wall-clock time. Snapshot IANA zones remain owned by the history services.
"""
from datetime import datetime


def clock(value):
    """Render an existing normalized workout clock as HH:mm, or empty if unknown."""
    return str(value)[:5] if value else ''


def timestamp(value):
    """Render ISO timestamps in explicit 24-hour form without changing the instant."""
    if not value:return ''
    try:
        parsed=datetime.fromisoformat(str(value).replace('Z','+00:00'))
        return parsed.strftime('%Y-%m-%d %H:%M:%S %Z')
    except ValueError:return str(value)


def workout_timestamp(value):
    """Render a workout instant at minute precision, retaining its explicit zone."""
    if not value:return ''
    try:return datetime.fromisoformat(str(value).replace('Z','+00:00')).strftime('%Y-%m-%d %H:%M %Z')
    except ValueError:return str(value)
