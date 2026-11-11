# Schema 12 — larger custom SVG illustrations

**SHAMELESSLY VIBE-CODED 🤖**

This application was built with a healthy dose of AI, questionable amounts of confidence, and minimal human supervision. It appears to work, but don’t mistake that for a warranty. Use at your own risk, and keep backups.

Patch 0.15.1 originally requested unchanged schema 11. Review found that its
exercise_icons table independently limits stored text to 65,536 characters.
The user then explicitly approved schema 12 for the smallest safe change.

Only exercise_icons changes: its size constraint becomes
`length(CAST(svg AS BLOB)) BETWEEN 1 AND 307200`, counting UTF-8 bytes rather
than characters. Columns, composite key and exercise foreign key are unchanged.
Original schema-11 DDL remains frozen in interface_schema.py. New DDL and the
candidate-only table rebuild live in icon_size_schema.py.

Explicit migration copies verified source storage, rebuilds this one table on
the candidate, copies every original cell exactly, records version 12 and checks
exact DDL, integrity, foreign keys, all table data and effective history/audits.
Only then is selection atomically activated. Failures preserve original bytes
and selection, including rollback after an activation durability failure.
Startup never initializes, repairs or migrates. A target-12 no-op is read-only.

The application independently checks raw and canonical SVG bytes. Element,
attribute, coordinate, description and passive XML allowlists remain unchanged.
Start and End slots each have their own limit. Existing schema-11 small icons
remain supported; larger uploads require this explicit migration.

Backup/restore includes both icons, verifies canonical SVG and accepts only the
same storage identity and exact schema. Keep older databases/backups for recovery;
never restore an older backup silently into 12. Browser and v4 use existing
release-info target detection and confirmed migrate-storage --target-version 12.
No new host script or service refresh is required after Phase 12 setup.
