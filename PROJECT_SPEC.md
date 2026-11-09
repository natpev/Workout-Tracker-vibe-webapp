# PROJECT_SPEC.md — Workout Tracker Design

> **SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.** This is a human-directed, AI-generated software project. Its code has not been assumed to be professionally audited, secure, or correct.

**Project status:** Phases 1–10 are implemented; latest patch suite passed all 439 tests (375 backend/script, 51 Chromium, 13 Docker; zero failed/skipped). Final Phase 10 suite: 384 passed, zero failed/skipped; evidence is in PHASE_10_REVIEW.md. Direct fast-forward merge/push and cleanup are explicitly authorized after verification. Do not create or attempt a pull request. No live deployment, production data or Phase 11.
**Current scope:** application 0.10.4 / unchanged schema 7. Progress/CSV/settings requirements are in section 25. Header/date requirements supersede earlier placement in section 24. Patch 0.10.1 sorts routine cards (section 22); patch 0.10.2 fixes hamburger positioning (section 23). Phase 10 adds inline historical validation, structured optional time, Progress quick ranges and point tooltips, automatic independent update tabs and sanitized live host output. Existing defaults, Administration, navigation, accents and safe storage remain. No accounts, passwords, login, roles, HTTPS or certificates.
**Goal:** a small, reliable, phone-friendly household workout tracker, with a better desktop view for history and charts.

## 1. Technology, environment, and repository

- **Backend:** Python + Flask.
- **Database:** SQLite (simple local file database).
- **UI:** responsive HTML/CSS with minimal JavaScript; locally rendered SVG charts for exercise history.
- **Packaging/hosting:** Docker Compose on a Linux home server, possibly hosted by Proxmox; no requirement for cloud services or public internet access.
- **GitHub:** initially private repository. Codex may plan and implement code only after user approval; use reviewable changes.
- **Access:** local home network only for v1. Architecture must permit later remote access with HTTPS/authentication, but not expose it now. Initial user switching is **not authentication**.
- **Durable storage:** active DB, prior schema DBs, manual/automatic backup files, backup schedules/configuration, and logs must live on the host outside the Git repository and disposable application containers.

## 2. Users, routines, and exercise definitions

- Choose people through the Phase 6 **People cards** (existing people before Add person), without passwords or automatically selecting a prior person. Separate menus provide management/history/preferences; do not add browser-style account tabs.
- Each person owns independent routines, workout drafts, history, weights, and increase flags.
- Create, rename, edit, duplicate, reorder, and delete individual routines.
- Within a routine, add/edit/remove/reorder exercises and choose **Weight** or **Time**, define sets for both, and configure target reps (Weight) or target minutes/seconds per set (Time). Optional exercise notes/instructions and equipment labels are desirable, but must not complicate basic logging.
- **Copy from user:** select a different user and a routine, create an independent copy of the routine definition. No persistent link between copies; no copied logged weights, increase flags, or workout history.
- **Duplicate own routine:** same independence behavior for a copy within one user.
- Modifying/deleting a routine must never rewrite or remove already completed workout history.
- Maintain permanent, global exercise identities; historical snapshots survive edits/removal. Optional exercise notes are included. Archive users who have workout history.

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
- Phase 3 rule: weight defaults to pounds with at most **one decimal place**. Truncate additional digits, **never round**: 40.99 → 40.9; 42.56 → 42.5; whole 40 displays as 40.0. Store integer tenths of a pound (`actual_weight_tenths_lb`), so 40.9 lb = 409. Parse decimal input exactly rather than using binary floating-point rounding. Explicit zero is valid, stores 0, and counts as entered; empty input stores SQL NULL. This is implemented in Phase 3; retained Phase 2 databases are not altered in place.
- When the user finishes/saves, **each exercise from the session's routine snapshot gets a saved workout-entry record**, even if its applicable measurement was never entered.
- If skipped, the applicable measurement must be true SQL **`NULL`**: weight for Weight exercises or duration for Time exercises. `NULL` ≠ `0` and ≠ the previous measurement; a skipped exercise must **not be omitted** from the saved workout.
- The workout bar uses the furthest acknowledged Next destination, independent of measurements. Weight, duration, flags and ordinary autosave never raise it; Back/Jump do not add progress and revisits do not count twice. Skipped exercises advance through Next. Performed counts still distinguish true NULL from valid zero for completion confirmation/statistics. This supersedes the former measurement-population bar.
- Tables display skipped entries clearly as **Skipped** or an em dash; charts omit/gap skipped measurements rather than plotting zero. Skipped entries remain visible in history and are excluded from numeric progress calculations.
- Show the previous session's matching measurement and increase indicator. If that session skipped the exercise, show that fact plus the last successfully performed matching measurement, including an explicitly entered zero weight. Do not compare or inherit recommendations across Weight/Time type changes.
- Increase-next-time note applies to a performed exercise; do not invent a new increase recommendation when its applicable measurement is NULL. Use “Increase weight next time” or “Increase duration next time” according to type.

### Weight meaning and historical integrity

- One numeric weight per exercise, for example 40 lb **per dumbbell** vs 95 lb **total barbell**. UI labels/metadata should make the meaning clear without requiring multiple weight fields.
- Keep a **snapshot** of exercise names, order, measurement type, target sets, target reps or duration, unit/weight meaning, optional exercise notes, and related prescribed routine information in every saved session; changes to routines never alter old sessions.
- A user's previous weights/increase flags must be drawn only from that user's logged exercise history; copied routine ownership must not leak values from another person.
- Prevent accidental duplicate workouts if Finish & Save is tapped twice or retried.
- Time exercises have a target duration per set entered as minutes and seconds, and one actual duration per exercise regardless of set count. Store both target and actual durations as integer seconds, not decimal minutes; do not multiply actual duration by sets. Phase 3 actual duration must be at least 1 second: zero seconds is invalid, and empty duration stores SQL NULL for a skipped exercise. Phase 9 accepts minutes only, seconds only, or both; a blank part is zero when another is supplied. Seconds may exceed 59 and total seconds are normalized. Reject malformed/negative/zero-total/overflow values. Fully blank means SQL NULL. Phase 3 uses the signed 64-bit SQLite integer storage limit and bounds form strings to 100 characters; it does not change retained Phase 2 databases.
- Allow one active draft per user. Allow completing an entirely skipped workout only after confirmation.

