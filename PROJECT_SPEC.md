# Workout Tracker — maintained application specification

**SHAMELESSLY VIBE-CODED 🤖**

This application was built with a healthy dose of AI, questionable amounts of confidence, and minimal human supervision. It appears to work, but don’t mistake that for a warranty. Use at your own risk, and keep backups.

## Product and release

Version 1.1.0 / schema 14 is a private home-server Flask/SQLite application for
multiple household people. It is passwordless trusted-LAN software, not public
hosting or a security boundary between household members. Ordinary workouts/history
work offline; optional Garmin and application updates need internet. Docker Compose
runs web and scheduler; the independent host updater stays outside app containers.

README.md is the beginner operating guide. docs/MEASUREMENTS.md describes current
and legacy results; docs/STORAGE.md covers persistence/recovery; docs/UPGRADING.md
preserves older upgrade prerequisites; docs/GARMIN.md records verified API contracts;
docs/TESTING.md and RELEASE_1_0_0_TEST_REPORT.md record verification.

## PERMANENT — never reset user-configured exercise settings

Updates, migrations, maintenance, imports and general application changes MUST NOT
silently replace existing Exercise Library defaults or anyone's routine settings.
Preserve the database's CURRENT sets, reps, duration, capabilities, Weight Basis,
meaning, notes and every other configuration field. A stored 2 × 15 stays 2 × 15;
never substitute generic 3 × 12. Never guess or reconstruct previously altered
settings. New exercises may use initial defaults. Explicit user edits and confirmed
Apply-to-My-Routines remain allowed and person-scoped.

Every candidate migration MUST capture and compare semantic configurations using
configuration_protection.capture/verify before activation. Schema representation
changes must map equivalent meanings. A deliberately authorized change must name
the exact identity, field, old/new values and reason and validate that exact result;
no blanket exemptions. Unexpected changes reject activation and retain the original
database, selection and existing backups. Keep regression tests with varied library
and independently customized per-person routines, including a simulated reset that
must fail. This requirement applies to every future release.

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
Each set records enabled actual reps/duration and an internal status. The live form
has no status dropdown. Empty inputs use a visual em dash only. Complete enabled
values imply Completed; partial required values block Next/Finish with inline
errors. Draft autosave preserves partials and blanks as Incomplete; blank sets may
be navigated past and become Skipped only on Finish. Weight-only exercises have
one shared weight plus a Done checkbox per set; shared weight never performs a set.
Unfinished checkbox intent is persisted separately even before weight is entered.
Zero weight/reps are valid; duration must be positive. Finish is one transaction,
resolves every untouched blank set to SQL NULL Skipped, and clears exercise weight
and increase flag when all sets are skipped. All-skipped workouts require explicit
confirmation. Historical completed snapshots and their old status meanings remain
unchanged; deliberate historical/correction forms retain explicit status controls.

Exercise weights use integer tenths lb, truncating extra decimals without rounding.
Durations use integer seconds; over-59 seconds normalize. Autosave must preserve
focused text/cursor/node and not steal focus. Blur/Next can normalize validated
weight. One active draft per person; owner/revision checks prevent stale writes.
Acknowledged Next controls furthest navigation checkpoint; Back/revisits/autosave
never add false progress. Keep bar and Exercise N of M, remove redundant advanced
text. Finish atomically saves/completes; discard/exit retain their confirmations.

Previous compatible performance is person/exercise/capabilities/basis specific.
Show Last session: Completed/Partially completed/Skipped separately from Last
performed measurements, actual reps/durations, date and increase recommendation.
Search across routines and repeated skips by person/permanent exercise ID and
compatible capabilities/Weight Basis using effective corrections. Skips never erase
the last performed recommendation; missing legacy actuals remain labeled unknown. Never prefill actuals. Increases remain manual, not automatic targets.

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
duplicate imports; revised tagged source values append audits, Manual records untouched.
Accept numeric epoch milliseconds and aware ISO timestamps, normalize to UTC without
float rounding. The individual-reading wire adapter converts grams using exact
453.59237 g/lb, rounds once to 0.1 lb with Decimal ROUND_HALF_UP and retains
original value/unit. Schema 14's explicit candidate upgrade appends before/after
precision revisions for prior Garmin records while retaining IDs, dates, sources
and old audits. Manual precision remains unchanged. SQL guards reject new Garmin
weights not divisible by 100 thousandths. No unit repair or credential changes. Refuse malformed, ambiguous or
out-of-envelope readings atomically. Do not reinterpret existing untagged imports;
conflicting old values stop for review. See docs/GARMIN.md for the public-reference
discrepancy. All exceptions/cancellation release owned claims with fixed nonsecret
errors; hard-killed workers have bounded five-minute recoverable leases.

Sync uses bounded verified HTTPS, no redirects, short claims and atomic imports,
rate-aware backoff; network never holds the workout lock. Default automatic interval
six hours, opt-in/configurable 1–168, last 30 local days. Existing scheduler stays
network-none unless .env explicitly opts into bridge; manual sync uses web network.
Local history works during outages. Private-file recovery needs whole-tree backup.

At workout start check local body-weight records for today. If present proceed;
otherwise optional weigh-in with real cached Garmin status. Blank/Skip creates no
record and durable session acknowledgment prevents repeated prompts. Never contact
Garmin synchronously to start a workout or create duplicate workout sessions.

## Ego Lifts

A trophy button immediately below routines opens a searchable alphabetical global
library and independent selected-person attempts. One weight (existing truncation)
and positive whole reps; save captures UTC now and displays configured local IANA
time. Signed person/exercise-bound submission IDs make double taps/retries idempotent.
Snapshot exercise name, permanent ID, established basis/meaning; otherwise record
Total Weight for this attempt only. No library/default/routine/draft/history edits.

Person/exercise history offers confirmed, revision-checked corrections and soft
deletion with immutable before/after audits. Compare records only within compatible
exercise/basis/meaning groups. Heaviest weight includes its reps; estimated 1RM uses
Epley for 2–10 reps and actual weight for one rep, never estimates above 10 reps.
Exclude Ego Lifts from every ordinary workout, total, recommendation and consistency
query. Backup/restore/download includes their SQLite records/audits. Explicit global
exercise deletion previews and removes associated Ego attempts/audits too.

## Storage, administration and updating

Explicit init only for a new path. No ordinary-startup initialization/migration/
restore/repair. Migration copies a separate candidate; validate schema, every old
value/NULL, integrity/FKs/counts/logical chains before atomic activation. Retain
originals/failed candidates. Schema 13 added capabilities, sets, audited body weights and durable prompt
acknowledgment. Schema 14 adds separate Ego records/audits, draft checkbox intent,
Garmin precision guards and an audited candidate-only precision adjustment. Existing
workout/configuration/set cells remain unchanged.

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
