AGENTS.md — Workout Tracker

> **SHAMEFULLY VIBE-CODED PROJECT.** This project is developed primarily with AI-generated code under human direction. Do not assume the code is audited, secure, or correct. Keep this disclosure prominent in the README, all project notes, and headers of every project-owned source file where comments are supported.

Read this first

• PROJECT_SPEC.md is the authoritative description of the user’s requested behavior; read it completely before planning or changing code.
• Current authorization: Phase 1 (Foundation and Storage Safeguards) only, on a separate Git branch with tests and review. Stop before Phase 2. Do not deploy or connect to real workout data. Broader architecture approval does not authorize later phases.
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

• People are selected with simple tabs/selector; no login for initial LAN-only use. Each person has independent routines, active drafts, weights, flags, history, and charts.
• Routines can be created, renamed, edited, reordered, duplicated, and deleted. Exercises in routines can be added, edited, removed, and reordered, including prescribed sets and target reps.
• A routine may be copied from a different user or duplicated within the same user. The result is an independent snapshot, not a shared/live link. Do not copy weight/history/increase state.
• Historical workouts must retain exercise name, order, prescribed sets/reps, and results even after routine editing or deletion.

Workout entry

• Open site → select person → choose their routine → start a session with automatically recorded local date/time.
• One exercise is shown at a time, with prescribed sets/reps, previous weight and previous increase next time flag for that person.
• Enter exactly one weight per exercise (not one per set); no mandatory per-set or performed-reps entry. Set today’s weight initially blank so skipped exercises are unambiguous; previous weight is display-only, not silently copied into the new entry.
• Offer an optional increase-next-time toggle, Back/Next, jump-to-exercise controls, a routine overview, and a progress bar counting nonblank weighted entries, not navigation position.
• A skipped exercise must be included in the saved session with SQL NULL for weight. Never replace a blank weight with 0, an old weight, or a missing row. Charts must not interpret skipped entries as 0 lb.
• Finish & Save atomically saves the whole workout, including NULL entries, then completes the session. Avoid accidental double submission.
• Persist unfinished drafts promptly on the server with visible save/error status so they can be resumed after an interruption without losing entered weights.
• Discard Workout requires an explicit “Are you sure?” dialog, acknowledgment checkbox, Cancel, and OK disabled until acknowledgment. Cancel keeps the draft; confirmed discard affects only that unsaved/in-progress session, never saved history.
• Allow manual entry of older workouts with a chosen past date; they belong in the same history and analytics as normal sessions.
• Approved decisions: pounds by default with decimals; explicit zero is valid and distinct from NULL; one active draft per user; all-skipped completion requires confirmation; show previous-session weight/increase plus last performed weight after a skip; permanent exercise identities and optional exercise notes; corrections to saved workouts require confirmation and validation. Archive users with history. Safe restore UI is required for v1; automatic backups stay disabled until configured. Implement these in their approved phases, not all in Phase 1.

Interface and reporting

• Simple uncluttered phone-first UI; rounded cards, round/oval pill buttons, large tap targets. Support Dark, Light, and Auto (device theme, default), with a per-browser/device override.
• Screens: Home/user selection, Routine selection, single-exercise Workout entry + overview, Routine editor/copy, History/charts + historical entry, Settings.
• Separate user-specific historical tables, exercise weight progression charts, date/exercise filters, and basic personal records. Show skipped entries as skipped/blank, never as zero performance.

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
• No public-facing bind by default. LAN-only without passwords means LAN users can see and alter shared household data; document this. If remote access is added later, revisit authentication, HTTPS, rate limiting, and access controls before enabling it.
• Standard web safeguards still apply: server-side ownership checks (even though selector has no auth), CSRF protection on mutating forms, escaping, input validation, least-privilege file access, and safe backup/restore path handling.

Tests, review, and working style

• Use test fixtures, never a real workout DB, for development tests, destructive commands, migrations, or restore rehearsals.
• Cover: user/routine isolation and independent copies; exercise ordering; one weight per exercise; skipped exercise produces a present row with SQL NULL; progress bar semantics; previous-value display after skip; save idempotency; drafts/resume/discard confirmation; historical snapshots; migration success/failure with unchanged original; backup/restore integrity; scheduler missed-run and duplicate-run protection; theme persistence; core responsive accessibility.
• Before changes to schema, data storage, backup, restore, or session completion, explain the risk, data path, validation, and rollback approach.
• Make changes in small reviewable phases/branches/PRs. Record test results and limitations; never silently deploy to the live home server.
• Update PROJECT_SPEC.md when the user approves new requirements. Keep undecided implementation details in its “Open decisions” section rather than deciding unasked.