## 4. Manual historical entry and history

- Manually enter workouts performed before app installation, selecting the user and any past calendar date.
- Choose a routine and prepare independent historical snapshots. If an old prescription differs, create or duplicate/configure a separate routine first using the existing editor; this supports manual composition without changing the routine used by active workouts. Store snapshots rather than overwriting current routines.
- Enter the same one weight or duration per exercise, according to its snapshotted type (or leave skipped exercises NULL), optional increase flags, and preserve a consistent historical date.
- Provide a history view with past sessions by date/person/routine, drill-down exercise records, and an exercise selector plus date-range filters.
- Show separate weight/duration progression charts and tables of measurements, sets, target reps or duration, and increase flags. Weight axes use pounds; duration axes use time labels backed by integer seconds. Never combine incompatible units on one numeric series. Personal records must use the matching type and unit. User-specific data only.
- Allow corrections to previously saved workouts with confirmation and validation. Preserve routine snapshots except for deliberate validated corrections; Phase 4 appends complete before/after effective actual values and occurrence, with correction timestamp, sequential revision, confirmation and stale-submission rejection; original completed records remain immutable. Deletion of completed workouts is not approved.

## 5. Screen designs and styling

### Screen A — Home
- People is the opening screen: names/cards select routines directly, separate accessible hamburger disclosures offer management actions, and Add person follows existing people. Routine cards provide prominent Start workout and secondary Edit routine. Appearance is in Settings only.
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

## 6. Data model (schema 6 retains global exercise identities and detaches routine snapshots)

- **Users (`people`)** — permanent UUID, display name, archive flag. Phase 2 always archives rather than deletes people, preserving records whether or not history exists.
- **Exercises (`exercises`)** — permanent global UUIDs, names and archive status. person_id retains original registration provenance only. Renaming updates current displays across people; historical snapshots retain their names. Copies reuse IDs. Legacy matching names are not merged.
- **Routines (`routines`)** — permanent UUID, owner, name, archive status and ordering. Schema 6 deletes the definition/configuration permanently after confirmation and draft checks; saved routine IDs/names remain independent snapshots. Retained older schemas use archival behavior.
- **Routine exercises (`routine_exercises`)** — ordered permanent exercise references, measurement type (`weight` or `time`), positive target sets, mutually exclusive target reps or integer target-duration seconds, optional notes/weight-meaning labels, and pounds for Weight (NULL unit for Time). Routine configurations and session entries retain composite ownership foreign keys. Schema 6 routine IDs on live/historical snapshots are independent immutable references, with new insert guards enforcing routine/preparation ownership; exercise foreign keys remain global. Type is selected on the routine exercise, not inferred from its name.
- **Workout sessions (`workout_sessions`)** — permanent ID, person/routine ownership, routine-name snapshot, UTC started/updated/finished/discarded timestamps, workout date, IANA timezone, draft/completed/discarded status, revision, snapshot entry count and current position. A unique partial index permits only one draft per person.
- **Workout entries (`workout_entries`)** — ordered per-exercise snapshot (name, sets/reps, equipment/weight meaning), separate nullable integer **actual_weight_tenths_lb** (tenths of a pound, including valid 0) and integer **actual_duration_seconds** (minimum 1 when non-NULL), snapshotted measurement type, sets, reps or duration target, nullable/non-applicable increase flag, optional notes. Only the applicable actual measurement may be non-NULL; both are NULL for a skip. Routine edits do not change snapshots. Completed/discarded entry updates and entry deletion are blocked by schema-3 triggers; Phase 4 corrections append separate revisions and never disable those triggers.
- **Backup/scheduler metadata** — settings and run status persist independently of code deployment; avoid coupling fragile critical state to a DB migration.
- **Schema version** — SQLite user schema version recorded separately from the Git/app release number.

The final SQL must enforce referential integrity, preserve past sessions when a routine is removed, and allow saving **every scheduled exercise row with both actual measurements SQL NULL** for skipped ones. Enforce valid type-specific target and measurement combinations with explicit NULL checks. See [MEASUREMENT_DESIGN.md](MEASUREMENT_DESIGN.md) for architecture, proposed fields, safety, and future automated acceptance tests.

## 7. Database preservation and updates

**Three distinct operations:**

1. **Ordinary code/container replacement without schema change:** replace/restart app code only. **No DB copy, backup, migration, replacement, or overwrite** occurs implicitly. The separately confirmed Phase 8 browser/v4 maintenance workflow explicitly includes a verified backup, even without migration.
2. **Actual schema upgrade:** compare schema versions; stop new writes; safely snapshot old DB into a **new distinct versioned database**, migrate only the new one, verify both structural integrity and logical data equivalence; activate the new copy only after validation. Original remains intact and available. Failed upgrade leaves original active and displays/logs error. Major redesign may create new DB and import old data with the same safeguards.
3. **Backup or restore:** triggered by a manual UI action or by the separately configured backup schedule; must never happen *merely* because code was updated.

Integrity verification should include `PRAGMA integrity_check`, `PRAGMA foreign_key_check`, expected schema version, and key data counts/relationships. Never silently create a blank DB if an existing database is broken. Plan for SQLite journal/WAL handling, open connections, and an atomic active-DB switch. A code rollback after entering new workouts can lose visibility of those new workouts if pointed at an older DB: clearly disclose this and do not attempt automatic data merging.

Persistent **host** directory organization (configurable root; supplied installation paths are recorded in section 18):

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

- Exact server operating system, Proxmox VM/container layout and binding LAN interface/port. Installed checkout/storage/updater paths were supplied with Phase 7 and are recorded in section 18.
- Statistics are highest logged weight or longest logged duration in the selected date range, with separated exercise/type/unit/meaning. Any additional personal-record definitions and future product-specific upper bound remain undecided. Phase 3 actual durations use integer seconds within SQLite signed 64-bit range, accept either nonnegative whole part, normalize seconds above 59, reject zero totals and preserve two blanks as SQL NULL.
- Any future product-specific weight limit or configurable units beyond pounds; weight-meaning labels remain configurable per routine exercise. Phase 3 uses the SQLite signed 64-bit limit for stored tenths. Precision is settled: integer tenths of pounds, truncate beyond one decimal place, never round; zero is valid and blank is SQL NULL.
- Whether workout-level notes are needed in addition to approved optional exercise notes.
- Correction behavior is implemented for actual weight/duration, increase flag and occurrence date/optional time only, with append-only before/after/timestamp/revision audit. Snapshot identity/name/type/targets/units/notes cannot be corrected. Completed-workout deletion remains unauthorized.
- Household backup frequency/time/zone must be explicitly configured; scheduling starts disabled. Phase 5 implements local calendar-day cadence, earlier fold, first valid gap minute, and at-most-one missed-run handling. On corruption, startup must refuse unsafe storage rather than replace it.
- Restore confirmation and backup deletion are implemented. Restore requires checkbox plus typed RESTORE, accepts only the same storage identity and exact selected schema 2–7, and rejects silent older-schema recovery. Any future offline cross-version recovery workflow requires separate review.

