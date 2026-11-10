# Phase 6 mobile UX review

> **SHAMELESSLY VIBE-CODED 🤖**
>
> This application was built with a healthy dose of AI, questionable amounts of confidence, and minimal human supervision. It appears to work, but don’t mistake that for a warranty. Use at your own risk, and keep backups. Human-directed AI-generated code, not independently audited or deployed.

## Scope, branch and review boundary

`phase-6-mobile-ux-redesign` starts from fetched approved main
`2be4c740749f4d2923583321a40271859c13f79e` (Phases 1–5 and installation guide).
Implementation increment `5d0a990` introduces the coordinated presentation,
preference and deliberate-exit changes. `a216f5e` records the browser tests and
19 inspected screenshots. `7435462` records documentation and initial validation.
Phase 6 was reviewed and approved on November 6, 2026. The authorized completion
workflow runs the full suite, updates approval documentation, fast-forwards main,
verifies remote containment and then deletes the fully merged feature branch.
No additional development phase is authorized.
No actual Proxmox access/deployment, real household data, network/port change,
new authentication, public exposure or unrelated development is included.

## Complete requirements checklist

| Requested area | Implemented behavior / evidence |
| --- | --- |
| Preparation and existing behavior | Read project instructions/source, fetch approved main, separate branch; all earlier tests retained. |
| Mobile-first priorities | Compact neutral surfaces, readable input, 44px minimum primary controls, one exercise card and ordered actions; no fixed-height clipping. |
| Home/person selection | Opening the configured app shows People immediately, never a remembered account; existing cards precede Add person. |
| People redesign | Name/avatar selects routines directly. Independent hamburger disclosure contains manage/history/progress/exercises/appearance/rename/archive/reactivate; no expanded per-person management wall. |
| Accessible menus | Button state/control association, ArrowDown focus, Tab traversal, Escape returning focus, outside-click/focus dismissal. Selection links and menu buttons are separate actions. |
| Routine selection | Direct Start workout on routine cards, secondary Edit routine; create/copy management remains available. Existing empty-routine server validation retained. |
| Workout person switching | Active pages omit global switching/navigation. Finish, deliberate save-and-exit, or confirmed discard releases this tab for switching. Other browser sessions remain independent. |
| Exit without data loss | New CSRF-protected exit POST uses existing revision/type validation and one transaction before redirect, retaining the same resumable draft. Failed/stale exit cannot overwrite it. |
| Back/reload/multiple tabs | Per-tab sessionStorage focus guides Back/management navigation back to the draft; back-forward-cache pages reload current server state; native unload warning covers unacknowledged input. Existing stale revisions still reject concurrent overwrites. |
| Visible disclosure removal | Repeated banner removed from shared/foundation UI; disclosures remain in README, AGENTS, specification, notes and source headers/comments. |
| Appearance placement | Auto/Light/Dark selector appears only in Settings. Every page still applies persisted browser theme and automatic device preference. |
| Neutral dark/colorful light | Charcoal/navy surfaces replace green backgrounds; restrained colored primary controls, progress, current navigation and highlights. |
| Person accents | Independent Blue/Teal/Green/Purple/Orange/Red, accessible fixed light/dark pairs, default blue, server persistence across devices/restarts, Settings person context. No arbitrary CSS input. |
| Compact navigation | Small brand/person header, selected-page pills, secondary menu; workout header has only brand/person. |
| Workout essentials | Routine/exercise/count/progress, previous measurement, conditional increase, one typed input, current increase flag and main actions. No appearance/global menus competing with entry. |
| Details uncluttered | Dates, exact timestamps, timezone, notes and extra explanation remain in More → Workout details. Detailed confirmation timestamp is updated only on server acknowledgment. |
| Save status | Compact ✓ Saved / Saving / Save failed; detailed failure text stays available with retained input. No local-only edit is called Saved. |
| Previous session | Short label; date moves to details. Existing matching identity/type/unit/meaning, skipped fallback and effective correction readers unchanged. |
| Previous increase | Increase ↑ only for the performed previous session with a saved request; no “no increase” placeholder or skipped recommendation. Text/accessible label does not rely on color. |
| Action order/final exercise | Back/Next before Save draft/Finish; Next prominent, last exercise explicitly identified, Finish remains deliberate. Enter defaults to Save draft, not completion. |
| Secondary controls | More contains jump, overview, details, Exit Workout and confirmed Discard. All-skipped confirmation appears when needed; no essential action is hidden in More. |
| Preservation | NULL/zero, decimal truncation, integer durations, flags, progress, recovery, immutable snapshots, audits, history/charts, historical entry and all recovery/logging services remain tested. |
| Browser/screenshot evidence | Six viewport sizes × two themes and all six accents; full workflow, failed save/exit, separate browser contexts, Back/reload, text enlargement and reduced keyboard-height checks; 19 actual PNG artifacts. |
| Documentation/update safety | README/AGENTS/specification/measurement design updated, installation verification labeled historical, explicit no-migration update steps below. |
| GitHub workflow | Reviewed and approved; verify, fast-forward main, push, verify remote containment, then delete the fully merged feature branch. No deployment. |

