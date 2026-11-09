AGENTS.md — Workout Tracker

> **SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.** This project is developed primarily with AI-generated code under human direction. Do not assume the code is audited, secure, or correct. Keep this disclosure prominent in the README, all project notes, and headers of every project-owned source file where comments are supported. By explicit Phase 6 instruction, do not render the repeated visible banner in application pages; HTML/Jinja source headers retain it.

Read this first

• PROJECT_SPEC.md is the authoritative description of the user’s requested behavior; read it completely before planning or changing code.
• Current status: application 0.10.1 / unchanged schema 7 adds read-only routine-card sorting by latest completion (PATCH_0_10_1_REVIEW.md). Phases 1–10 are implemented. Phase 10 (application 0.10.0 / unchanged schema 7) adds inline historical validation, a structured 24-hour picker, URL-based Progress ranges and SVG tooltips, a synchronous independent update tab and a separate bounded sanitized host console. Final suite: 384 passed, zero failed/skipped (339 backend/script, 32 Chromium, 13 Docker). See PHASE_10_REVIEW.md for evidence. The user authorizes verified direct fast-forward merge/push/cleanup, with NO PR creation or PR API attempt. No server deployment, real data or Phase 11. The explicitly excluded duplicate/orphaned exercise issue must not be investigated, diagnosed, repaired, migrated or targeted with cleanup; do not alter identity matching. Preserve disclosures without a visible application banner.
• Final corrections: initialize and persist recovery inputs before attempting shutdown, reverify quiesced storage before refreshing its hash, and probe a retained image as the configured writer UID/GID. Recovery must verify storage/config/selection/bytes and actual app/scheduler health; never restore backups or restart an incompatible image. Carry explicit person_id throughout Settings maintenance/log links/forms/redirects, and show restore outcomes through read-only GET so refresh cannot replay maintenance.
• Phases 1–4 remain intact. Phase 5 keeps schema 4 unchanged; operations settings/backup history/restore audit use private external atomic JSON and logs use private daily JSONL. The scheduler is a separate process, disabled until Settings explicitly enables it. All backup/restore/config writes coordinate with the existing storage-root lock. Log writes use a separate logs lock and must not prevent workout commits.
• Phases 1–3 remain intact. Phase 4 adds schema 4 only through explicit separate-candidate migration. Original schema-3 files, completed rows and Phase 3 protection triggers remain unchanged. Corrections append audit revisions and use an effective-value read layer; never update completed records directly. Follow MEASUREMENT_DESIGN.md and PHASE_4_REVIEW.md. No startup migration/initialization/repair/replacement is allowed.
• The user is learning the codebase. Optimize for readability, simplicity, and safe maintenance, not cleverness.
• When a detail is unresolved, flag it clearly. Do not quietly turn an illustrative mockup or your own suggestion into an agreed requirement.

Required architecture

• Python + Flask, SQLite, responsive HTML/CSS, minimal JavaScript, charts for history; Docker Compose for self-hosting.
• Code lives in a GitHub repository, initially private. Persistent databases, settings, schema archives, backups, and logs live outside the repository and replaceable containers via explicit host bind mounts.
• LAN-only for v1, without passwords; still validate input and secure the application. No public exposure, cloud dependence, analytics, telemetry, or unexpected third-party network services. Architect for possible future remote access and authentication, not enabled by default.
• Keep the app straightforward to install, update, troubleshoot, and roll back. Document paths and commands in plain English.

Mandatory disclosure and comments