**Never treat these open decisions as permission to change the agreed core requirements.** Seek review where they materially affect data safety or the workout experience.

## 12. Original phased plan (Phases 1–7 completed and approved; later phases below)

1. **Foundation and Storage Safeguards:** Flask skeleton, Docker Compose, configuration, responsive theme, test harness, external durable paths, explicit first-install initialization, read-only compatibility checks. Only storage metadata tables; no workout tables or real data. Missing, unreadable, corrupt, or incompatible storage must fail safely. Ordinary startup never initializes, repairs, migrates, backs up, or overwrites storage.
2. **People and routines:** person selection, permanent exercises, routine editing/ordering, Weight/Time segmented selector, sets plus type-specific targets and notes, independent copies; ownership, type/target validation, accessibility, and copy-isolation tests.
3. **Workout workflow (approved and merged):** one draft per user, type/target snapshots, one actual weight or duration per exercise, one-decimal weight truncation and integer-tenths storage, valid zero-weight/NULL semantics, minimum-1-second integer durations and empty-duration NULL semantics, matching previous values and increase flags, draft revisions, idempotent completion, all-skipped confirmation, discard dialog; transaction/concurrency and browser tests.
4. **History (completed and approved):** charts/tables, manual past sessions, confirmed validated corrections, date ordering, pounds/time chart labels, typed previous-performance lookup, snapshot preservation after type/target edits, NULL exclusions, and user isolation tests.
5. **Backups and recovery (completed and approved):** schema-versioned upgrade/copy/validation, manual/scheduled backups (disabled until configured), required safe restore UI, log viewer; corruption/interruption/DST and recovery tests, plus preservation of type, integer duration, weight, explicit zero weight, and all original NULL measurements. The minimum schema-1 → schema-2 migration was brought forward into Phase 2 as a safety prerequisite; full migration/recovery expansion remains here.
6. **Mobile UI/UX redesign (completed and approved; no live deployment):** compact People/routine selection, tab-scoped workout focus/save-and-exit, compact one-exercise layout, Settings appearance, neutral themes and persistent person accents; actual screenshot and browser viewport testing. Further installation, real-world testing and final polish: responsive/accessibility review, regression/integration tests, README/operator documentation, disposable deployment/recovery rehearsals. Live deployment requires separate authorization.
7. **Shared Exercise Library (completed and approved):** global IDs, independent person histories, named ID-preserving copies, candidate schema 5 and actual version displays. Approved for final merge/cleanup only; no deployment.

Build in small, reviewed increments after explicit authorization. Never deploy silently.

## 13. Retained Phase 2 compatibility and maintenance

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
by an active routine; remove it there first. On retained schemas 2–4, routine copying creates new exercise identities. Schema 5 deliberately supersedes that behavior: reuse global IDs for same-person and cross-person copies.

Management POSTs require signed-session CSRF tokens, ownership checks, and server
validation. Routine edit forms include a state fingerprint and reject stale
writes. No password/authentication is added: household user switching is still
navigation. Retained Phase 2 databases have no actual measurement columns. Phase 3 stores
weight as integer tenths with extra decimal digits truncated, not rounded;
actual time uses integer seconds with minimum 1. Empty measurements retain SQL NULL
entry rows, never historical values or zero. Historical snapshots must preserve
tracking type, targets and actual measurements independently of routine edits. See
[PHASE_2_REVIEW.md](PHASE_2_REVIEW.md) for the implementation/test record.

## 14. Phase 3 storage, persistence and completion

The explicit CLI supports target schema 3 from verified schema 1 or 2. It changes
only a new candidate, compares every existing table row including NULL fields,
validates integrity, foreign keys, exact table/index/trigger DDL and migration
history, then atomically selects the candidate. Prior files and selections remain
retained. Compatible target-3 requests are no-write/no-copy no-ops. Normal startup
supports schemas 1/2/3 without automatically migrating them; workout routes require
3, while old management routes continue supporting 2. No real data is used in tests.

Start copies all routine configurations into blank actual-entry snapshots in a
single transaction. Empty routines cannot start. A repeated start offers the
existing draft rather than replacing it. People switching remains unchanged.
`WORKOUT_TIMEZONE` selects an installed IANA zone; absent configuration follows
the server-local zone, falling back to UTC when no local zone is configured.
Compose explicitly defaults to Etc/UTC and permits overriding it. Store UTC
instants, the zone and computed local workout date; never infer these from the
browser timezone.

Every update checks ownership, entry membership, revision, typed measurements
and cursor position under the shared storage-lock protocol. Writes serialize;
stale tabs receive 409 without overwriting anything. Input autosaves after a
short debounce; only post-commit acknowledgments show Saved and update progress
and overview. Navigation/Finish wait for pending saves. Input typed during a
pending response stays intact and is saved next. Invalid/network-failed input
stays visible with an error; earlier committed values remain recoverable. Browser
closure before acknowledgment cannot guarantee persistence; warn on unsaved
changes rather than claim success. There is no offline client queue.

Finish includes current form data and status transition in one transaction,
checks every original snapshot row is present and confirms an all-NULL workout.
Completed retries return the existing completion without writing another session.
Discard uses “Are you sure?”, acknowledgment, disabled-until-checked OK, and
Cancel/Escape preserving the draft. A confirmed discard changes only its active
session status; completed history cannot be discarded or deleted. A singular
saved-workout confirmation is included; general history exploration and charts
were added in Phase 4 through a shared effective-value read layer. The Phase 3
record remains at [PHASE_3_REVIEW.md](PHASE_3_REVIEW.md).

## 15. Phase 4 history, manual completion and corrections

