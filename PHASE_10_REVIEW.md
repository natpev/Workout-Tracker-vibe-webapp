# Phase 10 — historical forms, Progress and independent live update output

> **SHAMELESSLY VIBE-CODED 🤖**
>
> This application was built with a healthy dose of AI, questionable amounts of confidence, and minimal human supervision. It appears to work, but don’t mistake that for a warranty. Use at your own risk, and keep backups. Human-directed generated code; not an independent security audit or live deployment.

Started on `phase-10-workout-history-and-progress-ux` from fetched approved main
`c4d2db4683e23cd896152961a9d7ba5ed894256d`. Application **0.10.0**, target SQLite
schema **7 unchanged**. The user authorizes complete verification and a direct
history-preserving main merge/push/cleanup. No PR creation or PR API attempt.
No server deployment, real workout data or Phase 11.

## Historical validation and time entry

`historical_forms.py` collects field errors separately from the existing atomic
history services. Routes keep raw POST dictionaries and render the same preparation,
measurement-review or correction form on expected 400 validation / 409 revision
conflict. Exceptions leave the locked database transaction before redisplay,
preventing partial preparation/completion/audit writes. CSRF/generation/ownership,
immutable snapshots, idempotent completion and append-only correction services
remain authoritative. System/storage failures retain the safe application handler.

Shared Jinja macros provide unique field IDs, aria-invalid/describedby, red borders,
text markers and linked assertive error summaries immediately above Save. JavaScript
focuses the summary; no browser Back is required. Invalid raw strings, valid fields,
blank/zero distinction, increase checkboxes, clock/fold and stale correction revision
survive. Duplicate duration messages are condensed in the summary but associated
with both duration parts. A stale form retains input and requires reload/review;
it cannot silently adopt a newer revision.

The optional clock is explicit HH:mm with a small hour/minute selector: 00–23 and
00–59, no locale AM/PM, no displayed seconds. Four-digit entry normalizes only on
blur/submit, leaving the typing cursor alone. Picker selections apply together;
Unknown time clears the field. Server validation independently normalizes/revalidates.
Existing IANA occurrence, future-date, DST gap/overlap/fold and hidden precision
rules remain unchanged. Correction GET shows effective saved minute/clock values.
Older direct server callers may still supply valid HH:mm:ss; the browser UI always
displays HH:mm. Exercise duration is still independently normalized integer seconds.
Historical forms remain submission-based, not autosaved; navigation away can lose
unsubmitted input.

## Progress ranges and tooltips

`progress_ranges.py` supplies default 30, 60, 90 inclusive rolling local calendar-day
ranges; start = today minus N−1 days. 6/12 Months use calendar arithmetic: clamp the
anniversary to a valid day, start one day later, end today. The configured IANA zone
supplies today. All Time has no bounds. Custom reveals optional inclusive From/To,
rejects malformed/reversed dates inline, keeps exercise/raw values and uses previous
valid URL bounds for chart fallback. Opening Custom from a preset retains those
bounds until edited. Exercise changes, History/Progress tabs, saved detail/correction,
refresh and Back carry explicit URL context; no household identity is remembered.

The existing `history.chart_series` reader, geometry, numeric calculations, stats,
identity resolution and type/unit/meaning separation are unchanged. Original SVG
lines/dots and accessible skipped-inclusive data lists remain. Local `progress.js`
adds textContent bubbles for date, measurement and known clock on hover, keyboard
focus/Enter/Space and tap. Escape/blur/outside click hide them; positioning clamps
to viewport edges. Light/Dark/Auto use existing palettes. SQL NULL skips produce
no numeric dot; explicit zero remains a real point. No external chart dependencies.

## Install tab and browser-safe live console

`updates.js` intercepts only confirmed Install, opens one configured trusted HTTP
status URL synchronously with null opener, disables duplicate attempts and submits
CSRF-protected fetch. The app tab remains. Blocked popups show a clear fallback;
installation continues. Check opens no tab. Native validity and server release/
install/migration consent remain; JSON changes presentation only. The status page
is GET-only and can never trigger an installation. After network uncertainty,
review status before reloading/retrying; no automatic duplicate retry is issued.

`process_output.py` drains both real subprocess pipes as output arrives, with fixed
argv/no shell, existing command deadlines, 2-MiB parse tails per pipe and bounded
unterminated line buffers. Private raw logs remain SSH-only; resolved Compose
config is withheld altogether. `console.py` default-denies arbitrary output and
recognizes only structural Git numeric/revision, BuildKit DONE/CACHED, dependency
lifecycle, backup verification IDs/schema verification and container lifecycle
patterns. Fixed actual stage/start/exit messages cover health and command outcomes.
Known environment values are filtered; arbitrary URLs, arguments, configuration,
exception bodies, shell output, credentials, tokens, signing keys and private file
contents are not served. Sanitization deliberately omits most detailed errors;
private SSH diagnostics remain necessary for troubleshooting.

