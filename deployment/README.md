# Workout Tracker installation, LAN updater v4 and recovery (Phase 12)

> **SHAMELESSLY VIBE-CODED 🤖**
>
> This application was built with a healthy dose of AI, questionable amounts of confidence, and minimal human supervision. It appears to work, but don’t mistake that for a warranty. Use at your own risk, and keep backups. Not an independent audit. Commands below are for the operator, not deployment performed by Codex.

Application **0.12.0**, full-feature schema **8**. For an existing schema-8 installation, use the [Phase 12 host upgrade](#phase-12-host-service-upgrade); no database migration is needed. The application remains
**http://10.0.69.9:8000**. It is intentionally passwordless: every person who can
reach it may confirm updates or permanent deletion. Network isolation is the trust
boundary. No accounts, administrator passwords, login, HTTPS, certificates or
reverse proxy are installed. Retain trusted-host checks, CSRF and confirmations.

## Layout and one-time prerequisites

- Checkout: `/root/WorkoutTracker/app`
- Authoritative configuration: `/root/WorkoutTracker/.env`
- Application copy: `/root/WorkoutTracker/app/.env`
- Existing storage: `/root/WorkoutTracker/data/storage`
- Host environment/code/config/status/private logs: `/root/WorkoutTracker/updater`
- Local control: `data/storage/config/updater-bridge/control.sock`
- Operator-provisioned client metadata: `data/storage/config/updater-bridge/client.json`
- Independent GET-only progress: **http://10.0.69.9:8001/status**
- Unit: `/etc/systemd/system/workout-tracker-updater.service`

Initial SSH/root access is required once. The host needs Linux/systemd, Python
3 with venv/pip support (3.12 tested), Git, Docker Engine/Compose, standard Linux
utilities and enough free disk space. Install the distribution's Python/venv
packages if missing (for the reported Python 3.12 ensurepip error on Debian/Ubuntu,
run `apt update` and `apt install python3.12-venv` as root, then rerun the installer;
no database or partial venv deletion is needed). Do not change Docker networking/ports to solve a dependency
error. No host SQLite package is needed. The existing root Git credentials must
support noninteractive fetch of this repository. Credentials are never entered
into the app or embedded in source. GitHub/PyPI build transport continues using
normal verified transport; this does not enable HTTPS on the LAN application.

Protect the whole storage tree, private .env, and updater state separately (for
example with existing VM/offsite backups). SQLite backups omit external keys,
settings, accents, schedules and host updater files. Stop external SQLite tools
before maintenance. Do not initialize installed storage or delete retained files.

## First upgrade from schema 6

These commands use the latest approved main, currently Phase 12. Schemas 4/5 can
also upgrade explicitly to 8 through the same candidate machinery; verify the
actual installed schema rather than assuming it. The initial step updates source
only; the currently running image/database remain unchanged until v4 is confirmed.

First inspect your checkout. If it lists local changes, stop and reconcile them;
never reset or discard work:

```sh
cd /root/WorkoutTracker/app
git status --short --branch
```

With a clean main checkout:

```sh
(
  set -eu
  cd /root/WorkoutTracker/app
  test "$(git branch --show-current)" = main
  test -z "$(git status --porcelain)"
  git fetch origin
  git merge --ff-only origin/main
  bash deployment/update_workout_tracker_v4.sh --install-service \
    --lan-address 10.0.69.9 \
    --app-url http://10.0.69.9:8000 \
    --status-port 8001
)
```

The explicit installer creates a private host venv/runtime and Unix bridge,
installs/enables the independent systemd service, and binds only read-only
progress to the supplied LAN address/port. It does **not** stop/rebuild/migrate the
workout app, create a database or change its normal HTTP port. No privileged setup
runs at Flask startup. Systemd hardening keeps writes under the installation tree;
Docker client config/cache is private under updater/docker. Docker itself grants
root-equivalent host capability to this deliberately separate fixed-command worker,
not to the web container. Protect host access and merge rights accordingly.

Now run the new manual entry point explicitly, not an old same-named v3 copy:

```sh
bash /root/WorkoutTracker/app/deployment/update_workout_tracker_v4.sh
```

It checks approved main, displays the release, asks to install with a verified
backup, and prompts **MIGRATE 8** if the actual source schema needs upgrading.
This is a safety confirmation, not authentication. The shared engine stops only
web/scheduler, verifies a distinct backup, preserves the previous image/commit,
builds, checks actual release-info, invokes confirmed candidate migration and
validates schema/original bytes before restart. It then verifies actual app 0.12.0 /
schema 8 and scheduler status. No unsupported older image is started after schema
activation. The parent .env is copied atomically/private into app/.env with the
same contents, as explicitly requested; paths, ports and values are not changed.

For deliberately preapproved noninteractive operator maintenance only:

```sh
bash /root/WorkoutTracker/app/deployment/update_workout_tracker_v4.sh \
  --confirm --allow-migration
```

Those flags explicitly approve the update/schema change; routine browser use
still reviews and confirms both. Legacy `--backup` is accepted for compatibility:
all confirmed v4/browser updates already include a verified backup.

After success:

```sh
docker compose --project-directory /root/WorkoutTracker/app \
  --env-file /root/WorkoutTracker/.env \
  -f /root/WorkoutTracker/app/compose.yaml ps

docker compose --project-directory /root/WorkoutTracker/app \
  --env-file /root/WorkoutTracker/.env \
  -f /root/WorkoutTracker/app/compose.yaml exec -T web python -c \
  'import json,urllib.request; r=json.load(urllib.request.urlopen("http://127.0.0.1:8000/health/ready",timeout=10)); print(r); assert r==dict(status="ready",app_version="0.12.0",schema_version=8)'
```

Open **http://10.0.69.9:8000/settings/updates**. No login or certificate action
is required. Keep port 8001 restricted to trusted LAN devices in the existing
host/VM firewall policy; never forward either port from the public internet.
No application port/bind setting is changed by the installer. The extra listener
is read-only; update control is not exposed there.

## Routine browser updates

1. Settings → Administration → Application Updates → Check for Updates.
2. Review the approved version, full commit, release notes and required schema.
3. Open View Update Progress and Logs (the independent HTTP page) in its own tab.
4. Acknowledge Install Update. If schema changes, explicitly check the migration
   confirmation explaining that a separate verified database candidate is created.
5. Watch named real stages; the app may temporarily disconnect. The independent
   page stays available and refreshes while busy. Reconnect to the normal app
   after completion and verify footer/Settings versions.

No update is installed automatically. No-update checks do not stop containers,
create backups or mutate the database. Two operations cannot run together.
No cloud callback, remote script or unmerged branch is executed.

## Approved release policy

Only fetched **main** in `natpev/Workout-Tracker-vibe-webapp` is approved. The policy
relies on the repository owner's main-merge/review governance, not a claim of GPG
signature verification. Review pins the full commit SHA. If approved main changes
before install, review again; the worker refuses to substitute a new commit.
It rejects dirty/diverged local history, unexpected origin, browser-supplied URLs,
repositories, commands, branches and images. Metadata is parsed with AST literal
evaluation before execution and compared with the newly built image's
`release-info`. Schema compatibility is never guessed from application versions.
The target schema is not capped at 5 or 6 by v4; a future approved release must
actually support its target/source migration in its own verified application CLI.

## Host control/status boundary

- Unix socket: mode 0660, root:configured writer group; bridge directory 0750.
  Linux peer UID must be the configured app writer or root. JSON accepts only
  status/check/install with fixed fields and a known approved release.
- No Docker socket or host command endpoint is mounted/exposed in web/scheduler.
  The app uses the existing data bind only to reach the local control socket.
- Status server: GET-only `/status` and `/status.json`, explicit private interface
  and trusted Host. No install/check/shell API, credentials or user sessions.
- Host `updater/` and operation diagnostics are private (0700 directories/0600
  files). Public LAN status includes safe stages/notes, not .env, private command
  output, session keys or performance values. Resolved Compose output is withheld
  from diagnostics to avoid leaking explicit secret overrides.
- Unit is independent, so app replacement does not stop it. A per-service lock
  prevents duplicate listeners; the shared operation flock also coordinates v4.

For a service upgrade, explicitly rerun `--upgrade-service` with the same LAN
address/app URL. It refuses overlapping operations and never performs privileged
installation implicitly during app startup or a normal page view.

## Emergency SSH checks and failure recovery

```sh
bash /root/WorkoutTracker/app/deployment/update_workout_tracker_v4.sh --status
bash /root/WorkoutTracker/app/deployment/update_workout_tracker_v4.sh --check
systemctl status workout-tracker-updater.service --no-pager
journalctl -u workout-tracker-updater.service -n 80 --no-pager
```

A private `OPERATION_ID.recovery.json` saves the original manifest/hash and retained
image/version/commit before any stop attempt. Safe status records name the failed stage and preserve previous commit/image,
backup ID, database filename and operation ID. Detailed host-only output is in
`/root/WorkoutTracker/updater/OPERATION_ID.private.log`. Do not publish .env or
private diagnostics blindly. Existing app logs remain available in Settings.

Before migration activation, safe recovery can retag/start the preserved image
only when the selection and original bytes are unchanged, configuration matches,
the old image verifies storage read-only using the configured Compose UID/GID,
and actual old web/scheduler health is checked. Failed recovery checks are logged
without masking the initial failure. A changed dataset or failed cleanup requires
manual inspection; storage permissions are never relaxed.
The Git checkout can remain on newer approved main while that retained old image
runs; no commits are reset/discarded. A later retry rebuilds the reviewed release.
After schema activation, a failed startup/readiness check leaves both services
stopped and preserves the selected candidate/original/backup; it does not blindly
run an older image or overwrite newer workouts with a backup.

A stopped/interrupted host service does not replay accepted updates at restart.
It records failure and stops workout services for interrupted installs; interrupted
checks do not stop a healthy app. Inspect sources, active manifest and logs before
retrying. SIGKILL/power loss/disk faults can interrupt cleanup; inspection remains
necessary. Never edit schema markers, initialize a replacement or silently restore.
A deliberate offline rollback must pair a compatible image and retained selection;
it cannot merge workouts entered after the newer schema was activated.

The engine reserves space using current DB size plus image allowance and checks
both installation and Docker filesystems. If inspection is refused, use the installed
root host service and inspect its permissions; do not bypass the check. Config
changes to Compose mounts/images/services must be reviewed separately, never applied
silently by the updater. Backups, retained databases and old images are not pruned.

## Verification limits

Development uses synthetic data, loopback-only HTTP and unpublished Docker app
ports. Script flow/failure tests use fake Git/Docker but real application backup/
migration code. The real Docker rehearsal simulates Git release metadata and the
cloud rootless-daemon disk-path probe (the test UID cannot traverse that user's
private folder); build, backup, migration, container restart, peer UID checks and
HTTP status are real. Actual systemd syntax is verified offline; no live systemd
unit or production installation is changed. Your server's Git credentials,
firewall, Python packages and permissions still need the one-time operator checks.


## Phase 9 compatibility and already-installed host runtime

V4 remains the supported wrapper; it reads approved release targets dynamically
and invokes the new image's explicit migration CLI. Tests cover 0.9.0/schema 7,
code-only schema-7 updates, actual schema-6→7 Docker upgrades and original-byte
preservation. The host engine's safety and fixed operation protocol are unchanged.
Only host status timestamp presentation was standardized to explicit 24-hour UTC.
The separately installed Phase 8 host engine can already deliver this release.
To copy the latest host presentation code too, explicitly rerun:

```sh
bash /root/WorkoutTracker/app/deployment/update_workout_tracker_v4.sh   --upgrade-service --lan-address 10.0.69.9   --app-url http://10.0.69.9:8000 --status-port 8001
```

This refreshes only the independent host runtime; it does not initialize or
migrate workout storage. A first installation still uses --install-service as
above. Keep the existing .env timezone America/Indiana/Indianapolis; do not replace
it with a UTC offset or change the normal HTTP port. Backup schedule timezone is
configured independently in Administration and is not silently overwritten.

Migration adds exercise_defaults on a separate candidate, initializes neutral
Weight/3×12/pounds presets for old identities, and verifies old cells, source
hashes, exact DDL, integrity/FKs and completeness before activation. Existing
routine settings and historical snapshots are unchanged. Schema-6 backups stay
retained but Restore accepts only the exact currently selected schema; do not
silently downgrade a schema-7 installation. No application startup migration.

## Phase 10 existing-installation upgrade

**SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.**

Release **0.10.4 / target schema 7** is code-only for an existing schema-7 database.
V4 remains supported. Install Update opens one independent status tab with a
popup-blocked fallback; Check opens none. The new live console requires changed
host Python modules and local status.js/status.css, copied by the existing explicit
installer. Flask/Docker replacement alone never updates that separate runtime.
An older host can still install this release, with basic status only, until you
perform the host upgrade. Its missing console_protocol capability produces an app
warning. Never assume container restart upgrades the host service.

Run the following **over SSH on your server**, from root, only after this release
is on main. These commands were not executed on your server. They require your
existing installed service, clean main checkout, fixed paths/private address, Docker
and Python venv dependencies. Keep your actual existing address if different.
First ensure no check/install job is running; the service installer also refuses
an overlapping update lock. Stop at an error; do not reset/clean local work.

```bash
(
  set -e
  cd /root/WorkoutTracker/app
  test "$(git branch --show-current)" = main
  test -z "$(git status --porcelain)"
  git fetch origin main
  git merge --ff-only origin/main
  bash deployment/update_workout_tracker_v4.sh \
    --upgrade-service --lan-address 10.0.69.9 \
    --app-url http://10.0.69.9:8000 --status-port 8001
  bash deployment/update_workout_tracker_v4.sh
)
```

Fetching/fast-forwarding source before the host upgrade does not change running
containers or SQLite. The explicit upgrade copies the new runtime/assets, refreshes
the independent service and bridge configuration, and leaves app containers/storage
running. The final v4 command asks for update consent, verifies a backup and uses
the existing safe build/health workflow. For schema 7 it does not migrate or switch
the selected database. If your installation is older, review its detected schema
and explicitly approve the existing candidate migration separately; never initialize
or restore to force an upgrade. Keep parent .env and Compose settings unchanged.

Afterward verify:

```bash
curl --fail http://10.0.69.9:8000/health/ready
curl --fail http://10.0.69.9:8001/status.json
systemctl status workout-tracker-updater.service --no-pager
```

Ready JSON should report app_version 0.10.4 / schema_version 7; host status JSON
should include console_protocol 1. Open http://10.0.69.9:8001/status for retained
console output and Administration → Application Updates for future browser updates.
A missing ensurepip/venv error requires the matching distro Python venv package
(e.g. apt install python3-venv, or python3.12-venv when Python is 3.12), then rerun
the explicit service-upgrade command. No replacement update script is required.

### Safe console and diagnostic boundaries

A selector streams actual fixed-argv child stdout/stderr before exit, under the
original deadlines. Both pipes drain; parse tails are bounded to 2 MiB each and
unterminated line buffers are bounded. Private operation logs remain detailed
SSH diagnostics, except resolved Compose configuration is withheld altogether.
The browser gets only a separate default-deny classification of recognized
structural output and actual stage/command-exit events. Numeric Git progress,
BuildKit DONE/CACHED, dependency lifecycle, verified backup/schema and container
lifecycle appear; arbitrary text, commands, URLs, environment values and exception
bodies do not. This deliberately omits many detailed build/error lines; use SSH
private logs for diagnosis rather than expanding the public allowlist casually.

Safe rings are atomic private JSON files with 500 × 500-character lines and the
newest 20 operations; only those safe files are pruned. Raw private logs, recovery
records, images, backups and schema archives retain existing policy. GET-only
console.json accepts an allowlisted current/retained 32-hex operation ID and bounded
cursor, never a pathname, shell text or control command. Local CSP-bound scripts
render via textContent. Polling every 1.5 seconds survives web container downtime;
24-hour timestamps explicitly use UTC. Upward scroll stays fixed; Scroll to Latest
resumes following, and refresh reconnects to retained output. Without JavaScript,
high-level status/events remain available by manual refresh; live console needs JS.
The status page remains passwordless and private-LAN-only, with no TLS/proxy added.


## Patch 0.10.1 compatibility

This patch changes only the server-side routine-card ordering and application
version. Target schema remains 7. Use the existing browser Check for Updates →
review → confirmed Install Update workflow, or v4. A schema-7 installation needs
no migration or new host runtime beyond Phase 10. The existing verified backup,
original selection/bytes, health, recovery and fixed-source protections remain.
No updater script or server Compose/.env changes are required for this patch.


## Patch 0.10.2 compatibility

The hamburger fix changes only application CSS and release metadata. Existing
browser/v4 updates detect 0.10.2 and target schema 7 through the unchanged release
protocol. No schema migration, new host runtime, Compose/.env change or extra
installation command is needed for an existing Phase 10 installation. Existing
backup, source verification, recovery and health checks remain. Routine-ordering
patch 0.10.1 is included; its changes are not overwritten or downgraded.


## Patch 0.10.3 compatibility

Header placement and routine activity labels are a code-only update to application
0.10.3, with target schema 7 unchanged. Existing browser/v4 release detection,
backup, consent, health and recovery protocols are unchanged. No database migration,
new host runtime or server Compose/.env change is required for schema-7 Phase 10
installations. Do not initialize or restore storage as part of this update.


## Patch 0.10.4 compatibility

Use the existing browser updater/v4 for application 0.10.4 / target schema 7. The
existing cursor stores the Next checkpoint; no DDL or migration is introduced.
CSV is an in-memory, person-scoped read-only download. No new host service, server
Compose/.env changes, PDF/Excel dependencies or export storage are required. Keep
the existing confirmation, verified backup, original storage and health safeguards.


## Phase 11 schema 7 to 8 upgrade

**SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.**
This section records the Phase 11 release **0.11.0 / schema 8**. For current 0.12.0 instructions see the Phase 12 section below. Earlier Phase 9/10 and patch instructions
above document their historical release targets, not a schema-7 code-only update
for this release. Existing schema 7 must explicitly migrate a separate candidate.

For a working installed Phase 10 browser updater:

1. Open Settings → Administration → Application Updates → Check for Updates.
2. Review approved main, application 0.11.0 and target schema 8.
3. Confirm installation and the schema migration, then press Install Update.
4. Watch the independent http://10.0.69.9:8001/status tab through backup, build,
   candidate migration and health verification. Do not close it or start another job.
5. Reopen the app; Settings/footer and /health/ready must show 0.11.0 / schema 8.
   Make a new verified schema-8 backup. Older schema-7 backups stay retained but
   Restore cannot downgrade a schema-8 installation.

The existing host engine/v4 supports dynamic target 8 and invokes the new image's
CLI. No Phase-11 host runtime reinstall, new script, Compose/.env change, port or
server timezone change is required. Older pre-Phase-10 services still need their
previously documented one-time upgrade for live console output, separately.

Emergency SSH alternative on your installed server (operator commands only):

```bash
cd /root/WorkoutTracker/app
git status --short --branch
# Stop here if there are local changes or a non-main checkout; reconcile safely.
bash /root/WorkoutTracker/app/deployment/update_workout_tracker_v4.sh
```

Review the release; confirm installation and type **MIGRATE 8** when prompted.
This is the existing repository v4, not an uninspected external root wrapper.
It stops web/scheduler, verifies a unique backup, retains source/image/selection,
builds, confirms release-info, runs candidate migration and verifies health. Never
run init-storage or Restore as an upgrade shortcut. If v4 is not present locally,
with a clean main checkout fetch and fast-forward first:

```bash
cd /root/WorkoutTracker/app
git fetch origin main
git merge --ff-only origin/main
bash deployment/update_workout_tracker_v4.sh
```

If deliberate manual maintenance is required instead, stop both services and
external SQLite tools, protect the whole tree/private .env and verify a backup
before updating. With the new image built and writers stopped, its explicit
migration command is:

```bash
docker compose --project-directory /root/WorkoutTracker/app \
  --env-file /root/WorkoutTracker/.env \
  -f /root/WorkoutTracker/app/compose.yaml run --rm --no-deps web \
  python -m workout_tracker migrate-storage --data-root /var/lib/workout-tracker \
  --target-version 8 --confirm-upgrade

docker compose --project-directory /root/WorkoutTracker/app \
  --env-file /root/WorkoutTracker/.env \
  -f /root/WorkoutTracker/app/compose.yaml run --rm --no-deps web \
  python -m workout_tracker check-storage --data-root /var/lib/workout-tracker
```

Continue only after verification succeeds, using the same existing Compose/.env:

```bash
docker compose --project-directory /root/WorkoutTracker/app \
  --env-file /root/WorkoutTracker/.env \
  -f /root/WorkoutTracker/app/compose.yaml up -d --no-build
curl --fail http://10.0.69.9:8000/health/ready
```

Expected JSON: {"app_version":"0.11.0","schema_version":8,"status":"ready"}.
Failure retains original schema-7 database and prior selection; failed candidates
stay for diagnosis. A post-activation startup failure must not automatically run
an incompatible old image or restore older data. Inspect retained versions and
private recovery logs. Rollback cannot merge workouts entered after schema 8.
No server command above has been executed by development tests.


## Phase 12 host service upgrade

**SHAMELESSLY VIBE-CODED 🤖**

This application was built with a healthy dose of AI, questionable amounts of confidence, and minimal human supervision. It appears to work, but don’t mistake that for a warranty. Use at your own risk, and keep backups.

Current release: **0.12.0 / schema 8 unchanged**. Schema-8 installations need no
migration. No Compose/.env, port, timezone or storage change is required. Browser
updates/v4 still require explicit installation consent and a verified backup.

The new host reads releases/VERSION.json from approved pinned main before install
and persists plain notes. Independent console CSS now scrolls long lines without
wrapping. The host runtime/assets are copied separately from the Docker app, so
an explicit one-time upgrade is required for both improvements. Updating only the
web container does not replace the service. Old hosts can still install releases
safely; the new app hides their Git-log notes and displays an upgrade explanation.

On your existing server, over SSH as root, with no check/install job running:

```bash
(
  set -e
  cd /root/WorkoutTracker/app
  test "$(git branch --show-current)" = main
  test -z "$(git status --porcelain)"
  git fetch origin main
  git merge --ff-only origin/main
  bash deployment/update_workout_tracker_v4.sh \
    --upgrade-service --lan-address 10.0.69.9 \
    --app-url http://10.0.69.9:8000 --status-port 8001
)
```

Keep your actual private address if different. Stop at any error; never reset or
clean local work. Fetching code and refreshing this service do not initialize,
migrate or replace workout storage/containers. The installer refuses an active
update lock. Root needs the distribution's matching Python venv package and Git
credentials as previously documented.

Then use browser Check → review What's New in v0.12.0 → confirm → Install, or:

```bash
bash /root/WorkoutTracker/app/deployment/update_workout_tracker_v4.sh
```

Verify http://10.0.69.9:8000/health/ready reports app_version 0.12.0 and schema 8;
verify the independent http://10.0.69.9:8001/status page has readable release notes
and a non-wrapping, internally scrollable live console. Make a new verified backup.
For a new installation, use --install-service instead of --upgrade-service after
following the current README. Older schemas still need their separately confirmed
candidate migration to 8. Never initialize or restore storage as an update shortcut.
No production host/service/database was changed by development verification.
