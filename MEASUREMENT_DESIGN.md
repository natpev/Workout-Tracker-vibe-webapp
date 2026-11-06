# Weight and Time exercise design

> **SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.** Phase 4 adds history, local typed charts, historical completion and append-only effective corrections; original snapshots remain protected. Review and test before use.

## Current state and authorization

Phase 1, this design and Phase 2 are reviewed and approved. Phase 2 implements people, permanent
exercise definitions and the typed routine editor, plus the minimal safe
schema-1 → schema-2 migration prerequisite. Phase 3 is reviewed, approved and
merged into main, including typed workout entry, snapshots, server drafts,
recovery, previous performance, atomic completion/discard and candidate schema 3.
Phase 4 only is now authorized and implemented for review on phase-4-history-charts:
history, local SVG charts, independent historical completion and append-only
correction revisions. Stop before merging or beginning Phase 5. Full backup/
restore, scheduling and application log viewing remain later phases. No deployment or production data access is authorized. See PHASE_3_REVIEW.md.
The validation record at the end describing the earlier documentation branch
is historical, not the current implementation result.

## Interface and significant data flows

User switching remains through the approved People screen. Do not redesign it
or add browser-style tabs.

The routine editor provides a segmented **Weight / Time** selector with
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
blank measurement to SQL NULL, decimal pounds to integer tenths with digits
beyond the first decimal place truncated (never rounded), and entered minutes/seconds to integer seconds. Never use a
truthiness check that turns valid zero weight into NULL. Treat a fully blank
duration control as skipped; a partially entered control must be handled by an
explicit validation rule, not silently converted into a skip. Require whole
minutes and seconds, nonnegative minutes and seconds in 0–59; reject fractional
seconds and invalid values. A nonblank actual duration must be at least 1
second; zero is invalid, while fully empty remains SQL NULL. Both parts must
be supplied for a performed duration, including explicit zero minutes when
appropriate. Partial input is an error, never silently normalized to a skip.
The implementation lives in schema 3 and does not alter retained schema-2 files.

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

## Schema design (schema-3 sessions and results implemented)

Type belongs to the routine's exercise configuration and is copied into each
session entry. Permanent exercise identities remain person-owned. A type edit
changes future routine usage, never earlier snapshots or existing drafts.
History queries use the entry's type, not the routine's current type.

| Record | Fields relevant to this feature |
| --- | --- |
| Routine exercise | `exercise_id`, `measurement_type` (`weight`/`time`), `target_sets`, `target_reps`, `target_duration_seconds`, optional exercise notes and weight-meaning metadata. |
| Session entry snapshot | Permanent exercise ID, name/order, measurement type, target sets, target reps or duration seconds, unit/weight meaning, optional notes, nullable integer `actual_weight_tenths_lb`, nullable integer `actual_duration_seconds`, nullable increase flag. |

Use separate nullable actual columns for weight and duration. Do not overload a
single number whose unit depends on a mutable routine record. Weight uses the
approved integer-tenths representation (`actual_weight_tenths_lb`). Retain at
most one decimal place by truncating extra digits, never rounding. Examples:
40.99 → 40.9 → stored 409; 42.56 → 42.5 → stored 425; 40 → displayed 40.0 →
stored 400. Explicit zero stores 0 and displays 0.0; empty input is SQL NULL.
Use exact decimal parsing, not binary floating-point rounding. Duration is a
STRICT SQLite INTEGER in seconds, minimum 1 for a non-NULL actual measurement;
zero is invalid and empty is SQL NULL. Target duration also uses integer seconds.
These result columns are implemented in schema 3; retained schema 2 stays unchanged.
Both actual representations are bounded by SQLite signed 64-bit integers; form
measurement strings are limited to 100 characters before parsing.

Required database constraints and service invariants:

- Weight: positive target sets/reps, target duration NULL, actual duration NULL;
  actual weight may be NULL or a nonnegative integer number of tenths of a pound, including valid zero.
- Time: positive target sets/duration, target reps NULL, actual weight NULL;
  actual duration may be NULL or integer seconds >= 1; zero is invalid.
- Skip: both actual columns NULL, a retained entry row, and increase flag NULL.
- Performed: exactly the type-appropriate actual column non-NULL, with a valid
  false/true increase flag. No second measurement may be stored on the same row.
- Explicit `IS NULL` / `IS NOT NULL` clauses are needed in CHECK constraints:
  SQLite can accept a CHECK evaluating to NULL, so `value > 0` alone is insufficient.
