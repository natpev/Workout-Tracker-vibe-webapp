# Patch 0.10.4 — navigation progress, exercise scope and selected CSV

> **SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.** Human-directed generated code; not an independent audit or production deployment.

Branch `workout-progress-and-csv-export` starts from fetched main
`3e031c170439a42ba1f36769e30fa6f290f1faae`, version 0.10.3/schema 7.
Target **0.10.4 / schema 7 unchanged**. User authorizes complete verification,
direct history-preserving main merge/push/cleanup and no PR attempt. No real data,
deployment, unrelated phase or orphan/duplicate exercise investigation/repair.

## Navigation-only progress and storage

The bar uses the furthest acknowledged Next destination, not measurements or
performed counts. The existing current_position column stores this checkpoint.
Back, jumping, typing weight/duration, flags and ordinary autosave do not raise
it. A validated Next targets the following snapshot exercise; max(old, destination)
prevents revisits/double submissions counting twice. The chosen interpretation
retains the furthest Next position; jumping alone changes only the view, and Next
from a jumped view uses that following destination. This is a positional checkpoint,
not a count of arbitrary independent visits. No schema migration is necessary.

Actual values and checkpoint update in the same locked, revision-checked SQL
transaction. Only a committed acknowledgment changes the browser bar. API completed
retains the actual performed count for existing consumers/all-skipped handling;
navigation_progress controls the bar. The URL/view_position tracks the viewed page,
so revisiting then Save draft stays on that exercise. Resume opens the checkpoint.
Existing draft cursors remain as stored; old navigation events cannot be rebuilt.
JavaScript is required for the acknowledged Next navigation flow, as with existing
autosave/navigation protection. No silent initialization or storage migration.

Finish remains atomic/idempotent and still requires confirmation for entirely
skipped actuals, regardless of navigation progress. Blank entries remain present
with true SQL NULL; zero weight stays a recorded value. Completed records and
immutable triggers/audits are not rewritten. New tests cover skipped Next across
three entries, revisits, Back, refresh, persistence, actuals/flags and completion.
The old bar assertions change only where the user explicitly replaced the
measurement-count contract; all measurement/save assertions remain. The existing
cursor/restart HTTP test now sends an explicit Next action to retain its assertions.

## Configuration explanations

The shared configuration macro takes a routine/library scope and displays the
exact requested explanatory sentence near the top of every relevant routine add/
edit and Library add/default-edit form. Muted input-hint styling remains readable
on phones. This only describes existing behavior: defaults copy once into new
routine rows; editing either side never propagates to existing routines/history.
Catalog/default SQL is unchanged; browser tests compare actual routine rows before
and after changing a Library default.

## Read-only wide CSV

The Progress filter form adds a compact multi-ID export chooser with Select All/
Clear and a separate GET attachment endpoint. Existing range presets/custom dates
and chart filter stay; export checkbox selection is independent of the chart's
single exercise selector. Repeated query parameters retain selection across range
submits/errors. Validation redisplays the original form/choices and prior valid
graph state, not a generic error page or empty CSV. Successful export skips SVG
preparation and writes only an in-memory CSV.

csv_export.py uses the existing person-owned effective history, including native,
manual and corrected records. Bounds are inclusive actual workout dates. Rows are
oldest-first using the existing deterministic chronology, one per completed workout
containing at least one selected ID. Same-date/time rows retain unique Workout ID.
No defaults/current routine configuration or previous actual values are substituted.

Columns: Date (ISO), Time (24-hour HH:mm or blank unknown), Routine snapshot, Workout
ID, then adjacent actual/prescription pairs. Weight: Weight (lb), Sets × Reps; Time:
Duration, Sets × Target Duration. Prescriptions are historical targets, not actual
per-set reps. Exact stored tenths render whole numbers without .0 and preserve 0;
duration uses total minutes:two-digit seconds. Present skipped entries leave actual
blank and retain prescription; absent selected exercises have both blanks.

Column groups separate permanent ID, type, unit and weight meaning. Matching names
get full IDs in headings; repeated group entries get occurrence-number columns so
no value is overwritten. Occurrence numbers follow each snapshot's original order.
No matching-name merging, cleanup, reconciliation or orphan investigation occurs.
Selection order determines exercise order, then deterministic mode/meaning/slot.

Standard csv.writer quoting handles commas/quotes/newlines; UTF-8 BOM and CRLF support
common spreadsheets. Formula-like user text, including leading whitespace/control
variants, gets an apostrophe prefix in headers and cells. Names/routine text are
protected without modifying storage; numeric zero/decimals remain intact. Filename
uses configured local today. No decorative pre-header rows, cloud, PDF or workbook.

## Verification and compatibility

Final complete run: **439 passed, 0 failed, 0 skipped** in 576.68 seconds
(9 minutes 36 seconds): **375 backend/script, 51 Chromium, 13 Docker**.

```sh
WORKOUT_CONTAINER_TESTS=1 /workspace/phase1-venv/bin/python -m pytest -q --tb=short --show-capture=no --junitxml=/tmp/progress-csv-complete-final.xml
```

JUnit confirms zero errors/failures/skips. The final local integration image is
`sha256:04bd57eee582425d7c2f487411f49bbcf8c0c23ee7d952cd68ad7b2beba22ef6`.
Storage-free release-info reports application **0.10.4**, target schema **7**.
`git diff --check` passed. No PR was created or attempted.

The initial complete run found four browser failures (435 passed): the broad
Skipped locator matched newly collapsed CSV help; a Resume check expected the
old view cursor instead of the Next checkpoint; a skipped-Next assertion still
expected the old performed count; and a delayed scroll could hide a tapped chart
tooltip. The skipped-record assertion now targets the actual expanded chart row;
Resume still verifies both saved actuals and now verifies the checkpoint/Back;
only the deliberately replaced progress expectations changed. Event diagnostics
confirmed touch can synthesize mouseleave after click. Activated labels now stay
pinned through that event and follow a still-visible point during scroll; outside
click, blur, Escape and offscreen points still close them. Explicit delayed-scroll
and mouseleave regressions retain the existing hover-dismissal check. Existing touch, Escape, outside-click,
hover, theme, actual-value, completion and discard assertions remain intact.
A second complete run passed 438 tests but hit a Chromium automation-target race
when reload overlapped the Check for Updates POST/redirect. That browser test now
waits for navigation to finish before explicit reload (and Progress filter
reload/Back sequences use the same synchronization); all update/tab,
consent, safe-output and offline-status assertions remain unchanged.
Targeted backend covers wide columns, adjacency, prescriptions, effective corrections,
chronology, same-date separation, NULL/zero/decimals, absent/repeated entries, mode
changes, ID-distinct matching names, quoting, formula injection, date/selection errors,
person isolation, HTTP attachment/BOM and known/unknown clocks. Browser tests cover
actual downloaded file contents, range/selection retention, scope notes, settings
independence, phone/desktop progress, Back/revisit/refresh and real completion.

All tests use disposable schema 3/7 data and local HTTP/Docker fixtures. The full
suite includes retained schema compatibility, candidate migration, backups/restores,
scheduler/logging, host/v4/browser update, Chromium and Docker fault recovery.
Target schema remains 7, existing updater metadata/protocol/backup/recovery remains.
No host upgrade or server config change is required after Phase 10. Physical iPhone
Safari, the external root wrapper and live systemd/server installation are not
claimed tested. No production data is accessed or changed, and nothing is deployed.

Selected exercises absent throughout a range still retain blank column pairs, using their historical configurations for headings; no out-of-range data rows are added.
