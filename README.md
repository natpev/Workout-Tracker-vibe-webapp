# Workout Tracker

> **SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.** Human-directed AI-generated software; not audited or approved for production.

Phases 1–5 are completed and approved for main. Phase 5 adds Settings, verified server-side
backups, deliberate candidate restores, a dedicated scheduler and persistent
filtered logs. Phase 6 (installation, real-world testing and final polish) is next
and requires separate authorization. No deployment, real
workout data, cloud synchronization, internet exposure or authentication is authorized.

Read [AGENTS.md](AGENTS.md), [PROJECT_SPEC.md](PROJECT_SPEC.md), and
[MEASUREMENT_DESIGN.md](MEASUREMENT_DESIGN.md). Current implementation evidence
and limitations are in [PHASE_5_REVIEW.md](PHASE_5_REVIEW.md).
[PHASE_4_REVIEW.md](PHASE_4_REVIEW.md) retains the approved history/correction record.
[PHASE_3_REVIEW.md](PHASE_3_REVIEW.md) retains the prior implementation evidence.
[PHASE_2_REVIEW.md](PHASE_2_REVIEW.md) and the earlier
[PHASE_1_REVIEW.md](PHASE_1_REVIEW.md) are retained as historical records.

## Architecture and data flow

- `workout_tracker/__init__.py`: Flask factory, configuration, readiness, safe errors and browser protections.
- `storage.py`: external-path validation, explicit first install, schema verification and per-transaction locking. Every database connection enables foreign keys.
- `schema.py`: exact schema-2 definitions; no performance tables.
- `workout_schema.py`: schema-3 session/entry snapshots, one-draft index and immutable-finalized-record triggers.
- `operations.py`, `maintenance.py`: private external settings/history and verified backup/restore candidates; no schema-5 migration.
- `scheduler.py`: dedicated background CLI process, independent of Gunicorn/browser.
- `diagnostics.py`, `settings_views.py`: protected structured logs, safe paginated viewer and confirmed maintenance forms.
- `history_schema.py`: additive schema-4 history, preparations, registry and append-only audit objects; no Phase 3 protection is removed.
- `history.py`, `history_views.py`: shared effective values, chronology/filters, chart preparation, historical completion and deliberate corrections.
- `migrations.py`: explicit candidate-only upgrade from known schema 1/2/3 to target 2/3/4, preserving every original row/NULL and verifying registry consistency.
- `workouts.py`, `workout_views.py`, `static/workout.js`: exact measurements, server drafts, serialized autosave, revision conflicts and atomic finalization.
- `catalog.py`: parameterized SQL and rules for people, identities, ordering, typed targets, and independent copies.
- `views.py`: CSRF-protected forms, ownership checks and stale-routine conflict detection.
- `__main__.py`: operator initialization, verification and migration commands.
- `templates/` and `static/`: server-rendered HTML, local responsive CSS, native segmented radios, and browser-local Auto/Light/Dark themes. No CDN or analytics.
- `tests/`: temporary fixtures only; never point tests at household storage.

Browser → Flask CSRF/ownership validation → catalog service → locked SQLite
transaction → redirect to refreshed page. A failed operation rolls back as a
whole. User selection is instant navigation, **not authentication**: anyone who
can reach this passwordless household app can choose another person.

## Local development with disposable storage