- Foreign keys and ownership rules preserve user isolation. Routine copying
  copies type/targets/notes only, never results or increase state.
- Routine edits/removal never cascade into historical measurements or snapshots.
  Confirmed saved-workout corrections remain a separate validated action, not a
  side effect of editing a routine. Only actual values, increase flags and occurrence date/time can be corrected. Full before/after values, UTC correction timestamp and sequence are appended; immutable snapshots and prior corrections stay retained.

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

Phase 2 implements an explicit candidate-only migration from metadata-only
schema 1 to schema 2. Phase 3 extends this with explicit schema 1/2 → 3
candidates. Original files remain unchanged. Existing metadata, people, exercise
definitions and routine targets (including NULLs) are compared row-for-row; only
new workout tables/index/triggers are added. Phase 4 extends the same explicit
candidate path to schema 4, adding historical preparations/completions, registry
links and append-only correction revisions. Every original schema-3 row, NULL
and protection trigger is preserved; effective readers apply validated overlays.
Startup never migrates or initializes.
Future domain changes require separately reviewed candidates, not in-place changes.

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

Phase 2 routine tests and Phase 3 workout/persistence/migration tests are implemented. Phase 4 history/chart/manual/correction tests are also implemented. Backup and restore assertions remain future tests, not claimed as passing.
Use disposable fixtures only, including corruption/migration/restore tests.

| Phase | Required automated coverage |
| --- | --- |
| 2 — Routine editor | Weight/Time selector using pointer/keyboard, sets for both types, reps vs minutes/seconds visibility, 3 × 12 reps and 3 × 45 seconds round trips, server-side type/target validation, inactive fields cleared, independent copies, user isolation, theme/mobile behavior. |
| 3 — Workout entry | One actual measurement regardless of sets, blank defaults despite previous data, 40.99 → 40.9/stored 409, 42.56 → 42.5/stored 425, 40 → 40.0/stored 400, truncation never rounding, explicit zero weight, integer-second conversion (1:05 → 65), actual duration 1 accepted/0 rejected/empty SQL NULL, invalid/partial duration input, SQL NULL skipped rows for both types, no recommendation on skips, matching previous/increase display, last performed after a skip, mixed-type progress denominator, all-skipped confirmation, draft resume/conflicts, idempotent save. |
| 4 — History | Snapshots unchanged after type/target/name changes and removal; existing drafts stable; mixed-type histories separated; pounds/time labels; NULL gaps and excluded summaries; zero weight retained; chronological backdated entry; confirmed validated corrections; cross-user isolation. |
| Domain schema introduction and Phase 5 — Compatibility/recovery | Supported source schemas only; schema-1 compatibility unchanged until an authorized migration exists; separate candidates; original unchanged on success/failure; failed activation rollback; integrity/foreign-key/logical checks; exact NULL and zero preservation; duration integer/type constraints; backup/restore round trips; no source overwrite or automatic startup migration. |

## Open decisions and validation history

Phase 4 statistics are highest logged weight and longest logged duration in
the selected range. Corrections append only actual values/flags and occurrence;
original identity/type/configuration stays immutable. Additional record metrics
and product-specific limits below SQLite bounds remain future decisions. Phase 3 uses signed 64-bit integer storage and requires both
duration parts or neither; partial input is a clear validation error. Weight precision/truncation/storage,
valid zero weight, minimum-one-second actual time, empty-as-NULL semantics and
People-screen switching are final decisions, not open questions. Every skipped
exercise must retain its own snapshot entry with NULL measurements; never
substitute zero or previous performance, and preserve tracking type and values.
These rules remain in effect through Phase 4, with no Phase 5 work.

Phase 2 validation remains recorded in [PHASE_2_REVIEW.md](PHASE_2_REVIEW.md).
Current Phase 3 evidence is in [PHASE_3_REVIEW.md](PHASE_3_REVIEW.md), including
workout entry, NULL/zero semantics, truncation, concurrent writes, network faults,
restart recovery, candidate migration and browser/container regressions. Current
Phase 4 evidence is in [PHASE_4_REVIEW.md](PHASE_4_REVIEW.md): effective chronology,
typed chart separation, independent historical entry, audit/concurrency and
schema-3 preservation. Backup/restore assertions still await Phase 5.

Historical design-only branch (`a5f7c35`): 37 existing foundation tests passed;
documentation links, disclosures and whitespace checks passed. No application
or schema changes were made in that earlier branch, so no typed runtime behavior
was claimed then. Its approval led to the current Phase 2 implementation.
