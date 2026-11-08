# Phase 9 — interface, Administration, defaults and normalized entry

> **SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.** Human-directed generated code; not an independent audit or live-server deployment.

Branch `phase-9-ui-and-exercise-improvements` starts from verified Phase 8 main
`e99adf04f419016c71bb583fb2c1c4a11dd2e0db`. Release target is **0.9.0 / schema 7**.
The user explicitly authorizes comprehensive verification and a history-preserving
direct main merge/push/cleanup. **No PR creation or PR API attempt is permitted.**
No production server/data access, deployment or Phase 10 is included.

## Administration and navigation

Settings contains personal theme/accent preferences and Open Administration.
The compact Administration page groups updates, versions, maintenance/diagnostics,
backup settings/history, deliberate restore and logs. Existing URLs for maintenance
are retained; `/settings/administration` is the grouped entry point.
`administration.administrative_access()` is one shared boundary and explicitly
allows every request. Settings maintenance and Updates endpoints invoke it before
work; appearance is separate. A future approved authentication design could replace
that policy without decorating every route. No accounts, roles, passwords, login,
TLS/certificates or reverse proxy are created. The independent read-only host
status trust boundary would need its own review before any future remote exposure.

Existing CSRF, dataset-generation checks, typed restore/deletion confirmations,
permanent IDs, person ownership and host command restrictions remain. Anyone who
can reach the trusted LAN app can use Administration. Network isolation remains
the trust boundary, with normal HTTP at http://10.0.69.9:8000.

The hamburger menu has Routines, Exercise Library, History & Progress and Settings.
Without selection, person-specific destinations open People. Only the history
area displays History | Progress tabs; filters/charts and existing URLs remain.
Person/accent stays in the sticky header through links, forms, redirects, Back
and refresh. Active workout save/exit/resume/navigation protection stays intact.

Confirmed exercise deletion commits, flashes success and returns Library; Cancel
also returns Library. Routine deletion returns the owner's routines. Permanent
exercise/history erasure, new IDs on name reuse, unrelated-data preservation,
correction reconciliation and retained routine history remain unchanged.

## Global defaults and schema 7

The new STRICT exercise_defaults table has one primary/FK row per global ID:
measurement_type, target_sets, mutually exclusive target_reps/target_duration_seconds,
unit, weight_meaning and notes. Constraints mirror existing typed routine rules.
The only cascade removes editable defaults when their global identity is explicitly
erased; existing snapshot/ownership/protection triggers are unchanged.

Migration creates the table on a separate candidate and gives each old identity
neutral Weight, 3 sets, 12 reps, lb, empty meaning/notes. It never guesses a global
preset from one person's routine or history. Every old cell, ID, NULL/zero, draft,
preparation, correction and routine configuration stays exact. Validate source
hash, every old table/cell, DDL, migration record, one preset per ID, integrity/FKs
and logical snapshot/audit invariants before atomic selection. Original schema-6
files/manifests remain retained. DDL/validation/activation faults keep the original
selection. Startup never initializes or migrates. Matching-schema migration is
a read-only no-op; backup/restore supports exact schema 7 and retains defaults.
Old-schema backups remain retained and cannot silently downgrade schema 7.

Library registration/editing reuses catalog configuration validation, including
mode switching clearing incompatible fields. Validate new defaults before any
identity insertion; stale default edits are refused. Edit links are schema-7-only,
and forged legacy calls fail explicitly rather than opening a missing table.
Pounds is still the supported weight unit; no kilogram/conversion feature is added.

Add library exercise copies the current defaults once into an owned routine row.
Routine editing then provides independent overrides. Existing routine settings
never track later library edits. Duplicated/copied routines retain their actual
settings and share global IDs, with no measurements, history or increase-state
copy. Completed snapshots and per-person results remain independent.

## Accents, labels, clocks and durations

The old blue/teal/green/purple/orange/red preference keys and exact palettes remain
as Soft selections; six vibrant-* keys add visibly stronger color. Compact radio
choices preserve per-person external preference storage and Auto/Light/Dark.
Actual rendered primary-button contrast is checked against 4.5:1 for all 12 palettes
in each theme on phone and desktop.

Active/historical/correction labels are Weight (lb), Minutes, Seconds. Named
exercise groups preserve accessible context without repeating names in visual
labels. Exercise headings remain prominent.

Workout clocks display/edit HH:mm with explicit text fields and server validation,
so browser locale cannot substitute AM/PM. Internal seconds/microseconds remain;
a measurement-only correction with the same displayed minute/fold preserves its
original instant. History/chart chronology still uses the full effective instant.
Original IANA zones and DST gap/fold checks remain; installation timezone stays
America/Indiana/Indianapolis, not a fixed offset. Diagnostic timestamps retain
seconds in explicit 24-hour UTC, including host progress. Log date filters remain
UTC. Duration MM:SS is separate from wall-clock time.

One shared duration parser accepts minutes only, seconds only or both; seconds
may exceed 59. Blank+120=120, 1+90=150, 2+blank=120, 3+150=330. Save integer total
seconds, not a product with sets. Two blank actual inputs remain SQL NULL, while
targets and performed totals must be positive. Reject negatives, fractions,
malformed strings, zero totals and overflow. Strings stay bounded at 100 characters;
actual totals retain the signed-64-bit bound and targets retain 359999 seconds.
Autosave acknowledgments and saved forms normalize back to minute/second parts.
Weight zero/NULL and exact one-decimal truncation are unchanged.

