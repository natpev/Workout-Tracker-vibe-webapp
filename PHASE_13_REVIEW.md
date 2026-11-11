# Phase 13 — Weight Basis transition, Update 1

**SHAMELESSLY VIBE-CODED 🤖**

This application was built with a healthy dose of AI, questionable amounts of confidence, and minimal human supervision. It appears to work, but don’t mistake that for a warranty. Use at your own risk, and keep backups.

Application **0.13.0**, database **9**. Started from approved main
304d2a9610510ee6713730fbdc983b508fbfcc7d on phase-13-weight-basis-transition.
Direct main merge/push/cleanup is authorized after verification, without a PR.
No production server/database access or deployment is performed.

## Weight Basis and save scopes

Weight and Weight + Duration support Not Configured (temporary), Total Weight
(×1) and Per Hand / Side (×2). Time-only configuration keeps neutral internal NC
metadata and exposes no basis controls. Existing free-text Weight Meaning stays
editable and is preserved by migration. Neither names nor descriptions classify
anything automatically. New routine additions copy shared defaults, including
basis; copies retain the source routine's independent settings and shared IDs.

Save Defaults Only saves the shared name/defaults without modifying existing
routines, completed records or personal history baselines. Missing basis on an
existing configuration edit retains its current convention; selecting NC remains
explicitly available during Update 1. Type changes to Time clear incompatible
metadata using the existing configuration rules.

Save Defaults & Update My Routines first shows a signed, expiring confirmation:
all new settings, selected person, routine/item counts, personal last-applied
baseline, actual snapshot bases, divide/multiply/first-assignment counts and saved
workout counts. It replaces all configuration fields only for that person's
matching IDs (including retained archived routines). Shared name/defaults remain
global. No other person's existing routine settings or actuals change.

CSRF is bound to the selected storage generation. A full database fingerprint
rejects new workouts/edits/corrections after preview; the exclusive root lock and
one SQLite transaction cover every change. A unique operation ID binds exact
canonical settings, so repeated/concurrent confirmed submissions cannot apply
again. Same-basis fresh saves may record a settings-application event but never
repeat a numerical conversion. Preview expires after 30 minutes.

## Exact arithmetic and auditable history

Existing history starts NC. Its first classification changes no numbers. Later
Total→Per Side divides integer tenths by two; reverse multiplies by two with signed
64-bit bounds. Zero stays zero; skipped measurements stay NULL and increase flags
stay unchanged. Odd tenths on
division (25.5→12.75) or multiplication overflow refuse **the entire operation**,
identify the exercise/workout and retain settings. Review the source for accuracy;
never round a true measurement to force a transition.

Each original workout entry has immutable basis metadata. Append-only personal
basis_transitions track the last actually applied baseline separately from global
defaults. Per-workout/entry basis_assignments retain exact before/after bases and
weights, expected effect manifests and ordinary correction IDs. Independently
configured new snapshots use their own actual basis, not an assumed global or
personal baseline; heterogeneous history is converted entry by entry, explicitly
shown in the preview. NC records receive first classification without arithmetic.
Configured history cannot be silently reset to NC through the bulk operation.

Numeric conversions append ordinary workout_corrections, including a value-
preserving revision for first classification. Thus stale correction forms are
rejected even when classification changes no number. Original completed rows,
old correction JSON, sets/reps/targets, durations, dates and routine associations
are untouched. Later user corrections start from converted effective values; no
old multiplier is reapplied. Reversal uses the latest effective value, preserving
legitimate intervening corrections without rounding drift.

History, charts, previous-performance lookups, corrections, CSV and saved summaries
already share the ordinary effective-correction layer. Only basis metadata is
overlaid separately. Different bases have separate series/export columns and
comparisons; NC retains legacy Weight Meaning comparison behavior. Classified
previous comparisons use basis rather than interpreting old descriptive text.
Legacy free-text differences can still produce distinct chart/CSV groups.

Transition audit links appear in saved-workout correction details. New metadata
is append-only; only the existing explicitly confirmed permanent-exercise deletion
capability may delete its own audit links. No conversion invokes that capability.
Routine removal/deletion retains history and its basis audit.

## Drafts, reviews and Update 2 preparation

Bulk application refuses a selected-person active draft containing the exercise.
It never changes/discards drafts; Defaults Only remains usable. Other people's
drafts are unaffected. Original snapshot guards also protect the new basis column.
Pending historical snapshots remain frozen: if a transition made their recorded
basis incompatible, saving fails with raw inputs retained and asks for a new
review. Same-basis and duration-only pending reviews remain usable. No old form
JSON is rewritten during migration or conversion.

The Library shows configured/total weight-based exercise IDs independently for
shared defaults, your routines and your history. All relevant configurations or
records for an identity must be classified for that counter to count it complete.
No automatic finalization. Update 2 is **not implemented**: Weight Meaning, NC and
the temporary conversion operation remain. All audits/original NC snapshot facts
must survive eventual UI/tool removal. No Estimated Total Weight Lifted, lifetime,
30-day, ton or summary-total statistics are added. The model supports future
Weight×sets×reps×multiplier and combined Weight×sets×multiplier; unknown remains
unknown, and Time/skips can contribute zero without changing stored NULLs.

