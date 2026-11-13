# Upgrades and historical prerequisites

**SHAMELESSLY VIBE-CODED 🤖**

This application was built with a healthy dose of AI, questionable amounts of confidence, and minimal human supervision. It appears to work, but don’t mistake that for a warranty. Use at your own risk, and keep backups.

## Existing schema 13 installation

Version 1.0.2 is a code-only patch for schema 13. Use the normal browser update;
no database migration, connection reset or host-service upgrade is needed. It fixes
Garmin timestamp parsing, gram-to-pound conversion and sync error recovery.
After updating, confirm **1.0.2 / schema 13 / ready**, then open the selected
person’s Settings → Garmin → Sync Now. Saved keys and local records remain.
An old abandoned claim expires after five minutes; an error normally defers retry
for 15 minutes (or longer when Garmin requests it). Do not reconnect or edit private
files merely to clear a claim. Older-format import conflicts stop safely for review;
this release does not automatically repair potentially incorrect earlier imports.

## Existing schema 12 installation

Use Settings → Application Updates → Check for Updates, review version 1.0.2 and
explicitly consent to target schema 13 migration. Confirm Install and watch the
independent status tab. Before updating create a verified backup and protect the
complete storage tree/.env. Afterwards health must report app_version 1.0.2,
schema_version 13, ready. Create a new verified schema-13 backup.

The existing Phase-12-capable host runtime and v4 entry point understand release-info
and explicit target 13; no replacement updater script is needed. The default
scheduler network configuration resolves exactly as before. Automatic Garmin sync
requires optional explicit bridge networking; see README and GARMIN.md. No live
server/script outside the repository was inspected or changed during development.

For emergency SSH:

```sh
bash /root/WorkoutTracker/app/deployment/update_workout_tracker_v4.sh
```

Never init-storage on an existing installation. Never overwrite .env or force-reset
local changes. Source fetching alone does not rebuild/restart containers. Host
service upgrades require the separate explicit installer; app container updates
cannot replace its private runtime/assets. See deployment/README.md.

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
docker compose --env-file ../.env run --rm --no-deps web   python -m workout_tracker migrate-storage --data-root /var/lib/workout-tracker   --confirm-upgrade --target-version 13
docker compose --env-file ../.env run --rm --no-deps web   python -m workout_tracker check-storage --data-root /var/lib/workout-tracker
```

This is not a substitute for the updater's image/build/recovery safeguards. Never
restart an old incompatible image after successful schema activation. Failed
migration retains original selection; failed startup after activation requires
compatibility-aware recovery, not silent restoration. Full details are retained in
[deployment guide](../deployment/README.md).