• Start each project-owned source file that permits comments (Python, HTML, JS, CSS, shell, YAML, etc.) with a comment prominently saying SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE. Use valid comment syntax for its language. For formats that do not permit comments (such as JSON), place the disclosure in adjacent documentation rather than creating invalid files.
• All README files, project notes, diagrams, and architecture/implementation documents must prominently disclose that this is shamefully vibe-coded.
• Source-file header: explain what this file does, who calls/imports it, what data it reads/writes, and important dependencies.
• For functions and meaningful blocks, explain inputs, outputs, side effects, and data flow in beginner-friendly language. Clearly label database reads/writes, browser → Flask → SQLite flow, background jobs, and cross-file calls.
• Explain non-obvious why, error handling, and safety checks. Avoid noise from line-by-line comments describing self-evident syntax.
• Maintain an approachable README with architecture, setup, updates, persistent storage, backups/restores, logging, and troubleshooting.

Functional contract

People, routines, exercises

• Phase 6 replaces the original expanded People layout with person-selection cards and separate accessible action menus. Open app → People → routine selection → Start workout; editing is secondary. Do not automatically select a previous person or add account-style tabs. No login for initial LAN-only use. Each person has independent routines, active drafts, weights, flags, history, and charts.
• Routines can be created, renamed, edited, reordered, duplicated, and deleted. Exercises in routines can be added, edited, removed, and reordered, including sets and target reps (Weight) or target duration per set (Time), selected with a segmented Weight/Time control.
• A routine may be copied from a different user or duplicated within the same user. On schema 5 the new routine/settings are independent; its permanent global exercise IDs are deliberately shared. Retained schemas 2–4 keep their earlier local-identity behavior. Do not copy weight/history/increase state.
• Historical workouts must retain exercise name, order, measurement type, prescribed sets/reps or duration, and results even after routine editing or deletion.

Workout entry

• Open site → select person → choose their routine → start a session with automatically recorded local date/time.
• One exercise is shown at a time, with sets × target reps or duration, previous matching measurement and previous increase next time flag for that person.
• Enter exactly one applicable measurement per exercise (weight or duration, never one per set); no mandatory per-set or performed-reps entry. Today’s measurement starts blank; previous performance is display-only. Use type-specific increase labels. Store duration as integer seconds, independent of set count.
• Offer an optional increase-next-time toggle, Back/Next, jump-to-exercise controls, a routine overview, and a progress bar counting non-NULL applicable measurements, not navigation position.
• Active workout pages omit unrestricted person switching. More contains Exit Workout (validated save then retain draft), jump/overview/details and confirmed Discard. A per-tab workflow marker handles navigation/Back without blocking other browser sessions; server revisions and acknowledged saves remain authoritative. Native unload warnings explain unacknowledged-input risk.
• A skipped exercise must be included in the saved session with true SQL NULL for the applicable measurement; both actual weight and duration are NULL when skipped. Never replace a blank weight with 0, an old weight, or a missing row. Charts must not interpret skipped entries as zero; label weight in pounds and duration as time, and separate the two types.
• Finish & Save atomically saves the whole workout, including NULL entries, then completes the session. Avoid accidental double submission.
• Persist unfinished drafts promptly on the server with visible save/error status so they can be resumed after an interruption without losing entered measurements.
• Discard Workout requires an explicit “Are you sure?” dialog, acknowledgment checkbox, Cancel, and OK disabled until acknowledgment. Cancel keeps the draft; confirmed discard affects only that unsaved/in-progress session, never saved history.
• Phase 4 historical entry copies a chosen routine into a separate review snapshot, preserves unknown time as NULL, distinguishes occurrence from entry time, and atomically completes via an idempotent submission token without touching an active draft.
• Phase 3 implemented measurement rules: pounds by default, at most one decimal place, extra digits truncated never rounded (40.99 → 40.9; 42.56 → 42.5; 40 → 40.0). SQLite stores integer tenths (40.9 lb = 409). Explicit zero is valid; empty weight is SQL NULL. Actual durations are integer seconds, minimum 1 second; zero is invalid and empty is SQL NULL. One actual duration per exercise regardless of sets. Every skipped exercise retains an entry with NULL actual measurements, never previous values or zero; tracking types and measurements belong in historical snapshots. Do not backport workout-entry behavior or schema changes into retained Phase 2 databases.
• Approved decisions: pounds by default with one decimal place and truncation; explicit zero is valid and distinct from NULL; one active draft per user; all-skipped completion requires confirmation; show previous-session weight/increase plus last performed weight after a skip; permanent exercise identities and optional exercise notes; corrections to saved workouts require confirmation and validation. Archive users with history. Safe restore UI is required for v1; automatic backups stay disabled until configured. Implement these in their approved phases, not all in Phase 2.

