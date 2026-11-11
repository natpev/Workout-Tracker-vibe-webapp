# Phase 14 — Permanent Weight Basis, actual repetitions and lifting estimates

**SHAMELESSLY VIBE-CODED 🤖**

This application was built with a healthy dose of AI, questionable amounts of confidence, and minimal human supervision. It appears to work, but don’t mistake that for a warranty. Use at your own risk, and keep backups.

Application **0.14.0**, target schema **10**. Baseline remote main was
`8d1f9cadb4c28fbd2ee75a06e7dd789cab936431`, Phase 13 Update 1 / 0.13.0 / schema 9.
Prerequisites were read and checked against source; all 46 Phase 13 basis tests and
471 baseline backend/script tests passed. One systemd test required execution
outside the command sandbox for its local credential socket option.
No PR, production data access, server deployment or unrelated identity repair.

## Permanent configuration

New Weight and Weight + Duration exercise IDs require explicit Total Weight or
Per Hand / Side, with neither preselected. Existing editors show a read-only lock.
UI, request validation, catalog services and database guards enforce permanence.
Changing between weight/time mode families requires a new exercise. Weight and
Weight + Duration may change within their compatible family.

Both global/personal save scopes remain. Defaults Only affects future additions;
Update My Routines confirms a signed expiring preview and atomically saves global
name/defaults and all compatible configuration fields in that person's routines.
Other people's existing routines, completed history and all basis values remain
unchanged. Draft snapshots stay frozen. Replays cannot append historical changes.

The user's final conflict policy is **Exercise Library takes precedence**. Migration
aligns classified current routine basis with Library defaults, without rewriting
completed snapshots or recorded conversions. Unclassified weighted configurations,
effective completed history or active drafts reject migration with Update 1 guidance.
Incompatible time/weight configuration families also reject without guessing.

## Repetitions and effective history

One weight field remains. Rep-based exercises render exactly one actual-reps field
per captured set, supporting sets 1–1000. New fields start at target reps; valid edits
autosave and survive Back/Next, refresh and Resume. Invalid/blank sets remain visible
and unsaved; whole reps 0–10000 are accepted. Focused inputs and newer edits are not
replaced by stale autosave responses. Combined/time exercises retain duration behavior
and have no repetition fields. Completed skips preserve SQL NULL values and reps.

Schema 10 stores ordered nullable JSON arrays per workout exercise occurrence, with
SQL guards for shape, integer bounds and completed/skipped semantics. Original
legacy completed reps remain NULL. Resumed pre-upgrade drafts initialize missing
fields from captured targets while preserving weight/duration/flags. New manual
historical workouts record reps. Corrections append effective arrays, preserve old
before/after payloads and allow a legacy workout to gain actual reps. All-blank
legacy correction reps retain unknown semantics. History and CSV show actual reps
when present; legacy display explains the prescribed-target assumption. Wide CSV
retains its initial columns and adds an adjacent actual-reps column for Weight.

## Shared estimates and units

`weight_statistics.py` uses exact rational arithmetic over effective historical
snapshots: weight × actual rep sum × basis multiplier; legacy weight × captured
sets × target reps × multiplier; combined weight × sets × multiplier. Time/skips
and zero weight/reps contribute zero. Prior conversions already live in ordinary
correction values; classification overlay never repeats numerical conversion.

Routine selection displays history-derived lifetime totals per person, including
manual completions, corrections and retained deleted-routine history. Saved live
and historical details show workout total, same-routine preceding-30-day comparison
and lifetime pounds/short tons. No cached accumulator can drift. Known times compare
aware instants; date-only records use prior calendar dates, without inventing times.
No prior positive average displays Not enough data. Signs are neutral comparisons.

Pounds are always primary. One shared formatter uses 2,000 lb per imperial short
ton, singular/plural names, meaningful fractional pounds, unrounded prefix thresholds,
and exactly two decimals from kilotons through quettatons. No metric conversion.

## Phase 13 cleanup and compatibility

Removed runtime writers `basis.plan`, `basis.apply`, personal `baseline`, setup
`status`, preview `fingerprint`, conversion `convert`, and runtime `payload`.
Removed `basis_views.py`, `basis_confirm.html`, conversion preview/confirmation UI,
classification counters, existing-basis radios, Weight Meaning inputs and new
preparation-epoch tracking. Old signed conversion confirmations are invalid under
the new settings-only salt. No new automatic historical conversion can execute;
insert guards also close both conversion tables.

Retained read-only `basis.audit_weight`, `audit_payload`, `digest`, `overlay`, and
`validate`: they verify exact old arithmetic, payload hashes, correction linkage,
expected-effect completeness and original classification metadata. Old migration
scripts/constants stay unchanged. Original Weight Meaning columns and old prepared
JSON epochs remain for immutable snapshots, grouping and hash compatibility.

No obsolete database structures were removed: both basis audit tables, lookup
index, original columns and ownership/immutability guards remain necessary for
lossless historical interpretation and verification. Closing inserts replaces
transition runtime functionality. See [schema documentation](docs/SCHEMA_10.md).

## Verification

Final verification covers **659 unique tests passing**: **530 backend/script,
109 real Chromium, 20 Docker**. No blocking failures or skipped coverage remain.

- Complete final backend run: **530 passed in 185.80 seconds**. It includes
  migration faults/activation rollback, original bytes/cells/effective-history
  equivalence, old correction/conversion chains plus later rep corrections,
  invalid/zero/legacy reps, exact arithmetic, imperial thresholds, manual/scheduled
  backups, damaged-schema-10 restore, updater scripts and offline systemd syntax.
