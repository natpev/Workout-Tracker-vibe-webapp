# Development and release testing

**SHAMELESSLY VIBE-CODED 🤖**

This application was built with a healthy dose of AI, questionable amounts of confidence, and minimal human supervision. It appears to work, but don’t mistake that for a warranty. Use at your own risk, and keep backups.

## Disposable development

Use a virtual environment and an explicitly new storage path. Never point tests at
household data. Install requirements-dev.txt and requirements-browser.txt; use
Playwright's installed Chromium or WORKOUT_CHROMIUM. PDF tests also use pypdf.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt -r requirements-browser.txt
.venv/bin/python -m playwright install chromium
.venv/bin/python -m pytest -q
```

The complete container-enabled run requires Docker and the current image:

```sh
docker build -t workout-tracker:local -t workout-tracker:phase8-review .
WORKOUT_CONTAINER_TESTS=1 .venv/bin/python -m pytest -q
```

phase8-review is the retained test image tag, not an old release. Tests clear Docker
endpoint/context selectors and use the local socket. Temporary containers/bind
mounts/loopback ports contain synthetic records only. Managed cloud builds use the
existing pip_ca BuildKit secret for verified TLS; never disable certificates.

## Coverage and claims

Retained backend/Chromium/Docker tests exercise earlier schema/readers, safeguards,
updater, SVG security, history, defaults, reports and responsive layouts. New release
tests cover all seven capabilities, one weight, explicit statuses/NULLs, partial
save/resume/completion, append-only set corrections, body trends/edits, mocked
per-person Garmin, safe downloads and PDF/CSV parsing. Failure injections preserve
original selection/storage and reject unsafe candidates.

Acceptance includes temporary fresh Compose initialization, actual Gunicorn browser
workflows and restart persistence, plus real container CLI schema-12 upgrade with
synthetic legacy conversions/corrections/drafts/icons/preferences. No physical
server, ARM, iPhone/Safari or real Garmin-account claim is implied. Official Garmin
documentation/SDK was reviewed; all authenticated API calls are mocked.

See RELEASE_1_0_0_TEST_REPORT.md for actual run counts, defects and remaining limits.
Commands were checked against Compose and the real CLI, not invented from plans.
The per-release README/link/command and plain-English notes checks are mandatory.

## Patch 1.0.1 verification

695 backend/script tests passed, plus 16 relevant Chromium cases and two Docker
integration cases (713 distinct checks, zero failures). The complete backend
suite includes token transport, HTTP 406/other safe status codes, cached-token
reuse, retained connection settings and unchanged local weight records. Transport
mocks inspect actual urllib request headers rather than replacing the adapter.
The production image repeats the token/JSON/error checks with networking disabled;
a real schema-13 code-only updater cycle preserves database bytes and selection.

Library browser cases cover 320/390/844/768/1280 widths in Light/Dark, full-width
names beneath top-right actions, long-name truncation, viewport-safe dropdowns,
keyboard/focus/Escape/outside-click behavior and correct editor/deletion links.
Six additional browser cases cover Garmin settings and body-weight workflows.
No real Garmin credentials/accounts or production data were used. This focused
patch did not rerun every browser/Docker case from the 1.0.0 release.

README was opened/reviewed and updated for 1.0.1 and the Library layout. Installation
and update commands were checked against the existing CLI/Compose configuration;
local documentation links and shell examples validated. Version-matched plain-English
release notes are in releases/1.0.1.json. Schema remains 13; neither the existing
host service nor repository v4 needs replacement for this patch.
