# Exercise Library three-dot menu — 0.12.1

**SHAMELESSLY VIBE-CODED 🤖**

This application was built with a healthy dose of AI, questionable amounts of confidence, and minimal human supervision. It appears to work, but don’t mistake that for a warranty. Use at your own risk, and keep backups.

## Scope and preservation

Started from approved main 468720259c8ce4e6c92a10818b0902c938715469 on
exercise-library-meatball-menu. Application 0.12.1, database schema 8 unchanged.
This is presentation only: no schema, catalog, defaults, deletion, history,
correction, ownership or updater behavior changes. No identity cleanup.

The Library row has a full-text heading on the left and a fixed 44px three-dot
button on the right. Flex min-width:0 and CSS ellipsis clip only the visual name;
full heading text, title tooltip, accessible button name and editor value remain.
The row—not the narrow button—anchors the bounded dropdown. Cards retain overflow
visibility so actions appear above later content. Destructive actions have a
separate line and theme-appropriate red text.

The existing navigation disclosure handles tap/toggle, ArrowDown, native Tab/Enter,
Escape with focus return, outside click/focus and one-open-at-a-time behavior.
Only Library panels additionally scroll into view when opened at the page bottom.
No JavaScript shortens names. Edit Defaults and Delete Exercise point to existing
ID-based editor and permanent-delete review routes. Legacy schemas keep their
existing archival form inside the disclosure, without introducing deletion there.

## Release and README review

README was opened/reviewed: installation commands, configuration, bootstrap and
update instructions still match Compose, Dockerfile, CLI and v4. Updated its
Library usage, current version and readiness examples; preserved the beginner
opening, installation distinction and humorous disclosure. Current deployment
checks use 0.12.1. Versioned releases/0.12.1.json contains the concise user-facing
note, reviewed against this UI-only diff. Historical Phase 12 notes remain intact.
AGENTS and PROJECT_SPEC retain their permanent README/release-note requirements.

Existing schema-8 installations use the normal confirmed browser update. No
migration, Compose/.env change or new updater script is needed. If the independent
host service was refreshed for Phase 12, do not refresh it again for this patch.
Older hosts follow the existing documented one-time Phase 12 service procedure.
No server deployment, real storage access, PR or next-phase work is performed.

## Verification

Final complete run on 2026-11-10: **519 passed, 0 failed, 0 skipped in
750.75 seconds**: **423 backend/script, 79 Chromium browser, 17 Docker integration**.

```sh
WORKOUT_CONTAINER_TESTS=1 /workspace/phase1-venv/bin/python -m pytest -q \
  --tb=short --show-capture=no --junitxml=/tmp/library-menu-full.xml
```

New ten-case viewport/theme tests also passed independently (38.47 seconds).
Retained affected browser/documentation workflows passed (22 tests), as did
45 targeted backend/documentation tests. The first new synthetic name exceeded
the existing 100-character validation limit by one; corrected the fixture to
100 characters without changing validation. Retained UI tests now open the menu
before using its links/forms; all underlying identity/deletion assertions remain.
The current-note check validates the new patch and separately retains every
original Phase 12 note-content assertion. No tests were removed or weakened.

The tested application image was
sha256:b6f52457592bdc42718b0d766cddfe5b6bfbde25c8ddd62899ae7a3b53ea49aa.
Only documentation changed after the runtime build. Python compilation and
git diff --check pass. README links, shell syntax, real CLI flags and environment
names pass the retained automated documentation checks. No production commands
were executed. Release notes were verified against 0.12.1 and this user-facing diff.

All tests use synthetic households and disposable storage.
New Chromium tests cover 320/390 phone portrait, 844 landscape, 768 tablet and 1280
desktop in Light and Dark. Check left/right row alignment, CSS truncation, complete
accessible names, full editor values, ID-bound routes, bounded/frontmost menu
links, no page overflow, tap/toggle/outside/Escape/keyboard/focus, one open menu,
and unchanged SQL dumps after read-only navigation. Retained workflows still test
real editing, routine/default independence and confirmed permanent deletion.

No physical iPhone/Safari or production/systemd installation is claimed tested.