Each independent operation owns a mode-0600 atomic safe JSON ring: newest 500 lines,
500 ASCII characters per line, newest 20 operations. Only safe rings are pruned;
backups, archives, recovery inputs and private logs retain prior policies. GET-only
`console.json` accepts only retained 32-hex operation IDs and bounded cursors,
validates sequence/UTC metadata, refuses path/link/file substitution and never
executes commands. Local CSP-bound JS/CSS and textContent prevent console HTML
interpretation. Optional safe-console write failure cannot undo a storage result.

Independent host polling every 1.5 seconds stays online when Flask stops. Status
summary/events remain above/below the console, with current operation ID and retained
operation selection. UTC timestamps are explicit 24-hour HH:mm:ss. The viewer follows
new output at the bottom, preserves upward scroll, has Scroll to Latest, and resumes
retained output after refresh/reconnect or success/failure. Without JavaScript,
manual-refresh status/events remain available but the live console is unavailable.
Trusted-LAN/passwordless policy remains; no terminal, TLS, proxy or login is added.

## Database and updater compatibility

No schema or migration file is changed, nor any exercise identity matching,
chart numeric reader, storage selection, immutable audit or deletion implementation.
The explicitly excluded duplicate/orphaned exercise issue was not investigated,
diagnosed, reconciled, repaired or targeted by cleanup. Schema 7 does not migrate
or copy its database during ordinary startup/container replacement. Existing
confirmed updater maintenance deliberately still verifies a separate backup.
Older-schema upgrades remain explicit separate-candidate operations with original
bytes/selection preserved and validation before activation. Restore remains exact
schema/identity; safe console does not change retention/recovery behavior.

V4 remains the emergency script. The existing installer copies the entire host
package, including new local JS/CSS. **A one-time explicit --upgrade-service is
required on existing Phase 9 hosts for live console output.** Updating containers
alone cannot update independently copied host runtime. Older service retains its
basic update/status protocol; missing console_protocol displays an app warning.
Exact root SSH commands, prerequisites, health checks and venv troubleshooting are
in [deployment/README.md](deployment/README.md#phase-10-existing-installation-upgrade).
Those commands are documentation, not a claim of executing them on the home server.
The external root wrapper itself is not available here; the committed v4 entry
point and shared engine are the exercised compatibility boundary.

## Verification record

Final complete suite: **384 passed, 0 failed, 0 skipped** in **466.24 seconds**
(339 backend/script, 32 Chromium, 13 Docker). The final full run used the rebuilt
image sha256:272c4ed9fb7f7151642171f53ea1ed4748edfb15002bd74d9a6be9e5146d39fd.
An earlier complete run also passed all 382 then-collected tests. Final targeted
Phase 10 checks passed 33 backend and 8 browser cases; two later boundary checks
are included in the final full total. Bash syntax, disclosure-header and git diff
whitespace checks passed. ShellCheck is unavailable, not counted as a test pass.

Verified implementation commit: `4807c89d8879f1f7c9065dd122043f57b6300491`.
This release note is a separate documentation-only commit. Main merge is explicitly
authorized only after these passing checks; the completion report records the
verified final remote main SHA and feature-branch deletion. No PR is attempted.
The suite uses only disposable SQLite/storage/Compose roots. Coverage includes all
Phase 1–9 assertions plus new multi-error/raw-value/atomicity/stale-form cases,
24-hour/DST/picker controls, local/calendar boundaries, URL navigation, zero/NULL
points, touch/hover/focus/themes, popup fallback, actual child-stream timing,
console secrecy/bounds/retention/reconnect and web-offline operation.

Docker rehearsals keep actual build, backup, schema-6→7 candidate migration,
code-only schema-7 replacement, startup/shutdown faults, recovery checks and
Unix/HTTP control/status; approved remote Git and the cloud-inaccessible Docker
storage-path probe are simulated. Separate unit/script tests cover fixed-source
Git validation, preflight faults, v4 command consent, environment isolation and
systemd unit syntax. These are not physical phone/Safari, real systemd-root
installation, home firewall, external wrapper or production-server tests.

Reproduce the complete suite locally (development tools and local Docker required):

```bash
# Optional trusted CA secret is for managed development builds only.
docker build --secret id=pip_ca,src=/etc/ssl/certs/ca-certificates.crt \
  -t workout-tracker:phase8-review -t workout-tracker:local .
WORKOUT_CONTAINER_TESTS=1 .venv/bin/python -m pytest -q
```

Use the installed development venv path if different; set WORKOUT_CHROMIUM to the
actual Chromium executable where necessary. The final verification environment
uses /workspace/phase1-venv and /usr/bin/chromium, not a live server. Unit syntax
verification uses systemd-analyze --user verify with a dependency stub, not a real
system service install. Bash -n covers both committed host scripts; ShellCheck is
not installed. All modified/new source/document headers retain the disclosure.
Mobile screenshots from the new tests are disposable under /tmp/phase10-screenshots;
visual review covers inline errors, the structured picker, chart tooltip palettes
and the actual 320-pixel independent console.
