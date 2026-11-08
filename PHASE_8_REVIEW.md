# Phase 8 — permanent deletion, passwordless LAN updates and person context

> **SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.** Human-directed AI-generated code; not an independent audit or a live-server deployment.

Revised branch: **phase-8-lan-management-and-updates**, created fresh from approved
main `7253b044c48ee9e45f479e7130a9dc058c41dac3`. Target **app 0.8.0 / schema 6**.
The interrupted earlier attempt was preserved locally on its own branch, not
merged wholesale. Reviewed schema/deletion/engine pieces were selectively reused;
all administrator/login/password/TLS/proxy components were excluded.

## Trust and scope

The explicit revised requirement is implemented: anyone who can reach the app on
the trusted private LAN may confirm permanent deletions and approved updates.
There are **no user accounts, roles, administrator passwords, login prompts,
HTTPS/certificates or reverse proxy**. App address stays **http://10.0.69.9:8000**.
CSRF, signed anonymous browser state, trusted hosts, input validation, exact person
ownership/context and deliberate safety confirmations remain. Those safeguards
are not user authentication. Network isolation is the deployment's trust boundary.

No production data/server was accessed. No host service was installed on the
user's machine, no live schema was migrated, and no Phase 9 work is included.

## Permanent exercise deletion

A dedicated preview shows exact global ID, name, affected people, routine count
and recorded entry count. POST requires typed **DELETE** or the exact name, an
acknowledgment, CSRF and a current exact-row impact fingerprint. Active native
drafts referencing that identity block deletion with finish/discard instructions.
There is no password or role check.

One exclusive caller-owned SQLite transaction:

1. Removes configurations for the global ID from every routine and closes order gaps.
2. Removes only that ID's entries from live/completed/discarded and historical
   workouts across all people. Other integer/NULL measurements, notes, targets,
   flags, identity, ownership and occurrence fields remain exact.
3. Normalizes remaining positions/counts/cursor bounds. Empty completed/discarded
   workouts and their registry/correction records are consistently removed.
4. Projects each existing correction before/after entry array to surviving IDs,
   retaining unrelated measurements and audit times/revisions. Appends a value-
   preserving revision barrier so old indexed correction forms cannot apply a
   deleted row's value to another exercise.
5. Invalidates affected unfinished historical preparation forms. Saved preparation
   prescriptions are projected consistently to surviving snapshots. A stale manual
   submission is rejected, not silently reinterpreted.
6. Deletes the global definition, validates foreign keys and the same complete
   logical snapshot/audit invariants used by backup verification, then commits.
   Any failure rolls the entire transaction back.

Reusing the name produces a fresh UUID with no association to erased results.
Legacy distinct IDs sharing a name are not silently merged or deleted together;
if another definition still has that name, reuse/rename/delete it deliberately
before registering the name anew. The exact preview ID makes that distinction clear.
Charts and previous-session readers naturally exclude erased entries; per-person
history boundaries and all weight/time/NULL/zero/truncation rules are unchanged.

Backups/retained databases are never rewritten or deleted. Deliberately restoring
an older compatible backup can resurrect deleted history; this is stated in the
confirmation UI and tested on synthetic data.

## Permanent routine deletion

Definition and routine-specific configurations are physically removed. Global
exercise definitions and all completed native/historical workout snapshots remain,
including original routine names. History can display that the routine was deleted.
New routines receive a fresh ID and may reuse its name. Other routines are unchanged.
An active draft blocks deletion. Previously archived routines/definitions remain
reachable for deliberate cleanup after migration. **Remove From Routine** continues
to affect only one configuration, with no global/history deletion side effect.

## Why schema 6 is required

Schema 5's routine foreign keys and unconditional snapshot triggers correctly
blocked these new destructive operations. Schema 6 is an explicit, separate-
candidate migration, not a live trigger bypass or an archive flag substitution.

- Detach live-session and historical form/workout routine references from live
  definitions so history can outlive physically deleted routines.
- Keep routine-configuration and session-entry ownership FKs and global exercise
  references. Add insert guards requiring owned live routines/preparations; no
  cross-person snapshot insertion is permitted by detaching old references.
