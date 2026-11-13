# Working on Workout Tracker

**SHAMELESSLY VIBE-CODED 🤖**

This application was built with a healthy dose of AI, questionable amounts of confidence, and minimal human supervision. It appears to work, but don’t mistake that for a warranty. Use at your own risk, and keep backups.

## Current release and scope

Version 1.0.0 targets schema 13. The user authorizes implementation, verification
and direct main merging for this release, without a pull request or PR API attempt.
Never deploy, access production workout data, force-push, bypass protections,
discard unrelated work or investigate the excluded duplicate/orphaned-history issue.
Read PROJECT_SPEC.md, README.md and maintained docs before changing application code.
Historical migration definitions and audit compatibility are required operating code.

## Architecture and documentation

Use Flask, SQLite, responsive HTML/CSS and small local JavaScript modules. Keep
business validation in shared Python services, not duplicated across seven capability
combinations. Every new workout uses one exercise-level weight and independent
set rows for enabled reps/duration/status. Frozen legacy snapshots retain their
original type/meaning and compatibility readers. See docs/MEASUREMENTS.md.

Comment every source file using valid language syntax. Header disclosure:
SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
Explain purpose, callers, data reads/writes and significant functions/data flows
in beginner-friendly comments. Explain nonobvious safety/error handling; avoid
line-by-line noise. Do not put comments in JSON. Preserve the full humorous
disclosure in documentation; never add a repeated visible application banner.

Keep components understandable: catalog/routines, measurements/workouts, history,
statistics, body weight, Garmin, reports, storage/maintenance, updater and frontend.
Avoid speculative rewrites and unnecessary abstraction. Preserve accessible
mobile navigation, one exercise per screen, themes, accent colors and local assets.

## Permanent data guarantees

- No initialization, migration, restoration, replacement or repair at ordinary
  startup. Missing/damaged/incompatible storage must fail safely.
- Migration uses a separate copied candidate and explicit consent. Verify exact
  DDL, every old cell/NULL, integrity, foreign keys and logical audit consistency
  before atomic selection. Preserve originals and failed candidates for recovery.
- Completed snapshots and original set rows are immutable. Corrections append
  confirmed before/after revisions; all readers use validated effective values.
- Preserve prior Weight Basis conversions/classification audits exactly once.
  Never restore old conversion writers. Assigned exercise basis remains permanent,
  including when weight tracking is disabled. No name-based identity merging.
- SQL NULL is unknown/unrecorded/skipped, never implicit zero. Explicit set status
  distinguishes incomplete/completed/skipped. Zero weight/reps are valid; duration
  is positive. Never fabricate old set durations/status or actual repetitions.
- Each person's routines/drafts/results/body weights/Garmin remain independent.
  Exercise definitions/IDs/defaults are shared. Copy only settings, never history.
- Defaults Only never changes routines/history. Confirmed Apply changes only the
  selected person's configurations, atomically; started drafts remain snapshots.
- All writes use existing root/database locks, owner checks, transactions, CSRF,
  revision checks and signed previews where required. Protect stale requests.
- Workout progress follows acknowledged Next navigation, never populated fields.
  Autosave must not replace focused inputs, alter their text or steal focus.
- Backups and restores preserve exact schema/identity and candidate validation.
  Never silently downgrade, restore after an update, or restart an incompatible
  old image after a new schema has been activated.
- Database downloads use SQLite backup, verify the snapshot and remove temporary
  paths. They exclude Garmin secrets and are not whole-tree backups.
- Secrets stay in private external files, mode 0600, never SQL, exports, diagnostics
  or response payloads. Garmin uses verified official endpoints, bounded HTTPS,
  no redirects, per-person credentials, idempotent source identities and safe retry.
  Keep remote requests outside workout/storage transactions.
- Passwordless trusted-LAN operation stays explicit. Do not introduce accounts,
  passwords or HTTPS requirements. LAN users can access/manage household data.

## Testing and release workflow

Use disposable synthetic storage for all tests, including failure/destructive
scenarios. Never real workout data or actual Garmin credentials. Use official API
response mocks. Run backend, Chromium/mobile, migration/backup/updater and available
Docker suites. Do not weaken/remove tests to make a release pass. Fix defects and
add regression coverage. Document actual limits; do not claim physical Safari,
hardware installation or real Garmin-account testing without performing it.

Review full diff, fetch latest main, reconcile safely and rerun affected tests.
Only merge when blocking tests pass. Push feature branch, fast-forward main where
possible, push/fetch and verify remote ancestry/SHA, then delete only the fully
merged feature branch. No PR or PR API request is permitted in this task.

## PERMANENT mandatory checks — every future release

Before merging any major, minor or patch release, bug fix, UI, database or deployment
change, Codex MUST:

1. Open and review README.md against actual features.
2. Verify installation commands, settings and upgrade/recovery instructions against
   the real repository; update anything that changed.
3. Check versions, links and referenced filenames.
4. Preserve the friendly opening, near-top Installation — Start Here guide and full
   SHAMELESSLY VIBE-CODED disclosure.
5. Include accurate concise human-readable release notes in releases/VERSION.json
   in the approved source. Match the version; no raw commit logs, hashes, internal
   filenames, schema jargon or invented features.
6. Verify release notes and record README/command/link review in the release report.
   If no README edit is needed, explicitly report that review confirmed accuracy.

These requirements are mandatory, not optional. Keep maintained docs current
rather than adding a new obsolete phase checklist for every small patch.
