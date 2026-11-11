# Schema 11: exercise interface, artwork and measurement corrections

**SHAMELESSLY VIBE-CODED 🤖** — AI-generated with questionable confidence and minimal human supervision. Keep backups.

Application 0.15.0 explicitly migrates a separate candidate from schema 10. Startup
never migrates. Every existing column, identity, timestamp, measurement, repetition
array and audit record is copied unchanged; the original database remains retained.
Released schema definitions and migration steps are retained unchanged.

`exercise_weight_basis` holds each exercise’s permanent total/per_side assignment.
Update/delete guards preserve that assignment, even while Duration makes it dormant.
Only permanent exercise deletion may cascade-delete it. Defaults and routines may
use different measurement types; their assigned basis must match the canonical
assignment. A duration exercise without an assignment requires an explicit first
selection when changing to a weighted type. Confirmation is required in services
and signed web previews. No historical or draft snapshots are rewritten.

`exercise_icons` stores canonical sanitized SVG text by exercise ID and start/end
position. Both slots cascade on permanent deletion. No external upload directory
exists. Database backups, restores, updates and container restarts preserve artwork.
Validation rechecks canonical SVG content during storage integrity checks.

`reps_required` marks new weight occurrences, including skipped entries that might
later be corrected into performed entries. Migrated completed rows retain legacy
semantics; existing repetition arrays remain intact. Active weight drafts receive
the marker without rewriting their inputs. Live draft JSON arrays may contain null
items for unentered sets. Completed performed weight entries require exactly the
captured set count of integers 0–10000; skipped measurements/repetitions remain SQL
NULL. Historical correction validation preserves old payload/hash formats while
requiring explicit reps for new weight records. Unknown legacy actual reps still
use historical targets for lifting estimates.

The candidate migration verifies original-cell preservation, effective history,
foreign keys, SQLite integrity, schema objects and historical audit chains before
activation. Failure retains the source selection and database. Restore requires
matching storage identity and schema; make a fresh schema-11 backup after upgrading.
