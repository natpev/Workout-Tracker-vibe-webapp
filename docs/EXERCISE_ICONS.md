# Exercise SVG illustrations

**SHAMELESSLY VIBE-CODED 🤖** — AI-generated with minimal human supervision and questionable confidence. Review before trusting.

Exactly two defaults live in `workout_tracker/static/exercise-icons`: Start is a
pair of dumbbells; End is a plated barbell. Both are transparent 256 × 256 vectors.
Exercise names do not select artwork. Independent custom slots belong to the shared
permanent exercise ID. Edit Defaults offers preview, upload/replace and removal.
These separate forms never update routine configurations.

Use `fill="var(--accent)"` or `stroke="var(--accent)"` for highlighted elements and
`currentColor` for neutral theme-aware outlines. Artwork is validated, serialized
canonically, then rendered inline through a narrowly scoped safe Markup function.
Ordinary external image elements are not used: their SVG documents would not
inherit the selected person’s CSS variables. Saved artwork contains no person color.

Each Start and End upload independently supports **300 KiB (307,200 bytes)**.
Both the original UTF-8 upload and its canonical SVG must fit this limit;
canonicalization can slightly enlarge some documents. Reads stop at 307,201 bytes
to detect overflow without reading an unbounded stream. No combined slot limit
applies, and no artwork is compressed or simplified to meet the limit.

The separate **1,024-element** complexity limit and **32,768-character** attribute
bound remain unchanged. Too many elements produces a complexity error, not a
file-size error. Supported elements: svg,
g, path, rect, circle, ellipse, line, polyline, polygon, title and desc. Supported
attributes cover normal shape geometry, transforms, viewBox/preserveAspectRatio,
fill/stroke, opacity and line/fill rules. Coordinates are finite and bounded;
paths and transforms use checked SVG command grammars. Paints allow neutral named
colors, hexadecimal colors, none, currentColor and the exact accent token.
See `exercise_icons.py` for the explicit per-element attribute allowlist.

Scripts, events, links, href resources, style attributes/elements, external files,
embedded HTML, foreignObject, animation, definitions, filters, entities/DOCTYPE,
non-XML processing instructions and unknown namespaces/elements/attributes are
rejected. Uploaded filenames are never used for storage. CSRF and trusted-LAN
request protections apply. Invalid uploads preserve the prior icon atomically.

Canonical SVG is stored in SQLite, included in existing manual/scheduled backups,
validated on restore and retained across container rebuilds. Permanent exercise
deletion cascades both slots; no external assets can be orphaned. Icon changes
never alter workouts, audits, measurement types or lifetime statistics.

Version 0.15.1 requires explicit candidate migration from schema 11 to **12**
because the original table also capped stored text at 65,536 characters. Schema
12 changes only that constraint, enforcing 307,200 UTF-8 bytes. Every original
icon, identity, workout and audit stays unchanged. No startup migration occurs;
existing schema-11 installations retain small-icon support and receive an upgrade
message for larger uploads. See [schema 12](SCHEMA_12.md) and the
[patch verification](../PATCH_0_15_1_REVIEW.md).