## Original favicon

The original local SVG uses simple white dumbbell geometry on a rounded blue
square, with no text, external art or fonts. Development Chromium exports PNG
16/32 and Apple touch PNG 180; ICO includes 16/32 variants. Shared template links
serve all assets locally. No new runtime dependency or external request is needed.
SVG and adjacent icon README retain the required disclosure; binary formats are
identified/documented without invalid embedded source comments.

## Updater and existing installation

V4 remains `deployment/update_workout_tracker_v4.sh`. Approved-source parsing and
built release-info already detect 0.9.0/schema 7; no new script or engine migration
logic is needed. Browser and emergency CLI share verified backup, candidate upgrade,
original/image/Git preservation, locks, explicit consent and real health checks.
Host service changes only timestamp presentation. Its installed Phase 8 engine
already supports the new release; explicitly --upgrade-service copies the new
host presentation if desired. No privileged installation runs at Flask startup.

Exact server commands and prerequisites are in [deployment/README.md](deployment/README.md).
For a clean existing main checkout after verified merge:

```sh
(
  set -eu
  cd /root/WorkoutTracker/app
  test "$(git branch --show-current)" = main
  test -z "$(git status --porcelain)"
  git fetch origin
  git merge --ff-only origin/main
  bash deployment/update_workout_tracker_v4.sh --upgrade-service \
    --lan-address 10.0.69.9 --app-url http://10.0.69.9:8000 --status-port 8001
  bash deployment/update_workout_tracker_v4.sh
)
```

For first host setup use --install-service instead. The reported ensurepip error
requires the matching host venv package (Python 3.12: apt install python3.12-venv),
then rerun the installer without deleting storage. Confirm the update and type
MIGRATE 7 when the actual source schema needs upgrading. Existing installed host
service users may instead use Settings → Administration → Application Updates.
No .env values, application port or live database were changed by development.

## Verification

The final complete suite passed **342 tests, 0 failed, 0 skipped**, in
**375.31 seconds**: **306 backend/database/updater**, **24 Chromium** and
**12 Docker** tests. Tested application/test source commit: `4fc59ac`; subsequent
finalization changes documentation only. Backend, Chromium and Docker checks
actually execute against disposable data.

```sh
WORKOUT_CONTAINER_TESTS=1 /workspace/phase1-venv/bin/python -m pytest -q --tb=short --show-capture=no
```

The final run includes all corrected contract assertions and pre-insert validation.
Dependency consistency (`pip check`), compilation, source disclosures/docstrings,
Bash syntax and documented shell syntax also passed. ShellCheck is unavailable. Focused
checks cover original-cell/byte preservation, migration faults/no-op, defaults
copy/override isolation, restore/deletion, all requested duration normalization,
minute-only correction precision, centralized open access/CSRF, local asset file
formats/HTTP, twelve-color contrast and UI navigation.

Earlier tests for the explicitly superseded duration rejection, labels, global
tabs and Settings layout were updated to assert the new contract. Invalid-input,
rollback, ownership and persistence assertions remain. Positive normalization
regressions replace the old assumption that partial/large-second input is invalid.
One first full-run Docker test still fetched maintenance forms from the old
Settings page; it was corrected to use Administration while retaining all backup/
restore assertions, and its focused rerun passed. Preset validation ordering was
also strengthened to avoid partial identities when validation is caught inside
a caller-owned transaction. Another older browser assertion treated minutes-only
autosave as invalid; it now verifies successful normalization, then tests a
negative-seconds failure before recovery. Tests are not removed or disabled for
a pass.

Actual Docker rehearsals use real build, backup, schema-6→7 migration, preserved
source bytes, container replacement/health, host Unix peer controls and independent
HTTP progress, plus verified recovery and post-activation refusal. Approved Git
metadata and the cloud rootless-daemon disk-root probe are simulated; application/
SQLite/Docker operations are real. Other fixture v4 tests simulate Docker/Git but
use the actual Bash wrapper/engine and real SQLite backup/migration code.

Bash syntax, source disclosures/docstrings, documented shell blocks and offline
systemd syntax are checked. ShellCheck is unavailable; no ShellCheck pass is
claimed. No real systemd installation or production deployment is implied.

## Known limitations

- Physical iPhone/Safari/VoiceOver, live host setup, credentials, firewall and
  service activation are not verified by Chromium/disposable Docker tests.
- Initial presets for old identities are neutral, not inferred from personal
  routines. Pounds remains the supported weight unit. Other units need separate
  schema/history/chart/conversion design.
- The access boundary is deliberately open; network isolation is essential.
  Future authentication and host-status exposure need explicit approval.
- Existing acknowledged-save, hard-close/offline, cooperative SQLite locking,
  storage durability and offsite-backup limits remain.
- Backups/retained versions can resurrect deliberately erased records on a
  compatible restore. No versions/backups/images are silently pruned.
- The interrupted older Phase 8 branch contains unique work and is retained.
  Only the fully merged Phase 9 branch is eligible for cleanup.


## Direct Git workflow

The authorized workflow is feature push, fresh main fetch and ancestry verification,
normal fast-forward merge/push, remote tree/commit/target/asset verification, then
remote/local deletion of the completed feature branch. No PR is created or
attempted, no history is rewritten, and repository protections are not bypassed.
The final completion report records the actual remote main SHA and cleanup outcome.
Only the completed Phase 9 branch may be removed; unrelated interrupted work stays.
