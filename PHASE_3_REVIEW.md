# Phase 3 review — workout tracking and saving

> **SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.** This is review software, not a production deployment.

## Scope, base and review increments

Branch `phase-3-workout-tracking` starts from verified approved main
`29652faffad25fa539458540f1419100ea97f0ff`, containing Phases 1/2 and the
Weight/Time design. Main is not changed; do not merge or delete this branch
before review. No Phase 4 work, deployment or production data access occurred.

- `dfe9745`: candidate-only schema 3 migration, session/entry snapshots,
  transactional workout services, measurement and migration tests.
- `544b775`: CSRF-protected screens, revision-checked autosave, recovery,
  confirmations and browser/HTTP/container coverage.
- Documentation and final verification are recorded in the following commit.

## Implemented behavior

People switching and routine management stay intact. Start copies a nonempty
routine into an owned snapshot, records UTC/local-date/IANA-zone information,
and enforces one draft per person. Existing drafts offer resume/discard. Every
exercise starts with blank actual values; names, order, type, targets, notes,
units and weight meaning are independent of subsequent routine edits/removal.

The mobile workout screen has one exercise, reference performance and flags,
typed actual input, increase toggle, Back/Next/jump, expandable overview, progress,
Save draft, Finish & Save and Discard. Auto/Light/Dark and large rounded controls
are retained. Weight truncates to tenths without float rounding; explicit zero
is valid. Time requires both minute/second parts, seconds 0–59 and total >= 1.
Two blank parts skip; partial input is an error. Neither type is multiplied by
sets. Skipped entries retain SQL NULLs and no new increase flag.

Autosave serializes revision-checked requests, acknowledges only committed saves,
keeps newer typed input during delayed responses, and preserves earlier commits
on failures. Conflicts return 409 without overwriting another tab. Navigation
and Finish flush pending changes; the final POST also validates/includes current
input atomically. Completed retries return the existing session. An entirely
skipped workout requires additional confirmation. Discard uses a dialog with
warning, acknowledgment, disabled OK and safe Cancel/Escape; it only changes a
draft status and never deletes completed data.

## Schema, data path and migration/rollback safeguards

Schema 3 adds `workout_sessions`, `workout_entries`, a unique active-draft index
and immutable-snapshot/finalization triggers to the existing schema-2 objects.
STRICT integers store pounds in tenths and durations in seconds. Composite
foreign keys enforce person/session/exercise ownership; CHECKs enforce typed
NULL/value/flag combinations. Every snapshot row is retained, including skips.
The session carries immutable completion timestamps and workout date/timezone.
No chart, backdated-entry, correction, scheduler or recovery-interface tables
or routes are introduced.

Risk: schema changes or interrupted completion could otherwise corrupt data,
replace the wrong database or lose a saved workout. The explicit CLI upgrades
known schema 1/2 to a separately named candidate. It reads the source only,
compares every pre-existing row/NULL, checks integrity, foreign keys, application
identity, exact table/index/trigger DDL, version history, empty new tables and
unchanged original bytes. Only a validated/synced candidate is selected through
atomic manifest replacement. Original files/selections stay retained. Failures
retain or atomically restore the prior selection; rollback durability failure
reports uncertainty rather than success. Compatible target requests are no-op
reads. Startup never migrates, initializes, repairs or replaces storage.

Every app transaction participates in the root-directory lock protocol;
maintenance refuses busy connections. WAL headers and sidecars are refused
before opening SQLite; stop external tools before migration. Save/finish SQL is
inside one transaction, so failures after a pending entry update roll back to
previously saved values and draft status. Finalized entries/sessions reject SQL
mutation/deletion; Phase 4 corrections need separately reviewed safeguards.

## Validation record

Final command: `WORKOUT_CONTAINER_TESTS=1 /workspace/phase1-venv/bin/python -m pytest -q`

**152 passed, 0 failed, 0 skipped** on final source and the rebuilt Phase 3 image:

- 141 foundation, migration, catalog, management, workout-service and HTTP tests.
- 7 Chromium tests: all earlier UI regressions plus workout autosave/normalization,
  immediate Finish with pending input, restart/reference behavior, zero-progress
  navigation, jump/overview updates, all-skipped confirmation, discard gating,
  Cancel/Escape, themes, widths 320/768/1280, offline failures, stale tabs, and
  typing while an earlier committed response is deliberately held.
