# Phase 1 review

> **SHAMELESSLY VIBE-CODED 🤖**
>
> This application was built with a healthy dose of AI, questionable amounts of confidence, and minimal human supervision. It appears to work, but don’t mistake that for a warranty. Use at your own risk, and keep backups. This review describes unapproved-for-production software.

## Scope and safety

Only Foundation and Storage Safeguards are implemented. Flask renders a theme
shell; an operator CLI initializes fresh external metadata; startup/readiness
only verify existing storage. No people, routines, workout entry, corrections,
migration execution, backup creation, scheduler, or restore interface exists.

The main risk is selecting or replacing the wrong storage. The explicit CLI
requires a new external directory and refuses existing trees. A constrained
manifest selects one database; startup uses read-only SQLite and rejects
incompatible metadata. All validation uses temporary fixtures. There is no
connection to real workout data and no deployment.

First installation reserves a new directory, writes a distinct database, syncs
it, then atomically publishes the manifest without overwriting an existing
selection. Interrupted initialization leaves evidence and refuses blind retries.
The rollback for Phase 1 is stopping the test process and reverting application
code; existing storage is never converted or removed. Restoring older schema
data is deliberately unavailable until safe recovery tooling is implemented.

## Validation record

Validated on the cloud development machine using Python 3.12.14 and SQLite
3.53.1. All databases were disposable fixtures outside the checkout.

- Final command: `WORKOUT_CONTAINER_TESTS=1 /workspace/phase1-venv/bin/python -m pytest -q`
- **41 passed, 0 failed, 0 skipped** (37 foundation/storage cases, 2 Chromium
  cases, 2 opt-in Docker/Compose cases).
- Storage checks cover explicit confirmation, existing/missing/orphan storage,
  identity/schema mismatch, corruption, unreadable files, symlinks, traversal,
  interrupted publication, competing initialization, and refusal to recover
  sidecars. Hash comparisons verify existing files remain unchanged.
- Browser checks cover Auto/Light/Dark, reload persistence, device theme changes,
  blocked/invalid browser preferences, label/focus behavior, local-only asset
  requests, no JavaScript exceptions, and widths 320/768/1280 pixels. These are
  focused checks, not a complete accessibility audit.
- Built the pinned Python image using the configured proxy and trusted CA, with
  TLS verification retained. Initial testing exposed private copied source
  permissions; the Dockerfile now makes packaged sources readable to its
  unprivileged runtime user, and the final tests pass.
- Container checks exercised actual Gunicorn HTTP responses, no-network/no-port
  execution, read-only filesystem and external mount, replacement of the
  container against unchanged retained storage, and incompatible-schema startup
  failure without modification. All test containers were removed afterward.
- `python -m pip check`: no broken requirements. `git diff --check`: passed.

Reproduce using a local virtual environment and README instructions. Browser
and Docker tests need the documented optional tools and socket access; their
absence is reported as skipped rather than silently counted as validated.

## Review boundaries and limitations

- Startup performs a full integrity check; this is acceptable for the empty
  foundation database. Reassess readiness frequency before large databases.
- Phase 1 has no mutating HTTP requests or sessions. CSRF protection must be
  added and tested before Phase 2 adds forms; it is not a completed capability.
- Storage must be on a local POSIX filesystem. Symlink rejection protects
  configuration mistakes, not a hostile administrator racing filesystem changes.
- Startup refuses sidecars instead of replaying/recovering them. WAL and
  cross-process maintenance require later design and tests before real data.
- Schema version 1 contains only metadata. Later schema additions require an
  explicit migration strategy; startup will not apply one automatically.
- Log viewing/retention, backup/restore, scheduling, user authentication, and
  production host configuration are not included or claimed to work.
- Approved saved-workout corrections are scheduled for the history phase;
  exact editable fields and audit behavior still need definition.
- The base image digest is pinned, but no external security audit or production
  readiness claim is supplied. Stop for user review before Phase 2.
