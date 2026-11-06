# Phase 4 review — history, charts and historical entry

> **SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.** This is review software, not a production deployment.

## Scope, branch and increments

`phase-4-history-charts` starts from fetched main
`52cba2a6415757dff98eb2509f72a6b91eea1c8d`, verified to include approved Phase 3.
Phase 4 was reviewed and approved on November 6, 2026. The authorized completion
workflow fast-forwards main after full regression testing, verifies remote
containment and then deletes the fully merged feature branch. Phase 5 is next
but requires separate authorization. No deployment or production database access
is included.

- `406b429`: candidate-only schema 4, immutable historical records, correction
  overlays, ownership/chronology services and migration/service tests.
- `b2818f3`: history/manual/correction screens, local SVG charts, browser/HTTP/
  container tests, effective legacy references and responsive chart styling.
- `28f3d42`: repeated-hour UTC ordering/fold-only correction regression and
  readable phone chart labels.
- `0ed5ba7`: implementation documentation and complete-suite validation.
- Approval/status documentation is committed before the approved fast-forward.

## Implemented behavior and significant data flow

People switching and existing routine/workout management are retained. Direct
History/Progress links lead to per-person completed workouts, occurrence-based
ordering, inclusive date/routine/exercise filters, and saved snapshot details.
Discarded/live drafts do not appear as completed history. Original order,
names, tracking type, targets, units/weight meaning and notes remain visible
even after definitions are renamed, removed or archived. Zero is a measurement;
SQL NULL displays Skipped and never becomes zero.

Charts use server-generated local SVG and accessible value lists. Series keys
include permanent exercise identity, tracking type, unit and weight meaning.
Weight uses pounds with one decimal; time uses integer seconds labeled readable
minutes:seconds, never multiplied by sets. NULL is not plotted; zero is plotted.
Statistics are highest logged weight/longest logged duration in the selected
range. No chart library, external CDN, cloud service or new dependency is used.

Historical entry first validates a chosen routine, past local date and optional
time, then appends an immutable preparation snapshot. Review shows copied
prescriptions; actual values use existing truncation/zero/NULL/duration rules.
Save writes session, every entry and registry link atomically. A unique form ID
makes retries return the already saved workout. There is no transient live draft,
so an existing active workout is untouched. If an older prescription differs,
create/duplicate/configure a separate routine before preparing its history form.

Actual date/optional time, zone and known UTC occurrence are separate from entry
time. Date-only entries retain NULL time, not an invented midnight. Unknown time
sorts before known times that day, with a stable entered-time/ID tiebreak. Future
values and DST gaps are rejected; ambiguous repeated times require a fold choice.

## Correction design and original-data protection

Original Phase 3 tables, indexes and triggers remain unchanged. No direct update
or deletion of completed session/entry values is enabled. New historical tables,
preparations, registry links and correction rows reject updates/deletes too.

A correction must explicitly confirm and match the latest correction revision.
Only actual measurements, increase flag and occurrence date/optional time are
accepted. The service revalidates type, integer bounds, weight truncation,
nonzero durations, skips and all-skipped confirmation. It appends complete before/
after value states with UTC timestamp and sequence under one locked transaction.
The next-revision SQL guard and unique constraint protect ordering; stale forms
return 409. Immutable metadata is neither form-editable nor part of an overlay.

The effective-value reader validates the latest correction shape, entry IDs,
measurement types, NULL/flag rules and occurrence consistency before applying
only correctable fields. History/detail, charts/stats, the original completion
bookmark and previous-performance lookups use this same read layer. Previous
performance uses effective actual chronology, so a backdated entry or corrected
date can enter/leave the reference set without relying on when it was entered.
Every original row and all sequential before/after records remain available.
There is no authenticated author field because household selection has no login.

## Schema 4 and migration safeguards

New tables: `historical_forms`, `historical_workouts`, `historical_entries`,
`workout_registry`, `workout_corrections`. STRICT columns/composite ownership
foreign keys and typed-entry CHECKs constrain records. The registry references
native or historical completion for ownership-safe correction targets. Existing
completed native sessions are linked in the candidate; an added trigger links
new native completions without altering their original protection triggers.

