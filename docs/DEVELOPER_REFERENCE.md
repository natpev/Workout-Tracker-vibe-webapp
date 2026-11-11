# Developer and historical implementation reference

SHAMELESSLY VIBE-CODED 🤖

This application was built with a healthy dose of AI, questionable amounts of confidence, and minimal human supervision. It appears to work, but don’t mistake that for a warranty. Use at your own risk, and keep backups.

This reference retains prior implementation evidence. Release-specific instructions below describe older releases. Use the current [README](../README.md) and [deployment guide](../deployment/README.md) for installation and updates.

## Current Phase 14 implementation

Application 0.14.0 targets schema 10. Read [schema and audit compatibility](SCHEMA_10.md)
and [Phase 14 review](../PHASE_14_REVIEW.md). Earlier implementation sections are
archived descriptions. Current users cannot change basis or create conversions.

## Architecture and data flow

- `workout_tracker/__init__.py`: Flask factory, configuration, readiness, safe errors and browser protections.
- `storage.py`: external-path validation, explicit first install, schema verification and per-transaction locking. Every database connection enables foreign keys.
- `schema.py`: exact schema-2 definitions; no performance tables.
- `workout_schema.py`: schema-3 session/entry snapshots, one-draft index and immutable-finalized-record triggers.
- `operations.py`, `maintenance.py`: private external settings/history and verified backup/restore candidates; schema upgrades remain in the separate migrator.
- `scheduler.py`: dedicated background CLI process, independent of Gunicorn/browser.
- `diagnostics.py`, `settings_views.py`: protected structured logs, safe paginated viewer and confirmed maintenance forms.
- `library_schema.py`: schema-5 global references and candidate-only table rebuilds, preserving every original cell and trigger.
- `history_schema.py`: additive schema-4 history, preparations, registry and append-only audit objects; no Phase 3 protection is removed.
- `history.py`, `history_views.py`: shared effective values, chronology/filters, chart preparation, historical completion and deliberate corrections.
- `migrations.py`, `combined_schema.py`: explicit candidate-only upgrades through schema 8, preserving every original row/NULL and verifying registry consistency.
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
.venv/bin/python -m workout_tracker migrate-storage --data-root "$WORKOUT_DATA_ROOT" --confirm-upgrade --target-version 8
.venv/bin/python -m workout_tracker check-storage --data-root "$WORKOUT_DATA_ROOT"
.venv/bin/gunicorn --bind 127.0.0.1:8000 --workers 1 --threads 2 'workout_tracker:create_app()'
```

These commands are for synthetic review data only, not deployment permission.
Stop the server with Ctrl+C. The readiness endpoint is `/health/ready`; verify
`status: ready`, app version `0.11.0`, and schema version `8`. Schema 1 still opens
the foundation shell; schema 2 supports existing management but not workout
recording. Schema 3 supports tracking but history/corrections need an explicit
target-4 upgrade. Startup never migrates these automatically. Stop workers before
explicit upgrade, then restart them to reload configuration/signing keys.
Missing/damaged/incompatible storage is an error, never permission to initialize
another database or replace an existing one.

## Phase 6 navigation and appearance

Open app → choose a person → choose a routine → Start workout. Existing people
precede Add person; their hamburger menus separate selection from management.
Routine cards start workouts directly; Edit routine and Manage routines remain
secondary. The compact header/selected-page pills replace crowded text links.

Active workouts have no unrestricted person-switch control. More contains jump,
overview, date/time/notes, **Exit Workout**, and confirmed Discard. Exit validates
and saves current input before returning to routines, preserving the draft for
Resume later. Finish/Discard also allow switching afterward. A per-tab marker
assists Back/reload navigation without locking other browser sessions; this is
workflow assistance, not authentication. Native unload warnings explain the risk
of leaving unacknowledged input; no offline/hard-close persistence is claimed.

Appearance now lives **only in Settings**. Auto/Light/Dark changes immediately and
persists for that browser. Choose **Person appearance** from a person’s menu (or
Settings while that person is selected) to save Blue, Teal, Green, Purple, Orange
or Red across devices. Dark backgrounds are neutral charcoal/navy; accents color
primary controls and progress. Person colors live in private external
`config/person-preferences.json`, default blue when absent. No SQLite schema or
migration change is required. Database backups do not include this file; protect
the whole external tree separately. A corrupted preference file is preserved;
read-only pages fall back to blue and writes report an error.

The repeated visible AI banner is removed from pages; mandatory disclosures remain
in this README, all developer notes and every supported source-file header.
Browser review images are in [docs/phase-6](phase-6). Tests save screenshots
under `/tmp/workout-ux-screenshots` by default; set `WORKOUT_UX_SCREENSHOTS` to an
absolute artifact directory when collecting review evidence. This variable does
not affect production containers.

## People, exercise names, and routines

Keep the approved user-switching interface: create/select people through the
People screen, without a redesigned selector or browser-style tabs; rename, archive or reactivate them there.
Archiving always retains their IDs and records. Each person has independent
routines and workout histories. Exercise definitions are shared globally on schemas 5–6.
On schema 6, confirmed routine deletion permanently removes its definition/settings
while retaining completed snapshots and global exercises. Active drafts block deletion.
Retained schemas 2–5 use their earlier archive behavior.

Within a routine, register a new global exercise or select an existing library ID.
Exercise Library renames definitions across everyone’s current routines, preserving
historical snapshot names. Copies reuse the original IDs but keep independent
targets/notes/order. On schema 6, the separate confirmed Permanently Delete Exercise
action erases that identity and its history across everyone; Remove From Routine
affects only that routine. Older schema-5 archive rules remain unchanged. Legacy
same-name definitions retain distinct IDs; new case-insensitive duplicate names
are rejected rather than merged. Existing archives can be permanently removed
on schema 6, but there is no exercise unarchive interface.

Choose Weight or Time in the segmented control. Both use positive-integer sets.
Weight configures reps and defaults to pounds; Time configures whole minutes and
seconds. Three sets × 45 seconds stores a target of 45 seconds, not 135. Switching
mode clears incompatible stored fields. Optional notes belong to the routine
configuration. Numeric inputs provide the approved simple set controls.

Configuration limits: sets 1–1000, reps 1–10000, target duration 1–359999 seconds
(normalized total; seconds may exceed 59); names 100 characters, notes 2000 and weight
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
durations either part may be blank and seconds may exceed 59: blank+120 → 02:00,
1+90 → 02:30, 2+blank → 02:00. Two blanks skip; negative, fractional, malformed
and zero-total performed durations are rejected. Actual
measurements are bounded by SQLite signed 64-bit integers; input strings are
limited to 100 characters. Previous values never prefill a new workout.

Use the routine's up/down controls to reorder routines or exercises. Duplicate
within a person or use Copy a routine to copy between people. Every copy gets
fresh routine/item identities and reuses global exercise IDs and independent settings, with no workout
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
selector and expandable overview (inside More) navigate without marking blank entries done.
Progress tracks the furthest acknowledged Next destination, including skipped exercises.
Typing/autosaving measurements or flags does not move it; Back/Jump do not add
progress, and revisits cannot count twice. Actual performed counts remain separate. Save draft
is available manually. With JavaScript, input automatically saves after a short
debounce. The compact ✓ Saved indicator, progress and overview change only on a valid
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

The hamburger menu opens History & Progress, with History | Progress tabs only
inside that area; both retain the person and original URLs. People menus also
provide direct history access. History lists completed native and historical sessions by
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
  data/schema-4-<identity>-<candidate>.sqlite3  # retained pre-library schema
  data/schema-5-<identity>-<candidate>.sqlite3  # retained shared-library schema
  data/schema-6-<identity>-<candidate>.sqlite3  # retained deletion-capable original
  data/schema-7-<identity>-<candidate>.sqlite3  # retained global defaults schema
  data/schema-8-<identity>-<candidate>.sqlite3  # current combined measurement schema
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
protocol. Known schema 1/2/3/4/5/6/7 can explicitly upgrade to 8; targets 2/3/4/5/6 remain
available for compatible tooling. Select `--target-version 8` for the current release.
The CLI keeps its target-3 default for backward compatibility; its programmatic
helper keeps the existing target-2 default for backward-compatible callers.

Migration opens the original read-only and creates a distinct candidate using
SQLite's backup API. DDL changes only the candidate. Checks cover application
identity, exact schema, integrity, foreign keys, schema/migration versions,
equality of every pre-existing table row including NULLs, new historical/audit
tables being empty, and original file hashes. The new registry must match exactly
the existing completed native sessions. Exact tables/indexes/triggers and
migration records are verified. Schema 5 changes only exercise FK constraints; all protection triggers are retained identically, and all original cell values remain unchanged.
The candidate and selection files are synced before atomic manifest replacement.
A post-switch sync failure attempts atomic restoration of the original selection;
if that also fails, the CLI reports uncertainty and requires inspection. No
original database is overwritten or removed. Previous versions stay in `data/`
and their selection manifests in `archives/`; failed candidates stay for diagnosis.

All eight supported schemas use rollback journals. WAL headers and any journal/WAL/SHM
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

## Development container checks

Installation variables, security settings and service commands are documented
in the [installation guide](../README.md#4-choose-your-address-and-time-zone) above. The checks below are for
contributors using disposable fixtures, not a second installation procedure.
Containers never initialize or migrate storage at startup.

For isolated image review, build `workout-tracker:phase8-review` with build secret
`pip_ca` set to a trusted system CA bundle. Managed cloud proxy/CA configuration
must be preserved. Run container tests only against the local Docker daemon:

```sh
docker build --secret id=pip_ca,src=/etc/ssl/certs/ca-certificates.crt -t workout-tracker:phase8-review .
WORKOUT_CONTAINER_TESTS=1 .venv/bin/python -m pytest -q
```

They use disposable fixtures, no network or published ports, and remove their
own containers. Browser tests need Chromium and optional pinned dependencies:

```sh
.venv/bin/python -m pip install -r requirements-browser.txt
.venv/bin/python -m pytest -q -k browser
```

Install Chromium or use `.venv/bin/python -m playwright install chromium`. Set
`WORKOUT_CHROMIUM` to its executable if needed. Browser tests need loopback socket
access. Without optional tools, their skipped status is distinct from a pass.

## Backups, restore, scheduling and logs

Open **Settings → Administration** from the hamburger menu. Database status, Backup Now, scheduling,
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
requires the same storage identity and exact selected schema (2–8), copies to a
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
[PHASE_5_REVIEW.md](../PHASE_5_REVIEW.md) for validation and remaining limits.


## Application and database versioning

The application uses semantic versions, currently **0.11.0**: major.minor.patch.
After 1.0, breaking public-contract changes increment major, compatible features
increment minor, and compatible fixes increment patch. During 0.x development,
feature releases increment minor and compatible fixes increment patch; any
breaking changes require explicit release notes. SQLite schema is
separate, currently **8**, and increments only when persistent structures change.
A code release does not automatically require a migration. Settings About and
the small document-flow footer read the running application version and verified
active DB schema; /health/ready reports the same source values.

### Existing /root/WorkoutTracker schema-4/5 installations

Use [deployment/README.md](../deployment/README.md#first-upgrade-from-schema-6) for
this release's explicit schema-8 upgrade and one-time passwordless host updater
installation. Do not use the historical Phase 7/schema-5 guide as the current
release target. Existing databases, root .env and original versions are preserved.
The app remains HTTP port 8000; read-only updater progress is private LAN port 8001.

### Machine-readable release target for Docker updaters

After building the new image, an updater can detect its release target without
mounting data, starting Flask, or triggering migration:

```sh
docker run --rm --network=none --read-only --entrypoint python \
  workout-tracker:local -m workout_tracker release-info
