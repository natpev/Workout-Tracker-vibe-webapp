# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Read-only inclusive Progress ranges using the configured IANA local date.

URLs carry explicit selections across refresh/Back/history tabs. Month presets
start the day after the clamped calendar-month anniversary, not fixed-day guesses.
"""
from calendar import monthrange
from datetime import date,timedelta
from .catalog import ValidationError

RANGES=(('3m','3 Months'),('6m','6 Months'),('12m','12 Months'),('24m','24 Months'),('all','All Time'),('custom','Custom Range'))
LEGACY_DAYS=('30','60','90')


def month_before(day,months):
    """Subtract calendar months, clamping days such as August 31 to February 28."""
    absolute=day.year*12+day.month-1-months;year,month=divmod(absolute,12)
    return date(year,month+1,min(day.day,monthrange(year,month+1)[1]))


def valid_date(value):
    """Accept blank/open bounds or exact ISO dates; preserve bad strings for redisplay."""
    if not value:return True
    try:return date.fromisoformat(value).isoformat()==value
    except ValueError:return False


def selection(values,today):
    """Return validated chart filters plus a stable explicit range token/description."""
    token=values.get('range') or ('custom' if values.get('from') or values.get('to') else '3m')
    if token not in dict(RANGES) and token not in LEGACY_DAYS:raise ValidationError('Choose a listed date range.')
    filters=dict(values);filters['range']=token
    if token=='all':start=end=''
    elif token=='custom':
        start,end=values.get('from',''),values.get('to','')
        for value in (start,end):
            if not valid_date(value):raise ValidationError('Choose valid From and To dates.')
        if start and end and start>end:raise ValidationError('From date must not be after To date.')
    else:
        beginning=today-timedelta(days=int(token)-1) if token.isdigit() else month_before(today,int(token[:-1]))+timedelta(days=1)
        start,end=beginning.isoformat(),today.isoformat()
    filters.update({'from':start,'to':end})
    # Old bookmarks keep their exact day bounds; show those bounds as Custom
    # rather than silently reinterpreting them as a different month interval.
    if token in LEGACY_DAYS:token='custom';filters['range']=token
    return filters,token,('All available dates' if token=='all' else f'{start or "Beginning"} through {end or "latest"} (inclusive)')