Schema 4 adds immutable historical preparation/session/entry tables, a registry
linking native and historical completed sessions, and append-only correction
revisions. The original schema-3 tables/index/triggers remain byte-for-byte the
same DDL. Existing completed sessions are linked in the new registry during
candidate migration; new native completions register through an added trigger.
All original rows including NULL/zero values are compared after copying. Registry
links, integrity, foreign keys, exact DDL and migration records are validated
before atomic activation. Startup never migrates or initializes automatically.

Historical entry chooses a routine, actual past date and optional time. Prepare
copies configuration into an immutable review form; Save validates all typed
measurements and atomically creates a separate completed session/entries. A
unique preparation ID prevents duplicate completion on repeated submission.
No temporary live draft is created and the person's active draft is untouched.
Store entered-at UTC separately from local occurrence date, optional clock time,
UTC occurrence when known and original IANA zone. Unknown time remains NULL;
within the same day date-only records sort before known-time records, with a
stable entry-time/ID tiebreak. DST gaps are rejected; repeated times require an
explicit earlier/later choice. Future occurrence values are rejected.

Corrections require acknowledgment and the latest audit revision. Only actual
measurements, increase flags and occurrence can change. Append one full before/
after value state plus UTC correction timestamp; original native/historical
rows and every audit revision are retained and immutable. Concurrent/stale
forms receive 409. Every read path (history/detail/charts/statistics/native
completion references/previous performance) overlays the latest effective values.
Invalid correction payloads fail validation rather than silently becoming zero.

History lists completed sources only, newest first by effective occurrence,
with inclusive date filters plus routine/exercise identity filters. Discarded
and active drafts are excluded. Archived/renamed/removed definitions do not
remove snapshots or filter choices. Charts are locally rendered responsive SVG
with accessible data lists, one series per exercise/type/unit/weight meaning.
NULLs remain visible as Skipped but are never numerical points; explicit zero
weight is plotted and included in maxima. Duration is plotted in seconds and
labeled minutes:seconds, never multiplied by sets. Stats are accurately labeled
highest logged weight/longest logged duration in the filtered range.
See [PHASE_4_REVIEW.md](PHASE_4_REVIEW.md) for evidence and limitations.


## 16. Phase 5 recovery and diagnostics

Settings is accessible from the header and preserves People-screen switching.
Backup Now uses SQLite backup API, unique timestamp/UUID files, structural/logical
validation and exact row comparison, including NULL/zero, historical snapshots
and every correction revision. Backup status/size/schema/source/hash/timestamps,
schedules and restore attempts persist in private external operations.json.
No workout schema migration is introduced; schema 4 and all protection triggers
remain unchanged. Compatible updates never copy or migrate the selected database.

Confirmed restore revalidates a listed ID, creates a distinct candidate, validates
all data and retains the pre-restore database/selection before atomic activation.
Post-switch durability/result-write failure triggers rollback; double failure is
explicitly uncertain. Interrupted intents are never automatically replayed.
Unconfirmed requests do not claim an operation. Dataset-generation-bound forms
prevent pre-restore pages from writing into the restored selection, with a second
check inside the write lock. Settings can show backup history during active-file
corruption; explicit CLI recovery is available if startup refuses it. Missing,
foreign/newer identity/schema, links and sidecars remain refused. Restore does
not merge records created after the backup. Backup deletion is explicit and
keeps metadata. No backup rotation or cloud synchronization is implemented.

A separate Compose scheduler process checks settings every 30 seconds, not per
Gunicorn worker. Backups remain disabled until explicitly configured. Frequency
is 1–3650 calendar days, default 1; default clock is 02:00 Etc/UTC. Local anchor
cadence uses earlier repeated times and first valid post-gap minute. Each due
slot is claimed durably under the shared root lock before copying; missed backlog
coalesces once and next advances into the future. Failures remain failed, without
retry storms. Settings revisions and last attempt/success/result/next persist.

Structured private UTC JSONL logs persist application lifecycle, unsafe storage,
workout failures, migrations, backup/restore attempts/results and scheduler/security
errors. Logs never include form bodies, private values, keys/cookies/tokens or raw
exception messages. Protected bounded frames remain server-only; safe error
details/event IDs are expandable in the browser. The viewer streams newest-first
with text/severity/category/date filters and 50-row pages. Retention defaults to
30 UTC days (1–36500), applies only to named log files, and runs on settings save
and scheduler cycles. Logging cannot roll back database transactions. All services
use non-root identities and external storage; the scheduler has no network/ports.
See PHASE_5_REVIEW.md for tests, interruption semantics and operating limits.


## 17. Phase 6 mobile UX and appearance

Existing people are shown before Add person; tapping a name selects routines and
a separate menu contains management/history/exercise/preference actions. Menus
support disclosure state, keyboard focus, Escape, outside-click and focus dismissal.
Routines offer Start workout without entering the editor. New browser sessions
always open People rather than a remembered account.

The compact workout screen shows routine, exercise/count and navigation progress (0.10.4 supersedes the original non-NULL bar),
previous measurement, conditional Increase ↑, one actual input, current increase
checkbox, Back/Next, then Save draft/Finish. More contains jump/overview/details,
validated Exit Workout and confirmed Discard. No global person-switch link appears
in an active workout. Exit atomically validates/saves current input, preserves its
one draft and releases this tab for switching; Finish/Discard release it too.
SessionStorage focus is tab-local, not authentication or a shared household lock.
Browser Back/reload use server state; failed saves keep input visible, stale writes
are rejected, and native unload warnings cover input not yet acknowledged. Another
browser/session can work independently. No offline queue or hard-close guarantee
for unacknowledged input is added.

Saved status is compact (Saved/Saving/Save failed) and still changes only after
server commit acknowledgments. Detailed timestamps, notes, original timezone and
previous dates are retained under More. Previous measurement comparison/effective
corrections are unchanged; only a performed previous increase request displays an
indicator. Entirely skipped completion still requires explicit confirmation.

