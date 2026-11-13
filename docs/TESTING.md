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
