# Storage, backup and recovery

**SHAMELESSLY VIBE-CODED 🤖**

This application was built with a healthy dose of AI, questionable amounts of confidence, and minimal human supervision. It appears to work, but don’t mistake that for a warranty. Use at your own risk, and keep backups.

## Layout and locking

External storage contains config/active.json selecting a versioned SQLite database
under data/, retained schema archives, backups, logs and private config. Code and
containers are replaceable; storage is not. Private .env and updater recovery state
also need protection. Use local POSIX disk and restrictive writer ownership.

Shared/exclusive root locks coordinate writers, migration and restore. Normal app
startup only inspects verified existing storage. Missing/corrupt/incompatible files
fail safely; never automatically initialize, replace, restore or migrate.

## Schema 13 candidate migration

Keep all frozen earlier schema constants. Copy verified schema 12 into a separate
candidate with SQLite backup. Rebuild only four measurement tables to add flex
constraints/capabilities; preserve all old fields/cells/NULLs. Add ordered set tables,
audited body weights and workout weigh-in acknowledgment. Legacy snapshots keep
NULL capabilities/no fabricated sets; current configs get 3/4/5 capability mapping.

Validate exact schema objects, integrity, foreign keys, old counts/values, immutable
snapshot structure and correction/conversion/body audit chains. Atomically select
only a verified candidate. Preserve original database bytes and old selection on
failure. Older migration steps and classification checks remain supported.

## Schema 14 and permanent configuration protection

Only explicit candidate migration adds Ego Lifts/audits, weight-only draft checkbox
intent and Garmin precision guards. Every schema-13 DDL object remains unchanged.
Original workout/set/correction/conversion cells and NULLs remain unchanged.
Exercise Library and per-person routine settings are captured semantically before
upgrading and compared before selection. No generic 3×12 reset is authorized.
configuration_protection.verify accepts only exact identity/field/old/new/reason
allowances for a deliberately approved future change. Legacy capability mappings
retain equivalent meanings; the previously approved schema-10 basis transition
has exact per-record allowances rather than a broad exemption.

Garmin body-weight precision is the one authorized existing-data adjustment:
Decimal ROUND_HALF_UP to a tenth of a pound, with original rows captured in new
before/after audit revisions. IDs/times/source metadata and earlier audits stay
unchanged; Manual values are untouched. Verified original gram metadata is used
when consistent with the saved value. Ambiguous/mismatched metadata refuses the
migration instead of repairing units. New Garmin records require multiples of 100
in integer-thousandths storage. Private credential files remain outside SQL and
are not rewritten. Migration failure retains original selection, database and
existing backups; failed candidates remain for inspection.

Ego attempts support confirmed audited soft deletion. Explicit global exercise
deletion includes those attempts and audits in its existing household-wide impact
review. New Ego data is included by the existing generic SQLite backup/download
infrastructure; credentials remain excluded.

## Backups versus downloads

Backup Now/scheduler creates verified SQLite copies with operation metadata.
Restore uses a separately copied verified candidate, same storage identity and
exact schema, explicit warning/type RESTORE confirmation. It retains originals;
it does not merge later records or silently downgrade. Corrupt/incomplete backups
must be rejected before selection. Download Database uses SQLite's backup API,
validates, unlinks temporary paths and streams a consistent current snapshot.

Both include SQLite workouts, set/body records, icons and audits. Neither includes
external Garmin credentials, session signing keys, person preferences, schedule
settings or host .env. Protect the whole external tree off-machine separately;
that copy contains secrets and must remain private. Same-server backups alone do
not protect against disk loss.

## Failed updates and manual recovery

Use the independent status page and private host recovery records. Before candidate
activation, recover only after verifying original storage/config/selection/bytes
and retained compatible image. After activation do not restart an incompatible
image or silently restore an older database. Keep services stopped if compatibility
cannot be proven. Preserve backups, originals and failed candidates for diagnosis.
Detailed operator commands and the exact CLI restore procedure remain in
[deployment/README.md](../deployment/README.md). Never edit schema markers or
initialize a replacement to conceal a damaged/missing mount.
