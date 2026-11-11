# Schema 10 and historical correction compatibility

**SHAMELESSLY VIBE-CODED 🤖**

This application was built with a healthy dose of AI, questionable amounts of confidence, and minimal human supervision. It appears to work, but don’t mistake that for a warranty. Use at your own risk, and keep backups.

Schema 10 adds nullable `actual_reps_json` to live and historical exercise entries.
It is an ordered array with exactly the captured set count, integer repetitions
0–10000. SQL NULL means actual reps were not recorded, never fabricated zeros.
Drafts initialize from captured targets; original completed legacy records remain
NULL. Completed skips retain NULL measurements and repetitions. One weight remains
on each exercise occurrence. Duration modes have no repetition array.

Original completed rows stay immutable. Effective history overlays append-only
correction JSON; new revisions may add `actual_reps`. Old payloads need no field
and are validated in their original shape/hash/chain. Before states match the prior
revision exactly. Original arrays and previous corrections are never rewritten.

Explicit candidate migration validates classifications before DDL, copies every
old cell and audit, aligns only current routine basis with Library defaults when
classified conventions disagree, reinstalls protection triggers, validates schema,
foreign keys, integrity and audit chains, then atomically activates. Original source
bytes and selection stay usable on failure. Unclassified weighted defaults,
routines, active drafts or effective completed history refuse migration with Update
1 guidance. Duration-only records need no basis. No startup migration is allowed.

Permanent basis triggers reject edits and incompatible time/weight mode-family
changes, and require routine convention to match the Library identity. New weighted
Library IDs require explicit total/per_side selection. Historical snapshots retain
their own bases; Phase 13 assignments overlay classification while ordinary
corrections already contain effective converted numerical values. Never reapply a
conversion multiplier to those recorded weights.

No Phase 13 audit table/column/index is safely removable: `basis_transitions` binds
canonical payload hashes and expected effects; `basis_assignments` links each
original entry's basis and numerical correction. Both are required to verify old
conversions and reconstruct effective historical bases. Original `weight_meaning`
and prepared `basis_epoch` data remain only for historical compatibility. No new
preparation epochs are written. Read-only `basis.audit_weight`, `audit_payload`,
`overlay` and `validate` preserve this compatibility. They cannot append conversions.
Insert guards close both conversion tables; transition writer/routes/forms are gone.
Previously released schema definitions stay unchanged for upgrades and recovery.

Manual/scheduled backups include the arrays and all old audit records. Restore
requires exact schema and storage identity and uses another verified candidate.
Schema-9 backups remain retained and cannot silently restore into schema 10. The
existing browser/host/v4 updater detects target 10 through release-info and invokes
explicit migration. Failed-update recovery never blindly starts an incompatible
old image after activation. Protect the whole storage tree and private .env too.