## Candidate migration and recovery

Schema 9 rebuilds only routine_exercises, exercise_defaults, workout_entries and
historical_entries **on a separate candidate** to add constrained weight_basis.
Every original column is copied by name and compared exactly, including all IDs,
NULLs, free-text meanings and audit JSON. Existing immutable/ownership triggers
are reinstalled identically, with additional immutable original-basis guards.
New strict audit tables have ownership FKs, revision/enum constraints, indexes,
append-only protection and explicit effect/correction linkage validation.

Validation checks original bytes/selection, exact candidate DDL, schema migration
records, integrity/FKs, old cell/row preservation, NC initialization, original
snapshots, correction/basis chains, effect completeness and exact arithmetic.
Only a verified candidate is atomically selected under the existing root lock.
Failure preserves original selection/bytes and the failed candidate; activation
sync failure restores the prior pointer. Startup never initializes or migrates.
Schema-9 ordinary storage checks validate basis/correction audit chains read-only.

Backups copy all basis/correction metadata and verify it. Restore uses a distinct
candidate and exact schema/storage identity; schema-8 backups are not silently
restored into 9. Old source versions/archives remain retained. Database backups
still omit external keys/settings: protect the entire storage tree separately.
The existing browser/v4 engine reads target 9 from approved pinned release metadata
and invokes the explicit container CLI. No new updater script or Phase-12-host
refresh is necessary. Real systemd/server provisioning is not claimed tested.

## Existing installation upgrade

For /root/WorkoutTracker/app with /root/WorkoutTracker/data/storage and the host
updater already refreshed for Phase 12:

1. Wait for Saved on any open workout before updating. Make/verify a backup and
   protect the whole storage tree and private .env separately.
2. Settings → Administration → Application Updates → Check for Updates.
3. Review **0.13.0 / target schema 9**, including the human-readable notes.
4. Explicitly approve the separate-candidate migration and Install Update.
5. Follow the independent host progress. It stops writers, verifies a backup,
   builds the approved image, migrates only a candidate, validates and restarts.
6. Confirm Settings/footer and readiness report 0.13.0/schema 9. Make a new verified
   schema-9 backup. Existing drafts remain; finish them normally before applying
   bulk basis changes to exercises they contain.

Emergency SSH alternative (no update already running):

```bash
bash /root/WorkoutTracker/app/deployment/update_workout_tracker_v4.sh
```

Review/confirm the release and type **MIGRATE 9** when requested. Do not initialize
storage, overwrite databases, reset Git work, or use Restore as an update shortcut.
The authoritative .env/Compose layout, addresses and ports remain unchanged.

```bash
curl --fail http://10.0.69.9:8000/health/ready
```

Expected: {"app_version":"0.13.0","schema_version":9,"status":"ready"}.
Use the actual configured address if different. On failure, preserve files and
inspect protected logs/retained selections; do not force an old image to use schema
9 or silently restore old data. Code rollback cannot merge later workouts.
See deployment/README.md for advanced recovery. No command above was executed on
the user's server during development.

## Documentation and verification

README was opened/reviewed against actual features, Compose, Dockerfile, CLI and
v4. Updated new-install target/readiness, existing-install migration instructions,
Weight Basis/save scopes/precision/drafts and current review links. Preserved the
friendly opening, numbered new-install guide, data separation and exact humorous
disclosure. New version-matched releases/0.13.0.json has concise user-facing notes;
technical schema/audit details stay in developer documents. Permanent README and
release-note requirements remain in AGENTS and PROJECT_SPEC.

Final complete automated suite: **590 passed, zero failed, zero skipped**, in
893.95 seconds (14m53s): **471 backend/script, 100 Chromium, 19 Docker**.
The suite retains every prior regression and adds 46 basis backend cases, seven
mobile/theme browser cases and one schema-8-to-9 Docker rehearsal; an additional
real host/Compose case verifies schema-9 code-only updates.

The 53 new backend/browser checks also passed together before the final run.
Migration tests cover original-byte/cell/NULL/audit preservation and five injected
failure stages, including rollback after activation sync failure. Transaction
tests inject four write/validation failures; concurrent tokens verify exactly-once
conversion. Backup/restore and browser/v4 container tests passed.
README shell blocks were syntax-checked, commands compared with actual Compose/CLI,
local links checked, disclosures verified, and current release notes parsed.
Final image was rebuilt after a comment-only form-header clarification:
`sha256:10b2ece96e4f102ad41961412da3c2d9acf81bc80345b6506e91de98cc8b5606`.
Final image migration/backup/HTTP rehearsal plus documentation checks: **4 passed
in 16.99 seconds** after that clarification; these are repeat checks, not extra
unique tests added to the 590-test count.
An earlier incomplete full run was intentionally stopped to strengthen ownership
guards; its partial result is not included in the final counts above.

Tests use synthetic households/disposable SQLite,
loopback Chromium and isolated Docker. No physical iPhone/Safari, real server,
production data or deployment is claimed tested. No unrelated identity cleanup.