Interface and reporting

• Simple uncluttered phone-first UI; rounded cards, round/oval pill buttons, large tap targets. Support Dark, Light, and Auto (device theme, default), with a per-browser/device override.
• Appearance controls live only in Settings; Auto/Light/Dark is browser-local. Each person has an allowlisted server-side accent in private config/person-preferences.json, written atomically under the root lock, with blue default and no SQLite schema change or startup initialization. Preferences are independent of SQLite backups/restores and require whole-tree protection.
• Screens: Home/user selection, Routine selection, single-exercise Workout entry + overview, Routine editor/copy, History/charts + historical entry, Settings.
• Per-person history supports date/routine/exercise filters and saved detail. Charts group permanent exercise ID, type, unit and weight meaning separately; local SVG and accessible data lists exclude NULL numeric points but retain zero. Statistics mean highest logged weight/longest logged duration in the selected range. History, charts and previous-performance references must all use effective corrected occurrence/measurements. Show skipped entries as skipped/blank, never as zero performance.

Database protection — highest priority

• Application version is different from database schema version. Startup and ordinary code/container replacement never implicitly copy, migrate, delete or initialize storage. The explicitly confirmed Phase 8 Install Update/v4 workflow deliberately includes a separate verified backup, even for a code-only update; this is user-authorized maintenance, not startup behavior.
• On first install only, initialize a new DB if no active DB exists. Never treat an incompatible, missing, or unreadable existing DB as permission to create an empty replacement.
• When a real schema upgrade is required: block writers, verify the original, create a consistent separate copy using SQLite’s backup API or a carefully controlled export/import, migrate the new database only, validate (PRAGMA integrity_check, PRAGMA foreign_key_check, schema, record counts, logical checks), then switch the active pointer safely/atomically.
• Do not modify the original version during migration; preserve prior DB versions indefinitely unless the user explicitly removes them. If anything fails, retain the original active selection and show/log the error. Reconcile connections/SQLite WAL sidecars when changing DBs; never implement active-file switching as an unsafe raw overwrite.
• Schema archives are not the same as manual/automatic backups. Rolling back application code to an old DB cannot silently merge new workouts written after an upgrade; make this limitation explicit.
• Use transactions for saving workouts, foreign keys, parameterized queries/ORM, input validation, and tests before data-affecting changes.

Manual and automatic backups

• Settings must provide Backup Now; use SQLite’s consistent backup mechanism to save a unique, timestamped file in a server-side backup directory. Do not download it to the browser. Verify the backup before reporting success and never overwrite a previous backup.
• Show last successful backup date/time and backup history. Leave historical backups until the user deliberately deletes them; no silent rotation/expiration.
• Settings must also provide an automatic-backup enabled switch, frequency as a positive integer number of days, and time of day (hour and minute); show previous and next scheduled runs. Schedule must run server-side without an open browser and persist across restarts.
• Ensure a missed scheduled run is handled at most once and that multiple workers/restarts cannot generate accidental duplicate runs. Treat local timezone/DST explicitly rather than guessing.
• If database integrity verification fails, surface an error and do not label a corrupted backup as good; preserve earlier verified backups.
• Safe restore: require deliberate confirmation, validate a selected backup, preserve the current DB as a distinct version before switching, quiesce writes, then atomically activate the restored DB. Never restore silently on startup.
• Proxmox VM backups/clones address full machine failure; these on-server backups address corruption and accidental data changes. Do not claim local backups protect against physical server loss.

