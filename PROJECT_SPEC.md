# Workout Tracker — maintained application specification

**SHAMELESSLY VIBE-CODED 🤖**

This application was built with a healthy dose of AI, questionable amounts of confidence, and minimal human supervision. It appears to work, but don’t mistake that for a warranty. Use at your own risk, and keep backups.

## Product and release

Version 1.0.1 / schema 13 is a private home-server Flask/SQLite application for
multiple household people. It is passwordless trusted-LAN software, not public
hosting or a security boundary between household members. Ordinary workouts/history
work offline; optional Garmin and application updates need internet. Docker Compose
runs web and scheduler; the independent host updater stays outside app containers.

README.md is the beginner operating guide. docs/MEASUREMENTS.md describes current
and legacy results; docs/STORAGE.md covers persistence/recovery; docs/UPGRADING.md
preserves older upgrade prerequisites; docs/GARMIN.md records verified API contracts;
docs/TESTING.md and RELEASE_1_0_0_TEST_REPORT.md record verification.

## People, exercises and routines

People switch through People, without browser-style tabs/accounts. Archive people
with history rather than deleting records. Each has independent routines, draft,
recommendations, history, body weights and Garmin settings. Accent colors persist
in private external settings; themes Auto/Light/Dark are browser-local.

The Exercise Library is globally shared with permanent IDs. Ordinary lists hide
raw IDs and safely truncate long names. The three-dot menu sits at the card’s top right above the full-width name.
The accessible three-dot menu offers
Edit Defaults and the existing impact-reviewed permanent deletion. Clicking a
name opens a read-only summary with icons/configuration and Edit Exercise action.
Rename preserves IDs/references; completed snapshots keep their original names.

Exercise measurement capabilities are any nonempty subset of Weight, Repetitions,
Duration. Sets remain 1–1000. Applicable targets are reference settings. Weighted
identities require explicit permanent Total Weight ×1 or Per Hand / Side ×2;
never infer equipment meaning or unlock basis by disabling a capability.

Defaults Only saves global name/defaults for future routine additions. Apply
previews a signed confirmed overwrite of only the selected person's current
routine settings in one atomic transaction. Other people's routines, active
snapshots and history stay unchanged. Capability changes also require explicit
confirmation. Temporary basis classification/conversion writers remain removed.

Routines support create/rename/edit/reorder/copy/delete. Copying creates independent
routine IDs/settings and reuses exercise IDs, never results or recommendations.
Cards sort by latest effective actual completion, never entry time; uncompleted
cards sort alphabetically last. Deleting routines preserves completed history.
Permanent exercise deletion retains its explicit household-wide impact workflow.

Two SVG slots independently support 300 KiB each with bounded upload/canonicalized
validation, passive vector allowlists, accent rendering and unchanged 1024-element
complexity restrictions. Invalid uploads preserve previous artwork.

## Workout recording

One exercise screen and exactly one exercise-level weight, regardless of sets.
Each set records enabled actual reps/duration and an explicit status:
incomplete, completed or skipped. Inputs start blank. Incomplete drafts preserve
partial NULLs and resume. Completed sets require every enabled value; zero weight
and reps are valid, duration must be positive. Explicit skips store true SQL NULL
per-set values; all-skipped exercise weight is NULL. Missing inputs never become
zero, previous performance or automatic skips. Unresolved sets block Next/finish.
An entirely skipped workout needs explicit confirmation.

Exercise weights use integer tenths lb, truncating extra decimals without rounding.
Durations use integer seconds; over-59 seconds normalize. Autosave must preserve
focused text/cursor/node and not steal focus. Blur/Next can normalize validated
weight. One active draft per person; owner/revision checks prevent stale writes.
Acknowledged Next controls furthest navigation checkpoint; Back/revisits/autosave
never add false progress. Keep bar and Exercise N of M, remove redundant advanced
text. Finish atomically saves/completes; discard/exit retain their confirmations.

Previous compatible performance is person/exercise/capabilities/basis specific.
Show previous measurements/manual increase recommendation and last performed after
a skip. Never prefill actuals. Increases remain manual, not automatic targets.

## History and progress

Completed live/manual history is newest first by actual occurrence. Date/routine/
exercise filters preserve person ownership. Snapshotted identity/name/order/targets/
capabilities/basis never change when routines change. Historical entry is independent
of active drafts, idempotent and atomic; optional unknown time stays NULL.
Corrections require explicit confirmation and append auditable before/after values
with stale-revision rejection. Original completed rows/set rows remain immutable.
All readers use the same validated effective correction/conversion layer.

Normal timestamps are local 24-hour HH:mm without visible IANA names. Retain stored
zones, precision and DST validation/diagnostics. History filters stack on phones.
Progress defaults to 3 calendar months, offers 3/6/12/24 Months, All Time and Custom,
and preserves URL selection. Old day-range links remain usable as Custom.

Separate weight, actual reps and actual per-set duration axes; never mix incompatible
capabilities/basis meanings/IDs. Combined capabilities show adjacent charts with
local tooltips and accessible data. Preserve zero; do not plot SQL NULL skips.
Legacy duration stays one exercise-level result, not invented per-set points.

