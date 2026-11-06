AGENTS.md — Workout Tracker

> **SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.** This project is developed primarily with AI-generated code under human direction. Do not assume the code is audited, secure, or correct. Keep this disclosure prominent in the README, all project notes, and headers of every project-owned source file where comments are supported.

Read this first

• PROJECT_SPEC.md is the authoritative description of the user’s requested behavior; read it completely before planning or changing code.
• Current status: Phases 1–5 are completed, approved and merged. A narrow installation-documentation task is authorized: add and verify the README guide, make minor Compose reliability/configuration improvements, run disposable checks, and fast-forward merge/clean up its temporary branch. Full Phase 6 (real installation, real-world testing and final polish) still requires separate authorization. Do not deploy to the actual server, use real workout data, add cloud synchronization or authentication.
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

• Keep the approved Phase 2 user-switching implementation: users switch through the People screen. Do not redesign the selector or add browser-style tabs. No login for initial LAN-only use. Each person has independent routines, active drafts, weights, flags, history, and charts.
• Routines can be created, renamed, edited, reordered, duplicated, and deleted. Exercises in routines can be added, edited, removed, and reordered, including sets and target reps (Weight) or target duration per set (Time), selected with a segmented Weight/Time control.
• A routine may be copied from a different user or duplicated within the same user. The result is an independent snapshot, not a shared/live link. Do not copy weight/history/increase state.
• Historical workouts must retain exercise name, order, measurement type, prescribed sets/reps or duration, and results even after routine editing or deletion.

Workout entry

• Open site → select person → choose their routine → start a session with automatically recorded local date/time.
• One exercise is shown at a time, with sets × target reps or duration, previous matching measurement and previous increase next time flag for that person.
• Enter exactly one applicable measurement per exercise (weight or duration, never one per set); no mandatory per-set or performed-reps entry. Today’s measurement starts blank; previous performance is display-only. Use type-specific increase labels. Store duration as integer seconds, independent of set count.
• Offer an optional increase-next-time toggle, Back/Next, jump-to-exercise controls, a routine overview, and a progress bar counting non-NULL applicable measurements, not navigation position.
• A skipped exercise must be included in the saved session with true SQL NULL for the applicable measurement; both actual weight and duration are NULL when skipped. Never replace a blank weight with 0, an old weight, or a missing row. Charts must not interpret skipped entries as zero; label weight in pounds and duration as time, and separate the two types.
• Finish & Save atomically saves the whole workout, including NULL entries, then completes the session. Avoid accidental double submission.
• Persist unfinished drafts promptly on the server with visible save/error status so they can be resumed after an interruption without losing entered measurements.
• Discard Workout requires an explicit “Are you sure?” dialog, acknowledgment checkbox, Cancel, and OK disabled until acknowledgment. Cancel keeps the draft; confirmed discard affects only that unsaved/in-progress session, never saved history.
• Phase 4 historical entry copies a chosen routine into a separate review snapshot, preserves unknown time as NULL, distinguishes occurrence from entry time, and atomically completes via an idempotent submission token without touching an active draft.
• Phase 3 implemented measurement rules: pounds by default, at most one decimal place, extra digits truncated never rounded (40.99 → 40.9; 42.56 → 42.5; 40 → 40.0). SQLite stores integer tenths (40.9 lb = 409). Explicit zero is valid; empty weight is SQL NULL. Actual durations are integer seconds, minimum 1 second; zero is invalid and empty is SQL NULL. One actual duration per exercise regardless of sets. Every skipped exercise retains an entry with NULL actual measurements, never previous values or zero; tracking types and measurements belong in historical snapshots. Do not backport workout-entry behavior or schema changes into retained Phase 2 databases.
• Approved decisions: pounds by default with one decimal place and truncation; explicit zero is valid and distinct from NULL; one active draft per user; all-skipped completion requires confirmation; show previous-session weight/increase plus last performed weight after a skip; permanent exercise identities and optional exercise notes; corrections to saved workouts require confirmation and validation. Archive users with history. Safe restore UI is required for v1; automatic backups stay disabled until configured. Implement these in their approved phases, not all in Phase 2.

Interface and reporting

• Simple uncluttered phone-first UI; rounded cards, round/oval pill buttons, large tap targets. Support Dark, Light, and Auto (device theme, default), with a per-browser/device override.
• Screens: Home/user selection, Routine selection, single-exercise Workout entry + overview, Routine editor/copy, History/charts + historical entry, Settings.
• Per-person history supports date/routine/exercise filters and saved detail. Charts group permanent exercise ID, type, unit and weight meaning separately; local SVG and accessible data lists exclude NULL numeric points but retain zero. Statistics mean highest logged weight/longest logged duration in the selected range. History, charts and previous-performance references must all use effective corrected occurrence/measurements. Show skipped entries as skipped/blank, never as zero performance.

Database protection — highest priority

• Application version is different from database schema version. Ordinary code/container updates with a compatible schema must NOT copy, back up, migrate, delete, or reinitialize the live database.
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
• Restore accepts only server-listed verified backups of the same storage identity and exact current schema (2–4); no silent downgrade. Preserve a present damaged active file only on explicit recovery with a valid manifest; refuse missing files/identity or readable newer/foreign storage. Never replay interrupted maintenance tokens. Forms are bound to the selected dataset and checked again inside the write lock.
• No public-facing bind by default. LAN-only without passwords means LAN users can see and alter shared household data; document this. If remote access is added later, revisit authentication, HTTPS, rate limiting, and access controls before enabling it.
• Standard web safeguards still apply: server-side ownership checks (even though selector has no auth), CSRF protection on mutating forms, escaping, input validation, least-privilege file access, and safe backup/restore path handling.

Tests, review, and working style

• Use test fixtures, never a real workout DB, for development tests, destructive commands, migrations, or restore rehearsals.
• Cover: user/routine isolation and independent copies; exercise ordering; one weight or duration per exercise; both types and type changes; integer seconds and strict partial-input rejection; exact weight truncation; autosave acknowledgment/network failure; concurrent tabs and restart recovery; skipped exercise produces a present row with true SQL NULL; progress bar semantics; previous-value display after skip; save idempotency; drafts/resume/discard confirmation; historical snapshots; migration success/failure with unchanged original; backup/restore integrity; scheduler missed-run and duplicate-run protection; theme persistence; core responsive accessibility.
• Before changes to schema, data storage, backup, restore, or session completion, explain the risk, data path, validation, and rollback approach.
• Make changes in small reviewable phases/branches/PRs. Record test results and limitations; never silently deploy to the live home server.
• Update PROJECT_SPEC.md when the user approves new requirements. Keep undecided implementation details in its “Open decisions” section rather than deciding unasked.