```

Expected JSON: `{"app_version": "0.11.0", "target_schema_version": 8}`.
The target is release metadata; `/health/ready` and Settings/footer report the
actual active schema instead. Parse JSON rather than scraping templates or the
foundation initialization constant. Stop writers and explicitly back up/verify
installed storage before updating; compare installed schema with this target,
request confirmation if an upgrade is needed, then run the separate migration.
Never infer consent from release detection or automatically initialize storage.
The actual available v3 was inspected; its schema-5 limit is incompatible with
this release. Use v4 and the operator sequence in deployment/README.md. The live
server copy was not accessed.


## Phase 8 — permanent deletion and LAN updates

The dedicated **Permanently Delete Exercise** preview shows the exact global ID,
affected people/routines/entries and requires typed DELETE (or exact name), an
acknowledgment and CSRF. It removes that ID and its recorded history for everyone,
retaining other measurements. Active drafts block deletion. Empty saved/discarded
workouts disappear; mixed workouts keep remaining entries and consistent audits.
A new definition gets a new ID, with no prior results. Older backups/database
versions remain and may restore deleted records on deliberate compatible recovery.

**Permanently Delete Routine** removes current definition/configuration, keeps all
global exercises and completed history, and blocks active drafts. **Remove From
Routine** still removes only one configuration. Older schema-5 archives remain
readable; full hard-delete behavior requires schema 6. Previously archived entries
are available for deliberate cleanup after upgrade. No deletion requires login.

The selected person/accent stays in a compact sticky header across management,
history/charts and Settings. Workouts also show the original routine name while
retaining existing save/exit/switch safeguards.

Settings → **Application Updates** checks fixed approved main, reviews version,
schema and notes, then confirms installation/migration. A separate host service
owns Docker/Git; the web container has no Docker socket. Control is a restricted
Unix socket with fixed actions and OS peer checks; independent progress is GET-
only HTTP bound to the configured private interface. There is no password/TLS
infrastructure. Network isolation and trusted-host/CSRF controls remain essential.

The executable [v4 updater](../deployment/update_workout_tracker_v4.sh) shares the
same host engine for emergency SSH use. It always verifies a backup for a confirmed
update, preserves old image/commit/database, uses the existing candidate migration,
privately recopies the authoritative parent .env into app/.env, and validates real
health/versions/scheduler. It never initializes or silently restores storage.
Exact **schema-5→6 and one-time host installation** commands are in
[deployment/README.md](../deployment/README.md). Do not use an old schema-5-only v3
script unchanged for this release. No service is installed at application startup.


## Phase 9 defaults, Administration and input rules

Settings contains personal appearance and an Administration entry point. The
compact Administration area groups updates, logs, versions, diagnostics, backup
settings/history and confirmed restore. Every application maintenance route
shares one currently allow-all boundary. Future authentication can be introduced
there after review; no login or unused account system is shipped today. Existing
CSRF, typed confirmations and updater source/command restrictions remain.

The hamburger menu offers Routines, Exercise Library, History & Progress and
Settings. Before choosing a person, scoped destinations return to People. There
are no global top tabs; only History & Progress shows its two tabs. Exercise
deletion and Cancel return to the refreshed Library; a successful committed
deletion shows a brief message. Routine deletion still retains completed history.

Schema 7 adds a separate exercise_defaults table, preserving all old cells,
NULL/zero measurements, snapshots, drafts and corrections. Existing exercises
receive neutral 3 sets × 12 reps, Weight/pounds, empty meaning/notes; no personal
routine is chosen as the global standard. Edit defaults in Library, then Add
library exercise to copy the preset into a routine once. Edit that routine for
independent overrides. Later default edits never propagate to existing routines,
and copied routines retain their actual configurations and global IDs. Pounds
remains the supported weight unit; there is no conversion feature.

The six existing color keys retain their exact soft palettes; six vibrant-* keys
add visibly saturated options. All 12 are independent per person and stored in
the same external preference file. Appearance stays separate from Administration.

Measurement labels are **Weight (lb)**, **Minutes**, **Seconds**. Historical forms
use named exercise groups for accessible context. Duration parts accept whole
nonnegative numbers in either/both fields and normalize to total seconds; targets
retain 359999-second limits, actuals retain the signed-64-bit limit, and two blank
actual fields remain SQL NULL. Saved duration displays use MM:SS; blank weight
and valid zero remain distinguishable and decimal weights still truncate.

Workout clocks use explicit **HH:mm** 24-hour text fields and displays. Internal
seconds/microseconds and IANA zones remain intact, including during measurement-
only corrections. Installation timezone remains America/Indiana/Indianapolis,
not a fixed UTC offset. Diagnostic timestamps may retain seconds in explicit
24-hour UTC; log date filters remain UTC. Original local SVG, ICO, 16/32 PNG and
180 PNG Apple touch icons are served without external requests or new runtime
dependencies. See static/icons/README.md for the original artwork/export details.

## Phase 10 historical entry, Progress and live updates

Historical Phase 10 targeted **0.10.0 / schema 7**. That release needed **no database migration for an existing schema-7 installation**. No exercise
identity or chart calculation changes are made; the separately reported duplicate/
orphaned exercise issue is explicitly untouched.

Historical entry/correction now keeps typed values on the same form after an
error. A red, linked summary appears immediately above Save, with accessible
field messages. Failed submissions save nothing; concurrent corrections show a
conflict and retain input. Existing snapshots, SQL NULL skips, valid zero and
append-only audit records remain protected. Optional workout time has an explicit
24-hour hour/minute picker; type **0930** and leave the field to get **09:30**, or
leave it blank when unknown. No AM/PM or seconds are displayed.

Progress starts with **30 Days** and offers 60/90 Days, 6/12 calendar Months,
All Time and Custom Range. The configured server IANA zone supplies today's date;
days include today and the prior N−1 dates. Months start one day after the clamped
calendar-month anniversary. Exercise/range choices survive History/Progress tabs,
refresh and Back. Invalid custom dates retain input and the last valid graph
where available. Hover, keyboard-focus or tap a graph dot for its date/measurement
and known time. Skipped measurements stay in the accessible data list, never as
zero-valued graph points.

**Install Update** opens the independent progress tab automatically, keeping the
app tab. Confirm installation and any required migration first. If a popup blocker
intervenes, use the displayed fallback link. Check for Updates opens no tab. Review
independent status before retrying a submission during an outage.

The independent host page now has a scrolling **sanitized live console** from real
Git/Docker/backup/verification/startup activity, plus status events. It stays online
while Flask restarts. Scroll up without losing your place, use Scroll to Latest,
refresh/reconnect, or select a retained operation. Only recognized safe messages
are shown: arbitrary command output, environment values, Compose config, secrets,
URLs and private logs are withheld. The newest 500 safe lines per operation and
20 operations are retained; detailed SSH logs and backups are not pruned by this
viewer. It is read-only, not a terminal. The trusted-LAN/no-password model remains.

**Existing Phase 9 host service needs a one-time explicit upgrade for live logs.**
Updating only the web image leaves the old separately copied runtime in place.
See [exact installed-server steps](../deployment/README.md#phase-10-existing-installation-upgrade)
and [PHASE_10_REVIEW.md](../PHASE_10_REVIEW.md) for implementation, tests and limits.
V4 remains the emergency script; no v5 script, deployment or startup migration is
introduced. Keep your existing Compose/.env and timezone settings.


## Patch 0.10.1 — routine selection order

The selected person's routine cards now show the most recently completed workout
first. Actual workout date is primary; live Finish timestamps and known historical
occurrence times resolve same-day ties. Corrections to occurrence date/time apply.
Equal timestamps and unknown times use alphabetical routine names; routines never
completed appear last, alphabetically. Names are compared without case, with the
exact name and permanent ID as deterministic fallbacks.

Only completed live/historical workouts count. Drafts, discarded workouts and
unfinished historical preparations do not. Each person and routine ID has an
independent history; copies do not inherit completion rank. Deleted/archived routine
definitions do not appear as cards. Card controls/layout and exercise ordering are
unchanged. This is a read-only server listing, not a rewrite of stored positions
or workout dates. Schema stays **7** and requires **no migration** for schema 7.

The existing browser updater/v4 supports this code-only patch. If already using
the Phase 10 host runtime, no additional host-service upgrade is required. Older
hosts still need the previously documented Phase 10 upgrade for live console logs.
See [patch review and tests](../PATCH_0_10_1_REVIEW.md).


## Patch 0.10.2 — viewport-safe hamburger menu

The hamburger dropdown stays inside the screen in portrait and landscape. It is
positioned relative to the full sticky header instead of the narrow button. With
a selected person it opens from the header's left edge; without a selection it
retains right alignment. Its width is capped by the header, with iPhone safe-area
insets reserved on both sides. All four navigation links and existing keyboard/
outside-click behavior remain. Person context, accents and themes are unchanged.

This is a CSS-only positioning fix plus the patch-version update. Schema is still
7; no database migration, server configuration or host-updater upgrade is needed
when already using Phase 10. The existing browser updater/v4 can install it. See
[MENU_POSITION_REVIEW.md](../MENU_POSITION_REVIEW.md) for the measured cause, viewport
coverage, full-suite results and limits.


## Patch 0.10.3 — rightmost navigation and routine activity dates

The hamburger stays at the far right of one compact sticky header row. Branding
is unchanged; the selected person's accent and name use the remaining space. Long
names truncate with an ellipsis and retain the full name in a title/accessibility
text instead of moving or wrapping the button. Header and dropdown reserve iPhone
safe-area insets; the menu opens to the right below the header with all four links.
Existing keyboard, focus and outside-click behavior is unchanged. Focused active
workouts keep their existing restricted header rather than gaining global navigation.

Routine cards show **Last completed: November 6, 2026**, or **Never completed**, in
a compact muted row below the name/actions. The exact completed-workout record
used by sorting supplies its ISO date and English label. Live and historical dates,
corrections, person ownership, unique routine IDs and independent copies follow the
existing rules. Drafts/discards/unfinished preparations do not count; deleted
definitions stay absent. No new history query or stored completion field is added.
The full-width date row avoids a tall narrow column beside Start Workout.

Application **0.10.3**, schema **7 unchanged**. Use the existing browser updater or
v4; no migration or additional host upgrade is needed on a Phase 10 installation.
[Review and test evidence](../HEADER_ROUTINE_DATES_REVIEW.md).


## Patch 0.10.4 — workout navigation and selected CSV export

The workout bar now follows **Next**, not populated measurements. It retains the
furthest Next destination across Back, revisits, refresh and resume, using the
existing saved cursor without migration. Jump changes the viewed exercise, not
the bar; Next from that view sets the following destination as a checkpoint.
Measurement/flag autosaves retain their existing validation and save status.
Resume opens the saved checkpoint; Save draft keeps the current viewed page.
Skipped exercises still save true SQL NULL, and entirely skipped completion still
requires confirmation. JavaScript provides acknowledged Next tracking.

Exercise forms now explain whether settings apply to this routine only or are
Library defaults copied into newly added routine exercises. These notes do not
change the existing independent settings or historical snapshots.

On **Progress**, choose a date preset/custom range, open **CSV export — choose
exercises**, check one or more exercises (or Select All), then **Export CSV**.
The export chooser is independent of the single exercise chart filter. Choices
persist through range changes and validation errors. No selection/no matching
workouts shows a helpful message. Export downloads locally, without cloud services
or changes to application data. The existing browser updater/v4 supports 0.10.4
with schema 7; no migration or new host upgrade is required after Phase 10.

The CSV is a wide paper-style sheet: **Date, Time, Routine, Workout ID**, then two
adjacent columns per selected exercise: **Weight (lb)** + **Sets × Reps**, or
**Duration** + **Sets × Target Duration**. Each row is a completed workout, oldest
first; same-date workouts stay separate. Dates/times and actuals use latest
effective corrections and historical occurrence, not entry time. Sets/reps/duration
targets are snapshots of the prescription, not actual per-set repetition records.
Missing exercises have both cells blank; skipped actuals are blank with their
prescription retained. Valid zero is 0. Decimal weights retain exact tenths; time
values use total **m:ss** (e.g. 0:45, 61:05), never multiplied by sets.

Distinct IDs with matching names have ID-labeled headers. Weight/Time and incompatible
weight meanings stay separate; repeated instances get occurrence-number columns.
UTF-8 BOM, normal CSV quoting and CRLF support Excel/Numbers/Sheets import. Formula-
like text is prefixed with an apostrophe for safety; commas/quotes are escaped.
The first row is always the header, with no decorative rows. See
[PROGRESS_CSV_REVIEW.md](../PROGRESS_CSV_REVIEW.md) for detailed tests and limitations.

Selected exercises absent throughout a range still retain blank column pairs, using their historical configurations for headings; no out-of-range data rows are added.


## Phase 11 — combined Weight + Duration (0.11.0 / schema 8)

Choose **Weight + Duration** in Library defaults or routine settings for any
exercise needing both resistance and time (for example a weighted plank or carry).
Configure sets, target duration per set, pounds, optional weight meaning (such as
per hand or total weight), and notes. There is no fixed target-weight field.
Library defaults copy once when added; existing routines remain independent.

One exercise screen records one actual weight and one actual duration, regardless
of set count. Both start blank. Both blank means skipped: both SQL measurements
and the increase flag remain NULL. A performed entry requires both values; a
partial pair shows field errors and cannot be saved or navigated away as Saved.
Zero pounds is valid, duration must be positive, either duration part can be blank,
and seconds above 59 normalize. Weight truncates to integer tenths as before.
Only **Increase weight next time** is offered, entirely manual even below target.
Previous performance shows both actuals and the previous weight recommendation.
The Next-only progress checkpoint and revision-checked autosave remain unchanged.

History, summaries and append-only corrections show both values and preserve
original snapshots/audits. Progress groups two separate local charts under the
exercise heading: pounds and seconds labeled m:ss. Targets come from each snapshot;
a dashed duration reference appears only when the range has one common target.
Varying targets remain in each point tooltip/data row, never one misleading line.
Existing filters, NULL exclusions, zero, person/ID/meaning isolation remain.

CSV keeps the existing first four columns and wide layout. Combined exercises
have three adjacent columns: **Weight (lb), Duration, Sets × Target Duration**.
Durations use total m:ss; prescriptions are historical targets. Skipped actuals
are both blank; absent exercises have all three cells blank. Ordinary Weight/Time
exports, quoting, formula protection and effective corrected values are unchanged.

**Existing schema 7 requires explicit candidate-only upgrade to 8.** Use the
existing browser updater, review 0.11.0/schema 8, confirm migration and Install.
Or use the existing v4 script over SSH; see the exact installed-server commands in
[deployment/README.md#phase-11-schema-7-to-8-upgrade](../deployment/README.md#phase-11-schema-7-to-8-upgrade).
No new updater, Compose/.env changes or Phase-11 host-service upgrade is required
for an already working Phase 10 updater. Startup never migrates. Original schema-7
files remain unchanged; schema-7 backups stay retained but cannot restore over
schema 8. Make new verified schema-8 backups after upgrading. Do not initialize or
restore to force an update. See [PHASE_11_REVIEW.md](../PHASE_11_REVIEW.md) for migration,
tests, recovery and limitations. Earlier patch sections are historical records.