Settings, diagnostics, security

• Settings includes a read-only log viewer: text search, severity and category/date filters, refresh, expandable error details, configurable retention (suggested default 30 days). Log meaningful app, workout-save, backup, integrity, migration, scheduler, and exception events, without noisy sensitive data dumps.
• Keep logs and backup schedules/settings persistent, separate from replaceable containers. Never expose paths that allow arbitrary file reads or writes.
• Restore accepts only server-listed verified backups of the same storage identity and exact current schema (2–7); no silent downgrade. Preserve a present damaged active file only on explicit recovery with a valid manifest; refuse missing files/identity or readable newer/foreign storage. Never replay interrupted maintenance tokens. Forms are bound to the selected dataset and checked again inside the write lock.
• No public-facing bind by default. LAN-only without passwords means LAN users can see and alter shared household data; document this. If remote access is added later, revisit authentication, HTTPS, rate limiting, and access controls before enabling it.
• Standard web safeguards still apply: server-side ownership checks (even though selector has no auth), CSRF protection on mutating forms, escaping, input validation, least-privilege file access, and safe backup/restore path handling.

Tests, review, and working style

• Use test fixtures, never a real workout DB, for development tests, destructive commands, migrations, or restore rehearsals.
• Cover: user/routine isolation and independent copies; exercise ordering; one weight or duration per exercise; both types and type changes; integer seconds and strict malformed-input rejection and Phase 9 partial-duration normalization; exact weight truncation; autosave acknowledgment/network failure; concurrent tabs and restart recovery; skipped exercise produces a present row with true SQL NULL; progress bar semantics; previous-value display after skip; save idempotency; drafts/resume/discard confirmation; historical snapshots; migration success/failure with unchanged original; backup/restore integrity; scheduler missed-run and duplicate-run protection; theme persistence; core responsive accessibility.
• Before changes to schema, data storage, backup, restore, or session completion, explain the risk, data path, validation, and rollback approach.
• Make changes in small reviewable phases/branches/PRs. Record test results and limitations; never silently deploy to the live home server.
• Update PROJECT_SPEC.md when the user approves new requirements. Keep undecided implementation details in its “Open decisions” section rather than deciding unasked.


Phase 7 shared-library contract

• Schema 5 uses global exercises with immutable IDs. exercises.person_id is retained registration provenance only, never an ownership filter. Preserve every old ID, name, archive flag and provenance; matching names from old schemas remain distinct. New registrations/renames reject casefolded duplicate names, including archived definitions; display IDs to distinguish legacy duplicates.
• All active people can select/rename library definitions. Archive checks active routine references across the entire household, including archived people. Historical names/configuration remain immutable. Routine ownership and workout/history/chart ownership remain person-specific.
• Named copies get new routine/item IDs but reuse global exercise IDs. Never copy measurements/drafts/flags. Previous performance matches person + exercise + type + unit + weight meaning across routines, with effective corrections and chronology.
• Candidate schema 5 changes only three exercise reference constraints. Rebuild only candidate tables with exact cell copying and reinstall identical immutable triggers before validation/activation; no application connections can see this intermediate state. Preserve source bytes and old manifests; verify all original tables, NULLs, logical snapshots/audits, exact DDL/integrity/FKs. Explicit --target-version 5 only; startup never upgrades.
• App version 0.7.0 follows semantic versioning; database version increments only for persistent schema changes. Footer and Settings obtain the active schema dynamically and application version from APP_VERSION, never duplicated template constants. No visible repeated AI banner.
• Existing schema-4 operators must explicitly upgrade once; an updater recognizing only 4 must be revised to require confirmed candidate migration to 5. See PHASE_7_REVIEW.md; do not assume access to /root/WorkoutTracker or its update script.

