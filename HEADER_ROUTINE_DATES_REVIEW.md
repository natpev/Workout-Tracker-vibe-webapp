# Patch 0.10.3 — header navigation and routine activity dates

> **SHAMELESSLY VIBE-CODED 🤖**
>
> This application was built with a healthy dose of AI, questionable amounts of confidence, and minimal human supervision. It appears to work, but don’t mistake that for a warranty. Use at your own risk, and keep backups. Human-directed generated code; not an independent audit or production deployment.

Branch `header-navigation-and-routine-dates` starts from fetched main
`3614bbe50b64466972a0b44e1b88b77a85b2f743`, verified version 0.10.2/schema 7.
This release is **0.10.3 / schema 7 unchanged**. The user explicitly authorizes
verified direct main fast-forward/push/cleanup without a PR or extra approval.
No real data, server deployment or unrelated phase.

## Header and dropdown

The existing sticky flex header now stays on one row. Branding cannot shrink;
the selected-person name takes available space with min-width:0 and ellipsis;
the menu wrapper is last in visual order and cannot shrink. The full name remains
in accessible text and a title. Safe-area padding protects header edges. This
supersedes the earlier position-varying button contract without changing links
or navigation JavaScript. Header height remains 64px with a menu, including long
names, at all tested widths. Focused active workouts keep their existing restricted
header with no new global-navigation escape.

The existing bounded dropdown is always right-aligned below the full sticky
header. Safe-area margins, max width/height, z-index and scroll behavior remain.
No person-menu/card action menus, themes, palettes, link destinations, focus/aria,
keyboard, outside-click or workout autosave behavior is redesigned.

## One source for routine rank and date

The existing selectable_routines helper computes its maximum occurrence exactly
as before. Each returned card is now a dictionary with two display-only fields:
last_completed_date (ISO date or None) and last_completed_label (English Month D,
YYYY or None). The same maximum supplies both sorting and display; there is no
second history query or stored date field. English month names are explicit and
days have no leading zero, independent of host locale. Jinja renders a semantic
time datetime=ISO element or Never completed; all text remains escaped.

Existing effective corrections, live Finish/historical actual-occurrence semantics,
ownership and routine identity matching, independent copies, unknown-time ties,
alpha ties, completed skipped workouts and excluded deleted/archived definitions
remain. Active/discarded sessions and unfinished historical preparations do not
count. Schema-2/3 compatibility stays; no startup migration or initialization.
SQL-dump comparisons cover read-only listing and dashboard GET.

A small muted activity row spans the card beneath its original name/Edit and
Start controls. A two-column grid retains those controls and avoids wrapping the
date into a tall narrow side column. Browser tests compare actual rendered card
height with/without the label and limit added height to 25px at the tested sizes.
Colors reuse the existing muted theme token. No measurement/history/audit is written.

## Version, updater and verification

APP_VERSION is 0.10.3; TARGET_SCHEMA_VERSION remains 7. No schema, migration,
backup/restore, scheduler/logging or host updater code changes. Existing browser/v4
release metadata and code-only update flow remain compatible, with their verified
backup, unchanged schema-7 selection/bytes and health/recovery checks. No additional
host upgrade or server configuration change is needed on Phase 10. External root
wrapper/systemd installation/live server are not claimed tested or modified.

Final complete suite: **416 passed, 0 failed, 0 skipped** in **532.05 seconds**
(356 backend/script, 47 Chromium, 13 Docker). Targeted new/expanded cases:
**20 passed** in 83.90 seconds. Review build:
`sha256:afaddd6794bfdccc4c7ee24099a14acfd74a4b67b1bdf18b179004375bcf80d3`.
Release-info reports 0.10.3 / target schema 7. Disclosure-header and git whitespace
checks passed. Latest remote main remained 3614bbe at final verification.
The completion report records the final verified main SHA and branch deletion.
Backend regression covers visible/semantic dates, exact sort-date correspondence,
late-entered older history, drafts/discards/preparations, person/copy/name isolation,
deleted definitions, corrections and deterministic English formatting. Existing
routine ordering and tie tests remain intact. Existing version assertions advance
only to the new release number.

The menu browser matrix keeps all earlier assertions and adds far-right button
bounds on every destination, one-row height, long-name containment and selected
information visibility. It covers 320×568, 390×844, 844×390, 768×1024 and 1280×900
in Light/Dark, three person contexts, sticky scroll, all links, keyboard/aria,
outside dismissal, safe margins and open-menu rotation. New card tests use
320/390/1280 widths and Light/Dark/Auto, with compact height, semantic labels and
original controls. Screenshots are under /tmp/header-dates-screenshots and the
existing menu screenshot directory. Chromium emulation and synthetic safe-area
geometry are not physical iPhone Safari testing. No deployment is performed.
