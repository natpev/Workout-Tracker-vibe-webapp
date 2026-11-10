# Phase 12 — UI cleanup, release notes and documentation

**SHAMELESSLY VIBE-CODED 🤖**

This application was built with a healthy dose of AI, questionable amounts of confidence, and minimal human supervision. It appears to work, but don’t mistake that for a warranty. Use at your own risk, and keep backups.

Started from approved main a9a021c19a84c6e79ec9d535bbebabaf4ec98573.
Branch phase-12-ui-and-documentation. Application 0.12.0, schema 8 unchanged.
Direct main merge/push/cleanup authorized without any PR attempt or deployment.

## Library and selectors

Cards show the exercise name and short Edit Defaults button with an accessible
description linking it to the heading. Library IDs appear on individual editing
screens, not listings. Global renaming moved into the defaults form; name/defaults
save together under CSRF, name+preset fingerprint and a single locked transaction.
Duplicate/invalid names or targets roll back all changes and retain raw input.
Historical snapshots and routine configurations stay unchanged. Legacy schemas
retain name-only editing without adding preset storage or startup migration.

Ordinary routine/Progress/export choices display names while submitting original
IDs. Matching-name options receive deterministic numbers within the displayed
list, without merging, deleting, investigating or repairing identities. IDs remain
on deliberate troubleshooting/detail and impact-review screens; CSV's deliberate
same-name disambiguation remains unchanged.

## Progress and update display

Default 3 Months; presets 3/6/12/24 calendar Months, All Time and Custom. Existing
inclusive day-after-clamped-anniversary arithmetic uses configured IANA local date.
Old 30/60/90 bookmarks retain exact day bounds as Custom, not silently different
graphs. Exercise, range, history/refresh/Back/CSV state and combined charts remain.

App notes wrap short bullets but contain/scroll unbroken long text. App update log
and independent host console preserve original line breaks in monospace with no
soft wrapping and internal two-axis touch scrolling. Safe classification, bounded
rings, escaping, live polling and scroll-position behavior are unchanged. Independent
host assets need explicit service upgrade; they never install at app startup.

## Versioned release notes

releases/0.12.0.json contains the actual concise user-facing bullets. Future
releases must provide releases/VERSION.json in the approved source commit. The
host obtains notes using git show at the exact pinned main SHA already used for
APP_VERSION/target metadata, before installation; it never infers notes from Git
logs. Version/shape/size/control-character checks reject invalid modern notes.
Validated plain text persists on the independent host and remains visible while
Flask stops. Both app and host templates escape it. Older releases without notes
get a neutral unavailable message; 0.12.0+ releases require a valid file. Old hosts
retain their safe update flow, while the new app hides legacy raw Git-log notes.

An explicit one-time --upgrade-service copies the new host parser/status assets.
No new updater script, source policy, install consent, migration or recovery
mechanism is introduced. V4 and browser continue sharing one engine. Source/commit
pinning, original preservation, verified backups and health checks remain intact.

## README, disclosure and permanent rules

README is rewritten as a user guide: friendly household/private-server opening,
exact humorous disclosure, Installation — Start Here, numbered new-install steps,
then usage, people/routines/library/types/history/charts/CSV, backups, separate
updates, troubleshooting, security and linked developer material. It distinguishes
application code from data and never tells existing users to initialize again.
Commands were checked against Compose, Dockerfile, CLI, host installer and v4.
The older deep reference is retained in docs/DEVELOPER_REFERENCE.md with an explicit
historical-guidance notice; detailed recovery remains in deployment/README.md.

Active supported source headers/documentation use SHAMELESSLY VIBE-CODED. Correct
comment syntax remains; JSON notes use adjacent disclosure documentation. No
visible app banner, Git-history rewrite or database/audit rewrite. Professional
security audit is not claimed. AGENTS.md and PROJECT_SPEC.md permanently require
README review and accurate human-readable notes before EVERY future release,
including patches, with explicit reporting even if no README change is needed.

## Existing server upgrade

Schema 8 needs no migration. Existing Compose/.env, addresses and time zones stay.
Over SSH as root, ensure no update job is running; from a clean main checkout:

```bash
(
  set -e
  cd /root/WorkoutTracker/app
  test "$(git branch --show-current)" = main
  test -z "$(git status --porcelain)"
  git fetch origin main
  git merge --ff-only origin/main
  bash deployment/update_workout_tracker_v4.sh \
    --upgrade-service --lan-address 10.0.69.9 \
    --app-url http://10.0.69.9:8000 --status-port 8001
)
```

Keep your actual address if different. Then browser Check → review v0.12.0 notes →
confirm Install, or run the existing repository v4 command. Verify /health/ready
reports 0.12.0/schema 8, and independent status has notes and scrollable nonwrapped
console. Make a verified backup. No server command was executed during development.
An older host can install the code first but needs the explicit upgrade for new
notes/host styling. No new host runtime is installed by containers automatically.

## Verification and limitations

Final complete run: **509 passed, 0 failed, 0 skipped in 704.29 seconds** on
2026-11-10: **423 backend/script, 69 Chromium browser, 17 Docker integration**.

```sh
WORKOUT_CONTAINER_TESTS=1 /workspace/phase1-venv/bin/python -m pytest -q \
  --tb=short --show-capture=no --junitxml=/tmp/phase12-final.xml
```

The first full run had 508 passes and one retained browser fixture failure: its
old unversioned notes were correctly hidden by the new UI. The fixture now models
the version-matched host protocol without removing any assertions. The isolated
workflow passed, followed by the clean complete run above. Dedicated tests retain
older-host fallback coverage. Existing test edits otherwise reflect requested
labels, presets, disclosure and release-version changes; no protections weakened.

Coverage includes atomic rename/default rollback, duplicate/stale validation,
identity/snapshot/routine independence, submitted ID values with display-only
labels, calendar clamping/IANA/legacy ranges, combined charts, approved-SHA notes,
malformed/missing/oversized/version-mismatched metadata, escaping, app/host scrolling,
live host polling after Flask stops, all earlier workout/correction/CSV/backup/
restore/scheduler/updater/migration regressions and disposable container replacement.
New browser cases cover 320/390 portrait, 844 landscape and 1280 desktop, Light/Dark;
the retained suite includes tablet widths and Auto theme.

README was opened and reviewed against real features, Compose/environment/CLI,
installer and v4; its relative links and shell syntax pass automated checks.
Commands match the repository, but root SSH/package/systemd provisioning and
physical server installation are not executed by those checks. Release notes
were reviewed against the user-facing diff and exact 0.12.0 metadata.
Python compilation and git diff --check also pass. The tested runtime image is
sha256:013fd2d650dc157836be0a218405408d81009368be8f92472aae1d84cbc8e0f8;
only documentation and the test fixture changed after the runtime build.

Tests use disposable
storage, synthetic records, loopback HTTP and local Docker only. Browser coverage
includes portrait/landscape/mobile/desktop, themes, actual form submissions,
paired charts, downloads, overflow geometry and host polling while Flask stops.

No physical iPhone/Safari, clean physical Linux installation, SSH provisioning,
firewall, live systemd/server, ARM/rootless production deployment or real workout
data is claimed tested. Documentation's root/server paths are instructions for
the operator, not permissions exercised by the development environment. Existing
limits on unacknowledged input, local backups, exact-schema restore and private-LAN
security remain. No production deployment or next phase is authorized/performed.
