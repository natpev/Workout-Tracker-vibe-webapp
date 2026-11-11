# Workout and History UI — 0.12.2

**SHAMELESSLY VIBE-CODED 🤖**

This application was built with a healthy dose of AI, questionable amounts of confidence, and minimal human supervision. It appears to work, but don’t mistake that for a warranty. Use at your own risk, and keep backups.

Started from approved main 281de344260550bedd58f294f26631d0a78bb9e3 on
workout-and-history-ui-improvements. Application 0.12.2/schema 8 unchanged.

## Changes and safeguards

Existing workout prescriptions use slightly larger/stronger theme text; previous
actuals and last-performed fallback stand out without new cards or wider margins.
Weight meanings, all three modes and manual increase indicators remain.

The formatting bug came from replacing input.value with every normalized autosave
acknowledgment. Focused weight now keeps raw text and selection. A successful
matching-sequence acknowledgment caches its raw/normalized pair; blur can apply
only that exact validated result. Input invalidates the cache; an outstanding
edit flushes through the existing serialized server validation/revision path.
No new client decimal parser, rounding or alternate validation. Delayed responses
never replace newer edits; Next/Back/Finish and stale conflicts retain safeguards.
The same input element remains; zero is valid and skipped actuals remain NULL.

History listing/detail/review/correction and completion displays omit normal IANA
labels. Initial historical entry also omits the static zone label, while retaining
fold controls/errors. Saved detail puts stored zone and technical timestamps in
closed Timing diagnostics. Audit diagnostics remain deliberate disclosures.
No stored timestamp, occurrence, timezone, original row or correction changes.
History alone gets history-date-filters: wrapping flex fields with 15rem basis;
narrow phones stack naturally, wider screens pair. Duration layouts stay unchanged.

No schema, Python service, migration, measurement rule, backup/restore, ownership,
chart/CSV or host-updater behavior changes. No duplicate/orphan investigation.

## README, release and upgrade

README was opened/reviewed against actual features, Compose, Dockerfile, CLI and
v4. Commands/configuration/links and separate new-install/update instructions
remain valid; current versions and workout/history guidance are updated. Preserve
the friendly opening and full humorous disclosure. Versioned releases/0.12.2.json
has four concise user-facing notes, reviewed against this patch. Permanent release
rules stay in AGENTS and PROJECT_SPEC.

Existing schema-8 users use normal confirmed browser Check/Install. No migration,
new script, Compose/.env change or another host refresh after Phase 12 setup.
Verify /health/ready and Settings/footer show 0.12.2/schema 8. No live server or
production data was accessed or changed, and no deployment/PR is performed.

## Verification

Final complete run on 2026-11-11: **535 passed, 0 failed, 0 skipped in
790.41 seconds**: **425 backend/script, 93 Chromium browser, 17 Docker tests**.

```sh
WORKOUT_CONTAINER_TESTS=1 /workspace/phase1-venv/bin/python -m pytest -q \
  --tb=short --show-capture=no --junitxml=/tmp/workout-history-full.xml
```

Before that, all 14 new Chromium cases passed in 88.97 seconds; 81 targeted
backend/documentation tests passed. Retained autosave/conflict/mobile/combined
workflows passed. Initial new readability assertions expected Weight-only meaning
in the previous actual, but the existing design places it in the prescription;
corrected those assertions to verify both locations as actually designed. No
application measurement formatting was changed to satisfy that fixture.

Retained focused-weight tests now assert raw text after a successful autosave,
then blur before asserting the same normalized values as before. All existing
offline, conflict, held-ack revision and stored-value assertions remain; no tests
removed or weakened. All data is disposable.

The tested runtime image is
sha256:783cdfd5a7d192754accdd0fea58adce55b4d0ae91b7fbd7d17e50294883eb34.
Only documentation changed after build. Python compilation and git diff --check
pass. README commands/flags/environment names, shell syntax and relative links
pass the retained documentation checks. Release notes were reviewed against the
user-facing changes and exact 0.12.2 metadata.

 New tests cover focused text,
slow/fast input, exact cursor/node stability, zero/skip, invalid partial input,
blur/Next, resumption/completion, compact typography, IANA/DST/correction preservation,
normal hidden zones and explicit diagnostics, scoped field geometry/filter values
at 320/390/844/768/1280 in Light/Dark. Retain existing held-ack, offline, stale-tab,
progress, history, charts/CSV, backup/restore, updater and container regressions.

Physical iPhone/Safari and its native numeric-keyboard rendering are not tested;
Chromium touch viewports verify inputmode=decimal and text inputs. No physical
server provisioning, production deployment or real workout data testing is claimed.
