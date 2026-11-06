# PROJECT_SPEC.md — Workout Tracker Design

> **SHAMEFULLY VIBE-CODED PROJECT.** This is a human-directed, AI-generated software project. Its code has not been assumed to be professionally audited, secure, or correct.

**Project status:** Phase 1 and Weight/Time design approved; Phase 2 authorized and implemented for review. Stop before Phase 3. No deployment or real workout data is authorized.
**Current scope:** people, permanent exercise definitions, typed routine configuration, and the minimal explicit candidate-only migration necessary for schema 2. Workout logging, snapshots/results, charts, automatic backups, restore UI, and scheduling remain later phases.
**Goal:** a small, reliable, phone-friendly household workout tracker, with a better desktop view for history and charts.

## 1. Technology, environment, and repository

- **Backend:** Python + Flask.
- **Database:** SQLite (simple local file database).
- **UI:** responsive HTML/CSS with minimal JavaScript; a charting library for exercise history.
- **Packaging/hosting:** Docker Compose on a Linux home server, possibly hosted by Proxmox; no requirement for cloud services or public internet access.
- **GitHub:** initially private repository. Codex may plan and implement code only after user approval; use reviewable changes.
- **Access:** local home network only for v1. Architecture must permit later remote access with HTTPS/authentication, but not expose it now. Initial user switching is **not authentication**.
- **Durable storage:** active DB, prior schema DBs, manual/automatic backup files, backup schedules/configuration, and logs must live on the host outside the Git repository and disposable application containers.

## 2. Users, routines, and exercise definitions

- Choose a household user via simple tabs/selector (like a browser tab); **no passwords** initially.
- Each person owns independent routines, workout drafts, history, weights, and increase flags.
- Create, rename, edit, duplicate, reorder, and delete individual routines.
- Within a routine, add/edit/remove/reorder exercises and choose **Weight** or **Time**, define sets for both, and configure target reps (Weight) or target minutes/seconds per set (Time). Optional exercise notes/instructions and equipment labels are desirable, but must not complicate basic logging.
- **Copy from user:** select a different user and a routine, create an independent copy of the routine definition. No persistent link between copies; no copied logged weights, increase flags, or workout history.
- **Duplicate own routine:** same independence behavior for a copy within one user.
- Modifying/deleting a routine must never rewrite or remove already completed workout history.
- Maintain permanent, person-owned exercise identities; historical snapshots survive edits/removal. Optional exercise notes are included. Archive users who have workout history.

## 3. Everyday workflow: agreed behavior

1. Open webpage.
2. Select person.
3. Select one of that person's routines to start.
4. Record the session date and start time automatically using a consistent server-local timezone; allow explicit past dates in the separate historical-entry workflow.
5. Display **one exercise at a time**, with its exercise name, prescribed sets × reps (Weight) or sets × target duration (Time), that person's previous matching measurement, and its previous **increase next time** flag.
6. Enter **one current measurement for the whole exercise** (weight for Weight; duration for Time, not one per set) and optionally mark **increase next time**. Do **not** ask for actual reps/set-by-set results during normal workout entry.
7. Navigate by **Back**, **Next**, exercise jump list, and expandable routine overview; show all exercise completion states and a whole-workout progress bar.
8. **Finish & Save** both saves and completes the workout in one clear action. All routine exercises, including skipped ones, are captured in the completed session.
9. If unfinished, automatically preserve a resumable draft when navigating away or losing the browser session. Save draft changes promptly on the server and show a clear save/error status so a failed save is not mistaken for a successful one.
10. **Discard Workout** must display **“Are you sure?”**, an acknowledgment checkbox, and **Cancel / OK**; OK stays disabled until the checkbox is checked. Cancel preserves the draft; confirmation discards only the *unfinished* session, never past completed workouts.

### Weight, time, and skipped-exercise semantics (important)