The visible repeated AI banner is removed by explicit authorization; README,
source headers and developer notes retain the full mandatory disclosure. Theme
controls appear only in Settings, apply immediately and persist in browser storage.
Dark surfaces are neutral navy/charcoal; light surfaces have restrained color.
Each person independently selects Blue/Teal/Green/Purple/Orange/Red in Settings.
Allowlisted light/dark palette pairs maintain primary-button contrast. Preferences
persist across devices/restarts in private atomic config/person-preferences.json
(version 1), under the existing storage-root lock and permanent person IDs. Missing
file means blue without a startup write. No schema migration is introduced;
schema 4, measurements, immutable rows/audits and backup/restore protections remain
unchanged. SQLite backups do not include this external preference file; whole-tree
host backups should preserve it. Corrupt preferences are never overwritten and
read-only pages fall back to blue so recovery controls remain accessible.

Phone test targets: 320×568, 375×667, 390×844, 430×932; tablet 768×1024;
desktop 1280×900. Layout allows ordinary scrolling with enlarged text or a reduced
keyboard viewport rather than clipping controls. Real Chromium screenshots and
coverage/limits are documented in PHASE_6_UX_REVIEW.md. No real iPhone/Safari or
production deployment is implied by emulated browser checks.


## 18. Phase 7 shared household Exercise Library

Global Exercise Library → person-specific routines → person-specific history.
New definitions are immediately selectable by all active people. Create/rename/archive
through Exercise Library; current library names update every referencing routine,
while workout snapshots are unchanged. Trim and casefold names to reject new
accidental duplicates, including archived names; never merge existing matching
names. Show permanent IDs in library and selectors to distinguish legacy duplicates.
Archive is refused if any active routine across any person still references it.

Copy requires a nonblank chosen name, new routine/item UUIDs and independent
sets/reps/duration/unit/meaning/notes/order, but the same global exercise IDs.
Neither history nor active drafts nor measurements/flags are copied. Compatible
personal previous performance therefore follows the exercise across routines,
not across people; matching also includes type, unit and weight meaning.

Schema 4 → 5 preserves every existing table cell, exercise ID/provenance,
relationship, draft, historical preparation, registry, snapshot and correction.
The candidate-only migration rebuilds only routine_exercises, workout_entries and
historical_entries to change exercise foreign keys from (ID, person) to global ID.
All other DDL and immutable triggers remain identical. Candidate-only trigger
reinstallation happens in the maintenance transaction, never on the original or
an application connection. Full structure/integrity/FK/identity/migration-history,
cell equality and logical history/audit checks precede atomic selection. Original
files/manifests remain recoverable; failures retain the original selection.
Restore requires the exact current schema and identity: schema-4 backups remain
retained but cannot silently downgrade schema 5. No startup migration is allowed.

Application version 0.7.0 uses semantic versioning (major.minor.patch). After
1.0, breaking public-contract changes increment major, compatible features minor
and compatible fixes patch. During 0.x, feature releases increment minor and
compatible fixes patch; breaking changes need explicit release notes.
Application and schema versions are independent. Increment schema only for
persistent schema changes, not every release. Settings About and every page footer
read APP_VERSION and the verified active database schema; unavailable storage is
reported honestly. Footer is small, in document flow, with no repeated AI banner.

The installed paths supplied by the user are /root/WorkoutTracker/app and
/root/WorkoutTracker/data/storage; the updater is
/root/WorkoutTracker/update_workout_tracker.sh. These are documentation context,
not permission to access them. Exact upgrade and schema-4-only updater requirements
are retained historically in PHASE_7_REVIEW.md. Revised Phase 8 instructions in section 19 and deployment/README.md supersede that older target.


Final updater verification: `python -m workout_tracker release-info` exposes
APP_VERSION and TARGET_SCHEMA_VERSION as JSON without constructing Flask or
opening/initializing storage. Updaters compare the new image target with a
separately verified active schema. Stop both services, explicitly back up and
verify existing storage, preserve whole-tree recovery protection, update/build,
detect the target, request confirmation for an actual upgrade, run candidate-only
migration, verify and restart/health-check. The external server script is unavailable
and is not claimed tested. Disposable Docker tests exercise release detection,
verified schema-4 backup and candidate upgrade to 5 before restart.


## 19. Revised Phase 8 — trusted-LAN management and updates

The interrupted authentication/TLS attempt is not part of this phase. Start fresh
from main on phase-8-lan-management-and-updates. Only reviewed components with no
user authentication/TLS are reused. Network endpoints stay HTTP on the configured
private LAN; normal app address remains http://10.0.69.9:8000. Initial root SSH
service installation is explicit; no privileged installation runs at app startup.

Schema 6 permits dedicated, confirmed hard deletion while preserving ordinary
snapshot/correction protections. Delete Exercise removes that global ID, its routine
configs and native/historical entries across every person. Keep other actual values,
NULLs, flags and prescriptions unchanged, normalize positions/counts, project every
correction before/after array to surviving IDs and append a no-value-change revision
barrier so stale forms cannot target a different row. Empty completed/discarded
sessions, registry and audits disappear consistently. Affected uncompleted manual
preparations are invalidated to prevent stale indexed input. Active native drafts
block deletion. New same-name registration gets a new UUID and no prior results.
Separate legacy same-name IDs are not merged/deleted together; another existing
same-name definition must be reused/renamed/deleted deliberately before registering
that name anew. Deletion previews show the permanent ID and people/routine/entry
counts. POST requires CSRF, typed DELETE or exact name, acknowledgment and current
impact fingerprint. No password or administrator authorization is required.

Delete Routine removes its definition/configs, blocks active drafts and preserves
all global definitions and completed snapshots (marked routine deleted). Remove
From Routine affects only that configuration and never history/global definitions.
Backups/retained schema versions are not rewritten; restoring an older same-schema
backup can resurrect deleted data. Ordinary corrections remain append-only; only
explicit global deletion redacts the deleted identity from existing audit arrays.

Schema 5→6 uses the existing backup-copy/candidate migration. Rebuild only the three
routine-referencing snapshot tables, remove their live-definition FKs, add insert
ownership guards and gate existing protection triggers with a connection-local
deletion flag. Preserve all original SQL cells/NULLs, migration identity and original
source bytes. Verify exact DDL, integrity/FKs, counts and complete logical audit
chains before atomic activation. Schema-6 application connections enable trusted
schema only after exact DDL validation because Python sqlite3 cannot mark its guard
function innocuous. The normal guard value is 0 and is restored after deletion.
Never drop triggers or change schema in a live deletion transaction. Backup/restore
accepts exact schema 6 and preserves guard DDL and audits. Startup never migrates.