- 4 Docker/Compose tests, including all previous container regressions and real
  Gunicorn workout autosave/recovery across container replacement with original
  schema-1/schema-2 bytes unchanged.

Additional checks passed: pinned image build with proxy CA/TLS verification,
`python -m pip check`, `git diff --check`, documentation links/disclosures, and
Python file headers/function docstrings. No new dependencies were introduced.

Schema-3 upgrade tests cover populated schema 2 with exact row/NULL preservation,
source byte/mtime preservation, candidate DDL/logical-data failure, activation
failure, post-switch sync rollback and compatible-target no-copy/no-write behavior.
Workout tests cover actual threaded start/update races, stale revisions, failed
finish rollback, NULL/zero distinctions, duration rejection/conversion, stable
snapshots after routine/type/name removal/edits, previous-type/owner separation,
and immutable finalized entries.

Browser validation found and corrected a native reentrant-submit edge case when
Finish had no pending save. A real two-tab test and deliberately held response
verified the serialized drain prevents same-page revision conflicts or replacement
of newer local input by an older acknowledgment. All final checks pass.
All tests use temporary external storage and synthetic names. Browser servers
are loopback-only. Containers have no network or published ports and are removed
by the test fixtures. No real workout database was accessed.

## Files changed

- `workout_tracker/workout_schema.py`, `storage.py`, `migrations.py`, `__main__.py`:
  schema/version validation, candidate upgrade and CLI target selection.
- `workout_tracker/workouts.py`, `workout_views.py`, `__init__.py`, `views.py`:
  service rules, routes, timezone configuration and management/start integration.
- `workout_tracker/templates/workout.html`, `workout_resume.html`,
  `workout_discard.html`, `workout_done.html`, `routine.html`, `dashboard.html`,
  `base.html`; `static/workout.js`, `style.css`: UI, serialized autosave,
  confirmations and local themed layout.
- `compose.yaml`: explicit configurable workout timezone; same local-only review
  configuration and external persistent storage.
- `tests/conftest.py`, `test_migrations.py`, `test_workouts.py`,
  `test_workout_http.py`, `test_workout_browser.py`, `test_container.py`:
  disposable fixtures, schema/data preservation, exact values, recovery,
  concurrency, confirmations, responsive/browser/container tests.
- `AGENTS.md`, `PROJECT_SPEC.md`, `MEASUREMENT_DESIGN.md`, `README.md`,
  `PHASE_3_REVIEW.md`: authorization, implemented behavior, operators' commands,
  safety/testing record and limitations.

## Limits and future work

- No charts/history explorer, backdated entry, completed-session editing, backup
  scheduling, restore UI or application log viewer. The singular saved-session
  confirmation and previous-performance references are necessary Phase 3 views.
- Only server-confirmed input is guaranteed recoverable. A network response may
  be lost after commit; reload can recover it. Unsaved text remains visible on
  errors, with a before-unload warning, but forced browser termination cannot
  guarantee unsent input. There is no offline storage/replay queue.
- JavaScript is required for autosave, jump navigation and gated discard dialog;
  ordinary explicit draft save/finish forms work without it. Without JS, save
  before navigating. No live stopwatch is included or required.
- Actual values are bounded by SQLite signed 64-bit range and form strings by
  100 characters; there are no new product-specific exercise limits. Target
  configuration limits from Phase 2 remain unchanged.
- `WORKOUT_TIMEZONE` must be an installed IANA zone. Local runs default to server
  local, then UTC; Compose defaults Etc/UTC explicitly. Configure the intended
  household zone before any later authorized use. No browser timezone inference.
- Storage remains local POSIX SQLite with cooperative locks and conservative
  sidecar refusal, not an external-writer or network-filesystem solution.
- Full integrity checks per transaction/readiness may be costly with large future
  histories; reassess before real-data use. No scalability/security audit claim.
- Household selection is not authentication; reachable LAN users can choose other
  people. No remote exposure, production deployment or real data use is authorized.