• Updaters read release targets using python -m workout_tracker release-info (JSON app_version and target_schema_version), without app startup or any storage mount. This metadata never migrates storage; compare with verified installed schema, request explicit confirmation, then call candidate migration separately.


Revised Phase 8 contract (supersedes older archive-only behavior on schema 6)

• Network isolation is the trust boundary: http://10.0.69.9:8000 remains passwordless, without TLS, accounts or roles. Keep CSRF, trusted hosts, bounded inputs, typed deletion and explicit update/schema confirmation. Local Unix socket peer UID/file permissions restrict host command access; these are not user login/authentication.
• Schema 6 is required to detach routine snapshots and add controlled deletion guards. Only a verified new migration candidate receives DDL. Default application connections deny snapshot mutation; exact-validated schema-6 connections register deletion_in_progress() as 0. Only the dedicated atomic deletion transaction enables it temporarily, then restores 0. Do not use this capability for ordinary correction or logging. No startup migration/initialization.
• Routine hard deletion removes definition/configs, blocks active drafts, retains global exercises and completed snapshots. Exercise hard deletion removes its global identity/configs/entries across all people, blocks active drafts, preserves other measurements, normalizes ordering/counts, projects correction arrays to surviving entry IDs and appends a value-preserving revision barrier against stale forms. Empty completed/discarded workouts and their registry/audits are removed; affected unfinished historical preparation forms are invalidated. Backups/old database versions remain untouched and may resurrect deletion on deliberate compatible restore.
• Never make Remove From Routine trigger global deletion. Show impact counts and exact exercise identity; check typed DELETE/name, acknowledgment, CSRF and a fresh impact fingerprint in the same locked transaction. Keep person ownership constraints and logical validation.
• Approved updater source is fetched main of the fixed repository (merge governance defines approval), pinned to a full commit SHA. Parse source metadata without executing it, then compare built release-info. No browser URLs/commands/branches/images. Host worker independently validates paths, source and consent. No Docker socket in web/scheduler. Read-only status uses configured private interface (default 10.0.69.9:8001), never 0.0.0.0 or a host command API.
• v4 and browser updates share one engine; file lock prevents overlap. Verify source/disk/storage/backup, preserve old commit/image/database, invoke the existing candidate migration command, verify versions/scheduler, and privately recopy authoritative parent .env to app/.env as explicitly required in Phase 8. No blind database/image rollback after schema activation. Keep persistent safe status and private host diagnostics outside containers. Install/upgrade systemd only on an explicit operator command.
• Interrupted earlier Phase 8 work is preserved on a separate local branch, never merged wholesale. Only reviewed database/deletion/updater pieces without user-auth/TLS infrastructure were selectively reused. Do not delete unique interrupted work.


Phase 9 contract (supersedes older UI and duration descriptions)

• Keep authentication entirely absent. administration.administrative_access is the one currently allow-all policy called by all application maintenance/Updates endpoints. Personal appearance is separate; CSRF and storage/generation checks still apply. Future authentication requires a new explicit review, including the independent read-only host status interface; do not add unused account infrastructure.
• Schema 7 adds only exercise_defaults, with one validated row per global exercise and cascade on explicit global erasure. Candidate initialization uses neutral Weight/3 sets/12 reps/lb/empty notes for old identities, without guessing from one person's routine. Compare every old table/cell and source bytes; validate DDL/FKs/integrity/counts before selection. Existing routines/drafts/history/corrections do not change. New library selections copy defaults once; independent routine editing and copying must retain the routine's own settings, not recopy current defaults. Pounds remains the supported weight unit.
• parse_duration accepts either nonnegative whole part, seconds above 59, and normalizes total seconds; two blanks mean NULL only for actual entry, targets require a positive value. Actual total retains signed-64-bit bound; targets retain 359999-second bound and strings retain the 100-character limit. No two-character seconds field or required-both-parts client rule.
• Workout clock fields use explicit HH:mm text entry/display, retaining internal precision and IANA zones. A measurement-only correction with an unchanged displayed minute must not erase original seconds/microseconds or change a DST fold. Duration MM:SS is separate. Diagnostic timestamp seconds remain 24-hour UTC and labeled; no AM/PM or fixed timezone offsets.
• Administration/backup/detail/result/log filters/pagination preserve explicit person context. The sticky header and tab-scoped active workout save/exit guard remain. Global hamburger destinations are Routines, Exercise Library, History & Progress, Settings; without a selected person scoped destinations lead to People. Only history-area pages show History/Progress tabs. Exercise deletion/cancel returns Library; routine deletion returns Routines. Report success only after committed deletion.
• Existing blue/teal/green/purple/orange/red keys are unchanged soft selections; vibrant-* adds six more. Persist independently per person. Original SVG/favicon raster exports are local assets with disclosures in SVG/adjacent README.

