# Phase 2 review — people, exercises and routines

> **SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.** No production readiness or deployment approval is implied.

## Scope and source branch

Implemented only Phase 2, including its minimal migration prerequisite. Remote
`main` fetched at task start remained at `6702250` and lacked the two approved
changes. Branch `phase-2-people-routines` was created from that main and then
fast-forwarded to approved design commit `a5f7c35`, which includes approved
Phase 1 commit `ed42a24`. Remote main was not changed. Review Phase 2's incremental
diff against `a5f7c35`; a PR targeting main also contains those approved ancestors.

Reviewable implementation increments:

- `91d68b4`: explicit candidate-only migration, schema definitions, storage locks and migration tests.
- `c312579`: people/exercises/routines, CSRF forms, typed configuration, browser/service/HTTP tests and container updates.
- Documentation and final validation follow as a separate commit.

People can be created, selected, renamed, archived and reactivated. Exercises have
permanent person-owned IDs and reusable names. Routines support creation,
renaming, editing, ordering, delete-as-archive, same-person duplication and
cross-person copying. Copies create independent identities/settings only.
Routine items support addition, editing, removal and ordering, optional notes,
Weight with sets/reps/pounds or Time with sets/integer-second duration targets.
The UI includes mobile form layouts, native segmented radios and all themes.

## Schema and migration risk, validation, rollback

Schema 2 retains both schema-1 metadata tables and adds `people`, `exercises`,
`routines`, `routine_exercises`. STRICT tables, CHECKs, unique positions and
composite ownership foreign keys constrain configurations. No actual measurement,
increase-state, workout, history, backup or schedule tables are introduced.
Actual decimal-weight precision is deferred until Phase 3 design is finalized.

The risk is changing the wrong database or selecting an incomplete upgrade.
Explicit CLI confirmation, shared app/maintenance directory locks, source/schema
verification, read-only SQLite backup source, a separately reserved candidate,
full candidate validation, source hash/equality checks and atomic manifest
publication address that risk. Original database bytes and modification time
remain unchanged. It stays under `data/` with the prior selection preserved in
`archives/`. No migration or application update overwrites a database.

Maintenance refuses busy app connections. All app writes are single transactions
under an exclusive storage lock; all reads use shared locks and readonly
connections. External tools must be stopped. WAL mode and sidecars are rejected
before SQLite is opened to prevent implicit read-time sidecar creation/recovery.
A compatible schema-2 update/migration request performs no copy or data write.

Failures before publication retain the original selection. A failure syncing
after publication triggers an atomic selection rollback; a rollback durability
failure reports uncertainty and requires operator inspection. Original and
candidate database files remain preserved. Process loss during atomic selection
can leave old or new selection; both refer to already valid synced databases.
No unverified candidate is exposed. Full restore/backup administration is not
implemented. Reverting to an old database cannot merge records created afterward.

## Validation

Final command: `WORKOUT_CONTAINER_TESTS=1 /workspace/phase1-venv/bin/python -m pytest -q`

**99 passed, 0 failed, 0 skipped** in the final run:

- 93 foundation/storage, migration, catalog service, and HTTP integration tests.
- 3 Chromium tests, including keyboard segmented selection, 1:05 → 65-second
  round trip, incompatible-field clearing, ordering, independent cross-person
  copy, themes/reload persistence and widths 320/768/1280 pixels.
- 3 Docker/Compose tests: actual Gunicorn requests, unsupported-schema refusal,
  original source unchanged, container replacement with retained schema-2 writes,
  loopback Compose configuration, no test network or published ports, and
  read-only container root with a writable external definition-data mount.

Storage fault injection covers candidate DDL failure, invalid candidate data,
publication failure, post-switch sync failure/rollback, busy maintenance lock,
and unsafe source refusal. Tests compare original bytes/mtime and selection,
and verify a compatible migration is a no-write/no-copy no-op. The foundation
suite now also checks WAL headers before SQLite can create sidecars. Security
checks include CSRF, forged Unicode tokens, ownership, escaped markup,
confirmation, stale routine forms, missing signing keys and restart-after-upgrade.

`python -m pip check` reported no broken requirements. `git diff --check`, local
Markdown links, mandatory disclosures, and Python function documentation checks
passed. The final pinned image built with TLS verification and configured CA
trust. All containers/test servers were stopped by their fixtures.
All fixture databases are disposable and external to the checkout; no real
workout data was accessed. No application deployment occurred.

## Changed files

- `workout_tracker/storage.py`, `schema.py`, `migrations.py`, `__main__.py`: safe storage sessions and explicit candidate upgrade.
- `workout_tracker/__init__.py`, `catalog.py`, `views.py`: Flask configuration, signed-session CSRF, ownership, validation and catalog rules.
- `workout_tracker/templates/base.html`, `macros.html`, `people.html`, `dashboard.html`, `exercises.html`, `routine.html`, `entry.html`, `error.html`: management screens and form components.
- `workout_tracker/static/editor.js`, `style.css`: typed field visibility and responsive themed controls.
- `compose.yaml`: writable external definition storage while keeping container root read-only.
- `tests/conftest.py`, `test_migrations.py`, `test_catalog.py`, `test_management.py`, `test_browser.py`, `test_container.py`, `test_foundation.py`: isolated fixtures, migration failure injection, service/HTTP/browser/container and foundation regressions.
- `AGENTS.md`, `PROJECT_SPEC.md`, `MEASUREMENT_DESIGN.md`, `README.md`, `PHASE_2_REVIEW.md`: scope, schema, usage, safety and review record.

## Limitations and later-phase requirements

- No workout logging, actual measurements, historical snapshots/charts, automatic
  backups, scheduler or restore UI. No Phase 3 work began. Consequently there is
  no real workout history to test archival against; all people are conservatively
  archived, never deleted, and there is no history mutation code.
- Permanent exercise IDs survive removal. Future snapshots must copy definition
  details at session start and remain independent of later configuration edits.
  Those tests belong to the future session/history phases.
- Routine editing uses stale-state fingerprints. People/name-management forms
  currently use normal last-writer behavior; they are not a collaboration editor.
- Renaming a reused exercise changes its name in that person's routine displays.
  Same-person and cross-person copies get new identities and are independent.
- Empty routines are allowed during editing. Routine deletion is soft archival;
  there is no routine/exercise reactivation UI yet (people can be reactivated).
- Positive configuration limits are documented in the README. Actual duration
  zero/partial-input rules, decimal performance precision and correction audit
  semantics remain open for later phases, not silently resolved here.
- Filesystem guarantees assume a local POSIX filesystem, one application storage
  root and all writers respecting locks. No hostile administrator, NFS storage,
  external SQLite writer or physical disk failure guarantee is claimed.
- Full integrity checks run per transaction/readiness and can be expensive with
  future large history databases; reassess before real-data use.
- No authentication: reachable household users can select and manage any person.
  Loopback review defaults are not permission to expose the server remotely.
- No full accessibility/security audit. Session cookies support local HTTP;
  remote HTTPS/authentication would require separate design and authorization.