- The current measurement input initially starts **blank** for both types; previous performance is visible for reference but is **not silently prefilled**. This prevents accidentally treating a skipped exercise as performed.
- Weight defaults to pounds and supports decimal values. Explicit zero is valid and counts as an entered weight; it is never treated as NULL. Exact decimal precision remains to be chosen before workout storage implementation.
- When the user finishes/saves, **each exercise from the session's routine snapshot gets a saved workout-entry record**, even if its applicable measurement was never entered.
- If skipped, the applicable measurement must be true SQL **`NULL`**: weight for Weight exercises or duration for Time exercises. `NULL` ≠ `0` and ≠ the previous measurement; a skipped exercise must **not be omitted** from the saved workout.
- A blank measurement does not count toward the workout progress bar. Progress means **number of exercises with non-NULL applicable measurements / total exercises**, across both types. Explicit zero weight counts as entered. Navigating to an exercise does not mark it done.
- Tables display skipped entries clearly as **Skipped** or an em dash; charts omit/gap skipped measurements rather than plotting zero. Skipped entries remain visible in history and are excluded from numeric progress calculations.
- Show the previous session's matching measurement and increase indicator. If that session skipped the exercise, show that fact plus the last successfully performed matching measurement, including an explicitly entered zero weight. Do not compare or inherit recommendations across Weight/Time type changes.
- Increase-next-time note applies to a performed exercise; do not invent a new increase recommendation when its applicable measurement is NULL. Use “Increase weight next time” or “Increase duration next time” according to type.

### Weight meaning and historical integrity

- One numeric weight per exercise, for example 40 lb **per dumbbell** vs 95 lb **total barbell**. UI labels/metadata should make the meaning clear without requiring multiple weight fields.
- Keep a **snapshot** of exercise names, order, measurement type, target sets, target reps or duration, unit/weight meaning, optional exercise notes, and related prescribed routine information in every saved session; changes to routines never alter old sessions.
- A user's previous weights/increase flags must be drawn only from that user's logged exercise history; copied routine ownership must not leak values from another person.
- Prevent accidental duplicate workouts if Finish & Save is tapped twice or retried.
- Time exercises have a target duration per set entered as minutes and seconds, and one actual duration per exercise regardless of set count. Store both target and actual durations as integer seconds, not decimal minutes; do not multiply actual duration by sets. Exact zero-duration rules and maximum limits remain open.
- Allow one active draft per user. Allow completing an entirely skipped workout only after confirmation.

## 4. Manual historical entry and history

- Manually enter workouts performed before app installation, selecting the user and any past calendar date.
- Permit selection of an existing routine or manual exercise composition if the old routine no longer matches current ones. Store historical exercise snapshots rather than overwriting current routines.
- Enter the same one weight or duration per exercise, according to its snapshotted type (or leave skipped exercises NULL), optional increase flags, and preserve a consistent historical date.
- Provide a history view with past sessions by date/person/routine, drill-down exercise records, and an exercise selector plus date-range filters.
- Show separate weight/duration progression charts and tables of measurements, sets, target reps or duration, and increase flags. Weight axes use pounds; duration axes use time labels backed by integer seconds. Never combine incompatible units on one numeric series. Personal records must use the matching type and unit. User-specific data only.
- Allow corrections to previously saved workouts with confirmation and validation. Preserve routine snapshots except for deliberate validated corrections; correction fields/audit detail remain to be specified before that phase. Deletion of completed workouts is not approved.

## 5. Screen designs and styling

### Screen A — Home
- Prominent user-switch tabs/selector, Start Workout, History & Progress, Manage Routines, Settings.
- Keep basic workout action obvious and minimize text-entry steps.

### Screen B — Workout selection
- List only the selected person's routines as clear cards with Start action; provide access to copy/manage routines.

### Screen C — Workout entry (primary mobile screen)
- Top: selected person, routine, automatic date/time, exercise count and completion progress bar.
- One focused exercise card: name, sets × reps (Weight) or sets × duration (Time), previous matching measurement and increase indicator, one blank actual measurement input, and the type-specific increase-next-time toggle. A minutes/seconds duration control represents one measurement, never separate per-set results.
- **Back / Next** oval buttons; exercise jump list and full/expandable routine overview to navigate out of order.
- **Finish & Save** always available; **Discard Workout** with checkbox acknowledgment confirmation.
- Show completed/skipped/unentered states without confusing navigation progress with actual logged measurements.
- On desktop, optionally show exercise overview beside current exercise.