## Actual rendered screenshots and visual inspection

All images use synthetic records in local Chromium; no generated mockup/images
or production screenshots are used. Device pixel ratio is 1 for reviewable CSS
viewport sizes; mobile/touch browser emulation is enabled. Images are committed
under [docs/phase-6](docs/phase-6).

- [Before: 390×844 dark](docs/phase-6/before-390x844-dark.png) reconstructs the
  approved main release's templates/assets from immutable commit `2be4c74`, using
  the same synthetic snapshot services. It is not claimed to be the user's actual
  iPhone screenshot. The legacy green layout spans multiple phone heights before
  reaching Next, with the disclosure, timestamps, expanded navigation and Appearance.
- [After: weight, 390×844 dark](docs/phase-6/workout-390x844-dark-green.png) keeps
  input, Next and Save/Finish visible, with neutral surfaces and green accents only.
- [After: time, 390×844 dark/purple](docs/phase-6/time-390x844-dark-purple.png)
  shows a compact minutes/seconds pair and the final-exercise state.
- [Small phone: 320×568 light](docs/phase-6/workout-320x568-light-blue.png).
- [People, 390×844 light](docs/phase-6/people-390x844-light.png).
- [Settings, 390×844 dark](docs/phase-6/settings-390x844-dark.png).
- [History](docs/phase-6/history-390x844-light.png) and
  [Progress](docs/phase-6/progress-390x844-light.png), with preserved corrections.
- [Desktop, 1280×900](docs/phase-6/workout-1280x900-light-red.png).
- [390×420 keyboard-height simulation](docs/phase-6/workout-390x420-keyboard-simulation.png).

The rendered baseline, weight/time phones, smallest phone, People, Settings,
charts, desktop and reduced-height screenshots were visually inspected. This
caught narrow backup-table headers, which now scroll within their card when
populated and use a simple empty state when no backups exist. Input/secondary
control borders were strengthened while decorative card borders stay subtle.

| CSS viewport | Accent | Light/dark result |
| --- | --- | --- |
| 320×568 | Blue | No horizontal overflow; controls remain reachable, natural vertical scrolling allowed. |
| 375×667 | Teal | No horizontal overflow, touch-sized controls. |
| 390×844 | Green | Weight input, Next and Save/Finish fit without scrolling; timed layout also inspected with Purple. |
| 430×932 | Purple | No horizontal overflow, compact phone layout. |
| 768×1024 | Orange | Readable tablet layout, no overflow. |
| 1280×900 | Red | Centered focused card, no overflow/clipped controls. |

Actual computed primary-button foreground/background contrast exceeds 4.5:1 in
all 12 theme/accent combinations. Main controls are at least 44px high. A reduced
390×420 viewport and 125% root text size retain normal scrolling/reachable actions.
No body scroll lock/fixed-height viewport hides essential controls.

Tests normally write images to `/tmp/workout-ux-screenshots` to avoid dirtying Git.
Set `WORKOUT_UX_SCREENSHOTS` to an artifact directory to capture review evidence.
This is a test-only option, not new application/Docker configuration.

## Preferences, draft state and database compatibility

**No schema migration is required.** Schema 4 remains current. Schema definitions,
measurement services, migration/candidate validation, backup/restore services,
operations metadata, scheduler and Compose configuration are unchanged from main.
No existing database file or actual household storage was read/modified in this task.

Person accents use private `config/person-preferences.json`, version 1, keyed by
permanent person UUID. Missing file means blue and never creates a file on startup.
An explicit Settings POST validates the person using read-only SQLite, then writes
an exclusive private pending JSON file, fsyncs it, atomically replaces the preference
selection and syncs its directory, all under the existing root lock. Concurrent
updates preserve different people. Tests compare original SQL bytes/mtime and
simulate failed publication. Invalid colors and malformed/private-file violations
are refused; corrupt existing preferences are never overwritten. Read-only pages
fall back to blue so backup/recovery UI remains available.

The preference file is external to SQLite and independent of operations.json;
no metadata format change can break older backup/scheduler readers. Database-only
backups/restores do not include or reset person colors; protect the full external
tree separately. Stale preference UUIDs after restoring an earlier dataset are
harmless and not silently purged. Auto/Light/Dark remains device/browser-local.

Tab focus is workflow assistance, not authentication: it has no password, shared
household lock or server-side restriction against another session. Active HTML
omits global switching. Native Back into management returns to the existing draft
when sessionStorage/network permits. Completion/discard status or successful
save-and-exit releases this tab. Server-side person ownership, generation-bound
CSRF, optimistic draft revisions and atomic saves remain authoritative. An exit
uses the same typed measurement validator and cannot modify completed snapshots.

## Automated validation

```sh
WORKOUT_CONTAINER_TESTS=1 \
WORKOUT_UX_SCREENSHOTS=/workspace/Workout-Tracker-vibe-webapp/docs/phase-6 \
/workspace/phase1-venv/bin/python -m pytest -q
```