Requires Linux, Python 3.12+, local POSIX storage supporting SQLite, flock, hard
links and directory syncing, and SQLite 3.37+ for STRICT tables. Dependencies and
the Docker base-image digest are pinned. Phase 4 adds no third-party dependencies or external chart resources; timezone handling uses Python zoneinfo.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q tests/test_foundation.py tests/test_migrations.py tests/test_catalog.py tests/test_management.py tests/test_workouts.py tests/test_workout_http.py tests/test_history.py tests/test_history_http.py
```

For a **disposable local review**, explicitly create a new, nonexistent external
path. Initialization refuses every existing directory, including empty ones.
It creates schema 1 first; a separate explicit command copies/upgrades it.

```sh
export WORKOUT_DATA_ROOT="$(mktemp -d)/review-storage"
.venv/bin/python -m workout_tracker init-storage --data-root "$WORKOUT_DATA_ROOT" --confirm-new-storage
.venv/bin/python -m workout_tracker check-storage --data-root "$WORKOUT_DATA_ROOT"
.venv/bin/python -m workout_tracker migrate-storage --data-root "$WORKOUT_DATA_ROOT" --confirm-upgrade --target-version 4
.venv/bin/python -m workout_tracker check-storage --data-root "$WORKOUT_DATA_ROOT"
.venv/bin/gunicorn --bind 127.0.0.1:8000 --workers 1 --threads 2 'workout_tracker:create_app()'
```

These commands are for synthetic review data only, not deployment permission.
Stop the server with Ctrl+C. The readiness endpoint is `/health/ready`; verify
`status: ready`, app version `0.5.0`, and schema version `4`. Schema 1 still opens
the foundation shell; schema 2 supports existing management but not workout
recording. Schema 3 supports tracking but history/corrections need an explicit
target-4 upgrade. Startup never migrates these automatically. Stop workers before
explicit upgrade, then restart them to reload configuration/signing keys.
Missing/damaged/incompatible storage is an error, never permission to initialize
another database or replace an existing one.

## People, exercise names, and routines

Keep the approved user-switching interface: create/select people through the
People screen, without a redesigned selector or browser-style tabs; rename, archive or reactivate them there.
Archiving always retains their IDs and records. Each person has independent
routines and exercise definitions. Routine Delete removes it from active lists
by archiving, preserving its identity; it does not delete exercise definitions.

Within a routine, create a new exercise name or reuse one owned by that person.
The Exercise names page renames a permanent definition wherever that identity is
reused; independent copied definitions are unaffected. Remove a definition from
active routines before archiving it. There is no exercise-archive restore UI yet.

Choose Weight or Time in the segmented control. Both use positive-integer sets.
Weight configures reps and defaults to pounds; Time configures whole minutes and
seconds. Three sets × 45 seconds stores a target of 45 seconds, not 135. Switching
mode clears incompatible stored fields. Optional notes belong to the routine
configuration. Numeric inputs provide the approved simple set controls.

Configuration limits: sets 1–1000, reps 1–10000, target duration 1–359999 seconds
(0–5999 minutes, 0–59 seconds); names 100 characters, notes 2000 and weight
meaning 200. These are configuration bounds. Schema 3 adds separate actual
measurement/flag columns without altering retained schema-2 files.

Phase 3 stores pounds as **integer tenths**, truncate additional decimal
digits **without rounding**, and display one decimal place: 40.99 → 40.9
(stored 409), 42.56 → 42.5 (425), 40 → 40.0 (400). Explicit zero is valid
(stored 0); empty weight is SQL NULL. Actual time is one duration per exercise
regardless of set count, stored as integer seconds with minimum 1; zero is
invalid and empty is SQL NULL. Every skipped exercise retains a saved entry
with NULL measurements, never zero or prior results. Historical snapshots
preserve tracking type and measurements even after routine edits. For performed
durations both minute and second parts are required (use explicit 0 minutes);
partial, negative, fractional or malformed values show a validation error. Actual
measurements are bounded by SQLite signed 64-bit integers; input strings are
limited to 100 characters. Previous values never prefill a new workout.

Use the routine's up/down controls to reorder routines or exercises. Duplicate
within a person or use Copy a routine to copy between people. Every copy gets
fresh routine/item/exercise identities and independent settings, with no workout
history, results or increase state. Routine edit forms reject stale submissions
with 409; reload before retrying if another page has changed the routine.

## Start, save, resume, finish, and discard

Choose a person through People, open their routine, and choose Start workout.
An empty routine must first get exercises. Starting copies every configuration
into a separate snapshot with blank actual values and records the local date,
UTC timestamp and configured IANA zone. Only one active draft is allowed per
person; another start offers Resume or explicit Discard, never replacement.
Routine editing/removal cannot change this draft or a completed snapshot.

One exercise appears at a time with target sets/reps or duration, optional notes,
previous comparable performance and increase recommendation. If the previous
session skipped it, the last performed result is shown separately. Comparisons
require the same person, permanent exercise identity, measurement type and
unit/weight meaning. Drafts/discarded workouts are excluded from comparisons.

Enter one measurement per exercise, independent of sets. Back/Next, the jump
selector and expandable overview navigate without marking blank entries done.
Progress counts non-NULL actual values; explicit zero pounds counts. Save draft
is available manually. With JavaScript, input automatically saves after a short
debounce. The Saved indicator, progress and overview change only on a valid
post-commit acknowledgment. Values typed during a pending save are preserved and
sent next; saved weights are normalized to one decimal place.

Navigation and Finish wait for pending saves. Validation/network errors leave
input visible and preserve earlier committed values. A stale tab receives a
conflict and cannot overwrite newer data; copy any unsaved text before reloading.
An acknowledgment can be lost after the server committed: reload to inspect the
persisted result rather than assuming a failed response means no commit.
Server-confirmed drafts survive refresh, browser closure and application/container
restart. Closing/force-killing a browser before acknowledgment cannot guarantee
unsaved input persistence; a before-unload warning is provided. There is no
offline client queue. Without JavaScript, use Save draft before navigating;
autosave, jump interaction and the acknowledgment-gated discard UI require JS.

Finish & Save validates current input again and commits the whole snapshot and
completion status atomically. Skips keep their rows with SQL NULL values. An
entirely skipped workout needs the additional confirmation checkbox. Repeated
Finish requests return the same saved session without duplicate completion.
The completion page shows this single saved workout; it is not a history browser.

Discard Workout opens “Are you sure?” with an explicit warning and acknowledgment
checkbox. OK stays disabled until checked. Cancel/Escape preserve the draft.
Confirmed discard changes only that unfinished session's status, retains its
snapshot, and never deletes completed history. Completed/discarded snapshots are
immutable as original records. Schema-4 correction workflows append effective
actual/date/time revisions rather than updating these snapshots.

## History, progress and historical entry

Each person's navigation has History and Progress charts links, also reachable
directly from People. History lists completed native and historical sessions by
actual effective workout date/time, newest first. Active/discarded drafts are
excluded. Filter by inclusive date range, original routine identity or permanent
exercise identity. Saved detail shows every original prescription in original
order, notes, actual values, skips and increase flags. Renaming/archiving/removing
routine definitions does not change history or remove its filter choices.

Progress charts are locally rendered SVG with accessible data lists and no CDN,
third-party services or new dependencies. Each permanent exercise/type/unit/
weight-meaning combination gets its own series, so pounds never mix with seconds
or incompatible weight meanings. NULL is excluded from numeric plotting; zero
pounds remains a plotted result. Durations are raw seconds labeled minutes:seconds
and never multiplied by sets. Statistics mean highest logged weight/longest
logged duration **within the selected range**. They are not inferred strength or
other performance claims. The expandable data list retains skipped rows.

Enter historical workout from History, choose a routine and its past date and
optional time, then review copied prescriptions and fill measurements before
Save. To recreate a different old prescription, create or duplicate/configure a
separate routine first in the existing routine editor. Preparation freezes its
snapshot, so later routine edits do not change the review form. Historical
completion uses separate tables and a unique preparation token, never a live
draft. Repeated submissions return the same saved workout and do not overwrite
measurements. All-skipped completion needs explicit confirmation. Historical
form measurements are saved atomically on submission, not live-autosaved.

Occurrence is separate from when entered into the system. Unknown time remains
NULL and is labeled Time unknown; no midnight timestamp is invented. Within one
date unknown-time records sort before known-time records, with entry-time/ID
as deterministic tiebreaks. DST gaps are rejected; repeated-hour times require
an earlier/later choice. Future occurrence values are rejected. Backdated entry
and effective date corrections affect charts and previous-performance lookups,
which use occurrence chronology rather than entry/correction time.

## Correcting a saved workout and the audit

Open a saved workout and choose Correct saved workout. Change actual values,
increase flags and/or actual date/optional time, then explicitly acknowledge the
correction. Names, identities, order, tracking type, targets, units/meaning and
notes remain immutable snapshots. The application appends full before/after
actual-value states, occurrence, correction timestamp and sequence; it never
updates the original completed rows or disables the Phase 3 protection triggers.
An all-skipped corrected workout also needs skipped-workout confirmation.

History, chart statistics, saved confirmation and previous-performance reads all
use the latest effective correction. Original saved values and every correction
remain visible in the audit. Two stale forms cannot overwrite each other: a
revision conflict returns 409 and requires reloading. This is a shared-household
audit without authenticated author attribution, consistent with passwordless
People selection. No completed-workout deletion is offered.

## Storage and explicit migration safety

```text
external-storage/
  data/schema-1-<identity>.sqlite3              # unchanged original
  data/schema-2-<identity>-<candidate>.sqlite3  # retained Phase 2 original
  data/schema-3-<identity>-<candidate>.sqlite3  # retained original workout schema
  data/schema-4-<identity>-<candidate>.sqlite3  # current history/correction schema
  config/active.json                          # active database selection
  config/session.key                         # private session signing material
  archives/selection-before-<candidate>.json   # original selection
  backups/<UTC-timestamp>-<id>.sqlite3         # verified copies and retained failed evidence
  config/operations.json                     # settings, backup history, restore attempts
  logs/events-YYYY-MM-DD.jsonl                # protected structured UTC logs