### Screen D — Routine editor
- Rename/reorder workouts; reorder/add/edit/delete exercises; define sets/reps or sets/target duration; copy another user's routine as an **independent** copy; duplicate own routine.

- Include a keyboard-accessible segmented **Weight / Time** selector when adding/editing a routine exercise. Both modes offer positive-integer sets through rounded plus/minus controls or a numeric input. Weight shows target repetitions per set; Time shows target minutes and seconds per set. Hide and clear inapplicable target fields on save; the server validates the selected type. Examples: Dumbbell Bench Press — 3 × 12 reps; Plank — 3 × 45 seconds.

### Screen E — History and charts
- Session table; exercise progress chart; choose user, exercise and date range; manually record historical workouts.

### Screen F — Settings
- User management; Appearance; Database Backups (manual, automatic, history, restore); Application Logs.

### Appearance
- Simple minimal visual design, spacious mobile tap targets, rounded cards, **oval/round pill buttons**.
- Theme options: **Auto** (follow phone/computer appearance, the default), **Light**, **Dark**, with a manual override stored for that device/browser rather than changing the theme unexpectedly on another device.
- Phone primarily for workout entry; PC primarily for routine editing, history tables and charts, but both should remain usable everywhere.

## 6. Data model (Phase 2 implemented; workout tables still conceptual)

- **Users (`people`)** — permanent UUID, display name, archive flag. Phase 2 always archives rather than deletes people, preserving records whether or not history exists.
- **Exercises (`exercises`)** — permanent person-owned UUIDs, names and archive status, independent of future historical snapshots. Renaming a reused identity updates this person’s routine displays; independent copies receive new identities.
- **Routines (`routines`)** — permanent UUID, owner, name, archive status and ordering. Delete removes from active lists by archiving, never reuses an identity.
- **Routine exercises (`routine_exercises`)** — ordered permanent exercise references, measurement type (`weight` or `time`), positive target sets, mutually exclusive target reps or integer target-duration seconds, optional notes/weight-meaning labels, and pounds for Weight (NULL unit for Time). Composite foreign keys enforce matching ownership. Type is selected on the routine exercise, not inferred from its name.
- **Workout sessions (not implemented)** — person, started/finished timestamps, date, selected routine identification, draft/completed/discarded status.
- **Workout entries (not implemented)** — ordered per-exercise snapshot (name, sets/reps, equipment/weight meaning), separate nullable **weight** and integer **actual_duration_seconds**, snapshotted measurement type, sets, reps or duration target, nullable/non-applicable increase flag, optional notes. Only the applicable actual measurement may be non-NULL; both are NULL for a skip. Routine edits do not change snapshots; explicit confirmed corrections may update saved workouts.
- **Backup/scheduler metadata** — settings and run status persist independently of code deployment; avoid coupling fragile critical state to a DB migration.
- **Schema version** — SQLite user schema version recorded separately from the Git/app release number.

The final SQL must enforce referential integrity, preserve past sessions when a routine is removed, and allow saving **every scheduled exercise row with both actual measurements SQL NULL** for skipped ones. Enforce valid type-specific target and measurement combinations with explicit NULL checks. See [MEASUREMENT_DESIGN.md](MEASUREMENT_DESIGN.md) for architecture, proposed fields, safety, and future automated acceptance tests.

## 7. Database preservation and updates

**Three distinct operations:**

1. **Normal code update without schema change:** replace/restart app code only. **No DB copy, backup, migration, replacement, or overwrite** is triggered by the update.
2. **Actual schema upgrade:** compare schema versions; stop new writes; safely snapshot old DB into a **new distinct versioned database**, migrate only the new one, verify both structural integrity and logical data equivalence; activate the new copy only after validation. Original remains intact and available. Failed upgrade leaves original active and displays/logs error. Major redesign may create new DB and import old data with the same safeguards.
3. **Backup or restore:** triggered by a manual UI action or by the separately configured backup schedule; must never happen *merely* because code was updated.

