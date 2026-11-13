# Measurement and historical compatibility

**SHAMELESSLY VIBE-CODED 🤖**

This application was built with a healthy dose of AI, questionable amounts of confidence, and minimal human supervision. It appears to work, but don’t mistake that for a warranty. Use at your own risk, and keep backups.

## Current model

Schema 13 represents enabled measurements with bits: Weight=1, Repetitions=2,
Duration=4, nonempty mask 1–7. Current writes use measurement_type=flex and one
shared validation path. Targets live in existing snapshot columns. Exercise-level
weight remains integer tenths lb; repetitions and positive duration seconds live
in ordered workout_sets/historical_sets rows with explicit status.

Incomplete drafts may contain partial enabled values. Completed sets require all
enabled measurements plus the shared exercise weight when enabled. Skips contain
NULL set actuals. All-skipped exercises also have NULL weight. SQL guards and
service validation protect the same invariants; completed original set rows cannot
be edited/deleted except through the existing deliberate deletion capability.

Corrections append sets in before/after JSON, validated against immutable captured
capabilities/targets. They never update original set tables. Effective readers
(history, charts, previous performance, both CSVs, reports and lifting totals)
share the validated correction layer and old basis overlay.

## Legacy preservation

Old measurement_type weight/time/weight_duration snapshots retain capabilities=NULL.
No legacy set rows are generated. Current definitions/routines receive mapping
3/4/5 without changing any old fields. Starting a new session captures flex and
creates incomplete sets; already-started old drafts retain their old UI/parser.

Legacy weights, duration, actual_reps_json, historical preparations and correction
payloads remain byte/value-equivalent. Unknown set duration/status is not estimated
into actual rows. Old actual reps remain actual; absent reps use original targets
only in labeled lifting estimates. One old duration remains an exercise-level value.

Original and corrected values are immutable/auditable. Frozen basis_transitions,
basis_assignments and their hashes are required to verify original conversion
chains. Classification overlay and already-converted correction values are applied
once. Never infer basis from names or reintroduce transition writers. Assigned
basis remains permanent even when Weight is disabled.

## Exact lifting and export semantics

Weighted rep sets: weight × actual completed reps × captured basis multiplier.
Weighted sets without reps: weight × completed-set count × multiplier. No elapsed
seconds multiplier. Without weight: zero contribution. NULL/skipped contributes
zero but never changes stored NULL. Legacy estimates keep their original convention.

Progress CSV remains wide and includes ordered semicolon-separated new set actuals
and statuses alongside historical targets. Detailed report CSV is one new set per
row with stable identity/status/source columns; exercise weight is context repeated
in that column, not independently recorded per-set weights. Legacy unknown data is
labeled and durations stay in legacy_exercise_duration_seconds. UTF-8 BOM, standard
quoting, formula protection, m:ss durations and exact decimal weights apply.
