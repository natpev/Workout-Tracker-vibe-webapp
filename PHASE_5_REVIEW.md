# Phase 5 review — backups, restore, scheduling and logs

> **SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.** Human-directed AI-generated software, not independently audited or deployed.

## Scope and review boundary

Branch `phase-5-backups-logs` starts from fetched approved main
`ad20d08eb3de40e2f8f05c7649bb92d8ececc957`, which contains Phases 1–4.
Phase 5 was reviewed and approved on November 6, 2026. The authorized completion
workflow updates approval documentation, runs the full regression suite,
fast-forwards main, verifies remote containment and then deletes the fully merged
feature branch. Phases 1–5 are completed and approved. Phase 6 (installation,
real-world testing and final polish) is next but requires separate authorization.
No real household storage, deployment, cloud backups/synchronization, public
exposure or authentication is included.
People switching, typed measurements, history/charts, permanent snapshots,
append-only corrections and original protection triggers remain intact.

The service increment is `aad9d7c`; `6d762bb` adds Settings/CLI integration,
expanded preservation checks and browser/container regressions. Final documentation
is a separate reviewable commit. No workout schema change is needed: schema 4
is unchanged. Operations metadata version 1 is an external JSON format, not a
SQLite schema migration. No original database receives new tables or triggers.

## Implemented controls and data flow

Header → Settings displays selected schema/status, Backup Now, scheduling and
retention controls, backup history/details, restore audit and Logs. Phone-first
cards/controls and existing Auto/Light/Dark themes are retained. Backup tables
scroll within their card instead of widening a phone page. Mutating forms use
CSRF; restore additionally requires acknowledgment and typed RESTORE. Backup
deletion requires explicit confirmation and keeps metadata after removing its
file. No backup download or automatic backup deletion/rotation is introduced.

Flask → maintenance service → storage-root OS lock → external attempt journal →
SQLite backup API → isolated verification → durable result. Only IDs select
server-controlled files. Timestamp/UUID names, exclusive file creation and 0600
permissions prevent overwrite. Read-only source connections and source byte/hash
checks preserve original contents. Each backup form has an idempotency token;
retries return its existing result. A newly loaded form intentionally creates a
new operation. Intent records precede work, so interruption never produces a
verified success or an automatically repeated job. Partial files are retained.

## Validation and restore safety

Verification reuses application ID/storage identity, exact known schema DDL,
integrity, foreign keys, version/migration records and rollback-journal checks.
It additionally validates ordered complete snapshots, preparation JSON ownership/
typed prescriptions, equality between historical preparation and original saved
prescriptions, exact completed registry membership, and every sequential correction
before/after chain. Source/copy comparison streams all table cells in stable
primary-key order, preserving NULLs, explicit zeros and audit JSON exactly.

Restore selects a verified listed backup, rechecks its hash/size and all structural/
logical checks, requires matching storage identity and current exact schema 2–4,
and creates a separate unique database candidate through SQLite backup API. It
never silently upgrades/downgrades a backup. Candidate validation and exact value
comparison precede activation. The original active database remains at its original
filename unchanged; the old selection is hard-linked into archives. Candidate and
manifest are synced before atomic selection. Post-switch directory-sync failure
rolls back selection. Result-metadata failure after activation also attempts
rollback. If rollback durability itself fails, outcome is explicitly Uncertain:
stop writers and inspect the retained evidence; never report success.

A retained damaged active file can be recovered only through explicit confirmation
with a valid private selection/identity. Missing active files/manifests, unsafe
layout/links, sidecars and readable newer/foreign identities are refused. Normal
startup still refuses damaged storage and never repairs/replaces/restores it.
An already-running worker can display Settings backup history during corruption;
if startup cannot proceed, `list-backups` and confirmed `restore-backup` provide
operator-only CLI entry points using the same services, IDs and safeguards.
README documents stopped-worker recovery and verification commands.

Every operation shares the existing root-directory lock with workout requests.
Conflicting writes wait; none can access a partial candidate. Browser CSRF tokens
also bind to the active dataset generation, which is checked again inside the
write lock. Pages opened before restore must reload, rather than silently applying
old input to the restored dataset. Repeated restore tokens never execute twice;
completed and unresolved attempts remain in the external audit. Restoring does
not merge workouts/corrections made after the backup. Those records remain in the
preserved original database for separately reviewed recovery.