Integrity verification should include `PRAGMA integrity_check`, `PRAGMA foreign_key_check`, expected schema version, and key data counts/relationships. Never silently create a blank DB if an existing database is broken. Plan for SQLite journal/WAL handling, open connections, and an atomic active-DB switch. A code rollback after entering new workouts can lose visibility of those new workouts if pointed at an older DB: clearly disclose this and do not attempt automatic data merging.

Suggested **host** directory organization (location/configurable path still undecided):

```text
workout-tracker-data/
├── data/        # active SQLite database (persistent)
├── archives/    # old unchanged DB schema versions
├── backups/     # manual + scheduled timestamped backups
├── config/      # scheduler settings, active DB selection, run metadata
└── logs/        # durable diagnostic logs
```

These directories must be outside the Git repository and the ephemeral Docker image. An initial deployment must create missing directories with safe permissions; upgrades must never purge them.

## 8. Backups and restore (server-side)

- Settings has **Backup Now**. When pressed, store a **unique timestamped SQLite backup file in a server directory**. Never download a file to the user's browser as the normal backup workflow.
- Perform a consistent snapshot using the SQLite backup API or equivalent, validate the result, and mark last success only after validation. Show **last successful manual/automatic backup time** and list of backup files with status and type.
- **Automatic Backup settings:** enabled/disabled toggle, **frequency in positive whole days**, **time of day** (hour/minute), last automatic run, and next scheduled run. Schedule runs server-side without an open webpage; settings survive restarts and app upgrades.
- Scheduler must avoid double execution across restarts/workers; on missed runs, at most one catch-up, not a burst. Date/time should be timezone aware, with documented behavior for daylight-saving transitions.
- Never quietly overwrite or auto-delete backup files. Keep them indefinitely by default unless user later chooses explicit deletion.
- On suspected source corruption, warn instead of labeling a corrupted copy as verified. Keep all previous valid backups intact.
- Required v1 Restore UI: choose an older backup, show the archive/date, require explicit confirmation, validate selected file, preserve currently active DB separately, suspend writers, then switch safely. Never overwrite a database during migration or restoration, and never silently restore or destroy the current DB.
- Automatic backups are disabled until configured.
- App-level backup/archive files primarily protect against corruption or app mistakes. **Proxmox clones/backups** handle machine-level failure; on-server copies are not off-site protection.

## 9. Settings and log viewer

- Include searchable, read-only **Application Logs** with severity filters (Debug/Info/Warning/Error/Critical), categories, date-range filter, refresh, and expandable error details.
- Categories: app startup, workout saving, database integrity, migrations, manual/automatic backups, restores, scheduler, failures.
- Logs stored outside the replaceable container; configurable retention default around **30 days**. Do not leak private details, credentials, or raw form payloads.
- Settings also contains user management, theme selector, and database backup controls described above.

## 10. Safety, code quality, and repository requirements

- Local network access only initially; no passwords for user switching. Document that people who can reach the web app can view/edit any household user's data.
- Validate client inputs server-side, use secure SQL queries and transactions, prevent duplicate saves, protect mutating requests from CSRF, and keep backup/restore filesystem operations constrained to intended server directories.
- Test with disposable fixtures; **never run destructive tests on a real workout database.** Explicit approval required before affecting a live database or deploying.
- `README.md`, `AGENTS.md`, `PROJECT_SPEC.md`, all notes, and every source-code header where syntax permits must prominently label the project **SHAMEFULLY VIBE-CODED / AI-GENERATED**.
- Comments must explain file responsibilities, significant code blocks, function inputs/outputs, and **browser → Flask → SQLite → chart** data flow in plain language.
- Maintain a clear README with home-server installation, updates, data location, backups/restores, troubleshooting and security limitations.

## 11. Open design / implementation decisions (not yet approved)

- Exact server operating system, Proxmox VM/container layout, binding LAN interface/port, and on-host storage paths.
- Time-entry limits and whether explicitly entered zero duration is valid (blank always means skipped); exact duration control layout and time personal-record rules.
- Decimal precision and limits; whether units beyond default pounds are configurable; per-dumbbell vs total-barbell labels.
- Whether workout-level notes are needed in addition to approved optional exercise notes.
- Exact fields and audit history for confirmed workout corrections; completed-workout deletion is not authorized.
- Configured backup frequency/time and DST rules; scheduling starts disabled. On corruption, startup must refuse unsafe storage rather than replace it.
- Restore confirmation wording, backup deletion UI, and whether restore of archived schema versions is exposed in v1.

