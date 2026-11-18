# Upgrades and historical prerequisites

**SHAMELESSLY VIBE-CODED 🤖**

This application was built with a healthy dose of AI, questionable amounts of confidence, and minimal human supervision. It appears to work, but don’t mistake that for a warranty. Use at your own risk, and keep backups.

## Existing schema 14 installation (v1.1.0)

Use the normal browser update to install **1.1.1**. No database migration or host
updater refresh is needed. Verify **1.1.1 / schema 14 / ready** after installation.
Keep your usual verified backup before updating.

## Existing schema 13 installation (v1.0.2)

Use **Settings → Application Updates → Check for Updates**, review **1.1.1** and
confirm the explicit **schema 14** candidate migration. Before installing, create
a verified backup and protect the complete storage tree, private `.env` and
Garmin credential file. Never initialize existing storage or reset settings.

The independent updater builds first, validates a separate candidate, compares all
existing library/routine configurations, preserves workout/set/correction snapshots
and retains the original schema-13 database/selection. Garmin precision corrections
append audits; measurement IDs/times/source metadata and Manual records remain.
The candidate adds separate Ego Lifts and draft Done-checkbox intent. Any unexpected
configuration change refuses activation. Existing settings are not reconstructed
or guessed from older releases.

After a successful update, Settings/footer and `/health/ready` must show
**app_version 1.1.1, schema_version 14, ready**. Check your existing routines and
library settings, try Ego Lifts with disposable data, and create a new verified
schema-14 backup. Keep schema-13 originals/backups for recovery; exact-schema
restore does not silently downgrade a running schema-14 installation.

Your Phase-12-capable host updater and repository v4 entry point already support
release-info and explicit candidate migration; no new updater script or service
refresh is required. Automatic Garmin still requires the optional scheduler bridge
networking described in README. No live server was inspected or modified.

For an emergency SSH update, use the existing entry point:

```sh
bash /root/WorkoutTracker/app/deployment/update_workout_tracker_v4.sh
```

Review the approved release and explicitly confirm migration. Fetching source alone
does not rebuild/restart containers. Never force-reset local changes or overwrite
`.env`. After activation never start an incompatible schema-13 image or restore
an older database silently. Retained recovery records and deployment/README.md
explain compatibility-aware recovery.

## Existing schema 12 or older installations

Supported older migrations remain available through target 14. Complete the
classification prerequisite below where applicable. The same candidate-only
verification preserves original measurements, NULLs, history and configurations.
No set durations are fabricated for old exercise-level measurements.

## Older unclassified installations

Migration through schema 10 deliberately refuses unclassified weighted defaults,
routine configurations, active drafts or effective history. Do not auto-classify
based on exercise names/old free text or edit the database to bypass this check.

Install the approved historical 0.13.0/schema-9 Update 1 release first using the
maintained release history/operator workflow. Finish unclassified active drafts.
For each relevant person/exercise use the temporary Total Weight or Per Hand / Side
classification and confirmed Save Defaults & Update My Routines. Check defaults,
personal routines and retained history, including deleted-routine history. First
classification keeps numerical weights. Later total/per-side conversion is exact,
audited and person-scoped; nonrepresentable half-tenths must be corrected before
conversion. Save Defaults Only does not classify another person's history. Review
all people, then upgrade through permanent-basis schema 10 and onward. Keep old
source databases/backups. Current releases intentionally contain no conversion
writers and cannot perform this prerequisite for you.

Frozen schemas 1–12, original JSON/audit readers and release metadata remain.
Schema 10 added optional actual reps, schema 11 allowed partial drafts and permanent
basis protections, schema 12 expanded icon byte constraints; schema 13 adds unified
sets/body weights. Read SCHEMA_10.md, SCHEMA_11.md and SCHEMA_12.md for their exact
historical interpretation. Never rewrite these migrations or completed snapshots.

## Explicit maintenance CLI

With writers stopped and the new verified image built, the operator may explicitly
invoke the same candidate migration used by the host updater:

```sh
cd /root/WorkoutTracker/app
docker compose --env-file ../.env run --rm --no-deps web   python -m workout_tracker migrate-storage --data-root /var/lib/workout-tracker   --confirm-upgrade --target-version 14
docker compose --env-file ../.env run --rm --no-deps web   python -m workout_tracker check-storage --data-root /var/lib/workout-tracker
```

This is not a substitute for the updater's image/build/recovery safeguards. Never
restart an old incompatible image after successful schema activation. Failed
migration retains original selection; failed startup after activation requires
compatibility-aware recovery, not silent restoration. Full details are retained in
[deployment guide](../deployment/README.md).
