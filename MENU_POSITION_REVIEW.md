# Patch 0.10.2 — viewport-safe hamburger positioning

> **SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.** Human-directed generated code; no independent audit or production deployment.

Branch `fix-mobile-hamburger-menu` starts from fetched remote main
`6cc0eea2e10f575f18181aff5c927c2f0258238e`, the completed routine-ordering release
**0.10.1**. This patch advances to **0.10.2 / schema 7 unchanged**. All routine-order
changes remain. Direct verified main merge/push and cleanup are authorized; no PR
attempt, server deployment, real workout data or unrelated development phase.

## Measured problem and CSS-only solution

Actual Chromium inspection reproduced the problem with a selected person: at
390px width the button was x=115.19..159.19, but the 320px panel began at x=-160.81.
At 320px the panel began at x=-132.81; landscape 844px also overflowed left.
Without a selected person the button moved to the right and the original right
alignment was safe. Always changing right:0 to left:0 would therefore not handle
both actual header layouts.

The fix scopes position:static to `.app-header .menu-wrap`, making the full sticky
header the dropdown's containing block. `#main-menu` is capped to that header's
width, reserving left/right CSS safe-area insets. The selected-person variant uses
left:0/right:auto; the no-person variant retains right alignment. The panel opens
below the complete header, including a wrapped long name, with existing z-index,
rounded styling and scrolling. Its height also reserves the bottom safe inset.
No button is moved. No navigation JavaScript, templates, links, page structure,
accent/theme palette or workout-focus behavior is changed. People/card action
menus keep their original relative containing blocks.

## Safety and updater compatibility

Only runtime CSS and APP_VERSION change. Target schema remains 7; no database,
history, sorting, migration, backup/restore, scheduler/logging or host updater
implementation changes. Existing browser and v4 update protocols discover 0.10.2
through unchanged release metadata. No additional host-service upgrade is required
on an already updated Phase 10 installation; earlier console prerequisites remain.
The code-only updater still requires confirmation, verifies its existing backup,
preserves schema-7 selection/bytes and checks actual health. No server Compose/.env
or external root updater wrapper is modified or claimed tested.

## Regression evidence

Final complete suite: **406 passed, 0 failed, 0 skipped** in **526.29 seconds**
(349 backend/script, 44 Chromium, 13 Docker). Targeted menu matrix: **10 passed**
in 66.88 seconds. All five viewports pass in both themes, with three person
contexts, 120 actual link navigations and synthetic safe-area/orientation checks.
Review image: `sha256:2f7d048e44433d0f210ef0bbe6df6fa4a4e2524d68fbf132c55a576fbe88d884`.
Release-info reports 0.10.2 / target schema 7. Disclosure-header and git diff
whitespace checks passed. Latest main remained 6cc0eea during final verification.
The completion report records the verified final remote main SHA and cleanup.
The new real-browser matrix covers Light/Dark at 390×844, 320×568, 844×390,
768×1024 and 1280×900. Each case checks short-person, long-person and no-person
headers; full menu and link bounds; all four actual link navigations with selected
context; frontmost hit tests over routine cards; no horizontal page overflow;
toggle/outside/focus dismissal; ArrowDown, Escape and restored focus; aria-expanded;
sticky scroll; and portrait/landscape reflow while the menu is already open.
The production CSS safe-area variables are also exercised with synthetic 44px
side insets. This is a geometry rehearsal, not a physical iPhone notch simulation.

The full suite includes all routine-ordering, workout autosave/completion, history,
correction/audit, NULL/zero, storage integrity, candidate migrations, backup/restore,
scheduler/logging, updater/browser and real Docker tests. Existing tests keep all
assertions; current version expectations advance to 0.10.2. Data is disposable.
Screenshots are generated under /tmp/workout-menu-screenshots for portrait and
landscape in both themes. Visual review checks readable, fully visible links.
Physical iPhone Safari, installed systemd/root service and the live server are not
tested or deployed. The fix uses :has, which the existing theme/editor UI already
uses and current Safari/Chromium support.