**Never treat these open decisions as permission to change the agreed core requirements.** Seek review where they materially affect data safety or the workout experience.

## 12. Approved phased implementation (Phase 2 only currently authorized)

1. **Foundation and Storage Safeguards:** Flask skeleton, Docker Compose, configuration, responsive theme, test harness, external durable paths, explicit first-install initialization, read-only compatibility checks. Only storage metadata tables; no workout tables or real data. Missing, unreadable, corrupt, or incompatible storage must fail safely. Ordinary startup never initializes, repairs, migrates, backs up, or overwrites storage.
2. **People and routines:** person selection, permanent exercises, routine editing/ordering, Weight/Time segmented selector, sets plus type-specific targets and notes, independent copies; ownership, type/target validation, accessibility, and copy-isolation tests.
3. **Workout workflow:** one draft per user, type/target snapshots, one actual weight or duration per exercise, decimal-weight/zero-weight/NULL semantics, integer seconds, matching previous values and increase flags, draft revisions, idempotent completion, all-skipped confirmation, discard dialog; transaction/concurrency and browser tests.
4. **History:** charts/tables, manual past sessions, confirmed validated corrections, date ordering, pounds/time chart labels, typed previous-performance lookup, snapshot preservation after type/target edits, NULL exclusions, and user isolation tests.
5. **Backups and recovery:** schema-versioned upgrade/copy/validation, manual/scheduled backups (disabled until configured), required safe restore UI, log viewer; corruption/interruption/DST and recovery tests, plus preservation of type, integer duration, weight, explicit zero weight, and all original NULL measurements. The minimum schema-1 → schema-2 migration was brought forward into Phase 2 as a safety prerequisite; full migration/recovery expansion remains here.
6. **Release preparation:** responsive/accessibility review, regression/integration tests, README/operator documentation, disposable deployment/recovery rehearsals. Live deployment requires separate authorization.

Build in small, reviewed increments after explicit authorization. Never deploy silently.

## 13. Phase 2 schema, validation, and maintenance

Schema 1 remains readable as a foundation-only screen. Startup never upgrades it.
`migrate-storage --confirm-upgrade` accepts only validated schema 1, uses SQLite's
backup API with a read-only source, adds the four Phase 2 tables to a distinct
candidate, verifies exact schema, integrity, foreign keys, metadata identity,
migration records and unchanged original logical data, then atomically replaces
only `config/active.json`. The original database stays unchanged under `data/`;
its selection manifest is retained under `archives/`. Failed candidates remain
for inspection and are never selected on validation failure. An already
compatible schema-2 migration request is a read-only no-op.

All application reads/writes and migration coordinate through a lock on the
persistent root directory. Definition writes use an exclusive lock and SQLite
transaction; migration refuses active connections. Stop all external database
tools before maintenance; they do not participate in this protocol. Both
schemas use rollback journals; WAL headers and sidecars are refused before
SQLite is opened. No automatic recovery, initialization, or replacement occurs.

The routine editor accepts sets 1–1000, reps 1–10000, and target duration 1–359999
integer seconds (0–5999 whole minutes plus 0–59 seconds). Optional notes are at
most 2000 characters and weight-meaning labels 200. These are configuration input
limits, not decisions about future actual-measurement limits or precision.
Switching mode clears incompatible stored fields. Native radio controls provide
the segmented selector; numeric inputs configure sets/targets. Routines may be
empty while being edited. An exercise definition cannot be archived while used
by an active routine; remove it there first. Routine copying always creates new
exercise identities, including duplication within the same person.

Management POSTs require signed-session CSRF tokens, ownership checks, and server
validation. Routine edit forms include a state fingerprint and reject stale
writes. No password/authentication is added: household user switching is still
navigation. Phase 2 has no actual weight column; future scaled integer weights
will support decimals without conflating explicit zero and SQL NULL. See
[PHASE_2_REVIEW.md](PHASE_2_REVIEW.md) for the implementation/test record.
