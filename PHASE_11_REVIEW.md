# Phase 11 — Combined Weight + Duration

> **SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.** Human-directed generated code, not an independent audit or live deployment.

Starting main: a46d2a8ae9d6daadc784a5bd1443ac14c0530c9e (0.10.4/schema 7).
Branch: phase-11-combined-weight-duration. Target: 0.11.0/schema 8.
Direct verified main merge/push/cleanup authorized; no PR creation or attempt.

## Implementation and data flow

The generic weight_duration mode configures sets, target duration, lb, existing
free-text weight meaning and notes, without fixed target weight or target reps.
Global defaults copy once into routine rows. Edits/copies remain independent and
exercise IDs remain global. Retained schemas reject the new mode until explicit
schema-8 migration; normal old Weight/Time behavior remains available.

Browser forms send one actual weight and duration per exercise to the shared
measurement validator. Both blank gives two SQL NULLs and a NULL flag. Performed
pairs require both; zero weight is valid, positive duration accepts either/both
parts and normalizes large seconds. Exact integer-tenths truncation is unchanged.
Partial autosaves show field-level errors and retain input but commit neither
actual nor a new revision/checkpoint. A later valid pair saves atomically.
Increase weight next time remains manual, even below target; no duration flag.
The Next-only checkpoint, stale revisions, all-skipped confirmation and one draft
remain. Previous display includes both actuals, meaning and weight recommendation.

History and append-only corrections use the existing effective read layer with
additional paired-value validation. Originals and before/after audits retain both
actuals. Partial corrections are rejected before an audit write. Snapshot names,
IDs, mode, targets and notes remain immutable. No orphan/duplicate investigation,
matching, reconciliation or cleanup was performed.

Progress produces two numerical series together under one heading. Weight and
duration never share an axis or mix with ordinary Weight/Time configurations.
Filters, local SVG, accessible data, date tooltips, person/ID/meaning isolation,
NULL exclusion and explicit zero are preserved. Duration targets come from each
snapshot. One common historical target gets a dashed reference; differing targets
appear per point/data row instead of a misleading single line.

CSV preserves Date, Time, Routine, Workout ID, oldest-first workout rows and all
selection/range/effective-history/escaping/formula defenses. Combined groups add
three adjacent columns: Weight (lb), Duration, Sets × Target Duration. Time uses
total m:ss; skip actuals blank with target retained, absent groups all blank,
zero weight 0. Ordinary two-column formats remain unchanged.

## Candidate-only schema 8

Existing schema-7 CHECK constraints prohibit the new type and paired actuals.
combined_schema.py derives four new table definitions: routine_exercises,
workout_entries, historical_entries, exercise_defaults. No result column is added.
The explicit migrator backs up to a distinct candidate, rebuilds only those tables
there and reinstalls the exact original protection/ownership triggers before
validation. It never bypasses protections on a live app connection or for ordinary
correction. All original tables/cells, IDs, NULLs, preparation JSON and audit JSON
are compared exactly, including migration records apart from the new version row.

Integrity, FKs, exact DDL/version, counts, prepared snapshots, registry and audit
chains validate before atomic active.json replacement. Original bytes/manifests
remain recoverable. Failure before activation leaves original selected; a failed
post-switch sync attempts selection rollback. Failed candidates remain evidence.
No startup migration/initialization/repair or source overwrite is introduced.
Backup/restore supports schema 8, including explicit damaged-file recovery, while
retaining exact-schema restrictions and old backups. Restore never downgrades 8.

## Upgrade instructions and updater compatibility

Use the existing browser updater: Check, review 0.11.0/schema 8, explicitly confirm
install and migration, Install, watch independent status, then verify readiness.
Emergency SSH: bash /root/WorkoutTracker/app/deployment/update_workout_tracker_v4.sh,
review and confirm MIGRATE 8. If unavailable, fetch/fast-forward clean main first.
No new updater script or Phase-11 host-service upgrade is required for a working
Phase 10 installation. Release-info stays storage-free JSON with target schema 8.
The generic host engine invokes the new image's explicit target-8 CLI and retains
backup/original/recovery/health checks. Exact operator commands and failure limits
are in deployment/README.md#phase-11-schema-7-to-8-upgrade. Server operations were
not executed. Preserve existing Compose/.env, LAN addresses and IANA timezone.

## Verification

Final complete run: **476 passed, 0 failed, 0 skipped** in **654.73 seconds**
(10 minutes 54 seconds): **402 backend/script, 57 Chromium, 17 Docker**.

```sh
WORKOUT_CONTAINER_TESTS=1 /workspace/phase1-venv/bin/python -m pytest -q --tb=short --show-capture=no --junitxml=/tmp/phase11-full.xml
```

JUnit confirms zero errors, failures and skips. The tested local integration image
is `sha256:92723d46d8206c6aaef16a6dba0ae778b611c1bd64ca7a13c00afcf25d091a4d`.
Storage-free release-info reports application 0.11.0 / target schema 8.
`git diff --check` passed. Initial targeted runs caught test-fixture mistakes
(retained minute parts, a CLI group name and error-label selectors) and the old
release-target assertion; these were corrected without removing any assertion.
No existing test was removed or weakened: current version/target expectations were
updated, and real Docker coverage grew from four updater scenarios to seven,
including schema-7 migration success, pre-activation recovery and post-activation
failure. A new container replacement scenario covers paired drafts/corrections.

 Tests use synthetic
records and disposable databases only. Coverage includes paired input/field errors,
SQL constraints, defaults/copy independence, snapshots, effective corrections and
audit rejection, previous fallback, navigation/autosave/restart, two charts/targets,
CSV download, zero/NULL, candidate migration/cell/trigger/source preservation,
fault rollback, schema-8 backup/restore, old-backup refusal and updater compatibility.
Chromium covers 320/390/1280 widths, Light/Dark/Auto, tooltips and actual downloads.
Docker rehearsals include schema 7→8 and no-schema-change updates/failure recovery.

## Limitations

An invalid partial pair is intentionally not persisted; finish entering both
fields and wait for Saved. Closing before acknowledgment cannot preserve unsaved
input. No offline queue, per-set recording, automatic progression or stopwatch.
Reference targets are per set, not multiplied by sets. Large exports/maintenance
retain the existing in-memory/household-scale behavior. Unknown historical clocks
remain unknown. Exact-schema restore does not migrate old backups or merge new
workouts into an old selection. Physical iPhone/Safari, Excel/Numbers/Sheets GUI,
external root updater wrapper, live systemd/server and ARM deployment are not
claimed tested. No production data accessed, server deployed or next phase begun.
