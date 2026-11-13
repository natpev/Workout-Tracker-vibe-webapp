# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""New capability chart series share existing responsive geometry/tooltips.

One exercise weight is plotted once. Repetition/duration points retain their set
number and skip status; incompatible capability/basis combinations never merge.
"""
from datetime import date


def append_series(groups, parent, row):
    """Append effective per-set points without multiplying durations by set count."""
    from .history import _day_fraction

    caps = row["capabilities"]
    for bit, axis in ((1, "weight"), (2, "reps"), (4, "time")):
        if not caps & bit:
            continue
        key = (
            row["exercise_id"],
            "flex",
            caps,
            row["unit"],
            row["weight_meaning"],
            row["weight_basis"],
            axis,
        )
        series = groups.setdefault(
            key,
            dict(
                name=row["name"],
                weight_basis=row["weight_basis"],
                kind=axis,
                combined=False,
                meaning=row["weight_meaning"],
                exercise_id=row["exercise_id"],
                points=[],
                records=[],
                highest=None,
                targets=set(),
            ),
        )
        if bit == 1:
            performed = any(r["status"] == "completed" for r in row["sets"])
            values = [
                (
                    None,
                    row["actual_weight_tenths_lb"] if performed else None,
                    "completed" if performed else "skipped",
                )
            ]
        else:
            field = "actual_reps" if bit == 2 else "actual_duration_seconds"
            values = [
                (index, r[field] if r["status"] == "completed" else None, r["status"])
                for index, r in enumerate(row["sets"])
            ]
        for index, value, state in values:
            prefix = f"Set {index+1}: " if index is not None else ""
            if value is None:
                label = prefix + ("Skipped" if state == "skipped" else "Not recorded")
            elif bit == 1:
                label = f"{value//10}.{value%10} lb"
            elif bit == 2:
                label = prefix + str(value) + " reps"
            else:
                label = prefix + f"{value//60}:{value%60:02d}"
            target = row["target_duration_seconds"] if bit == 4 else None
            target_label = (
                f"{target//60}:{target%60:02d}" if target is not None else None
            )
            if target is not None:
                series["targets"].add(target)
            record = dict(
                date=parent["workout_date"],
                time=parent["workout_time"],
                label=label,
                target_label=target_label,
                workout_id=parent["id"],
            )
            series["records"].append(record)
            if value is not None:
                point = dict(
                    record,
                    raw=value,
                    xday=date.fromisoformat(parent["workout_date"]).toordinal()
                    + _day_fraction(parent["workout_time"]),
                )
                series["points"].append(point)
                if series["highest"] is None or value > series["highest"]["raw"]:
                    series["highest"] = point
