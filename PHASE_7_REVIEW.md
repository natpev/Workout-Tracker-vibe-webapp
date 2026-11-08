# Phase 7 — Shared Exercise Library, Routine Copying, and Version Display

> **SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.** Human-directed AI-generated code; not assumed audited, secure or correct.

Phase 7 is implemented for review on `phase-7-shared-exercise-library`, based on
approved main `b8a35f13e0ae59642e7be4def70639ada11e8f1b`. Target application
**0.7.0**, persistent schema **5**. No main merge, deployment, server access or
real-data operation is authorized or performed.

## Shared identities and independent people

Exercise Library is reachable from a person's menu/navigation. All active people
see and can reuse the same registered IDs on schema 5. Creation, global rename
and guarded archive are available. Renaming changes current routine displays for
every person; historical preparations, live snapshots and saved names remain
unchanged. Archive checks references in active routines across all people,
including archived people, and refuses to break those references.

New names are trimmed and checked with Unicode casefold across active and
archived definitions. Duplicate registrations/renames get an actionable validation
error. Migration never merges old matching names. Full permanent IDs in the
library and selection options distinguish those older registrations.

`exercises.person_id` is deliberately retained as **registration provenance**
so every original stored value survives migration. It is no longer ownership.
The existing people foreign key retains that provenance identity; people are
archived rather than deleted. New registrations record the selected person as
the registrant but are immediately available household-wide.

Routines, routine items, live sessions, historical sessions, registry and
corrections retain their person ownership. Previous performance filters person +
global exercise ID + type + unit + weight meaning, across routines, using effective
corrected chronology. A previous skip stays a skip, with last performed displayed
separately. Charts/results/flags never transfer between people. Weight truncation,
integer seconds, explicit zero, SQL NULL skip rows and blank initial inputs are
unchanged.

## Routine copying

Same-person duplicates and cross-person copies require a nonblank chosen name.
They create new routine and item IDs, copy relative order, sets/reps/duration,
unit/weight meaning and notes, and reuse original global exercise IDs. No exercise
registrations, measurements, drafts, history or increase flags are copied.
Configuration edits remain independent; later global name changes are deliberately
shared. A person's own compatible previous results are found naturally rather
than copied. Retained schemas 2–4 preserve their earlier local definition behavior
until explicitly upgraded, keeping existing compatibility tests meaningful.

## Schema 4 → 5 migration safety

Only `routine_exercises`, `workout_entries` and `historical_entries` exercise foreign
keys change: `(exercise_id, person_id)` becomes `(exercise_id)` referencing the
global definition. Routine/session ownership foreign keys, all column order,
checks, identity/provenance values and other structures remain unchanged.

The explicit CLI uses the existing exclusive storage-root lock and SQLite backup
API to create a distinct private candidate. Foreign keys are disabled **only on
that private migration connection before BEGIN** to permit table rebuilding.
Existing trigger definitions are recorded and reinstalled identically inside the
same candidate transaction after exact column-for-column copies. No original or
application connection loses its constraints or snapshot protections. The candidate
is closed before independent read-only validation with foreign keys enabled.

Verification checks exact schema/index/trigger DDL, migration records, application
and storage identity, integrity, foreign keys, every original table cell including
NULL and zero, complete ordered snapshots, preparation JSON, registry and every
audit before/after chain. Original bytes/hash are checked before publication.
Only a verified candidate is atomically selected; old database and selection
manifest remain preserved. DDL, mutated-cell, logical-check, activation and
post-publication durability failures retain the original selection. Compatible
schema-5 migration requests are read-only no-ops. Startup never initializes,
migrates, repairs or restores storage. Known sources 1–4 can explicitly target 5;
CLI default 3 and programmatic default 2 remain for backward compatibility.

Schema-5 backups/restores use the same exact-schema validation, cell checks,
identity checks and candidate activation. Schema-4 backups remain on disk with
their metadata and are refused as a schema-5 restore source; no silent downgrade
or automatic backup migration occurs. Recovery of an older backup needs separately
planned offline recovery. Existing scheduler/config/log behavior is unchanged.

## Version information

`APP_VERSION` is the single application version source. Every normal page's small
footer and Settings About read that value and the verified active database schema;
no template hardcodes versions. Footer stays in document flow, including workout
pages, and uses existing light/dark readable styling. Damaged storage displays
Unavailable rather than a guessed schema. `/health/ready` retains actual version
reporting. Semantic versions and SQLite schema integers are independent: feature
releases increment minor during 0.x, compatible fixes increment patch, and only
persistent schema changes increment the database version.

## Existing-installation upgrade

**Documentation for the operator after release approval/merge, not commands run
by this task.** The supplied installation paths are:

- Checkout: `/root/WorkoutTracker/app`
- Persistent root: `/root/WorkoutTracker/data/storage`
- Existing updater: `/root/WorkoutTracker/update_workout_tracker.sh`

The updater was not supplied and the server was not accessed, so its contents
cannot be certified. Do **not** run a schema-4-only updater unchanged. It must
recognize application 0.7.0 / schema 5, distinguish compatible updates from an
explicit upgrade, stop both writers, require confirmation before migration,
check every exit status, and restart only after verification. It must never run
initialization on existing storage, silently restore, rewrite schema markers,
delete preserved versions, or change `.env`, mounts, ownership, networking/ports.

Before maintenance, verify independent whole-tree recovery protection (SQLite
backups alone omit external settings, signing keys, schedules and preferences).
Stop external SQLite tools as well. Ensure free space for a complete candidate;
previous versions and backups are not automatically pruned. Keep the old image
and code commit. Close/reload browser forms after any selection switch.

Run each block only after the preceding one succeeds. First inspect:

```sh
cd /root/WorkoutTracker/app
git status --short
```

