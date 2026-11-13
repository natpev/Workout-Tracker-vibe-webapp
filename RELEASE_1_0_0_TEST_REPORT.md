# Workout Tracker 1.0.0 — release test report

**SHAMELESSLY VIBE-CODED 🤖**

This application was built with a healthy dose of AI, questionable amounts of confidence, and minimal human supervision. It appears to work, but don’t mistake that for a warranty. Use at your own risk, and keep backups.

## Release status

Application **1.0.0 / schema 13** completed verification on November 13, 2026.
**850 tests passed, zero failed, zero skipped.** No production data, deployment,
real Garmin key/account or PR was used.

| Final group | Passed | Failed | Skipped |
| --- | ---: | ---: | ---: |
| Backend and scripts | 686 | 0 | 0 |
| Real Chromium browser tests | 135 | 0 | 0 |
| Docker integration and acceptance | 29 | 0 | 0 |
| **Total distinct tests** | **850** | **0** | **0** |

The complete existing suite and new tests ran in two independent groups:
821 application/browser cases and 29 Docker cases. Both exited successfully and
confirmed the same unchanged source fingerprint throughout their runs. Per-test
results were durably saved; the final runs required no skipped or reused cases.
All original synthetic SQL fixtures remain unchanged. README, release notes,
source disclosures, installation commands and local documentation links passed
review. The release is authorized for direct main merging only after this result.

## Completed acceptance scenarios

- Real Docker Compose clean bootstrap: explicit new storage, migration, verification,
  both services, Chromium-created people/routine/all seven measurement combinations,
  one weight per exercise, set completion/skips, autosave/refresh, PDF/detailed CSV,
  body weigh-in, SQLite download and restart persistence. Two acceptance Docker
  tests passed, including the separate realistic schema-12 upgrade scenario.
- Schema-12 container CLI upgrade preserves original source bytes, effective legacy
  history/lifting, correction chains, drafts, icons, settings and foreign keys.
  Additional candidate tests verify every old SQL cell and NULL and no invented sets.
- Browser release workflows at 390×844 and 844×390 in Light/Dark exercised all seven
  combinations, explicit zero, SQL NULL skipped rows, resume/navigation/completion,
  reports/downloads, separate chart axes and person-specific body/Garmin screens.
- PDF files parsed with pypdf; detailed CSV parsed using the standard CSV reader.
  Formula-like names are escaped. Shared totals agree with recorded completed sets.
- Consistent SQLite downloads pass integrity/foreign-key checks and exclude synthetic
  private Garmin keys. SQLite backup/restore retains body history and custom icons.
- Official Garmin docs/OpenAPI and official SDK reviewed on 2026-11-13. Authenticated
  transport uses mocks only, checking separate keys/persons, renewal, source timestamp
  idempotency, multiple readings/day, revised-source audit, safe errors/backoff,
  disconnect-during-request and no secret in rendered pages/database snapshots.

## Defects corrected during verification

- Adapted copy-on-add defaults before capability validation, preserving the shared ID.
- New per-set completion now validates unresolved sets before all-skipped confirmation.
- Garmin conflict errors retain their specific safe message instead of a generic parse error.
- Fixed PDF detailed-section iteration after adding progress charts.
- Capability changes preview the actual selected measurements; progression labels and
  body/basis hints now match enabled capabilities.
- Historical set validation errors link to the correct exercise/set inputs.
- Database-level capability guards reject duplicate legacy actual storage,
  weightless completed sets and non-NULL weight on an all-skipped completion.
- Failed Garmin import transactions clear their claim and record a fixed nonsecret
  retry message after rolling back the entire batch.
- Fixed copying an old nonweighted routine after its shared definition first
  receives a permanent Weight Basis. Dormant metadata cannot unlock that basis.
  Nonweighted previous-performance lookups remain compatible across such copies.
- Fresh-install driver was corrected for actual post-create redirects; application
  protections/tests were not weakened.

## Documentation and cleanup

README reviewed and rewritten against actual Compose/CLI, preserving the beginner
opening and near-top installation. Commands were checked against Compose. Current
schema/version, storage, backup/download distinctions, optional Garmin networking
and existing-server updates are documented. Maintained measurement/storage/upgrade/
Garmin/testing guides replace obsolete phase reviews and temporary design summaries.
Frozen migration definitions, fixtures, legacy readers, audit tables and release
metadata remain. AGENTS/PROJECT_SPEC retain mandatory README/release-note review.
Versioned 1.0.0 notes describe user-facing changes rather than Git logs.

## Verification limits

Tests use temporary Linux x86-64 containers and real Chromium, not a physical
server, iPhone/Safari, ARM hardware or live Garmin account. Official Garmin API
responses are mocked. Git/source and selected host probes in updater fault tests
use controlled adapters; real-container tests separately exercise actual Docker,
SQLite migration, backup, restart and health. No claim about an unknown external
server update wrapper is made. Existing browser updater and repository v4 share
the verified release-info/candidate-migration protocol.

Garmin synchronization imports the last 30 local calendar days; the official DTO
has no documented stable measurement ID, so canonical source timestamp/person
identity is used. Ambiguous same-timestamp conflicting values in one batch are
rejected. Automatic sync requires optional scheduler bridge networking. Secrets
need separate private whole-tree recovery. The passwordless LAN model permits
other reachable LAN users to manage household integrations/data.


## Additional acceptance checks

A larger in-memory history of 150 synthetic workouts with 100-character exercise
names generated a valid **191-page PDF** and **2,100 detailed CSV rows**. Exact
lifting totals and completed/skipped set counts matched expected values. An
additional all-skipped workout check required confirmation and preserved true
NULL values. These checks supplement the 850 collected repository tests.

## Existing server upgrade

From 0.15.1 / schema 12 at `/root/WorkoutTracker`:

1. Make a verified Backup Now and separately protect the whole storage tree/.env.
2. Open Settings → Application Updates → Check for Updates.
3. Review 1.0.0, explicitly confirm migration to schema 13, and Install Update.
4. Wait for Completed on the independent status page. Verify
   `http://10.0.69.9:8000/health/ready` reports 1.0.0 / 13 / ready.
5. Make a new verified schema-13 backup. Never initialize installed storage.

The already Phase-12-capable host updater and repository v4 need no replacement.
For emergency SSH use `bash /root/WorkoutTracker/app/deployment/update_workout_tracker_v4.sh`
and review its prompts. An unknown external root-level wrapper is not claimed tested.
Only after updating, optional automatic Garmin sync needs
`WORKOUT_SCHEDULER_NETWORK_MODE=bridge` in the private parent .env and planned
scheduler recreation; see README. Manual sync uses existing web networking.
No production server, configuration or database was changed during this work.
