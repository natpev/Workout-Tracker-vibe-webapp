# Measurement and historical compatibility

**SHAMELESSLY VIBE-CODED 🤖**

This application was built with a healthy dose of AI, questionable amounts of confidence, and minimal human supervision. It appears to work, but don’t mistake that for a warranty. Use at your own risk, and keep backups.

## Current model

Schema 13 represents enabled measurements with bits: Weight=1, Repetitions=2,
Duration=4, nonempty mask 1–7. Current writes use measurement_type=flex and one
shared validation path. Targets live in existing snapshot columns. Exercise-level
weight remains integer tenths lb; repetitions and positive duration seconds live
in ordered workout_sets/historical_sets rows with explicit status.

Live drafts retain incomplete and partially entered measurements. The form infers
Completed only from all enabled values and shows no status dropdown. Untouched
blank sets stay Incomplete through autosave/Back/Next and become Skipped only in
Finish's atomic transaction. Partially entered sets block Next/Finish with inline
errors. Weight-only sets use Done checkboxes, with unfinished intent persisted in
schema-14 workout_set_checks. One weight still belongs to the entire exercise.

Finish keeps NULL set actuals for skipped sets and clears exercise weight/increase
when no set was performed. Shared weight alone never performs a set. Zero weight
and reps remain valid. An all-skipped workout requires confirmation. Historical
completed sets remain frozen; explicit status controls remain on deliberate
historical entry/correction screens. No historical snapshots are rewritten to
match the new live-entry behavior.

Previous performance uses compatible corrected person/exercise history across
routines. Last session status is separate from the last genuine performance; any
number of skipped sessions cannot erase the latter's increase recommendation.
Missing actual legacy reps/durations remain unknown, never invented results.

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

## Ego Lifts

Schema 14's ego_lifts/ego_lift_audit are separate from workout sessions and all
normal statistics. Immutable name/basis/meaning snapshots qualify compatible
records. Weight uses the existing tenths/truncation convention; reps are positive.
Confirmed corrections and soft deletions append before/after audits with revision
checks. Epley estimates use exact fractions for 2–10 reps; a true single uses the
recorded weight. No 1RM is estimated above 10 reps. No library/routine fields change.
