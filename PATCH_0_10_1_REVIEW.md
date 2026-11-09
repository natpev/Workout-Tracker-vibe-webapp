# Patch 0.10.1 — routine cards ordered by latest completion

> **SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.** Human-directed generated code; no independent audit or production deployment.

Branch `sort-routines-by-last-completion` starts from latest main
`a0f0a1a524c13b7cd373f0b351626f313db78d5b`. Target **0.10.1 / schema 7 unchanged**.
The user authorizes direct verified fast-forward main merge/push and feature-branch
cleanup, without a PR attempt. No deployment, live data or new phase.

## Implementation

The dashboard GET calls `routine_listing.selectable_routines` using its existing
locked read connection. It selects only active routines owned by the selected
person, then reuses `history.all_completed` on schemas 4–7 to apply validated
append-only corrections and exclude drafts/discards/unsaved preparations. Schema 3
reads only completed live sessions; schema 2 has no history and sorts alphabetically.
No startup initialization or migration is added.

Per permanent routine ID, retain the maximum effective actual workout date and
known timestamp. Live Finish timestamps resolve same-day native completions;
historical sessions use actual occurrence time, never entry time. A corrected live
occurrence supersedes the original Finish timestamp when its date/time changed.
UTC timestamp normalization preserves microseconds and makes offset comparisons
consistent. Known times precede unknown on the same date. Equal timestamps or
unknown clocks use casefolded name, exact name and permanent ID. Never-completed
routines use the same alphabetical order at the bottom. Entirely skipped completed
workouts count as completions, independently of their NULL measurements.

Person and routine identities prevent same-name/copy result leakage. Renames keep
rank by ID. Deleted/archived definitions stay absent even when history is retained.
The helper writes nothing: no routine positions, exercise order, snapshots, dates
or audits change. The existing card template, CSS, controls, copy-source selector
and routine editor are untouched. The history reader validates snapshots as before;
its work grows with household history, with no new index or schema required.

## Updater and database compatibility

APP_VERSION becomes 0.10.1; TARGET_SCHEMA_VERSION remains 7. Storage/schema/migration,
backup/restore, scheduler, logging and host updater implementations are untouched.
The existing browser updater and v4 discover the patch through release metadata.
A confirmed code-only update still creates its existing verified backup and checks
source/storage/health; it does not migrate or switch a schema-7 database. No new
host-service upgrade is needed when already on the Phase 10 runtime. Earlier hosts
retain the previously documented console upgrade requirement. No server config or
external root updater wrapper is modified or claimed tested.

## Tests and verification

Final full suite: **396 passed, 0 failed, 0 skipped**, in **475.33 seconds**
(349 backend/script, 34 Chromium, 13 Docker). Targeted ordering/updater/browser
checks: **12 passed**. The rebuilt review image is
`sha256:f65facae44507f910cc95552eaec517955d13765891d35c1635a1b9b5a675336`.
Release-info reports 0.10.1 / target schema 7. Git diff whitespace checks passed.
The completion report records verified remote main and branch cleanup.
New backend tests cover recent/older/never ordering, late-entered older history,
multiple completions, unfinished preparations, saved native zero, active autosaved
drafts, discarded sessions, person isolation, same/cross-person copies, same names,
renames, timestamp/name ties, effective corrections, excluded deleted/archived
routines, schema-2/3 compatibility and exact SQL-dump equality on listing/HTTP GET.
A real v4/engine test with synthetic fixed Git/Docker commands checks patch metadata,
original DB bytes/selection and absence of migration on schema 7.

Chromium tests at 320/1280 pixels check the actual server-rendered routine-card
order, refresh after a historical completion, all three themes, original Edit/Start
controls, correct routine IDs and no horizontal overflow. Existing tests keep all
assertions; only current application-version literals are updated to 0.10.1.
The full suite also includes actual Docker builds, code-only schema-7 replacement,
candidate migration, backup/restore, scheduler/logging and update fault recovery.
Only disposable SQLite/storage/Compose fixtures are used. No physical Safari or
live-server deployment is claimed.