```

The CLI takes the same persistent-root lock used by all app connections. It
refuses maintenance while a request holds a connection; stop workers and all
external SQLite tools before migration. External tools do not follow our lock
protocol. Known schema 1/2/3 can explicitly upgrade to 4; targets 2/3 remain
available for compatible tooling. Select `--target-version 4` for this phase.
The CLI keeps its target-3 default for backward compatibility; its programmatic
helper keeps the existing target-2 default for backward-compatible callers.

Migration opens the original read-only and creates a distinct candidate using
SQLite's backup API. DDL changes only the candidate. Checks cover application
identity, exact schema, integrity, foreign keys, schema/migration versions,
equality of every pre-existing table row including NULLs, new historical/audit
tables being empty, and original file hashes. The new registry must match exactly
the existing completed native sessions. Exact tables/indexes/triggers and
migration records are verified; all original Phase 3 protection DDL is retained.
The candidate and selection files are synced before atomic manifest replacement.
A post-switch sync failure attempts atomic restoration of the original selection;
if that also fails, the CLI reports uncertainty and requires inspection. No
original database is overwritten or removed. Previous versions stay in `data/`
and their selection manifests in `archives/`; failed candidates stay for diagnosis.

All four supported schemas use rollback journals. WAL headers and any journal/WAL/SHM
sidecars are refused **before** SQLite opens a source; there is no implicit
recovery. Unknown, damaged, missing, symlinked or incompatible storage never
becomes an empty replacement. A migration request matching the selected schema version is a
read-only no-op. Ordinary compatible application updates just replace code/image
and never trigger a copy, migration, or backup.

Keep the generated `config/session.key` private (0600); explicit migration
provisions it and startup only reads it. It signs CSRF session cookies, not user
passwords. Losing it blocks normal configured startup rather than silently
replacing it. An operator may supply private `WORKOUT_SECRET_KEY` explicitly
instead; never commit key values or use a shared example key. Cookies are
HttpOnly/SameSite=Lax; Secure is not enabled for the current loopback HTTP review.

## Configuration and container review

| Setting | Purpose |
| --- | --- |
| `WORKOUT_DATA_ROOT` | Required absolute storage directory outside the checkout; no implicit default. |
| `WORKOUT_TRUSTED_HOSTS` | Accepted hostnames, default `localhost,127.0.0.1,[::1]`; host-header validation, not authentication. |
| `WORKOUT_SECRET_KEY` | Optional private operator-provided signing key; otherwise use the explicitly provisioned private file. |
| `WORKOUT_TIMEZONE` | Installed IANA server-local zone for workout dates; defaults to server local, then UTC. Compose defaults explicitly to Etc/UTC; set your intended household zone before review. |
| `WORKOUT_PORT` | Compose host port, default 8000, loopback only. |
| `WORKOUT_UID`, `WORKOUT_GID` | Compose process identity; match the owner of private storage. Defaults 10001. |
| `WORKOUT_BUILD_CA_BUNDLE` | Build CA bundle, default system bundle. Keep TLS verification enabled. |

The image uses a non-root process. Compose keeps its root filesystem read-only
but its **external storage mount writable** for definition and workout transactions. It
refuses to create a missing host mount, drops capabilities, and publishes loopback
only. Storage/key permissions must allow the configured UID/GID; do not make
private storage world-readable to fix ownership. No live home-server deployment
is authorized. Containers never initialize or migrate storage at startup.

For isolated image review, build `workout-tracker:phase5-review` with build secret
`pip_ca` set to a trusted system CA bundle. Managed cloud proxy/CA configuration
must be preserved. Run container tests only against the local Docker daemon:

```sh
docker build --secret id=pip_ca,src=/etc/ssl/certs/ca-certificates.crt -t workout-tracker:phase5-review .
WORKOUT_CONTAINER_TESTS=1 .venv/bin/python -m pytest -q tests/test_container.py
```

They use disposable fixtures, no network or published ports, and remove their
own containers. Browser tests need Chromium and optional pinned dependencies:

```sh
.venv/bin/python -m pip install -r requirements-browser.txt
.venv/bin/python -m pytest -q tests/test_browser.py tests/test_workout_browser.py tests/test_history_browser.py tests/test_settings_browser.py
```

Install Chromium or use `.venv/bin/python -m playwright install chromium`. Set
`WORKOUT_CHROMIUM` to its executable if needed. Browser tests need loopback socket
access. Without optional tools, their skipped status is distinct from a pass.

## Backups, restore, scheduling and logs

Open **Settings** from the main header. Database status, Backup Now, scheduling,
backup history/details, restore audit and Logs are available without changing
People-screen switching. The history links retain all prior functionality.

**Backup Now** makes a uniquely named SQLite backup-API copy in external
`backups/`, verifies integrity, foreign keys, application/storage identity, exact
schema, complete snapshot/order/registry/audit consistency, and every original
row/NULL/zero before showing Verified. Size, source, schema, SHA-256 and timestamps
are recorded in private `config/operations.json`. It never downloads a file.
The button waits for completion; retrying the same form reuses its operation ID.
A new form is a new intentional backup. Failed/interrupted attempts stay visible
and their files remain unverified evidence. No backups are rotated automatically.
Inspect a backup to deliberately delete its file with checkbox confirmation;
its metadata remains in history. These are SQLite data backups, not bundles of
signing keys, schedule settings or diagnostic files: protect the whole external
tree separately with host/offsite backups.

**Automatic backups are disabled by default.** Settings requires an explicit
enable, whole-day frequency (1–3650, default 1), HH:MM time (default 02:00), IANA
zone (default Etc/UTC) and log retention (1–36500 days, default 30). The schedule
zone is independent of workout-entry zone: choose it explicitly. Changes take
effect on the next 30-second scheduler check and schedule the next future slot.
Day cadence is anchored to the local configuration date, not 24-hour intervals.
Repeated times run at the earlier occurrence only; skipped times advance to the
first valid minute after the gap. A late restart handles at most one missed run,
then advances beyond the current time without replaying the backlog. Failures
are recorded, not immediately retried; the next scheduled slot can try again.
Settings shows last automatic attempt/success/result and next UTC scheduled time.

Compose now defines separate **web** and **scheduler** services using the same
image, external bind mount and UID/GID. The scheduler runs
`python -m workout_tracker scheduler`, with no ports or network and restart policy
`unless-stopped`; Gunicorn workers never start schedulers. Persisted claims and
the root-directory OS lock prevent overlapping/duplicate jobs across processes
and restarts. `scheduler --once --data-root /absolute/disposable/storage` performs
one due check for diagnostics. No new environment variables are required: the
scheduler uses `WORKOUT_DATA_ROOT`; `WORKOUT_UID/GID`, CA build secret and web
variables above remain in effect. No services have been deployed by this task. The image sets a 300-second web
worker timeout for synchronous maintenance; exceptionally large operations can
still exceed it and need operator inspection after an interruption.

**Restore Backup** requires a checkbox plus typing RESTORE. It warns that later
workouts/corrections are not merged. The service rechecks the selected backup,
requires the same storage identity and exact selected schema (2–4), copies to a
unique candidate, compares all values and audits, syncs it, retains the original
file/selection, then atomically selects the verified candidate. Original and
backup files are never overwritten. Failure before activation keeps the original;
a post-activation sync or result-metadata failure attempts atomic rollback.
If rollback durability also fails, the result is Uncertain: stop writers and
inspect retained files/manifests before doing anything else. Reusing an attempt
ID never runs restore twice. Forms opened before a restore are rejected; reload
other browser tabs before editing. Existing requests serialize with maintenance,
so saves cannot target a partially prepared candidate. Full verification can
pause other requests; this is conservative household maintenance, not zero downtime.

Older-schema backups are not migrated/downgraded by Restore. Keep them for a
separately reviewed offline recovery; never edit their version marker. A missing,
foreign/newer, symlinked or sidecar-bearing active file/manifest is refused.
A present damaged file with a valid selection can be preserved during explicit
recovery. Normal startup still refuses damaged storage and never restores,
initializes, migrates or replaces it automatically.

If a running worker detects corruption, Settings can still show backup history.
If corruption prevents startup, stop **both** web and scheduler and all external
SQLite tools, preserve the whole tree, then use the same explicit recovery service
from an operator shell with the configured storage owner:

```sh
python -m workout_tracker list-backups --data-root /absolute/disposable/storage
python -c 'from uuid import uuid4; print(uuid4().hex)'  # new operation identifier
python -m workout_tracker restore-backup --data-root /absolute/disposable/storage \
  --backup-id LISTED_VERIFIED_ID --operation-id NEW_32_HEX_ID --confirm-restore