Stop if there are local changes; reconcile without discarding them. Then, only
after Phase 7 has been approved and merged into main:

```sh
(
  set -eu
  cd /root/WorkoutTracker/app
  test "$(git branch --show-current)" = main
  test -z "$(git status --porcelain)"
  git fetch origin
  git merge --ff-only origin/main
  docker compose config --quiet
  docker image tag workout-tracker:local "workout-tracker:before-schema5-$(date -u +%Y%m%dT%H%M%SZ)"
  docker compose build
  docker compose stop web scheduler
  docker compose run --rm --no-deps web python -m workout_tracker check-storage \
    --data-root /var/lib/workout-tracker
)
```

Expect schema **4** on the first upgrade (5 on later compatible updates).
Anything else or any error means stop and inspect; never create an empty
replacement. The host path must still be `/root/WorkoutTracker/data/storage` in
the existing private `.env`; Compose passes `/var/lib/workout-tracker` inside
containers. Do not change those mounts to a new directory. The compatibility
check does not itself upgrade a healthy schema 4.

**Schema 4 only:** run this deliberate, confirmed, one-time candidate migration:

```sh
(
  set -eu
  cd /root/WorkoutTracker/app
  docker compose run --rm --no-deps web python -m workout_tracker migrate-storage \
    --data-root /var/lib/workout-tracker --target-version 5 --confirm-upgrade
  docker compose run --rm --no-deps web python -m workout_tracker check-storage \
    --data-root /var/lib/workout-tracker
)
```

Expect `Schema 5 verified. New candidate activated; original preserved.` and
`Storage verified; schema version 5.` If already schema 5, skip that migration
block entirely for ordinary code updates. If migration fails, leave services
stopped, preserve candidates/logs and the original selection, and inspect the
error. Do not treat a failed migration as permission to start an empty dataset.

Only after schema 5 verification succeeds:

```sh
(
  set -eu
  cd /root/WorkoutTracker/app
  docker compose up -d --no-build
  docker compose ps
  docker compose exec -T web python -c \
    'import json,urllib.request; d=json.load(urllib.request.urlopen("http://127.0.0.1:8000/health/ready",timeout=10)); print(d); assert d==dict(status="ready",app_version="0.7.0",schema_version=5)'
)
```

If readiness fails, stop both services and inspect; do not initialize or restore
automatically. Check People/routines, resume drafts, history/corrections and
Settings/backup status without making test workouts in real data. Settings and
footer should show 0.7.0/schema 5. Optional backup after upgrade is a separate
explicit action, not a side effect of a compatible update.

The original schema-4 database remains byte-for-byte under `data/`, with its
old selection under `archives/`. Migration failure automatically retains/reverts
the original selection when possible; a double durability failure reports
uncertainty and requires inspection. **After successful activation, do not merely
start application 0.6.0 against schema 5.** An operator-reviewed offline rollback
must choose the retained original selection and compatible image together.
Workouts entered on schema 5 are not merged into the older file; preserve the
whole tree before any recovery. No unsafe automatic rollback script is supplied.

## Automated verification

Final complete run:

```sh
WORKOUT_CONTAINER_TESTS=1 /workspace/phase1-venv/bin/python -m pytest -q
```

**260 passed in 180.25 seconds; 0 failed, 0 skipped.** This includes 235
backend/storage/HTTP tests, 16 Chromium tests and 9 Docker tests. Fourteen tests
are new to Phase 7; existing test assertions are retained, with the required
Exercise Library label and app-version expectations updated. Container coverage
retains schema-4 installation/restart checks and adds a stopped-writer explicit
4 → 5 upgrade, unchanged original bytes, retained person data and schema-5 readiness.

New tests verify shared selection and IDs, distinct person results/recommendations/
charts, cross-routine matching, incompatible type/unit/meaning exclusion, named
independent ordered Weight/Time copies, partial-copy rollback, Unicode duplicate
prevention, cross-person rename/archive guards, complete populated schema-4 cell
preservation (copies, matching names, historical/native completions, NULL, zero,
audits and active drafts), trigger preservation, resumability, same-schema backup/
restore and older-schema restore refusal. Fault injection covers DDL, changed cells,
logical validation, atomic publication and post-publication durability rollback.
Direct older-source candidates, CLI confirmation/no-op, Settings/health/footer,
mobile widths and Auto/Light/Dark remain covered.

Additional checks passed: git diff --check, Python compilation, project Python
disclosure/function-docstring checks, edited documentation disclosure/shell syntax
checks and pip dependency consistency. Docker image builds succeeded using the
existing CA secret; no runtime dependencies or Compose networking changed.
All test databases and containers are disposable; no household storage is used.

## Remaining limitations

- Existing same-name definitions remain distinct IDs. No reconciliation/merge UI
  or history-ID rewrite is introduced. Archived definitions reserve names and
  have no reactivation UI; use a distinct name or deliberate future design.
- Library writes are household-global and passwordless, consistent with LAN-only
  access. Person selection remains navigation, not authentication.
- Legacy schemas 2–4 remain readable with old behavior; schema 5 is required for
  shared selection/copying. No automatic startup upgrade is performed.
- Registration provenance retains the old column name `person_id` for exact-value
  preservation; it is not used to scope schema-5 library reads or references.
- GitHub API access in this managed environment returned `Forbidden`; branch push
  uses Git independently. PR creation may require the supplied manual GitHub
  comparison link if that API restriction persists.
- Physical iPhone/Safari/VoiceOver, actual server/updater execution and live-data
  verification are outside the managed Chromium/container evidence.
- Prior backup/offsite, cooperative locking, durability uncertainty, no offline
  input queue and preferences-outside-SQLite-backup limitations still apply.

Stop after feature-branch push and pull-request creation; do not merge or deploy.