## Scheduler architecture and interruption rules

Compose runs a dedicated scheduler service with the same image, UID/GID and
external writable mount as web. It has no network/ports, a read-only root filesystem,
private tmpfs, dropped capabilities, no-new-privileges and restart policy
unless-stopped. Gunicorn workers never launch independent schedulers. No new
environment variables are required: scheduler reads WORKOUT_DATA_ROOT; existing
UID/GID and build CA options apply. The web image uses a 300-second worker timeout
for synchronous verified maintenance (large operations can still exceed it).

Missing settings mean disabled, 1 calendar day, 02:00 Etc/UTC and 30-day log
retention. Reading defaults creates no operations file or database. Only explicit
Settings configuration enables automatic backups. A 30-second server loop rereads
persisted settings and claims due slots under the storage-root lock. Settings
changes anchor cadence to the chosen zone's current local date and set the next
future slot. Repeated clock times use the earlier occurrence; gaps advance to the
first valid minute. Frequency means calendar days, not fixed 24-hour intervals.

Claims persist revision, last attempt/result and next future slot before copying.
Multiple processes/restarts cannot overlap or duplicate a claimed job. A missed
backlog coalesces to one attempt; it is never replayed as a burst. Failed attempts
remain failed, with last successful time unchanged; a later scheduled slot can try
again. A crash between claim and outcome is labeled interrupted on the next cycle,
not replayed. This deliberately favors at-most-once over guaranteed retry of an
interrupted slot. Interrupted restores remain unresolved for operator inspection;
no startup guessing changes selection. Disabled backups do not disable log cleanup.

## Persistent diagnostics and viewer

External private UTC daily JSONL events cover worker lifecycle, rejected workout
saves/completions, database readiness/integrity problems, explicit migration
attempts/results, backup/restore attempts/results, scheduler errors and security
rejections. Matching-schema migration remains a read-only no-op without logging
writes. Graceful scheduler exit is logged; SIGKILL/power loss cannot log shutdown.

A separate logs-directory lock serializes bounded private appends across processes
without reentering the workout lock. Log failures produce a generic stderr warning
and never undo a committed workout. Raw request/form bodies, secrets, cookies,
tokens, database contents and raw exception messages/locals are omitted. Protected
server details contain exception type and bounded technical frames; safe project
StorageError messages can appear in the browser after redaction. Flask's raw
exception dump is replaced with the same protected logging path.

Logs stream backward in bounded blocks, exposing 50-row pages, newest-first text,
severity/category/date filters, Refresh and expandable safe details/event IDs.
No filename/path input selects log files. Technical paths/stack frames remain
server-only. Retention deletes only matching daily log files outside the UTC day
window, on Settings save and scheduler cycles. It cannot rotate backups, archives,
operation history or workout records. Default 30; configurable 1–36500 days.

## Durable paths and operations

- `data/schema-4-<identity>-<uuid>.sqlite3`: active and retained recovery candidates.
- `config/active.json`: synced atomic database selection.
- `config/operations.json`: private atomic settings, backup history and restore audit.
- `backups/<UTC-timestamp>-<uuid>.sqlite3`: verified copies/failed evidence.
- `archives/selection-before-restore-<uuid>.json`: retained pre-restore selections.
- `logs/events-YYYY-MM-DD.jsonl`: structured protected UTC diagnostics.
- Existing signing key and original schema archives remain unchanged.

All live paths remain outside Git and replaceable containers. Backups contain
SQLite records, not the whole storage tree/signing material; retain host/offsite
copies separately. No normal startup initializes, migrates or restores storage.
Only diagnostics are appended during ordinary compatible application updates.
See README for explicit commands, permissions and failure recovery procedures.

## Automated validation

Final complete-suite command:

```sh
WORKOUT_CONTAINER_TESTS=1 /workspace/phase1-venv/bin/python -m pytest -q
```

**236 passed in 65.77 seconds; no failures or skips**: 217 service/HTTP/storage,
11 Chromium and 8 Docker tests. The image was rebuilt from committed source
(`workout-tracker:phase5-review`, SHA-256
`bd52a41651476d3ce527921730b265248a4b92bcc1eb02ab34b451e5c5b63f1e`).
The complete earlier Phase 1–4 suite remains included. Schema definition files
are identical to approved main. `git diff --check`, Python compilation, dependency
consistency and Python disclosure/function-explanation checks passed.
Approval regression rerun on November 6, 2026: **236 passed in 62.19 seconds,
with no failures or skips** (217 service/HTTP/storage, 11 Chromium, 8 Docker).
Application code, tests, schema definitions and container configuration are
unchanged from the approved implementation.

