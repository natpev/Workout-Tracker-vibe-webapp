# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Read-only calendar frequency and responsive chart data for household pages/reports."""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from . import workouts as w
from .progress_ranges import month_before


def occurred_day(parent, zone):
    """Known instants use configured local time; unknown historical times retain their date."""
    if parent.get("occurred_at"):
        return (
            datetime.fromisoformat(parent["occurred_at"])
            .astimezone(ZoneInfo(zone))
            .date()
        )
    return date.fromisoformat(parent["workout_date"])


def consistency(workouts, zone, today=None):
    """Latest 12 Monday-based calendar weeks and months, including zero periods."""
    today = today or w.now().astimezone(ZoneInfo(zone)).date()
    monday = today - timedelta(days=today.weekday())
    first = today.replace(day=1)
    weekly = {monday - timedelta(weeks=i): 0 for i in reversed(range(12))}
    monthly = {month_before(first, i): 0 for i in reversed(range(12))}
    seen = set()
    for parent, _ in workouts:
        if parent["id"] in seen:
            continue
        seen.add(parent["id"])
        day = occurred_day(parent, zone)
        week = day - timedelta(days=day.weekday())
        month = day.replace(day=1)
        if week in weekly:
            weekly[week] += 1
        if month in monthly:
            monthly[month] += 1

    def series(values, months=False):
        """Convert calendar counts into scaled bars and accessible period labels."""
        high = max(values.values(), default=0) or 1
        return [
            dict(
                label=day.strftime("%Y-%m") if months else day.isoformat(),
                count=count,
                x=25 + index * 48,
                height=count / high * 90,
            )
            for index, (day, count) in enumerate(values.items())
        ]

    return dict(weekly=series(weekly), monthly=series(monthly, True))


def body_chart(rows, trend, values):
    """Actual readings and equal-day 7/30-day averages share local dates and pounds."""
    start, end = values.get("from", ""), values.get("to", "")
    chosen = [
        p
        for p in trend
        if (not start or p["day"] >= start) and (not end or p["day"] <= end)
    ]
    points = [
        dict(
            day=r["day"],
            value=r["weight_milli_lb"],
            label=r["weight"] + " lb · " + r["clock"] + " · " + r["source"].title(),
        )
        for r in rows
    ]
    all_values = [p["value"] for p in points] + [
        p[k] for p in chosen for k in ("ma7", "ma30")
    ]
    all_days = [p["day"] for p in points] + [p["day"] for p in chosen]
    if not all_values:
        return None
    low = min(all_values)
    high = max(all_values)
    first = min(date.fromisoformat(d).toordinal() for d in all_days)
    last = max(date.fromisoformat(d).toordinal() for d in all_days)

    def coordinates(day, value, fraction=0):
        """Place a reading within its local day on a bounded responsive SVG axis."""
        return (
            65
            + (date.fromisoformat(day).toordinal() + fraction - first)
            / (last - first + 1)
            * 570,
            190 - float((value - low) / (high - low or 1)) * 150,
        )

    for p, row in zip(points, rows):
        hour, minute = map(int, row["clock"].split(":"))
        p["x"], p["y"] = coordinates(p["day"], p["value"], (hour * 60 + minute) / 1440)
    lines = {}
    for key in ("ma7", "ma30"):
        lines[key] = " ".join(
            "%.2f,%.2f" % coordinates(p["day"], p[key]) for p in chosen
        )
    return dict(
        points=points,
        lines=lines,
        low=f"{float(low/1000):.1f}",
        high=f"{float(high/1000):.1f}",
        first=min(all_days),
        last=max(all_days),
    )