Progress CSV stays a wide selected-exercise/date-range sheet, one completed workout
per row, oldest first, stable tie ordering. Legacy formats remain compatible. New
records expose exercise weight once, ordered set actuals/statuses and historical
targets. Skip/absent actuals blank, zero preserved; semicolon per-set lists and
m:ss durations. CSV quoting/formula protection apply to all user text.

## Statistics and reports

One exact shared lifting engine: weighted reps sum completed actual repetitions ×
exercise weight × basis multiplier. Weight-only/weighted duration without reps
count one lift per completed set, never elapsed seconds. Without weight/skipped
sets contribute zero. Retain legacy prescribed-rep assumptions only when actual
reps never existed, explicitly labeled. Old conversions/corrections apply once.
Pounds primary, tons alongside with maximum one decimal across all scales; short
ton=2000lb, scaling thresholds chosen from unrounded values.

Routine selection shows latest 12 Monday weeks and 12 calendar months, including
zero periods, completed IDs counted once, local timezone and selected accent.
Workout summaries retain same-routine previous-30-day comparisons and lifetime.

Reports provide local PDF and detailed machine-readable CSV for selected dates,
with workout counts, weekly/monthly frequency, completed/skipped/unknown sets,
actual reps/durations/weights, compatible records/progress, lifting estimates and
the immediately preceding equal-length period. PDFs paginate, repeat table headers
and escape names. Generated files are not retained. Detailed CSV identifies
workout/exercise/set/source, preserves unknown legacy detail and formula safety.

## Body weight and Garmin

Weight navigation tracks selected-person body measurements locally, separate from
exercise lifting. Positive manual weights use integer thousandths lb, aware date/
time, permanent ID/source/metadata. Multiple readings per day remain distinct.
Manual edit/delete uses confirmation, revisions and before/after audit. Charts
show actuals and 7/30-day averages computed daily-first over observed days.

Each person has independent official Garmin Personal API key/token/status/attempt/
success/error/schedule. Verify current official docs before API changes. Private
0600 credentials live outside downloadable SQLite. Never expose them in responses,
logs, reports or exports. Token acquisition/renewal follows official plain-JWT
contract, with no invented refresh endpoint. Idempotent timestamp source IDs avoid
duplicate imports; revised source values append audits, Manual records untouched.

Sync uses bounded verified HTTPS, no redirects, short claims and atomic imports,
rate-aware backoff; network never holds the workout lock. Default automatic interval
six hours, opt-in/configurable 1–168, last 30 local days. Existing scheduler stays
network-none unless .env explicitly opts into bridge; manual sync uses web network.
Local history works during outages. Private-file recovery needs whole-tree backup.

At workout start check local body-weight records for today. If present proceed;
otherwise optional weigh-in with real cached Garmin status. Blank/Skip creates no
record and durable session acknowledgment prevents repeated prompts. Never contact
Garmin synchronously to start a workout or create duplicate workout sessions.

## Storage, administration and updating

Explicit init only for a new path. No ordinary-startup initialization/migration/
restore/repair. Migration copies a separate candidate; validate schema, every old
value/NULL, integrity/FKs/counts/logical chains before atomic activation. Retain
originals/failed candidates. Schema 13 adds capabilities, new set tables, audited
body weights and durable prompt acknowledgment while retaining legacy snapshots.

Backups disabled until configured. Verified SQLite backups/confirmed restores use
existing locks, identity/exact-schema checks and separate candidates. Never silently
downgrade or merge later records. Database Download uses SQLite backup, validates
and removes temporary paths; it includes local records but excludes external
credentials/preferences/signing material. It is not a full backup replacement.

Independent host updater pins approved source, reads release-info without storage,
backs up/validates, builds before candidate migration, requires explicit consent,
checks health and preserves recovery inputs. Failed migration keeps original;
after schema activation never restart an incompatible old image or silently restore.
Live console remains bounded sanitized text, independent of Flask availability.
Both browser and v4 remain supported; no application Docker socket access.

## PERMANENT mandatory release requirements

For every major/minor/patch/bug/UI/database/deployment release, Codex must open and
review README against real features, verify commands/configuration/updates, fix
versions/links/filenames and preserve the beginner-first opening/installation guide
and exact humorous SHAMELESSLY VIBE-CODED disclosure. Record the review even if no
README edits were needed. Accurate concise human-readable release notes in
releases/VERSION.json are mandatory; verify version/user-facing claims before merge,
never substitute Git logs/hashes/internal details. See AGENTS.md.

Use synthetic databases and official Garmin mocks, never production data. Run full
backend, Chromium/mobile, Docker and migration/backup/updater regressions; fix
blocking defects without weakening tests. Review security-sensitive code and full
diff. Direct verified merge/push/remote verification/merged-branch cleanup is
explicitly authorized; no PR API, force push, protection bypass, deployment or
unrelated identity investigation. Preserve beginner-friendly source comments.