The explicit `--target-version 4` upgrade takes the shared maintenance lock,
opens schema 1/2/3 read-only, copies through SQLite's backup API into a distinct
candidate and adds new objects there only. It compares every original row/value/
NULL (including completed/draft sessions), verifies original hashes/mtime in
tests, validates integrity, foreign keys, exact original/new DDL, schema/version
history, empty new historical/audit tables and exact completed-session registry
links. Activation atomically replaces the synced manifest only after validation.
Original databases and selection manifests remain retained. Failure keeps or
restores the original selection; failed candidates remain for diagnosis.

Matching-target migration/startup performs no copy/data write. No ordinary
startup initialization, migration, repair or restore is added. The CLI keeps its
existing target-3 default for compatibility; explicitly choose target 4. Local
POSIX/cooperative-lock and conservative sidecar assumptions from prior phases
remain. Complete backup/restore/scheduling/log interfaces are not implemented.

## Automated validation

Final complete-suite command:

```sh
WORKOUT_CONTAINER_TESTS=1 /workspace/phase1-venv/bin/python -m pytest -q
```

Approval regression rerun on November 6, 2026: **175 passed in 49.94 seconds; no failures or skips**: 161 service/HTTP/storage
tests, 9 Chromium browser tests and 5 Docker tests. All earlier Phase 1–3 tests
remain included. The final Docker image was rebuilt from the tested source.
Coverage includes original-byte/NULL preservation, failed candidate/activation
rollback, owner isolation, historical snapshots/filtering, active-draft coexistence,
retry idempotence, atomic failure rollback, correction audits and concurrent stale
revisions, effective previous-performance references, repeated-hour chronology/
fold-only corrections, typed charts, phone/desktop layouts and all three themes.
`git diff --check` passed and `pip check` found no broken requirements.
All databases use temporary external fixtures, not real workout data. Browser
servers are loopback-only; containers have no network/published ports and are
removed by fixtures. The earlier Phase 1–3 tests remain in the suite.

## Changed files

- `workout_tracker/history_schema.py`, `storage.py`, `migrations.py`, `__main__.py`:
  additive candidate schema/target validation and original-data comparisons.
- `workout_tracker/history.py`, `history_views.py`, `__init__.py`, `workouts.py`,
  `workout_views.py`: effective readers, chronology, snapshots, audit services,
  protected routes and existing-workout reference integration.
- `templates/history.html`, `history_detail.html`, `historical_start.html`,
  `history_form.html`, `progress.html`, `time_fold.html`, `base.html`, `people.html`,
  `workout_done.html`; `static/style.css`: local charts, navigation, review,
  confirmation, audit and responsive theme/keyboard controls.
- `tests/conftest.py`, `test_migrations.py`, `test_history.py`,
  `test_history_http.py`, `test_history_browser.py`, `test_container.py`:
  synthetic fixtures, migration/rollback/original protection, history/typed
  chart/correction behavior, concurrency and browser/container regressions.
- `AGENTS.md`, `PROJECT_SPEC.md`, `MEASUREMENT_DESIGN.md`, `README.md`,
  `PHASE_4_REVIEW.md`: scope, implementation, operators' commands and evidence.

## Limits and future work

- No Phase 5, automatic/scheduled backups, restore UI or persistent application
  log viewer. No completed-workout deletion, deployment or real database access.
- Historical entry uses a selected routine snapshot. Different old prescriptions
  can be composed with the existing routine create/duplicate/editor flow before
  preparation. The historical measurement review form does not edit snapshot
  names/types/targets. It saves on explicit submission, not live autosave.
- Preparations and audits are retained; abandoned preparations are not expired
  or automatically deleted. A new preparation is an intentional new submission,
  while retries of the same preparation cannot create another workout.
- Unknown time cannot establish an exact within-day ordering; it is labeled
  unknown and uses the documented deterministic ordering. Recorded local date
  and original zone are retained; no browser-zone inference is added.
- SVG charts have exact data lists and native point titles, but no interactive
  zoom/pan. Household-sized histories load in memory with per-workout effective
  queries; large histories will need pagination/query optimization later.
- Original rows and audit revisions are append-only. JSON audit value payloads
  are validated by services/effective readers, not an external authenticated
  audit system. Household users can select another person; no author identity
  or remote authentication is implied.
- Existing local filesystem, cooperative locking, full integrity-check cost,
  secret-key permissions and unsent live-draft network limitations still apply.
- No independent accessibility/security audit or production readiness claim.