- Recreate snapshot/correction protection triggers with a connection-local
  `deletion_in_progress()` gate. Normal validated app connections register 0;
  only the dedicated transaction temporarily enables it and resets it in finally.
  Ordinary saved corrections remain append-only. No persistent unlock flag exists.
- Python sqlite3 cannot mark a callback innocuous, so schema-6 write connections
  enable trusted_schema only after the exact schema was independently verified.
  The accepted DDL is fixed; no browser can supply functions/SQL/trigger definitions.
- Never drop/recreate schema during a deletion. Candidate DDL rebuilding is limited
  to the explicit versioned migration, preserving every original cell and NULL.

The original schema-5 file/selection are preserved byte-for-byte. Backup API copies
a distinct candidate, exact cell/DDL/migration records, integrity/FKs and complete
logical snapshot/audit checks precede atomic activation. Faulted DDL/validation/
activation keeps the source selection. Startup never migrates, initializes or
replaces storage. Schema-6 backups/restores preserve guards and audits and reject
incompatible restore schemas. Existing supported older schemas can explicitly
upgrade using --target-version 6; normal legacy reads remain supported.

## Selected-person header

A compact sticky header shows the correct selected person and accent throughout
routines/editing, library, history, charts and context-specific Settings/Updates.
Active workouts also show the snapshotted routine name. It uses normal document
flow and themed background; no large extra navigation or controls overlay is added.
Refresh/back/navigation retain URL-selected identity, and existing workout save/
exit/switch safeguards remain intact. Browser coverage includes 320/390/768/1280
widths, scrolling, light/dark and independent purple/teal identities.

## Browser updates and host boundary

Settings → Application Updates displays actual installed versions, host-verified
approved version/schema/notes, migration requirement, last success/failure and real
persistent stages. Household users can Check/Review/Install without logging in.
Install requires CSRF and explicit acknowledgment; schema-changing install needs
its own explicit structural-change confirmation. No fabricated release data or
progress percentages are shown. If the host component is absent, show the explicit
installation requirement rather than creating it at startup.

The independent host process owns Git/Docker. It accepts only fixed status/check/
install JSON fields through a Unix socket (0660, root:writer group), validates Linux
peer UID (configured writer/root), source, release ID, consent and overlap itself.
The web container has no Docker socket/root privileges. Browser inputs cannot
supply a shell command, repository, image, branch, URL or arbitrary commit.

Read-only progress is **http://10.0.69.9:8001/status** (or the operator's explicit
private interface/port), with exact trusted Host checks and GET-only status/JSON.
It has no control API, login or TLS and remains available while web is stopped.
Host status/logs persist in private updater state; safe stages/notes are exposed,
not .env, command output or session signing material. Public state is atomic JSON.

Approved policy is only merged main in the fixed repository, relying on owner
merge governance over normal verified GitHub transport, not a GPG-signature claim.
Review pins a full SHA. The worker refuses wrong origin, dirty/diverged checkout
or changed approved head; parses target metadata with AST literal evaluation and
compares it to built release-info. No unmerged branch/remote script is installed.

The engine checks source/space/storage, preserves commit/image, stops only workout
web/scheduler, verifies backup, advances approved code, builds, invokes the existing
candidate migration when explicitly approved, verifies active/original versions,
atomically recopies parent .env to app/.env, restarts and checks actual web/schema/
scheduler. Cross-process flock and process mutex prevent overlapping operations.
No-update checks do not stop/back up storage. Failures persist the exact stage,
recovery inputs and private diagnostics; Compose config output is withheld.

Before selection changes, automatic image-only recovery is permitted only if the
original bytes/manifest and config match, the old image validates storage, and
old web/scheduler health verifies. After activation, an incompatible old image is
never started blindly and no backup is restored automatically. Interrupted installs
are marked failed/stopped for inspection on service restart, never replayed. Normal
checks interrupted before maintenance do not stop a healthy application.

## Actual v3 review and v4 changes

The available actual `/workspace/outputs/WorkoutTracker-Updater-v3.sh` was read
completely. The live server copy was not accessed. Correct v3 behaviors retained:
fixed paths/repository, clean fast-forward main, separate image retention, explicit
schema approval, real check-storage/release-info, verified backup, candidate CLI,
original hash checks, health/scheduler verification and refusal of unsafe config.