The compact sticky header always identifies the selected person and accent; active
workouts also retain the snapshotted routine name. Normal navigation/context does
not constitute authentication. Settings links directly to Application Updates.

Browser updates use CSRF, approved-release review and explicit install/migration
confirmation. A root host service receives only fixed actions through a Unix socket
0660, validates Linux peer UID (configured app writer/root), fixed source, full SHA,
paths and consent. The app never gets Docker/root access. A separate read-only HTTP
listener binds explicitly to 10.0.69.9:8001 by default, validates Host and shows real
persistent stages/logs while web is stopped. It has no command/install endpoint,
accounts or TLS. Household users need no login anywhere.

Approved source policy: only merged main from natpev/Workout-Tracker-vibe-webapp,
through verified GitHub transport. The repository's main-merge governance is the
approval boundary; this is not a cryptographic signature claim. Pin reviewed SHA,
refuse dirty/diverged local work or a changed approved head before installation,
parse APP_VERSION/TARGET_SCHEMA_VERSION with AST literal evaluation, then compare
built release-info. Never run arbitrary remote scripts or unmerged branches.

Host engine/v4 share checks, backup/candidate workflow, persistent lock/stages and
safe recovery. Space checks cover installation and Docker storage with source-size
allowance. Stop only web/scheduler, verify backup, fast-forward approved code, build,
check metadata, explicitly migrate if needed, verify original hash/schema/selection,
recopy parent .env privately/atomically, restart and verify health and scheduler.
Preserve commit/image/backup/DB/logs. Pre-selection failure may restart the verified
old image only against the unchanged selection/bytes and identical configuration;
post-selection failure never blindly starts an incompatible old image or restores
older data. Interrupted installs are marked failed on host restart and stopped for
inspection, never automatically replayed. No-update checks do not stop/copy data.

The actual available v3 script was inspected. V4 is committed at
 deployment/update_workout_tracker_v4.sh; it dispatches to the installed shared
host engine and explicitly installs/upgrades the service when requested. Initial
SSH upgrade and recovery commands are in deployment/README.md and PHASE_8_REVIEW.md.


Final Phase 8 corrections require all recovery inputs and a private manifest/hash/
image/version record before shutdown. Reverify the same storage after shutdown;
probe retained images read-only using the installation's writer UID/GID and require
actual web/scheduler health before reporting recovery. Any incompatibility or
unverified changed bytes/selection stops recovery without restoring older data.
Settings backup/detail/delete/restore and filtered/paged logs preserve URL-selected
person/accent; restore redirects to a read-only recorded result, making refresh
safe. This remains navigation context, never authentication or a remembered account.


## 20. Phase 9 — interface, Administration and shared defaults

Application 0.9.0 uses schema 7 for one new exercise_defaults table; no old table
or immutable trigger is rewritten. Existing IDs, routines/configurations, drafts,
measurements including NULL/zero, preparations and correction chains remain exact.
The explicit candidate upgrade validates every original cell, source bytes, exact
DDL, migration record, one preset per exercise, integrity/FKs and history/audit
logic before atomic activation. Schema-7 backups/restores retain defaults. Older
backups stay retained but exact-schema restore never silently downgrades.

Existing definitions initially get neutral Weight/3 sets/12 reps/pounds defaults,
empty meaning and notes; migration never chooses one person's configuration as a
household-wide standard. Library registration/editing uses the existing validated
Weight/Time fields, sets, reps or target duration, pounds, meaning and notes.
Pounds is the supported weight unit; no kilogram conversion is introduced.
Add from Library copies the preset once into a new owned routine configuration.
Existing routine settings and snapshots never track later preset edits. Routine
copying preserves its actual configuration while sharing the global exercise ID.

Settings keeps personal appearance separate from Administration. Administration
groups Updates, Logs, backup settings/history, deliberate restore, actual versions
and maintenance/diagnostics. One administrative_access boundary is shared by all
application maintenance routes and explicitly permits everyone today. It creates
no accounts/roles/login/passwords or TLS. CSRF, generation checks, typed decisions,
host command restrictions and candidate safeguards remain. Future authentication
would change that centralized boundary after separate approval; the independent
read-only host status would also require review before remote exposure.

Hamburger destinations are Routines, Exercise Library, History & Progress and
Settings. Without selection, person-specific destinations lead to People. Remove
global page tabs; show only History | Progress inside their shared existing URL
area. All navigation retains URL-selected person/accent and browser Back support.
Active workout guard/save/exit behavior remains. Exercise deletion and Cancel
return Library, successful deletion flashes a committed success; routine deletion
returns the owner's routines. Delete behavior and correction reconciliation stay
unchanged, including backup resurrection warnings.

Keep six existing accent keys as Soft colors and add vibrant-blue/teal/green/
purple/orange/red; existing preferences are untouched. Saturated variants remain
readable in Light/Dark/Auto with rounded mobile controls. Each person owns their
preference independently of SQLite backups. Favicons are original local SVG,
16/32 PNG, 16/32 ICO and 180 PNG Apple touch icon, linked in the shared template.

Measurement labels are Weight (lb), Minutes, Seconds across active/historical/
correction forms. Named exercise groups provide screen-reader context. Clock
entry/display is explicit HH:mm in 24-hour form, not locale-dependent native time
widgets; exercise duration remains MM:SS. Internal instants retain seconds and
microseconds. Measurement-only corrections preserve a native timestamp's hidden
precision when its displayed minute/fold was not changed. Existing IANA zones,
DST handling and installation America/Indiana/Indianapolis remain; diagnostic
seconds use explicitly labeled 24-hour UTC. Never substitute a fixed UTC offset.

One duration parser accepts nonnegative whole minutes and/or seconds. Examples:
blank+120=120, 1+90=150, 2+blank=120, 3+150=330. Targets and actuals store total
integer seconds, never multiply by sets. Two blanks skip only actual entry;
performed totals must be positive. Actual totals retain SQLite signed-64-bit
bounds; targets retain 359999 seconds and all strings remain bounded. Client
forms allow either part and large seconds; server revalidates all workflows.

V4 remains the emergency script and browser updates keep the independent host
engine. No new updater script is needed: approved source/release-info metadata
already detects application 0.9.0 and schema 7. Explicitly confirm migration,
verify backup and original/candidate, preserve recovery inputs and health-check.
Host status changes only its 24-hour timestamp presentation. Installing/upgrading
that separately copied host runtime is always an explicit operator command.