- Complete Chromium run covered 108 cases: 107 passed and one updater test-driver
  reload raced an in-flight navigation. The driver now explicitly waits for the
  POST/303 navigation and host availability, preserving all assertions. All five
  affected LAN browser tests and two final feature-screen checks then passed:
  **7 passed in 45.56 seconds**. The additional native required-basis creation
  check passed too, giving **109 distinct passing Chromium cases** overall.
  Earlier failures from removed Weight Meaning controls were fixed by preserving
  noneditable legacy metadata and updating the obsolete creation-field assertion.
- Full Docker integration run: **20 passed in 695.76 seconds**. Actual containers
  cover schema-9→10 candidate migration, schema-10 code-only updates, safe refusal
  and old-image recovery for unclassified sources, shutdown/startup failures,
  independent host HTTP/Unix status, emergency v4, backups, scheduler and restart.
  Old unclassified fixtures now test required safe refusal rather than unsafe
  automatic upgrades; successful explicit migration and recovery remain covered.
- Final packaged image was rebuilt after the small native-validation, confirmation
  display and routine-copy fixes. Its schema-9→10/audit/copy/backup/restart test
  passed again: **1 passed in 11.66 seconds**. This repeats an existing Docker case,
  not an extra unique test. Final local image ID:
  `sha256:514382bfa6510a5fa90190c08a8c93a63f557e812094e993a529012b1d4b0ccc`.
- Focused final feature/calculation/documentation verification: **108 passed in
  9.69 seconds**. These overlap the full counts. Static searches, import review,
  compilation, staged diff/whitespace review, README shell syntax/link checks and
  release-note validation passed. Released schema definitions were not modified.

Chromium covers 320/390-pixel phones, 844×390 iPhone landscape, desktop, Light/Dark,
set counts through 1000, one weight field, navigation/resume, stale autosave input,
manual history/corrections, read-only basis and both save scopes. Date-only
comparison semantics and timezone/DST boundaries have backend coverage. No physical
iPhone/Safari, real systemd provisioning, production storage or deployment is claimed.

Reproduce using a workspace virtual environment with requirements-browser.txt and
installed Chromium, plus the managed local Docker daemon and a locally built
workout-tracker:phase8-review image (supply the trusted pip_ca build secret where
needed). All tests use temporary storage:

```bash
python -m pytest -q --ignore-glob='*browser.py' --ignore-glob='*docker.py' --ignore=tests/test_container.py
python -m pytest -q --ignore-glob='*docker.py' --ignore=tests/test_container.py -k browser
WORKOUT_CONTAINER_TESTS=1 python -m pytest tests/test_container.py tests/test_basis_docker.py tests/test_combined_docker.py tests/test_phase8_docker.py -q
```

A command-sandbox restriction required running socket/systemd/Chromium/Docker
checks in the normal managed executor outside that command sandbox. One final
image-check attempt was not executed because automatic approval review hit a
usage limit; the same approved action succeeded after the user requested Continue.
No approval check or branch protection was bypassed.

README was opened and reviewed against actual features, CLI, Compose and v4.
Beginner installation, commands, versions, links and exact humorous disclosure
are preserved. Version-matched human-readable release notes are in releases/0.14.0.json.
All previous release notes/reviews remain archives of earlier behavior.

## Existing server upgrade

These are operator instructions; none were executed on the user's server.
For `/root/WorkoutTracker/app` with `/root/WorkoutTracker/data/storage`:

1. While still on Update 1 (0.13.0/schema 9), classify all weighted Library defaults,
   every person's routine configurations and their retained completed history.
   Finish unclassified active drafts, then classify their completed history.
   Do not guess or alter truthful historical weights to force classification.
2. Wait for Saved on open workouts. Make/verify a backup, and protect the entire
   storage tree and private parent .env separately. Finish open historical reviews
   or prepare a fresh review after upgrade if their basis was not classified.
3. With the existing Phase 12 host updater already installed, open Settings →
   Administration → Application Updates → Check for Updates.
4. Review **0.14.0 / target schema 10** and the human-readable notes. Explicitly
   confirm installation and separate-candidate migration, then Install Update.
5. Follow the independent progress tab through verified backup, build, migration,
   original/candidate integrity and audit validation, activation and health checks.
6. Verify Settings/footer and readiness show **0.14.0 / schema 10**. Make a new
   verified schema-10 backup. Retained schema-9 backups cannot silently downgrade
   the active store. Existing classified drafts remain resumable.

Emergency SSH alternative, with no other update job running:

```bash
cd /root/WorkoutTracker/app
git status --short --branch
# Stop and reconcile local changes; never force-reset or discard them.
bash /root/WorkoutTracker/app/deployment/update_workout_tracker_v4.sh
```

Review/confirm the release and type **MIGRATE 10** when requested. No new updater
script, host-service refresh (after Phase 12), Compose/.env/port/timezone change,
initialization, Restore shortcut, authentication or HTTPS setup is needed.

```bash
curl --fail http://10.0.69.9:8000/health/ready
```

Use the configured address if different. Expected readiness JSON:
`{"app_version":"0.14.0","schema_version":10,"status":"ready"}`.
On failure, preserve source/candidate/selection and inspect protected logs. If
classification is missing, migration leaves the original database selected; use
the compatible Update 1 image to finish classification. Never force an old image
to use schema 10 or restore an older backup automatically. Code rollback cannot
merge workouts entered after activation. See deployment/README.md for recovery.