V3 cannot migrate to 6 because it deliberately caps source/target at 4/5→5. It has
no independent browser worker/persistent status and deliberately does not recopy
app/.env or attempt automatic image recovery. V4 removes that schema ceiling and
uses one shared engine rather than duplicating the database migrator. It adds
explicit host installation/upgrade, durable stages/private logs, fixed-source AST
preview and built metadata verification, disk guards, safe compatible image recovery,
interruption diagnosis, root .env synchronization and emergency SSH check/status.
All confirmed updates include a verified backup; legacy --backup remains accepted.

Executable entry point: **deployment/update_workout_tracker_v4.sh**.
Explicit installer: **deployment/install_updater_service.sh**.
No installer, update or migration executes merely because Flask starts.

## Exact existing-installation steps

Full commands, one-time SSH prerequisites, HTTP URLs, service upgrade, emergency
CLI and recovery details are in [deployment/README.md](deployment/README.md).

After approved merge, inspect a clean main checkout, fetch/fast-forward main,
then explicitly run v4 --install-service with LAN address 10.0.69.9, app URL
http://10.0.69.9:8000 and status port 8001. This provisions only the host service.
Then run the new v4 path explicitly, confirm the update/backup and type MIGRATE 6
when needed. Verify app 0.8.0/schema 6 and both services before browsing. Future
normal updates are available without SSH from Settings. Do not use old v3 unchanged,
initialize storage, alter .env values, change port 8000 or discard Git history.

## Automated verification

The complete suite passed **294 tests, 0 failed, 0 skipped**, in **266.55 seconds**:

```sh
WORKOUT_CONTAINER_TESTS=1 /workspace/phase1-venv/bin/python -m pytest -q
```

This includes **265 backend/database/updater tests, 19 real Chromium browser tests,
and 10 Docker tests**. Tests cover schema-6 exact preservation and failed activation,
same-schema backup/restore resurrection, native/historical deletion and correction
projection, ownership, actual v4/host-service/Docker integration, no-migration and
migration update paths, failure/recovery paths, disk guards, passwordless HTTP
confirmation/CSRF and generated systemd syntax. A final updater/Chromium rerun
also checks that a rejected overlapping browser worker cannot clobber a running
emergency CLI's persistent status.

Docker rehearsal uses real build, verified backup, schema-5→6 candidate, preserved
original bytes, container restart/versions and actual host Unix peer communication
through the existing data mount. Git approved-source metadata and the cloud-specific
rootless-daemon disk path probe are simulated (test UID cannot traverse that private
folder); they are independently checked by engine/source/disk tests. No app ports
are published and status binds loopback only in tests. Browser tests are real
Chromium/HTTP, including status surviving an actual test web-server shutdown.

Bash syntax, executable bits, source disclosures/docstrings and documentation
syntax are checked. Generated systemd unit syntax is verified offline in a temporary
user runtime with a dummy Docker dependency; no live system service is installed.
ShellCheck is not installed in the managed environment, so no ShellCheck result is
claimed. Existing tests are retained; expected version strings and current-image
tag are updated, not assertions weakened.

## Remaining limitations

- Physical iPhone/Safari/VoiceOver, real server/systemd activation, actual root Git
  credentials and firewall/Python/permissions are not verified by these fixtures.
- Host Docker access is root-equivalent despite the deliberately narrow command
  API and unit hardening; trust the fixed repository's main-merge governance and
  protect host access/network isolation. No Internet-safe authentication claim.
- Initial installation/source upgrade and exceptional recovery require SSH once;
  after installation, normal confirmed updates use the passwordless browser UI.
- Unreviewed Compose/image/mount changes are refused. A future host protocol/service
  change may require explicit --upgrade-service; normal startup never installs it.
- Existing backup/offsite, cooperative SQLite locking, acknowledged-save and storage
  durability uncertainty limits remain. State/log files and retained versions grow
  until the operator deliberately manages them; the updater deletes none silently.
- Historical correction audit arrays are deliberately redacted only for an explicit
  global deletion. They remain internally chained for surviving entries; an extra
  value-preserving revision invalidates pre-deletion forms. Pending manual reviews
  referencing deleted identities must be prepared again.