Run all Phase 1–9 tests, Chromium/mobile, Docker, candidate/fault/restore, actual
v4 flows and failure/recovery checks. Preserve earlier assertions except explicit
contract changes; add positive normalization tests rather than dropping coverage.
After verification, commit/push feature, fetch current main, reconcile safely if
needed, directly fast-forward/push main, verify remote commits/targets/assets,
then delete only the completed branch. No PR API calls, force push, deployment,
production database operation was authorized by Phase 9. Its earlier restriction
on Phase 10 is superseded only by the explicit Phase 10 authorization below.

## 21. Phase 10 — historical forms, Progress and independent update console

Application **0.10.0**, schema **7 unchanged**. No SQLite schema, storage selection,
identity reconciliation or history calculation change is needed. Phases 1–9 remain
intact. The noticed duplicate/orphaned exercise issue is explicitly excluded from
investigation, diagnosis, repair and cleanup in this phase.

Historical preparation, measurement review and saved correction show expected
validation failures on their original forms (400 validation / 409 stale revision).
Retain every raw weight/duration string, checkbox, date/time/fold and correction
revision; do not prefill blanks on POST. Collect exercise errors, associate each
with aria-invalid/describedby, include a non-color marker and linked assertive
summary immediately above Save. An exception exits/rolls back the write transaction
before redisplay. Completion idempotency and append-only confirmed corrections
remain the existing storage services; stale corrections cannot overwrite newer ones.
Unexpected system/storage errors use the existing safe handlers.

Optional workout clocks use 24-hour HH:mm text plus explicit hour/minute selectors,
00–23 and 00–59, without AM/PM or displayed seconds. Four-digit input such as 0930
normalizes on blur/submit, not while typing. Unknown remains blank/NULL; correction
GET prefills effective values and preserves existing IANA/DST overlap/gap checks
and hidden precision for unchanged displayed native times. Duration is independent.

Progress uses URL state and defaults to 30 rolling inclusive local calendar days
(today minus 29 days through today, configured IANA zone). 60/90 follow the same
rule. 6/12 Months start one day after the corresponding clamped calendar-month
anniversary and end today, including both endpoints. All Time removes date bounds;
Custom Range reveals optional From/To and rejects malformed/reversed bounds inline.
Keep selected exercise/raw dates on errors and display the previous valid graph
where its URL bounds are available. History/Progress links and detail/correction
flows carry explicit range context; refresh/Back retain it. Existing series, stats,
exercise IDs, compatible meanings, NULL exclusions, zero and person isolation are
unchanged. SVG lines/dots and accessible data lists remain local. Small escaped
textContent bubbles show point date/actual/known time on hover, focus or touch;
Escape/outside interaction hides them and viewport clamping limits overflow.

Install Update synchronously opens exactly one configured trusted status URL tab
per confirmed attempt and POSTs with CSRF without navigating the original tab.
Check opens no tab. Native validity and server install/migration confirmation remain.
Popup blocking shows a fallback link while installation continues; disable another
attempt until status is reviewed/reloaded. Status GET never triggers installation.

The independent host service retains its status/events and polls a separate
sanitized ring while Flask stops/restarts. Actual child stdout/stderr are drained
as they arrive, with deadlines, fixed argv/no shell and bounded parse tails.
Default-deny classification emits recognized Git numeric/revision, BuildKit step,
dependency lifecycle, verified backup/schema and container lifecycle messages,
plus actual command stage/exit events. Arbitrary text, URLs/credentials, environment
values, commands, stack traces and resolved Compose configuration are withheld.
Detailed private diagnostics remain SSH-only, never served. Safe JSON is atomic,
mode 0600, 500 lines of at most 500 ASCII characters per operation, newest 20 safe
operations only; no backup/private-log retention is changed. Allowlisted IDs and
bounded cursors accept read-only polling, not file paths or executable commands.
Use textContent, local scripts/styles and restrictive CSP. Safe log-write failure
must not reverse a completed storage action. Follow new output only at bottom;
allow scrolling upward/Scroll to Latest, refresh/reconnect and retained operation
selection after success or failure. Timestamps are explicitly 24-hour UTC.

V4 remains the emergency updater. Existing independently installed host runtimes
must be explicitly upgraded once to obtain streaming plus status JS/CSS; Flask
replacement alone cannot update them. Older hosts retain basic status/update
compatibility; the app warns when console_protocol is absent. Exact operator
commands and limitations are in deployment/README.md and PHASE_10_REVIEW.md.
Schema-7 installations need no migration; older schemas retain explicitly confirmed
candidate-only migration, original preservation and recovery safeguards. No live
storage, deployment, login/TLS, PR attempt or Phase 11 is authorized. After full
backend/Chromium/Docker verification, the user authorizes feature push, direct
history-preserving main merge/push, remote verification and completed-branch deletion.


## 22. Patch 0.10.1 — routines by latest completed workout

The selected person's routine-selection cards are sorted server-side by their
latest completed workout: actual effective workout date descending, then available
live Finish timestamp or historical occurrence timestamp descending, then routine
name alphabetically. For a live workout with a deliberately corrected occurrence,
that effective corrected timestamp supersedes the original Finish stamp. Compare
known timestamps in UTC with full stored precision. Known times precede unknown
times on the same date; do not substitute historical entry or correction time.
Names compare by casefold, exact name, then permanent routine ID for stable ties.
Never-completed routines come last alphabetically.

Include completed live and saved historical sessions, including entirely skipped
completed workouts. Ignore active/unfinished/discarded/canceled sessions and
uncompleted historical preparations. Match person plus permanent routine ID,
never the routine name or shared exercise IDs. Copies are independent; renamed
routines retain their own history, and deleted/archived definitions stay excluded.
Keep existing cards, actions, layout and within-routine exercise order. Do not
write routine positions, dates, workout snapshots or audit records while listing.

Reuse the existing effective correction/history reader on schema 4–7. Retained
schema 3 uses completed live sessions only; schema 2 has no workout history and
falls back to alphabetical routine cards without initializing/migrating anything.
Application 0.10.1 keeps schema 7. Existing browser/v4 code-only updates retain all
backup, recovery and consent safeguards. No new host-service upgrade is needed
after Phase 10. Add synthetic ordering/ownership/copy/tie/correction/read-only and
responsive browser regression tests and run the entire suite including Docker.
Direct fast-forward merge/push and completed-branch deletion are authorized after
verification, with no PR attempt, deployment, real data or new development phase.


