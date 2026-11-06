# Workout Tracker

> **SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.** Human-directed AI-generated software; not audited or approved for production.

Phase 1 provides a Flask shell, browser themes, and SQLite storage safeguards.
There are no people, routines, workout records, migrations, backups, restores, or
scheduler yet. Do not use real workout data. Stop for review before Phase 2.

Read [AGENTS.md](AGENTS.md) and the authoritative [PROJECT_SPEC.md](PROJECT_SPEC.md)
before changes. [MEASUREMENT_DESIGN.md](MEASUREMENT_DESIGN.md) describes approved
future Weight/Time exercise support and its phase-by-phase acceptance tests.
This is a design update only: no routine editor, workout entry, or typed
measurement storage is implemented yet. [PHASE_1_REVIEW.md](PHASE_1_REVIEW.md) records scope and validation.

## Architecture and data flow

- `workout_tracker/__init__.py`: Flask factory, home screen, read-only readiness endpoint, local-resource browser protections.
- `workout_tracker/storage.py`: external-path validation, explicitly requested first installation, read-only SQLite verification.
- `workout_tracker/__main__.py`: operator commands. Browser requests cannot initialize storage.
- `workout_tracker/templates/` and `static/`: responsive HTML/CSS and browser-local Auto/Light/Dark preference. No CDN, analytics, or external requests.
- `tests/`: disposable storage tests, never household database tests.

Browser → Flask → storage verification → SQLite reads → readiness response.
The home page has no database mutations. Application version `0.1.0` is separate
from schema version `1`. Schema 1 contains identity and migration metadata only;
domain tables belong to later phases. There is no automatic schema upgrade.

## Local development with disposable storage

Requires Linux, Python 3.12+, Git, and a local filesystem supporting SQLite,
hard links, and directory syncing. Python's SQLite must support STRICT tables
(3.37+). Exact dependencies are pinned, including transitive runtime packages.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
```

Browser checks require `.venv/bin/python -m pip install -r requirements-browser.txt`
and Chromium (or `.venv/bin/python -m playwright install chromium`). Set
`WORKOUT_CHROMIUM` to an executable path if it is not named `chromium` on PATH.
Run `.venv/bin/python -m pytest -q tests/test_browser.py` with loopback socket
access. Without the optional dependency, pytest reports browser checks skipped.
The Docker checks are opt-in: after building image `workout-tracker:phase1-review`,
run `WORKOUT_CONTAINER_TESTS=1 .venv/bin/python -m pytest -q tests/test_container.py`.
They use disposable bind mounts with no network or published ports and remove
their own containers afterward. The tests require the local Docker socket.

For a local shell review, choose a **new, nonexistent** directory outside the
repository. These commands create only disposable foundation metadata. Do not
point them at an existing data directory or a real database.

```sh
export WORKOUT_DATA_ROOT="$(mktemp -d)/phase1-storage"
.venv/bin/python -m workout_tracker init-storage --data-root "$WORKOUT_DATA_ROOT" --confirm-new-storage
.venv/bin/python -m workout_tracker check-storage --data-root "$WORKOUT_DATA_ROOT"
.venv/bin/gunicorn --bind 127.0.0.1:8000 --workers 1 --threads 2 'workout_tracker:create_app()'
```

In another terminal, `curl --fail http://127.0.0.1:8000/health/ready` must report
`status: ready`, application version, and schema version. Stop the server with
Ctrl+C. Readiness means the Phase 1 shell and storage checks work; it does not
mean workout logging or recovery is implemented.

Initialization requires explicit confirmation and refuses **every existing
directory**, including empty ones. If initialization is interrupted, inspect the
retained directory; do not delete it or initialize elsewhere to conceal a lost
database. For confirmed disposable fixtures only, choose a fresh test path.

## Configuration and persistent storage

| Setting | Purpose |
| --- | --- |
| `WORKOUT_DATA_ROOT` | Required absolute external directory, never inside the checkout. No default that might silently create a database. |
| `WORKOUT_TRUSTED_HOSTS` | Comma-separated accepted HTTP hostnames; default `localhost,127.0.0.1,[::1]`. This is host-header validation, not access control. |
| `WORKOUT_PORT` | Compose host port, default 8000; published on loopback only. |
| `WORKOUT_UID`, `WORKOUT_GID` | Compose process identity, default 10001; must have permission to read external storage. |
| `WORKOUT_BUILD_CA_BUNDLE` | Optional Compose build CA bundle path; defaults to the system bundle. Never disable TLS verification. |

Initialization creates private directories:

```text
external-storage/
  data/schema-1-<identity>.sqlite3
  config/active.json
  archives/
  backups/
  logs/
```

The manifest selects a constrained database filename and matching identity.
Startup refuses missing files, invalid manifests, symlinks, wrong identities,
unsupported versions, unexpected schemas, failed integrity checks, or SQLite
sidecars. It uses SQLite `mode=ro`, foreign keys, and query-only connections.
Phase 1 uses rollback journals; WAL support and safe maintenance coordination
must be implemented and tested before later writer/recovery phases.

Containers never initialize storage. The Compose bind mount refuses to create a
missing source path and is read-only in Phase 1. Replacing a container retains
external files. Never mount the Docker socket into this application.

## Container review, updates, and rollback

`Dockerfile` and `compose.yaml` are provided for isolated development review,
not permission to deploy. The image uses a non-root process; Compose uses a
read-only root filesystem, drops capabilities, and publishes loopback only.
Dependencies and the Python base image digest are pinned. Refresh these pins
deliberately and rerun validation when updating them.

With the disposable `WORKOUT_DATA_ROOT` exported, `docker compose config --quiet`
validates configuration. For isolated container tests, the system CA bundle is
supplied as build secret `pip_ca`. Managed cloud environments must retain their
configured proxy and CA trust. No public service is needed.

An ordinary compatible application update must only replace application code
or its image: it must not copy, migrate, back up, delete, or reinitialize storage.
Unsupported schemas stop startup. Never work around that error by running
initialization. Phase 1 supplies no migration or rollback execution command.

## Backups, restore, logging, and troubleshooting

Backup creation, scheduling, archive switching, restore UI, persistent log
viewing, and log retention are **not implemented** in Phase 1. Automatic backups
will remain disabled until configured. Do not introduce household data before
recovery features pass their dedicated tests. Future migrations/restores must
use separate candidates, retain originals, and never overwrite databases.
Rolling back to an older database cannot silently merge newer workouts.

Current startup errors go to the process console; readiness errors reveal no
private filesystem paths. The `logs/` directory is reserved for later persistent
logging. To troubleshoot, run the read-only `check-storage` command. Missing or
unreadable storage, corruption, a sidecar, or incompatible metadata requires
investigation; nothing is automatically repaired, restored, or replaced.

LAN-only user selection will not be authentication: reachable household users
can view and alter shared data. Remote access, real-data use, and deployment need
separate approval. Local backups will not protect against physical host loss.