Final approved-merge verification repeated the complete suite: **246 passed in
159.38 seconds; zero failures/skips.** The earlier implementation run also passed
all 246 tests in 150.72 seconds. This includes **222 service/
storage/HTTP tests, 15 Chromium tests and 9 Docker tests**. All earlier tests are
retained; outdated UI assertions were updated for menu/Settings placement and
compact status without removing their behavioral checks. New tests cover private
preference persistence/concurrency/failure, unchanged SQL, archived people,
CSRF/invalid colors, revision-safe exit, complete exit/switch/resume/history,
previous effective corrected measurements, all viewport/theme/accent bounds,
contrast, keyboard-height/text enlargement and real screenshots.

Existing coverage still tests SQL NULL/zero, weight truncation, time, all-skipped
confirmation, discard consent/cancel, stale tabs, delayed acknowledgments/typing,
offline failure, routine management/copying, historical entry/correction/audits,
backup/restore rollback/identity/generation checks, scheduling, logs, actual
Gunicorn/container replacement and documented Compose bootstrap. The review
image was rebuilt with the new source as `workout-tracker:phase6-review`.

`git diff --check`, Python source disclosure/function-explanation checks and
`pip check` passed. Baseline schema/recovery/measurement/Compose files compare
unchanged. No new runtime dependency, external asset/CDN or network service.

## Existing-installation update — after the approved merge

Finish & Save or Exit Workout with confirmed saves before maintenance. Keep your
existing `.env`, UID/GID, network bind/port and external storage. Do **not** run
init-storage, migrate-storage or restore merely to install this UI release.
The commands use the README checkout path `/opt/workout-tracker`; substitute your
existing checkout directory if different, without changing your data-root setting.
The following is documentation for the user/operator, not a deployment performed
by this task. Run only once the approved changes are merged to main:

```sh
cd /opt/workout-tracker
# Stop if tracked local changes exist; reconcile rather than discarding them.
git status --short
git fetch origin
git merge --ff-only origin/main
# Preserve the current image before rebuilding.
docker image tag workout-tracker:local "workout-tracker:before-ux-update-$(date -u +%Y%m%dT%H%M%SZ)"
docker compose config --quiet
docker compose build
docker compose stop
docker compose run --rm --no-deps web python -m workout_tracker check-storage \
  --data-root /var/lib/workout-tracker
# Only after successful compatibility verification:
docker compose up -d --no-build
docker compose ps
docker compose exec -T web python -c \
  'import json,urllib.request; d=json.load(urllib.request.urlopen("http://127.0.0.1:8000/health/ready",timeout=10)); print(d); assert d["status"]=="ready" and d["app_version"]=="0.6.0" and d["schema_version"]==4'
```

Choose person → Person appearance to save their accent. Existing people default
to blue automatically without touching SQL. Browser theme preference is retained.
Do not delete data, change ports, remove retained versions, or initialize a new
storage tree if the compatibility check fails. Stop and inspect instead.

## Known limits

- This is Chromium mobile emulation and actual browser screenshots, not a physical
  iPhone/Safari/VoiceOver audit. Browser chrome and the OS keyboard are not rendered;
  reduced viewport testing approximates their space constraints. Real-device
  follow-up remains the user's review/deployment decision.
- Long names/notes, smaller heights or enlarged text can require vertical scrolling;
  controls are not clipped to force a one-screen result. Secondary details are
  intentionally collapsed. Desktop workouts use a centered readable card.
- Hard browser close, network loss before acknowledgment and disabled JavaScript/
  sessionStorage cannot guarantee unsent input or navigation assistance. Save
  failures and native unload warnings are explicit; confirmed SQL drafts remain
  recoverable. There is no offline queue or authentication claim.
- Person appearance requires page reload/new navigation to reflect another
  device's color change; browser-local theme changes apply immediately.
- Preferences are not part of SQLite-only backups, and a damaged preference file
  needs operator inspection rather than automatic replacement. Household-sized
  configuration is bounded to 1 MiB; no automatic pruning.
- Existing Phase 1–5 local filesystem, cooperative locking, synchronous maintenance,
  no-auth LAN, backup/offsite and uncertainty-recovery limits still apply.
- No actual server access, network/port adjustment, real-data operation or
  deployment is included. Merge/cleanup is explicitly approved; stop afterward.


## Existing update-script compatibility

An existing script that fetches/fast-forwards approved main, rebuilds the same
Compose services and recreates containers while retaining the existing .env and
external data root is compatible with this release. No schema-4 migration,
initialization or restore step should be added. Stop both writers for read-only
compatibility verification as shown above. No server configuration/port change
is required; the new preference file is created only after explicitly saving
a person's accent. Confirm app 0.6.0 / schema 4 readiness afterward.

The user's actual update script was not supplied, so its arbitrary commands have
not been audited. If it initializes, migrates/restores automatically, deletes
persistent data, changes mounts/ownership/ports or discards local Git work, do
not run it unchanged. Use the exact conservative sequence above instead. This
is a compatibility assessment, not a deployment or real-database verification.