python -m workout_tracker check-storage --data-root /absolute/disposable/storage
```

Use only disposable storage for rehearsals. Restart workers/reload forms after
successful verification. If an attempt remains In progress after process loss,
do not replay it: inspect `operations.json`, protected logs, candidate and archived
selection with writers stopped. The scheduler labels interrupted backup attempts
failed on its next cycle; interrupted restores require operator inspection.
No automatic reconciliation guesses which selection an interrupted restore used.
If metadata is damaged, preserve it and seek operator review; it is never replaced
with defaults. A missing signing key still requires explicit operator recovery;
restoring SQLite does not invent a replacement key.

**Logs** are private daily JSONL files under external `logs/`, with structured UTC
time, severity, category and event IDs. The viewer supports newest-first text,
severity/category/date filters, Refresh, 50-entry pages and expandable safe error
details. Private paths/stack frames stay in protected server files; raw form bodies,
keys/cookies/tokens and database values are not logged. Exception messages/locals
are omitted from private traces; fixed safe messages, exception type and bounded
frames provide diagnostics. Log failures warn on stderr and do not undo a workout
commit. Ordinary startup/shutdown and failures append diagnostics, but compatible
updates never copy/migrate/back up the workout database. Abrupt SIGKILL cannot
write a shutdown event. Retention runs on Settings save and scheduler cycles;
only named UTC log files older than the retention window are removed. Disable
backups independently; keep the scheduler running for automatic log cleanup.

Local backups do **not** protect against complete server/storage failure or
replace Proxmox/offsite backups. There is no cloud backup/synchronization,
remote authentication or public exposure in this phase. See
[PHASE_5_REVIEW.md](PHASE_5_REVIEW.md) for validation and remaining limits.
