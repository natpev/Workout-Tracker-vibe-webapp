# Phase 15 review — v0.15.0 / schema 11

**SHAMELESSLY VIBE-CODED 🤖**

Built with a healthy dose of AI, questionable amounts of confidence, and minimal
human supervision. Review before trusting and keep backups.

## Scope and baseline

Verified remote main e1306ca2521d226e7e0f87d9490fc98117fbd1ed contained Phase 14,
application 0.14.0/schema 10, permanent Weight Basis, actual reps, effective history,
statistics and conversion audit readers. Work uses synthetic storage only. No
production access, server deployment, PR creation or unrelated history repair.

## Implementation

Library and Progress group selected-person all-time effective non-NULL measurements
first (including zero), then sort names case-insensitively with stable identity
ordering. Progress choices/chart sections retain exercises outside the date range.
All-time history is loaded once and reused, rather than rescanned per exercise.
CSV selections follow the same ordering and preserve permanent exercise IDs.

Add Exercise is a native collapsed disclosure. Validation reopens it with raw values.
The redundant lifetime footer is removed; pounds and imperial short tons remain.

New workouts capture blank per-set actual reps. Null/partial arrays autosave and
resume exactly; forward navigation and completion require every performed set.
Zero gets the same explicit-recorded indicator as positive reps. One weight applies
to all sets. Skips remain SQL NULL. Legacy completed records retain historical
prescription assumptions. Focus starts at the first measurement on fresh navigation;
Tab/Enter progress through fields without autosave stealing focus. Indicators have
accent styling and text, support dark/light themes and do not imply physical success.

Exactly two transparent SVG defaults show dumbbells (Start) and a plated barbell
(End). Shared independent slots upload, replace, remove and fall back separately.
Inline sanitized rendering inherits the current person’s accent. The strict SVG
allowlist rejects active/external/unsupported content and limits size/complexity.
Canonical SQLite storage provides atomic changes, deletion cascades and existing
backup/restore/update persistence. See [SVG security and convention](docs/EXERCISE_ICONS.md).

All measurement-type transitions use explicit confirmation. Both save scopes remain
atomic and person-isolated. Already started drafts and completed/history/audit
snapshots stay unchanged. Canonical permanent basis survives dormant Duration and
cannot be changed by cycling types. A previously unassigned Duration exercise must
select its first basis before becoming weighted. Historical Progress and previous
measurements retain compatible captured measurement types; weight statistics use
historical snapshots rather than current defaults.

Schema 11 adds canonical basis and icon tables, permits dormant config metadata and
partial live reps, and adds an immutable new-entry repetition marker. No historical
columns or audit tables are removed. Released migration definitions remain intact.
See [schema changes and integrity](docs/SCHEMA_11.md). Old correction payloads and
Phase 13 conversion readers remain required; no conversion writer is reintroduced.

## Verification

**740 distinct passing tests: 600 backend + 118 Chromium + 22 Docker.**
All identified failures resolved and affected checks rerun; no outstanding issues.

- Backend/script suite: **600 passed** (183.09 seconds), including 70 new Phase 15
  feature cases. Existing history, corrections, Phase 13 audit readers, lifetime
  arithmetic, backups, restore, scheduler, browser updater and emergency v4 tests
  remain covered. No backend tests removed or weakened.
- Real Chromium: **118 distinct passed**. The complete run passed 114 cases; four
  failures were resolved and the affected 10-case menu and 4-case CSV suites
  passed afterward. Nine new
  feature cases cover portrait/landscape/desktop, light/dark, blank and partial
  drafts, zero indicators, focus, SVG management, confirmed Plank correction and
  actual computed SVG accent fills across two people. Mobile screenshot inspected.
- Docker: **22 distinct passed**: 21 cases in the complete integration run and the
  corrected added case rerun against the final rebuilt image (9.28 seconds).
  Schema 9/10 to 11 upgrades, schema-11 code-only updates, candidate failure,
  shutdown/startup recovery, retained source bytes and actual web health verified.
  The SVG test migrates schema 10 with conversion audits and an active draft,
  uploads artwork, backs up, removes, restores, then reads from another container.
- SVG security review: explicit element/attribute/paint/numeric allowlists; malicious
  scripts, events, foreign content, references, styles, animation, entities,
  processing instructions, size and complexity cases rejected. Invalid changes
  preserve the previous image. Canonical artwork revalidated by storage checks.
- Migration fault injection covers upgrade, preservation, logical validation,
  activation and post-activation failure. Original source bytes/selection remain
  intact. Every original table cell, correction and conversion audit compared;
  effective converted weights/totals preserved. Later repetition correction after
  an old conversion appends a revision without reapplying the conversion.
- Signed web/service tests cover both save scopes, all six type transitions,
  first basis assignment, no cycling loophole, stale preview rejection, other
  people’s routines, captured drafts/history and atomic rollback on write failure.
- Static/diff review checks released migration definitions unchanged, no raw SVG
  rendering, no external dependencies, no name-based identity matching and no
  reopened historical conversion writer. README commands checked against Compose
  and actual CLI flags; release JSON is human-readable and version matched.

Initial failures were fixed: raw creation form duration fields needed an undefined
attribute guard; current-release assertions and collapsed-form browser actions
needed updating (including a scope note hidden inside the disclosure); empty
Progress ranges retain sections with no points; native menu
scrolling needed an edge margin for fractional viewport geometry. A Docker test
metadata dictionary assertion was corrected. No production storage was used.

## Existing-server upgrade

These are administrator instructions; this work does not execute them on a server.

1. On v0.14.0/schema 10, create and verify a manual backup in Administration. Retain
   the whole persistent storage tree, private .env and current image for recovery.
2. Preferred: Settings → Administration → Application Updates → Check for Updates.
   Read v0.15.0 notes, explicitly confirm installation and schema migration, then
   Install Update. The existing host updater uses a verified candidate and preserves
   the original database. Do not initialize storage or hand-edit its manifest.
3. For an existing manual Compose installation, from `/root/WorkoutTracker/app`,
   with no updater job running:

```sh
git fetch origin
git switch main
git pull --ff-only origin main
docker compose --env-file ../.env stop web scheduler
docker compose --env-file ../.env build
docker compose --env-file ../.env run --rm --no-deps web \
  python -m workout_tracker migrate-storage --data-root /var/lib/workout-tracker \
  --target-version 11 --confirm-upgrade
docker compose --env-file ../.env run --rm --no-deps web \
  python -m workout_tracker check-storage --data-root /var/lib/workout-tracker
docker compose --env-file ../.env up -d --no-build
docker compose --env-file ../.env exec -T web python -c \
  'import json,urllib.request; r=json.load(urllib.request.urlopen("http://127.0.0.1:8000/health/ready",timeout=10)); print(r); assert r==dict(status="ready",app_version="0.15.0",schema_version=11)'
```

Stop at any failure; never initialize again, delete source files or start an old
image against an activated newer schema. Use the documented updater recovery flow.
After success, verify Library, a resumed draft, history and statistics, then create
a new verified schema-11 backup. Restore requires matching schema/storage identity;
older backups remain retained but are not silently installed into schema 11.
