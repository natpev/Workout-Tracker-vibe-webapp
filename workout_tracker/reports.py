# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Local workout report calculations, detailed CSV and paginated PDF generation.

Inputs are already person-owned effective snapshots. No remote calls, database
writes or saved report files occur here. Legacy assumptions remain explicit.
"""
import csv
from io import BytesIO, StringIO
from datetime import date, timedelta
from fractions import Fraction
from xml.sax.saxutils import escape
from . import catalog as c, history as h, weight_statistics as stats
from .csv_export import spreadsheet_text, weight, duration
from .measurements import LEGACY, label
from .analytics import consistency

COLUMNS = (
    "person_id",
    "person_name",
    "workout_id",
    "date",
    "time",
    "routine_id",
    "routine_name",
    "exercise_id",
    "exercise_name",
    "capabilities",
    "weight_basis",
    "exercise_weight_lb",
    "set_index",
    "set_status",
    "actual_repetitions",
    "actual_duration_seconds",
    "legacy_exercise_duration_seconds",
    "target_sets",
    "target_repetitions",
    "target_duration_seconds",
    "measurement_origin",
    "estimated_weight_lifted_lb",
)


def detailed_rows(person, workouts):
    """One new set per row; old unknown set durations/statuses are never fabricated."""
    result = []
    for parent, entries in sorted(workouts, key=lambda pair: h.chronology(pair[0])):
        for row in entries:
            caps = row.get("capabilities")
            legacy = caps is None
            caps = caps or LEGACY[row["measurement_type"]]
            base = dict(
                person_id=person["id"],
                person_name=person["name"],
                workout_id=parent["id"],
                date=parent["workout_date"],
                time=(parent["workout_time"] or "")[:5],
                routine_id=parent["routine_id"],
                routine_name=parent["routine_name"],
                exercise_id=row["exercise_id"],
                exercise_name=row["name"],
                capabilities=label(caps),
                weight_basis=row["weight_basis"],
                exercise_weight_lb=(
                    ""
                    if row["actual_weight_tenths_lb"] is None
                    else weight(row["actual_weight_tenths_lb"])
                ),
                target_sets=row["target_sets"],
                target_repetitions=(
                    row["target_reps"] if row["target_reps"] is not None else ""
                ),
                target_duration_seconds=(
                    row["target_duration_seconds"]
                    if row["target_duration_seconds"] is not None
                    else ""
                ),
                legacy_exercise_duration_seconds="",
            )
            if not legacy:
                for index, set_row in enumerate(row["sets"]):
                    value = Fraction(0)
                    if set_row["status"] == "completed" and caps & 1:
                        count = set_row["actual_reps"] if caps & 2 else 1
                        value = Fraction(
                            row["actual_weight_tenths_lb"]
                            * count
                            * (2 if row["weight_basis"] == "per_side" else 1),
                            10,
                        )
                    result.append(
                        dict(
                            base,
                            set_index=index + 1,
                            set_status=set_row["status"],
                            actual_repetitions=(
                                set_row["actual_reps"]
                                if set_row["actual_reps"] is not None
                                else ""
                            ),
                            actual_duration_seconds=(
                                set_row["actual_duration_seconds"]
                                if set_row["actual_duration_seconds"] is not None
                                else ""
                            ),
                            measurement_origin="recorded_set",
                            estimated_weight_lifted_lb=stats.number(value),
                        )
                    )
            elif row.get("actual_reps") is not None:
                for index, reps in enumerate(row["actual_reps"]):
                    value = Fraction(
                        row["actual_weight_tenths_lb"]
                        * reps
                        * (2 if row["weight_basis"] == "per_side" else 1),
                        10,
                    )
                    result.append(
                        dict(
                            base,
                            set_index=index + 1,
                            set_status="unknown_legacy_status",
                            actual_repetitions=reps,
                            actual_duration_seconds="",
                            measurement_origin="recorded_repetitions_legacy_status_unknown",
                            estimated_weight_lifted_lb=stats.number(value),
                        )
                    )
            else:
                skipped = (
                    row["actual_weight_tenths_lb"] is None
                    and row["actual_duration_seconds"] is None
                )
                result.append(
                    dict(
                        base,
                        set_index="",
                        set_status=(
                            "skipped_exercise_legacy"
                            if skipped
                            else "unknown_legacy_status"
                        ),
                        actual_repetitions="",
                        actual_duration_seconds="",
                        legacy_exercise_duration_seconds=(
                            row["actual_duration_seconds"]
                            if row["actual_duration_seconds"] is not None
                            else ""
                        ),
                        measurement_origin=(
                            "legacy_exercise_duration_no_set_detail"
                            if row["actual_duration_seconds"] is not None
                            else (
                                "legacy_prescription_estimate"
                                if not skipped
                                else "legacy_skipped_exercise"
                            )
                        ),
                        estimated_weight_lifted_lb=stats.number(stats.entry_total(row)),
                    )
                )
    return result


def build(person, completed, start, end, zone):
    """Inclusive selected range and immediately preceding equal-length calendar period."""
    beginning = h.parse_date(start)
    ending = h.parse_date(end)
    if beginning > ending:
        raise c.ValidationError("From date must not follow To date.")
    completed = [pair for pair in completed if pair[0]["person_id"] == person["id"]]
    selected = [pair for pair in completed if start <= pair[0]["workout_date"] <= end]
    if not selected:
        raise c.ValidationError("No completed workouts match this date range.")
    length = (ending - beginning).days + 1
    try:
        prior_start = beginning - timedelta(days=length)
        prior_end = beginning - timedelta(days=1)
    except OverflowError:
        prior_start = prior_end = None
    prior = [
        pair
        for pair in completed
        if prior_start
        and prior_start.isoformat() <= pair[0]["workout_date"] <= prior_end.isoformat()
    ]
    rows = detailed_rows(person, selected)
    total = sum((stats.workout_total(entries) for _, entries in selected), Fraction(0))
    previous = sum((stats.workout_total(entries) for _, entries in prior), Fraction(0))
    completed_sets = sum(r["set_status"] == "completed" for r in rows)
    skipped_sets = sum(r["set_status"] == "skipped" for r in rows)
    legacy_sets = sum(
        row["target_sets"]
        for _, entries in selected
        for row in entries
        if row.get("capabilities") is None
    )
    records = {}
    progress = {}
    for parent, entries in sorted(selected, key=lambda pair: h.chronology(pair[0])):
        for entry in entries:
            caps = entry.get("capabilities") or LEGACY[entry["measurement_type"]]
            key = (
                entry["exercise_id"],
                caps,
                entry["weight_basis"],
                entry["unit"],
                entry["weight_meaning"],
            )
            record = records.setdefault(
                key,
                dict(
                    name=entry["name"],
                    capabilities=label(caps),
                    basis=entry["weight_basis"],
                    weight=None,
                    reps=None,
                    duration=None,
                    legacy_duration=None,
                ),
            )
            measurements = []
            value = entry["actual_weight_tenths_lb"]
            if value is not None:
                record["weight"] = (
                    value if record["weight"] is None else max(value, record["weight"])
                )
                measurements.append(("weight", value, "lb"))
            if entry.get("capabilities") is not None:
                for result in entry["sets"]:
                    if result["status"] != "completed":
                        continue
                    for field, actual, unit in (
                        ("reps", "actual_reps", "reps"),
                        ("duration", "actual_duration_seconds", "seconds"),
                    ):
                        value = result[actual]
                        if value is not None:
                            record[field] = (
                                value
                                if record[field] is None
                                else max(value, record[field])
                            )
                            measurements.append((field, value, unit))
            else:
                actual = entry.get("actual_reps")
                if actual is not None:
                    record["reps"] = (
                        max(actual)
                        if record["reps"] is None
                        else max(max(actual), record["reps"])
                    )
                    measurements.extend(("reps", value, "reps") for value in actual)
                value = entry["actual_duration_seconds"]
                if value is not None:
                    record["legacy_duration"] = (
                        value
                        if record["legacy_duration"] is None
                        else max(value, record["legacy_duration"])
                    )
                    measurements.append(
                        ("legacy_duration", value, "seconds (legacy exercise result)")
                    )
            # Every enabled actual axis gets its own series; legacy durations
            # cannot masquerade as individual-set performance.
            for axis, value, unit in measurements:
                series = progress.setdefault(
                    (*key, axis),
                    dict(
                        name=entry["name"],
                        axis=axis,
                        unit=unit,
                        first=value,
                        last=value,
                        first_date=parent["workout_date"],
                        last_date=parent["workout_date"],
                        points=[],
                    ),
                )
                series.update(last=value, last_date=parent["workout_date"])
                series["points"].append(dict(date=parent["workout_date"], value=value))
    greatest = max(
        (stats.workout_total(entries) for _, entries in selected), default=Fraction(0)
    )
    week_count = (
        (ending - timedelta(days=ending.weekday()))
        - (beginning - timedelta(days=beginning.weekday()))
    ).days // 7 + 1
    month_count = (
        (ending.year - beginning.year) * 12 + ending.month - beginning.month + 1
    )
    return dict(
        weekly_average=stats.number(Fraction(len(selected), week_count), 1),
        monthly_average=stats.number(Fraction(len(selected), month_count), 1),
        person=person,
        start=start,
        end=end,
        workouts=selected,
        rows=rows,
        total=total,
        total_label=stats.pounds(total),
        tons=stats.tons(total),
        completed_sets=completed_sets,
        skipped_sets=skipped_sets,
        legacy_sets=legacy_sets,
        records=list(records.values()),
        progress=list(progress.values()),
        highest_workout=stats.pounds(greatest),
        frequency=consistency(selected, zone, ending),
        previous_start=prior_start,
        previous_end=prior_end,
        previous_count=len(prior),
        previous_total=stats.pounds(previous),
        change=(
            "Not enough data"
            if previous == 0
            else stats.number((total - previous) * 100 / previous, 1) + "%"
        ),
    )


def csv_bytes(report):
    """Machine-readable detailed rows retain set order, identity, units and origin labels."""
    stream = StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\r\n")
    writer.writerow(COLUMNS)
    for row in report["rows"]:
        writer.writerow([spreadsheet_text(row.get(key, "")) for key in COLUMNS])
    return ("\ufeff" + stream.getvalue()).encode("utf-8")


def pdf_bytes(report):
    """Build a local PDF with embedded font, vector charts, repeated headers and pages."""
    from pathlib import Path
    import reportlab
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
    )
    from reportlab.graphics.shapes import Drawing, Rect, String, Line, Circle

    font = Path(reportlab.__file__).parent / "fonts" / "Vera.ttf"
    if "Tracker" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("Tracker", str(font)))
    styles = getSampleStyleSheet()
    for style in styles.byName.values():
        style.fontName = "Tracker"
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=40,
        bottomMargin=40,
        title="Workout Summary",
        author="Workout Tracker",
    )

    def text(value, style="BodyText"):
        """User text is escaped before ReportLab's limited paragraph markup parser."""
        return Paragraph(escape(str(value)), styles[style])

    content = [
        text("Workout Summary", "Title"),
        text(report["person"]["name"], "Heading1"),
        text(report["start"] + " through " + report["end"]),
        Spacer(1, 12),
    ]
    summary = [
        ["Completed workouts", str(len(report["workouts"]))],
        ["Average workouts per calendar week in range", report["weekly_average"]],
        ["Average workouts per calendar month in range", report["monthly_average"]],
        [
            "Estimated total weight lifted",
            report["total_label"] + " · " + report["tons"],
        ],
        ["Completed sets (explicitly recorded)", str(report["completed_sets"])],
        ["Skipped sets (explicitly recorded)", str(report["skipped_sets"])],
        ["Legacy sets with unknown individual status", str(report["legacy_sets"])],
        ["Highest estimated workout volume", report["highest_workout"]],
        [
            "Previous equal-length period",
            str(report["previous_start"]) + " through " + str(report["previous_end"]),
        ],
        [
            "Previous workouts / weight",
            str(report["previous_count"]) + " / " + report["previous_total"],
        ],
        ["Change in estimated lifting volume", report["change"]],
    ]
    table = Table([[text(a), text(b)] for a, b in summary], colWidths=[230, 290])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                (
                    "ROWBACKGROUNDS",
                    (0, 0),
                    (-1, -1),
                    [colors.HexColor("#eef2f6"), colors.white],
                ),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    content.append(table)
    content.extend(
        [
            Spacer(1, 12),
            text("Historical interpretation", "Heading2"),
            text(
                "New records show actual set results. Legacy unknown set status remains unknown. Actual legacy repetitions are labeled as recorded; otherwise original sets × target reps are an estimate. A legacy duration is one exercise-level result, never distributed across sets. Weight Basis and corrections are applied once. One short ton is 2,000 lb."
            ),
        ]
    )
    for key, title in (
        ("weekly", "Workouts per week — latest 12 calendar weeks"),
        ("monthly", "Workouts per month — latest 12 calendar months"),
    ):
        drawing = Drawing(520, 110)
        for index, point in enumerate(report["frequency"][key]):
            drawing.add(
                Rect(
                    15 + index * 41,
                    20,
                    25,
                    point["height"] * 0.7,
                    fillColor=colors.HexColor("#3267a6"),
                    strokeColor=None,
                )
            )
            drawing.add(
                String(
                    27 + index * 41,
                    26 + point["height"] * 0.7,
                    str(point["count"]),
                    fontName="Tracker",
                    fontSize=8,
                    textAnchor="middle",
                )
            )
        drawing.add(
            String(
                15,
                4,
                report["frequency"][key][0]["label"],
                fontName="Tracker",
                fontSize=8,
            )
        )
        drawing.add(
            String(
                405,
                4,
                report["frequency"][key][-1]["label"],
                fontName="Tracker",
                fontSize=8,
            )
        )
        content.extend([text(title, "Heading2"), drawing])
    content.append(text("Compatible exercise records", "Heading2"))
    for record in report["records"]:
        values = []
        if record["weight"] is not None:
            values.append(
                "Heaviest recorded weight: " + weight(record["weight"]) + " lb"
            )
        if record["reps"] is not None:
            values.append("Highest actual repetitions in a set: " + str(record["reps"]))
        if record["duration"] is not None:
            values.append(
                "Longest actual set duration: " + duration(record["duration"])
            )
        if record["legacy_duration"] is not None:
            values.append(
                "Longest legacy exercise duration (no set detail): "
                + duration(record["legacy_duration"])
            )
        content.append(
            text(
                record["name"]
                + " · "
                + record["capabilities"]
                + " · "
                + record["basis"],
                "Heading3",
            )
        )
        content.append(text("; ".join(values) or "No performed values"))
    content.append(text("Exercise progress", "Heading2"))
    for point in report["progress"]:

        def actual(value):
            """Keep each progress axis in its own honest displayed units."""
            if point["axis"] == "weight":
                return weight(value) + " lb"
            if "duration" in point["axis"]:
                return duration(value) + " " + point["unit"]
            return str(value) + " reps"

        content.append(
            text(
                point["name"]
                + " · "
                + point["axis"].replace("_", " ")
                + ": first "
                + actual(point["first"])
                + " ("
                + point["first_date"]
                + "), last "
                + actual(point["last"])
                + " ("
                + point["last_date"]
                + ")."
            )
        )
        drawing = Drawing(520, 65)
        drawing.add(Line(35, 15, 480, 15, strokeColor=colors.grey))
        top = max([p["value"] for p in point["points"]] + [1])
        first_day = date.fromisoformat(point["points"][0]["date"]).toordinal()
        last_day = date.fromisoformat(point["points"][-1]["date"]).toordinal()
        previous = None
        for measurement in point["points"]:
            x = (
                35
                + (date.fromisoformat(measurement["date"]).toordinal() - first_day)
                / (last_day - first_day or 1)
                * 445
            )
            y = 15 + measurement["value"] / top * 40
            if previous:
                drawing.add(
                    Line(
                        previous[0],
                        previous[1],
                        x,
                        y,
                        strokeColor=colors.HexColor("#3267a6"),
                        strokeWidth=2,
                    )
                )
            drawing.add(Circle(x, y, 3, fillColor=colors.HexColor("#3267a6")))
            previous = (x, y)
        content.append(drawing)
    content.append(text("Detailed workouts", "Heading2"))
    rows_by_workout = {}
    for row in report["rows"]:
        rows_by_workout.setdefault(row["workout_id"], []).append(row)
    for parent, entries in sorted(
        report["workouts"], key=lambda pair: h.chronology(pair[0])
    ):
        content.append(
            text(
                parent["workout_date"]
                + " "
                + (parent["workout_time"] or "")[:5]
                + " · "
                + parent["routine_name"],
                "Heading3",
            )
        )
        data = [
            [
                text("Exercise"),
                text("Set / status"),
                text("Actual result / historical origin"),
            ]
        ]
        for row in rows_by_workout[parent["id"]]:
            actual = []
            if row["exercise_weight_lb"] != "":
                actual.append(str(row["exercise_weight_lb"]) + " lb (exercise weight)")
            if row["actual_repetitions"] != "":
                actual.append(str(row["actual_repetitions"]) + " reps")
            if row["actual_duration_seconds"] != "":
                actual.append(duration(row["actual_duration_seconds"]))
            if row["legacy_exercise_duration_seconds"] != "":
                actual.append(
                    duration(row["legacy_exercise_duration_seconds"])
                    + " legacy exercise duration"
                )
            actual.append(row["measurement_origin"].replace("_", " "))
            data.append(
                [
                    text(row["exercise_name"]),
                    text(
                        str(row["set_index"])
                        + " "
                        + row["set_status"].replace("_", " ")
                    ),
                    text(" · ".join(actual)),
                ]
            )
        detail = Table(data, colWidths=[165, 135, 220], repeatRows=1, hAlign="LEFT")
        detail.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dfe8f1")),
                    ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.grey),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        content.append(detail)
        content.append(Spacer(1, 8))

    def footer(canvas, doc):
        """Add readable page numbers without retaining temporary generated files."""
        canvas.setFont("Tracker", 8)
        canvas.drawRightString(559, 20, f"Workout Tracker · Page {doc.page}")

    document.build(content, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
