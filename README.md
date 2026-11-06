# Workout Tracker

> **SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.** Human-directed AI-generated software; not audited or approved for production.

Phase 2 implements people, permanent exercise definitions, and independently
copyable Weight/Time routines. It includes only the safe migration prerequisite
needed for this phase. Stop for review before Phase 3. No workout logging,
results, historical charts, automatic backups, scheduling, or restore UI exists.
Do not deploy or connect to real workout data.

Read [AGENTS.md](AGENTS.md), [PROJECT_SPEC.md](PROJECT_SPEC.md), and
[MEASUREMENT_DESIGN.md](MEASUREMENT_DESIGN.md). Current implementation evidence
and limitations are in [PHASE_2_REVIEW.md](PHASE_2_REVIEW.md); the earlier
[PHASE_1_REVIEW.md](PHASE_1_REVIEW.md) is retained as a historical record.

## Architecture and data flow

- `workout_tracker/__init__.py`: Flask factory, configuration, readiness, safe errors and browser protections.
- `storage.py`: external-path validation, explicit first install, schema verification and per-transaction locking. Every database connection enables foreign keys.
- `schema.py`: exact schema-2 definitions; no performance tables.
- `migrations.py`: explicit schema-1 → schema-2 candidate-only upgrade and atomic selection.
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
the Docker base-image digest are pinned. There are no new Phase 2 dependencies.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q tests/test_foundation.py tests/test_migrations.py tests/test_catalog.py tests/test_management.py
```

For a **disposable local review**, explicitly create a new, nonexistent external
path. Initialization refuses every existing directory, including empty ones.
It creates schema 1 first; a separate explicit command copies/upgrades it.

```sh
export WORKOUT_DATA_ROOT="$(mktemp -d)/review-storage"
.venv/bin/python -m workout_tracker init-storage --data-root "$WORKOUT_DATA_ROOT" --confirm-new-storage
.venv/bin/python -m workout_tracker check-storage --data-root "$WORKOUT_DATA_ROOT"
.venv/bin/python -m workout_tracker migrate-storage --data-root "$WORKOUT_DATA_ROOT" --confirm-upgrade
.venv/bin/python -m workout_tracker check-storage --data-root "$WORKOUT_DATA_ROOT"
.venv/bin/gunicorn --bind 127.0.0.1:8000 --workers 1 --threads 2 'workout_tracker:create_app()'
```

These commands are for synthetic review data only, not deployment permission.
Stop the server with Ctrl+C. The readiness endpoint is `/health/ready`; verify
`status: ready`, app version `0.2.0`, and schema version `2`. Schema 1 still opens
the foundation shell, but management requires explicit migration and reports 503
until it is performed. Restart any schema-1 process after migration so it loads
the newly provisioned signing key; an old process returns 503 rather than broken
forms. Startup never initializes, migrates, repairs or replaces
storage. Missing or corrupt storage must be investigated, not worked around by
initializing another path.

## People, exercise names, and routines

Create/select people from People; rename, archive or reactivate them there.
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
meaning 200. These bounds prevent invalid configuration, not define future
actual-result precision. There are no actual weight/duration or increase-flag
columns in Phase 2; decimal weights and explicit zero/NULL semantics remain
specified for Phase 3 rather than prematurely adding workout logging.

Use the routine's up/down controls to reorder routines or exercises. Duplicate
within a person or use Copy a routine to copy between people. Every copy gets
fresh routine/item/exercise identities and independent settings, with no workout
history, results or increase state. Routine edit forms reject stale submissions
with 409; reload before retrying if another page has changed the routine.

## Storage and explicit migration safety

```text
external-storage/
  data/schema-1-<identity>.sqlite3              # unchanged original
  data/schema-2-<identity>-<candidate>.sqlite3  # candidate/current schema 2
  config/active.json                          # active database selection
  config/session.key                         # private session signing material
  archives/selection-before-<candidate>.json   # original selection
  backups/                                   # reserved, not an implemented service
  logs/                                      # reserved, not a persistent viewer
```

The CLI takes the same persistent-root lock used by all app connections. It
refuses maintenance while a request holds a connection; stop workers and all
external SQLite tools before migration. External tools do not follow our lock
protocol. Only the known schema 1 can upgrade to 2.

Migration opens the original read-only and creates a distinct candidate using
SQLite's backup API. DDL changes only the candidate. Checks cover application
identity, exact schema, integrity, foreign keys, schema/migration versions,
original metadata equality, empty new domain tables, and original file hashes.
The candidate and selection files are synced before atomic manifest replacement.
A post-switch sync failure attempts atomic restoration of the original selection;
if that also fails, the CLI reports uncertainty and requires inspection. No
original database is overwritten or removed. Previous versions stay in `data/`
and their selection manifests in `archives/`; failed candidates stay for diagnosis.

Both supported schemas use rollback journals. WAL headers and any journal/WAL/SHM
sidecars are refused **before** SQLite opens a source; there is no implicit
recovery. Unknown, damaged, missing, symlinked or incompatible storage never
becomes an empty replacement. A compatible schema-2 migration request is a
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
| `WORKOUT_PORT` | Compose host port, default 8000, loopback only. |
| `WORKOUT_UID`, `WORKOUT_GID` | Compose process identity; match the owner of private storage. Defaults 10001. |
| `WORKOUT_BUILD_CA_BUNDLE` | Build CA bundle, default system bundle. Keep TLS verification enabled. |

The image uses a non-root process. Compose keeps its root filesystem read-only
but its **external storage mount writable** for definition transactions. It
refuses to create a missing host mount, drops capabilities, and publishes loopback
only. Storage/key permissions must allow the configured UID/GID; do not make
private storage world-readable to fix ownership. No live home-server deployment
is authorized. Containers never initialize or migrate storage at startup.

For isolated image review, build `workout-tracker:phase2-review` with build secret
`pip_ca` set to a trusted system CA bundle. Managed cloud proxy/CA configuration
must be preserved. Run container tests only against the local Docker daemon:

```sh
docker build --secret id=pip_ca,src=/etc/ssl/certs/ca-certificates.crt -t workout-tracker:phase2-review .
WORKOUT_CONTAINER_TESTS=1 .venv/bin/python -m pytest -q tests/test_container.py
```

They use disposable fixtures, no network or published ports, and remove their
own containers. Browser tests need Chromium and optional pinned dependencies:

```sh
.venv/bin/python -m pip install -r requirements-browser.txt
.venv/bin/python -m pytest -q tests/test_browser.py
```

Install Chromium or use `.venv/bin/python -m playwright install chromium`. Set
`WORKOUT_CHROMIUM` to its executable if needed. Browser tests need loopback socket
access. Without optional tools, their skipped status is distinct from a pass.

## Backups, rollback, logs, and troubleshooting

Complete backup/restore interfaces, scheduling and persistent log viewing remain
Phase 5. Automatic backups are not active. Do not introduce real workout data.
On-server copies will not protect against physical storage loss.

Readiness verifies storage and returns a generic 503 when unavailable. Use the
read-only `check-storage` command for operator diagnosis. Console logs report
failures without raw form bodies or secrets; persistent `logs/` is reserved.
No update purges retained data, schemas or logs. Incompatible code/schema pairs
fail safely. Stop writers before any future rollback: selecting an older
schema cannot merge newer records, and this phase supplies no restore command.
A stopped-review code rollback to Phase 1 can read its preserved original only
after deliberate manual recovery; never improvise a production selection change.
