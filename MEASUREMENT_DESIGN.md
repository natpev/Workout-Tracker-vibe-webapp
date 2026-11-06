# Weight and Time exercise design

> **SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.** This document specifies future work; it is not an implemented or tested workout feature.

## Current state and authorization

Inspection of Phase 1 commit `ed42a24` found a Flask shell, themes, metadata-only
SQLite schema 1, and storage safeguards. There is no routine editor, workout
entry, exercise table, or workout history. This feature request therefore
updates documentation and design only. Application source, schema version,
dependencies, and existing tests remain unchanged. Phase 2 and later still
require authorization; neither deployment nor real-data access is authorized.

This branch builds on the Phase 1 review branch. Review its documentation changes
against `phase-1-foundation` to avoid mixing them with the earlier implementation.

## Interface and significant data flows

The routine editor will provide a segmented **Weight / Time** selector with
keyboard navigation, a programmatic selected state, and large touch targets.
Both types configure a positive integer set count using rounded plus/minus
buttons or a numeric input. Weight configures positive target reps per set;
Time configures positive target duration per set using minutes and seconds.
Examples: Dumbbell Bench Press — 3 sets × 12 reps; Plank — 3 sets × 45 seconds.

Browser → Flask validation → routine service → SQLite transaction: send the
selected type, sets, and only its applicable target. The server rejects unknown
types, invalid sets, inconsistent fields, and unauthorized ownership. Hiding a
field in the browser does not validate it. Switching type must clear obsolete
saved target fields rather than preserve hidden reps/duration accidentally.

Workout entry remains one exercise at a time. Starting a draft copies routine
configuration into session-entry snapshots and leaves actual measurements blank.
A Weight card has one actual weight field; a Time card has one actual duration
control (minutes/seconds may be paired parts of that one value). Set count never
creates per-set result fields. A recorded duration is not multiplied by sets.
No live stopwatch or timer is requested by this feature.

Browser → Flask validation → draft service → SQLite transaction: normalize a
blank measurement to SQL NULL, decimal pounds to the agreed exact weight
representation, and entered minutes/seconds to integer seconds. Never use a
truthiness check that turns valid zero weight into NULL. Treat a fully blank
duration control as skipped; a partially entered control must be handled by an
explicit validation rule, not silently converted into a skip. Require whole
minutes and seconds, nonnegative minutes and seconds in 0–59; reject fractional
seconds and invalid values. Exact zero-duration and partial-input rules remain
open before implementation.

Show previous matching weight/duration and its increase recommendation. When the
previous matching session was skipped, show that fact and the last performed
matching measurement. Use “Increase weight next time” or “Increase duration next
time.” A skipped entry has no new increase recommendation. Previous values are
never copied into today's actual input.

Preserve one draft per user, revision/conflict checks, atomic idempotent Finish
& Save, all-skipped confirmation, and the existing discard confirmation flow.
Progress is non-NULL applicable entries divided by all entries; navigation is
not progress. History keeps every skipped row visible but excludes NULL values
from numeric performance summaries and charts. Explicit zero weight is valid.

All screens retain mobile-first rounded cards, oval buttons, large inputs, and
Auto/Light/Dark themes. No external assets or third-party service is required.

## Proposed schema additions, not executable SQL

Type belongs to the routine's exercise configuration and is copied into each
session entry. Permanent exercise identities remain person-owned. A type edit
changes future routine usage, never earlier snapshots or existing drafts.
History queries use the entry's type, not the routine's current type.

| Planned record | Fields relevant to this feature |
| --- | --- |
| Routine exercise | `exercise_id`, `measurement_type` (`weight`/`time`), `target_sets`, `target_reps`, `target_duration_seconds`, optional exercise notes and weight-meaning metadata. |
| Session entry snapshot | Permanent exercise ID, name/order, measurement type, target sets, target reps or duration seconds, unit/weight meaning, optional notes, actual weight, `actual_duration_seconds`, nullable increase flag. |

Use separate nullable actual columns for weight and duration. Do not overload a
single number whose unit depends on a mutable routine record. Weight uses the
previously proposed exact scaled-integer representation; its decimal precision
must be decided before implementation. Duration is a STRICT SQLite INTEGER in
seconds; target duration is also an integer in seconds.

Required database constraints and service invariants:

- Weight: positive target sets/reps, target duration NULL, actual duration NULL;
  actual weight may be NULL, zero, or a valid nonnegative decimal representation.
- Time: positive target sets/duration, target reps NULL, actual weight NULL;
  actual duration may be NULL or valid integer seconds under the approved limits.
- Skip: both actual columns NULL, a retained entry row, and increase flag NULL.
- Performed: exactly the type-appropriate actual column non-NULL, with a valid
  false/true increase flag. No second measurement may be stored on the same row.
