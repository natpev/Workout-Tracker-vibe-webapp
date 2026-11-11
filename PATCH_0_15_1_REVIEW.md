# Patch 0.15.1 — larger exercise illustrations

**SHAMELESSLY VIBE-CODED 🤖**

This application was built with a healthy dose of AI, questionable amounts of confidence, and minimal human supervision. It appears to work, but don’t mistake that for a warranty. Use at your own risk, and keep backups.

Started from approved remote main 1aa6ef0f91f1f136292eeb7cb9da717f8ec371e8
on patch-0.15.1-icon-upload-size. Direct fast-forward merge/push/verification and
branch cleanup are authorized; no PR, deployment or production access.

## Implementation and scope

Application 0.15.1 sets MAX_BYTES = 300 * 1024. Start and End each independently
accept 307,200 bytes, including both at once. Multipart reads remain bounded to
MAX_BYTES+1; original UTF-8 and canonical output are checked separately. Upload
help and errors say 300 KiB per image. Existing safe inline accent rendering,
artwork, positions, defaults and independent management forms remain unchanged.

No element, attribute, coordinate, text, XML or paint security limit is enlarged.
The 1,024-element complexity error remains distinct from the byte-size error.
Script/event/HTML/resource/unsupported XML rejection remains. No illustration is
compressed, simplified or stripped to make it fit. Invalid/oversized/expanded
canonical output leaves the previous custom image unchanged atomically.

## Necessary database change — separately approved

Initial review found a second limit: schema 11's exercise_icons CHECK restricts
stored SVG text to 65,536 characters. A valid synthetic 84,046-byte SVG failed
that CHECK in an in-memory test. Increasing Python's constant alone could not
safely implement the requested upload sizes. The user explicitly approved the
minimal **schema 12** migration after this finding; schema 11 is not silently
redefined. See docs/SCHEMA_12.md.

Only the candidate's exercise_icons table is rebuilt, with identical columns,
keys and foreign key, replacing the text-size CHECK with a 307,200 UTF-8-byte
CHECK. Every other DDL definition is unchanged. All old cells, SVG text, IDs,
routines, drafts, histories, NULLs and correction/conversion audits are compared
and preserved by the existing migration validator. Integrity/FK/exact-DDL,
effective history and audit checks precede atomic activation. Failure leaves the
original unchanged and restores original selection even after activation sync
failure. Startup never migrates. Same-target migration is a read-only no-op.

Schema-11 storage remains readable and supports small icons; a larger icon gives
an explicit schema-12 upgrade message without replacing the previous image.
Verified backups/restores include both full-sized icons and require exact schema.
Older backups remain retained; no automatic downgrade or cross-version restore.

The existing browser/v4 updater detects target 12 through storage-free release
metadata and uses explicit candidate migration consent. No new updater script,
service refresh after Phase 12 setup, .env or Compose change is necessary.

## Existing installation upgrade

1. Wait for Saved on open workouts and make/verify a backup. Protect the whole
   storage tree and private .env separately as usual.
2. Settings → Administration → Application Updates → Check for Updates.
3. Review application **0.15.1 / schema 12**, explicitly approve migration and
   Install. The independent updater stops writers, verifies a backup, builds the
   approved pinned release, validates a separate candidate and restarts.
4. Verify Settings/footer and readiness:

```bash
curl --fail http://10.0.69.9:8000/health/ready
```

Expect app_version 0.15.1, schema_version 12 and status ready. Use the installation's
actual address if different. Make a new verified schema-12 backup after success.
Never initialize existing storage or restore older backups as an update shortcut.

Emergency SSH, with no other update running:

```bash
bash /root/WorkoutTracker/app/deployment/update_workout_tracker_v4.sh
```

Review/confirm the release and explicitly type **MIGRATE 12** when prompted. The
original schema-11 database remains preserved. No command was run on the server.

## Tests and release documentation

Final complete suite: **768 passed, zero failed, zero skipped**, in **1059.29
seconds (17m39s)**: **620 backend/script, 124 Chromium and 24 Docker**.

```sh
WORKOUT_CONTAINER_TESTS=1 python -m pytest -q --tb=short --show-capture=no
```

This retains the 740-test baseline and adds 20 backend, six browser, one Docker
icon test and one additional real updater case. Original SVG security tests stay
intact; previous size-only fixtures now use the new limit. Early test-development
failures were fixed by using the public selection manifest for database paths;
no application safeguards or assertions were removed to obtain passing results.

Focused backend run: 90 passed in 23.97 seconds. New mobile/theme browser
cases: 6 passed in 37.49 seconds. Initial real-image migration/restore plus
documentation checks: 4 passed in 7.30 seconds. These checks are repeated within
the full suite, not additional unique test counts.

Final runtime image: `sha256:0f0da069f20ff53a6d6a4c384c7651d7308452401197f092af133e80da173e42`.

New tests use real passive vector documents, with most bytes in path geometry:
85/150/250 KiB, exactly 307,200 and 307,201 bytes, independent/replaced slots,
canonical expansion, bounded reads, complexity/security rejection, prior-image
preservation, accent recoloring and verified full-size backup/restore. Migration
checks cover exact old cells/DDL, unchanged originals and five fault stages.
Chromium tests cover 320/390 portrait and 844 landscape in Light/Dark; disposable
containers exercise real CLI migration, stored icons, restore and replacement.
Existing browser/v4 updater regressions include schema-11 upgrade and schema-12
code-only maintenance without database migration/copy.

README was opened/reviewed against current features, CLI, Dockerfile, Compose and
v4. Updated versions, new-install target, existing upgrade path and icon guidance;
also corrected stale README wording that said reps started at targets, matching
Phase 15's already implemented blank-set behavior. Beginner opening, numbered
installation, data separation and humorous disclosure remain. Local links and
shell blocks are checked by the retained release-documentation tests. Versioned
releases/0.15.1.json contains two short user-facing notes without implementation
jargon. AGENTS/PROJECT_SPEC record the approved constraint-only schema change.

No physical iPhone/Safari, real host/systemd provision or production installation
was tested or modified. Git transport/source fetching and host disk-path probes
in existing updater rehearsals use their established synthetic adapters; actual
Docker/Compose, backup/candidate migration/recovery and health checks remain real.