All fixtures are disposable and synthetic; browser servers are loopback-only.
Containers have no network/published ports and are removed after tests. Existing
Phase 1–4 tests remain included. Old filesystem snapshot helpers now exclude
expected diagnostic appends but still compare every database/config/archive byte.

Coverage includes 1,000 mixed historical workouts with SQL NULL/zero and correction
audits; unique/repeated/concurrent backup and restore tokens; corrupt/missing/
foreign/newer/sidecar sources; candidate/activation/post-sync/result-metadata
failures and uncertainty; abandoned attempts; concurrent workout saves; restored
audit/effective history; disabled/persisted daily/multiday/custom-zone schedules;
missed runs, competing claims, DST, failures and corruption; log privacy/filtering/
pagination/retention/write failures; CLI recovery; actual Chromium controls/themes/
responsive layouts; Gunicorn replacement; and independent scheduler containers.

## Files changed

- `operations.py`, `maintenance.py`, `scheduler.py`, `diagnostics.py`: external
  metadata, backup/restore candidates, dedicated jobs and private logs.
- `storage.py`, `migrations.py`: isolated-file validator reuse, dataset generation
  write guard and explicit maintenance diagnostics; no schema/DDL changes.
- `settings_views.py`, `__init__.py`, `__main__.py`, `views.py`, `workout_views.py`:
  Settings/CLI integration, lifecycle/error events, CSRF generation and failures.
- `templates/settings.html`, `backup_detail.html`, `restore_result.html`,
  `logs.html`, `base.html`; `static/style.css`: responsive local controls/viewer.
- `compose.yaml`, `Dockerfile`: separate hardened scheduler and maintenance timeout.
- `tests/test_recovery.py`, `test_scheduler_logs.py`, `test_settings_http.py`,
  `test_settings_browser.py`, `test_container.py`, `test_foundation.py`,
  `test_migrations.py`: synthetic recovery/scheduling/logging regressions.
- README, AGENTS, PROJECT_SPEC, MEASUREMENT_DESIGN and this review: operator
  workflow, invariants, scope, evidence and limitations.

## Known limits and recovery cautions

- Local backups do not replace Proxmox/offsite backups or protect against complete
  server/storage failure. No cloud synchronization/authentication/public exposure.
- POSIX/cooperative local-directory locks and atomic same-filesystem rename/fsync
  are required. Stop all external SQLite tools; they cannot honor this protocol.
  WAL/sidecar storage and network filesystems are not supported.
- Backup/restore and verification hold the exclusive root lock. Requests can wait;
  synchronous web maintenance has a 300-second worker limit. Interrupted jobs are
  retained as unverified/unresolved, not replayed. Use off-hours maintenance and
  inspect evidence after a timeout; do not mistake a lost browser response for
  proof that no activation occurred.
- A crash after atomic selection can leave a fully verified new candidate active
  with an unresolved attempt. Stop writers and inspect the audit/archived manifest;
  the app never guesses or silently replays restore. Simultaneous disk/rollback
  failures can require operator recovery; no filesystem can guarantee durability
  after arbitrary hardware failure. All original files remain preserved.
- Restore accepts only current exact schema 2–4, same identity and registered
  backups; older-version/imported-file/archive recovery needs separate offline
  review. Missing active files/manifests/keys require operator recovery, not silent
  replacement. There is no automatic merge of later records or archive-restore UI.
- Operations metadata is a bounded 32-MiB private atomic JSON file; its histories
  are retained indefinitely. Very large operation histories will require a future
  indexed format. Backup tables are currently unpaginated; log pages stream.
- Abandoned failed files/intents are retained. Deliberate backup deletion removes
  its listed file only; metadata remains. No automatic expiry beyond log retention.
- Log cleanup needs the scheduler process or a settings save; disabled backups
  still permit cleanup. Logging failure may leave diagnostic gaps. No authenticated
  author attribution exists in this passwordless shared-household application.
- Backups include database metadata/audits, not config/signing keys/logs. Keep the
  whole external tree protected separately. No independent security/accessibility
  audit or production readiness is claimed.