- Explicit `IS NULL` / `IS NOT NULL` clauses are needed in CHECK constraints:
  SQLite can accept a CHECK evaluating to NULL, so `value > 0` alone is insufficient.
- Foreign keys and ownership rules preserve user isolation. Routine copying
  copies type/targets/notes only, never results or increase state.
- Routine edits/removal never cascade into historical measurements or snapshots.
  Confirmed saved-workout corrections remain a separate validated action, not a
  side effect of editing a routine. Exact correction fields/audit policy remain open.

Previous-value and chart queries must filter by person, permanent exercise ID,
snapshotted measurement type, unit/weight meaning, and workout chronology. Never
compare pounds with seconds or carry a weight increase flag into a timed entry.
The previous matching session means the latest comparable historical entry;
a type change cannot reuse an incompatible last result. If none exists, show
no previous comparable measurement. Retain both types as separate history series.
Time charts display time labels such as minutes:seconds while calculations use
integer seconds; weight charts display pounds. Target duration and actual
duration must remain distinguishable in tables and charts.

## Schema compatibility, migration, and rollback

This documentation change does not require or run a migration. Phase 1 schema 1
has no domain measurements to convert; leave its version, accepted DDL, manifest,
and startup behavior unchanged. Do not add columns in place or treat the design
as permission to initialize another database.

When a later authorized phase adds domain tables, determine the required schema
version explicitly. Normal startup must continue refusing unsupported versions;
never auto-upgrade or replace missing storage. Before an existing database can
be upgraded, implement and test the separate-candidate migration mechanism, even
if that prerequisite must precede other later-phase features. The Phase 5 plan
is not permission to bypass safety in Phase 2.

For a necessary upgrade: quiesce writers, coordinate the scheduler and database
connections/sidecars, verify the source, create a separate candidate using
SQLite's backup API, migrate only that candidate, validate it, and atomically
switch the active selection only after success. Preserve previous versions for
recovery and never overwrite a database. Failed validation/switching must leave
the original active selection and original logical data intact. If legacy
weight-only domain data ever exists, map it to Weight only from an identified
supported source schema, retaining every original NULL and explicit zero.
Unknown schemas must fail rather than be guessed. No such domain data exists
in the inspected Phase 1 schema.

Validate integrity, foreign keys, expected schema, ownership, row counts,
measurement type/targets, units, exact values, and NULL counts/locations. Counts
alone cannot prove that NULL was not changed to zero. Backup/restore must preserve
these same invariants. Reverting a database selection does not merge newer
workouts; disclose this before any future recovery action.

## Future automated acceptance tests by phase

These are required future tests, not assertions already implemented or passing.
Use disposable fixtures only, including corruption/migration/restore tests.

| Phase | Required automated coverage |
| --- | --- |
| 2 — Routine editor | Weight/Time selector using pointer/keyboard, sets for both types, reps vs minutes/seconds visibility, 3 × 12 reps and 3 × 45 seconds round trips, server-side type/target validation, inactive fields cleared, independent copies, user isolation, theme/mobile behavior. |
| 3 — Workout entry | One actual measurement regardless of sets, blank defaults despite previous data, decimal pounds and explicit zero weight, integer-second conversion (1:05 → 65), invalid/partial duration input, SQL NULL skipped rows for both types, no recommendation on skips, matching previous/increase display, last performed after a skip, mixed-type progress denominator, all-skipped confirmation, draft resume/conflicts, idempotent save. |
| 4 — History | Snapshots unchanged after type/target/name changes and removal; existing drafts stable; mixed-type histories separated; pounds/time labels; NULL gaps and excluded summaries; zero weight retained; chronological backdated entry; confirmed validated corrections; cross-user isolation. |
| Domain schema introduction and Phase 5 — Compatibility/recovery | Supported source schemas only; schema-1 compatibility unchanged until an authorized migration exists; separate candidates; original unchanged on success/failure; failed activation rollback; integrity/foreign-key/logical checks; exact NULL and zero preservation; duration integer/type constraints; backup/restore round trips; no source overwrite or automatic startup migration. |

## Open decisions and current validation

Before implementing affected phases, resolve decimal precision/limits for
weight; duration limits, zero-duration and partially entered control semantics;
time personal-record rules; and editable correction fields/audit behavior.
These do not block recording the requested feature design.

For this documentation branch, validate specification consistency and links,
confirm application/tests/dependency/schema files are unchanged from Phase 1,
and rerun the existing foundation suite with disposable storage. Typed exercise
behavior and migration acceptance tests cannot execute until their approved
phases implement those components. No feature runtime readiness is claimed.

Validation performed on this documentation branch: existing foundation suite
**37 passed, 0 failed, 0 skipped**; `git diff --check` passed. No new automated
feature tests were added, because their application components do not exist.
Browser/container suites were not rerun for documentation-only changes; their
earlier Phase 1 results are recorded separately in PHASE_1_REVIEW.md.
