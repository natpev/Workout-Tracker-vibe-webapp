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