## 23. Patch 0.10.2 — viewport-safe hamburger dropdown

The global navigation dropdown must remain fully visible in narrow mobile, iPhone
portrait/landscape, tablet and desktop layouts. Anchor the absolute panel to the
full existing sticky header, rather than right-aligning it to the narrow button.
Keep the current button location. With a selected person the button is near the
brand, so align the menu to the header's left edge; without a person the button
is on the right, so keep right alignment. Header-relative maximum width and CSS
safe-area margins prevent crossing either screen edge, even with long names or
when the header wraps. Keep the panel below the header, above cards and vertically
scrollable. Preserve all four links, current person/accent, Light/Dark/Auto and
existing tap/outside/Escape/ArrowDown/focus/aria-expanded behavior. No JavaScript
change or unrelated page redesign is needed.

Test 390×844, 320×568, 844×390, 768×1024 and 1280×900 in Light/Dark, including full
panel/link bounds, real frontmost hit targets, click navigation, sticky scroll,
closing/reopening, safe-area geometry and reflow while already open. Preserve
existing assertions and run the complete backend/browser/Docker/updater suite.
Version 0.10.2 follows verified merged 0.10.1; schema stays 7 and updater metadata/
protocol is unchanged. No new host upgrade or server configuration is required.
After verification, direct main fast-forward/push and branch cleanup are authorized;
no PR attempt, force push, live data, deployment or unrelated development phase.


## 24. Patch 0.10.3 — rightmost header and last routine completion dates

The hamburger remains at the header's far right in phone portrait/landscape,
tablet and desktop layouts. Keep a single compact sticky row: branding does not
shrink, selected-person text occupies remaining space with ellipsis/full-name
title, accent stays visible and the button cannot wrap. Reserve safe-area padding.
Right-align the existing viewport/header-bounded dropdown beneath it, above content.
Keep all links, keyboard/focus/toggle/outside behavior and themes; no navigation
JavaScript change. Active workouts retain their existing restricted focused header.

Cards display Last completed: Month D, YYYY or Never completed in smaller muted
text below their name/actions. Return ISO date and deterministic English label
from the exact routine-ID maximum already used by sorting, in one read pass.
Keep all existing date/timestamp/alpha tie rules; include completed live/manual
workouts and effective corrections, never historical entry times, drafts, discarded
sessions or unfinished preparations. People and copied routine IDs remain independent.
Deleted/archived definitions stay excluded. Use a full-width activity row so dates
do not create tall narrow columns; preserve Start/Edit, names, accents and mobile
controls. No positions, history, dates or audits are written by listing/rendering.

Test date formatting, matching sort order, historical chronology, ignored incomplete
records, copies/people/deletions, corrections, exact read-only SQL state, compact
card height and all required header/menu geometry in Light/Dark plus card Auto.
Run the full backend/Chromium/Docker/updater suite. Version is 0.10.3 from verified
main 0.10.2; schema remains 7 with no migration. Existing browser/v4 protocols remain
compatible, with no extra host upgrade. Verified direct fast-forward/push/cleanup
is authorized with no PR attempt, live data, deployment or unrelated development.


## 25. Patch 0.10.4 — navigation progress, configuration scope and CSV

Use the existing current_position as the furthest Next destination (0 initially).
Validate an explicit Next action and adjacent destination; store max(old, target)
in the same revision-checked transaction as pending actuals. Back/revisits cannot
raise or double-count it. Jump changes the viewed exercise only; subsequent Next
uses that following exercise as its destination. Refresh retains URL view and
checkpoint; Resume opens the checkpoint. Existing draft cursors are preserved as
the initial checkpoint, because earlier navigation cannot be reconstructed.
No new table/migration is needed. Performed counts remain separate for all-skipped
confirmation and actual-value summaries. Autosave acknowledgments expose both
counts; only navigation_progress controls the bar. Finish retains atomic/idempotent
completion, NULL records and confirmation. The current view is separate from the
checkpoint so Save draft does not unexpectedly switch a revisited page.

Configuration forms show the exact routine-only or global-default explanation
requested by the user. Include routine add/edit and library add/edit screens;
use muted readable styling. No defaults, routine independence or snapshots change.

Progress offers a compact collapsible multi-ID CSV chooser with Select All/Clear,
retaining existing preset/custom ranges and the chart's independent single filter.
Export only checked IDs, for the current person and selected dates. Empty selection,
invalid range/IDs or no matching completed workouts return inline validation with
choices retained, not an empty/misleading attachment. GET export is read-only.
Use completed live/manual effective records, including latest correction actuals
and occurrence; never current defaults or obsolete measurements. Sort oldest first
with the existing deterministic chronology and a unique workout ID for same-time
records. A row exists only when at least one selected exercise was present, even
if all its actuals were skipped. Missing selected exercises have two blank cells;
present skips retain the historical target and blank actual. No previous values
or zeros substitute for skips; explicit zero stays 0.

CSV columns begin Date (ISO), Time (HH:mm or blank unknown), Routine, Workout ID.
Each Weight pair is Name — Weight (lb), Name — Sets × Reps. Each Time pair is
Name — Duration, Name — Sets × Target Duration. Weight is exact stored tenths,
whole weights omit .0, and durations/targets use total minutes:two-digit seconds.
Targets describe the historical prescription, never actual set-by-set repetitions.
Column groups separate ID/type/unit/weight meaning; duplicate names include full
IDs, and repeated same-group entries get occurrence-number columns rather than
overwriting values. Keep selection order, then deterministic group/slot ordering.
Standard comma-separated UTF-8 with BOM, CRLF and CSV quoting opens in common
spreadsheets. Prefix formula-like user text (including leading whitespace/control
variants) with an apostrophe; escape names/headers/routine text as well as cells.
Filename is workout-progress-LOCAL-TODAY.csv. No PDF/workbook/cloud/reporting extras
or orphan exercise investigation/cleanup. Schema remains 7; existing browser/v4
updates work without new host runtime. Full tests and direct verified main merge/
push/branch cleanup are authorized, with no PR, deployment or production data.

Selected exercises absent throughout a range still retain blank column pairs, using their historical configurations for headings; no out-of-range data rows are added.