Phase 10 contract (supersedes historical form and Progress controls only)

• Historical initial/review/correction expected validation failures render the same form with raw submitted strings, linked field errors and an assertive summary immediately above Save. Roll back before rendering; keep CSRF, owned immutable snapshots and stale-revision 409 protection. Never replace an invalid/blank measurement with stored/default data. Unexpected storage failures retain existing safe error handling.
• Historical time remains optional explicit HH:mm with hour/minute selectors (00–23 / 00–59) and four-digit normalization on blur/submit, never during typing. Retain IANA/DST/fold and hidden timestamp precision rules. Durations are separate Minutes/Seconds fields.
• Progress defaults to 30 inclusive local calendar days; offer 60/90 days, 6/12 calendar months, All Time and Custom Range. Months start one day after the clamped prior-month anniversary. Carry exercise/range in URLs through History/Progress. Invalid custom ranges retain raw values and previous valid graph bounds where supplied. Keep chart_series calculations, person isolation and permanent identities unchanged. Local SVG tooltips use escaped metadata/textContent and support hover/focus/tap; NULL remains unplotted and zero remains valid.
• Confirmed Install opens one trusted configured independent status tab synchronously; keep the app tab, retain explicit migration/CSRF consent and offer a popup-blocked fallback. Ordinary Check opens no tab. Disable duplicate attempts until status is reviewed/reloaded; opening a status page cannot install anything.
• Host commands stream both pipes with fixed argv/no shell, original deadlines and bounded in-memory tails. Raw private logs never become browser responses. Only recognized structural messages enter a separate atomic safe ring (500 lines × 500 characters, newest 20 operations). Do not publish argv, Compose config, environment values, arbitrary output/paths or commands. Read-only retained-ID polling stays on the independent host service. Safe-console write failures cannot undo database operations.
• Existing Phase 9 installations need an explicit one-time --upgrade-service to copy the changed independent runtime and local status assets. Updating Flask containers alone cannot do that. V4, candidate migration, recovery and backup protections remain unchanged; schema 7 needs no Phase 10 migration. No automatic host-service install, startup database work or public authentication/TLS infrastructure.


Patch 0.10.1 routine-selection contract

• Routine cards use the latest effective actual workout date per person + routine ID, newest first; live completion timestamps or historical occurrence timestamps resolve date ties. Deliberately corrected live occurrences supersede original completion stamps. Never use historical entry/audit timestamps. Equal/unknown times sort by casefolded name, exact name and permanent ID. Never-completed routines are last alphabetically; copies inherit no completion history. Ignore active/discarded/unsaved preparations; exclude deleted/archived definitions.
• Keep card markup/actions, saved manual positions and exercise order unchanged. Listing is read-only under the existing connection lock and uses validated effective history on schemas 4–7; schema 3 reads completed live sessions, schema 2 has no history. No migration, initialization, identity change or history rewrite. Preserve existing updater protections; schema 7 and Phase 10 host runtime remain compatible. Direct verified main fast-forward/push/cleanup is authorized, with no PR, deployment, real data or next phase.
