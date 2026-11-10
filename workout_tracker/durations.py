# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Shared whole-number duration parsing for configuration and actual performance.

Catalog/workout services supply their own storage bounds. Empty parts normalize
only when another part is supplied; two blanks retain the SQL NULL skip meaning.
"""
import re


def parse_duration(minutes,seconds,maximum):
    """Return positive total seconds or None; never round or accept negative parts."""
    parts=[str(value).strip() for value in (minutes,seconds)]
    if parts==['','']:return None
    if any(len(part)>100 or (part and not re.fullmatch(r'[0-9]+',part)) for part in parts):
        raise ValueError('Enter nonnegative whole minutes and seconds.')
    total=int(parts[0] or '0')*60+int(parts[1] or '0')
    if not 1<=total<=maximum:
        raise ValueError('Duration must be positive and within the supported limit.')
    return total
