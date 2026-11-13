# Workout Tracker installation, LAN updater v4 and recovery

> **SHAMELESSLY VIBE-CODED 🤖**
>
> This application was built with a healthy dose of AI, questionable amounts of confidence, and minimal human supervision. It appears to work, but don’t mistake that for a warranty. Use at your own risk, and keep backups. Not an independent audit. Commands below are for the operator, not deployment performed by Codex.

Application **1.0.0**, full-feature schema **13**. This release needs no new host-service refresh after Phase 12 setup; use normal browser installation. If the host service predates Phase 12, use the [one-time host upgrade](#phase-12-host-service-upgrade). Schema-12 installations need an explicitly confirmed separate-candidate migration to 13. See [upgrade prerequisites](../docs/UPGRADING.md) for older installations. The application remains
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

## First host-service installation

Follow the current [beginner installation](../README.md) first. With clean main
and the existing storage/configuration preserved, install only the independent
service over SSH as root:

```sh
cd /root/WorkoutTracker/app
bash deployment/update_workout_tracker_v4.sh --install-service \
  --lan-address 10.0.69.9 --app-url http://10.0.69.9:8000 --status-port 8001
```

Use your actual private address. The installer creates private host venv/runtime,
Unix bridge and systemd unit. It neither creates/migrates a workout database nor
replaces the running app. Keep ports 8000/8001 on your trusted LAN only. This worker
has deliberate root-equivalent Docker capability; the Flask container does not.

For emergency updates, use the same protected host engine through v4:

```sh
bash /root/WorkoutTracker/app/deployment/update_workout_tracker_v4.sh
```

It displays approved 1.0.0 and prompts **MIGRATE 13** if necessary. Review explicitly.
No-update checks perform no copy/migration. A confirmed update makes a verified
backup, preserves original database/image/selection, builds, migrates a separate
candidate and verifies health. Parent .env is privately copied with identical
contents; values are never changed. Existing user-written root wrappers were not
inspected or tested as part of this release.

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

## Phase 12 host service upgrade

**SHAMELESSLY VIBE-CODED 🤖**

This application was built with a healthy dose of AI, questionable amounts of confidence, and minimal human supervision. It appears to work, but don’t mistake that for a warranty. Use at your own risk, and keep backups.

This procedure is needed only once for hosts not yet refreshed for Phase 12.
Version 1.0.0 does not change that host protocol; do not repeat this procedure if already refreshed.

Application **1.0.0 / target schema 13** uses the same host protocol. The
service refresh itself never migrates storage or replaces running containers.
No new refresh is needed when this capability is already installed.

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

Then use browser Check → review What's New in v1.0.0 → confirm → Install, or:

```bash
bash /root/WorkoutTracker/app/deployment/update_workout_tracker_v4.sh
```

Verify http://10.0.69.9:8000/health/ready reports app_version 1.0.0 and schema 13;
verify the independent http://10.0.69.9:8001/status page has readable release notes
and a non-wrapping, internally scrollable live console. Make a new verified backup.
For a new installation, use --install-service instead of --upgrade-service after
following the current README. Older schemas still need their separately confirmed
candidate migration to 13. Never initialize or restore storage as an update shortcut.
No production host/service/database was changed by development verification.


## Optional Garmin scheduler networking

Scheduler keeps `none` networking by default, resolving to the same Compose
configuration as before. Only automatic Garmin synchronization needs this explicit
setting in the private parent .env:

```text
WORKOUT_SCHEDULER_NETWORK_MODE=bridge
```

Recreate the scheduler during a planned maintenance window:

```sh
cd /root/WorkoutTracker/app
docker compose --env-file ../.env up -d --no-build scheduler
```

It publishes no ports. Manual sync uses web networking. Never put Garmin keys in
.env/Compose: private credentials live in storage/config/garmin-private.json with
0600 permissions. SQLite backups/downloads exclude them; preserve a separate
private whole-tree copy. See [Garmin contract and recovery](../docs/GARMIN.md).

## Deliberate offline restore

This is restoration, not an update shortcut. Later workouts are not merged. Use
only a verified backup of the same storage identity and exact schema, with a
compatible application image. Preserve the complete tree and inspect the failure
before choosing this operation. Stop all writers first, including external tools.
List server-controlled backup IDs without initializing or booting Flask:

```sh
cd /root/WorkoutTracker/app
docker compose --env-file ../.env stop
docker compose --env-file ../.env run --rm --no-deps web \
  python -m workout_tracker list-backups --data-root /var/lib/workout-tracker
```

Replace `COPY_BACKUP_ID` with a verified listed ID. Generate a new operation ID;
reuse it only to inspect/retry that same attempt. Run the following only after
explicitly deciding to discard the active selection in favor of that backup:

```sh
recovery_operation="$(python3 -c 'from uuid import uuid4; print(uuid4().hex)')"
docker compose --env-file ../.env run --rm --no-deps web \
  python -m workout_tracker restore-backup --data-root /var/lib/workout-tracker \
  --backup-id COPY_BACKUP_ID --operation-id "$recovery_operation" --confirm-restore
```

The CLI preserves originals and activates only a validated separate candidate.
Stop at any error; do not initialize replacement storage. Once successful, verify
before restarting the compatible image:

```sh
docker compose --env-file ../.env run --rm --no-deps web \
  python -m workout_tracker check-storage --data-root /var/lib/workout-tracker
docker compose --env-file ../.env up -d --no-build
```

Do not pair an older image with a newer selected database. Do not remove archives,
old backups or failed candidates blindly. [Storage details](../docs/STORAGE.md)
explain what SQLite backups omit and the audit-preservation rules.

## Verify the installed release

```sh
cd /root/WorkoutTracker/app
docker compose --env-file ../.env ps
docker compose --env-file ../.env exec -T web python -c \
  'import json,urllib.request; r=json.load(urllib.request.urlopen("http://127.0.0.1:8000/health/ready",timeout=10)); print(r); assert r==dict(status="ready",app_version="1.0.0",schema_version=13)'
```

Make a new verified schema-13 backup after success. Older-schema backups remain
retained but cannot silently downgrade 13. Ordinary startup never migrates.

## Verification limits

[The release report](../RELEASE_1_0_0_TEST_REPORT.md) records actual synthetic
Linux/Chromium/Docker results. Git/source and selected host-path probes use test
adapters; separate tests exercise actual builds, SQLite candidates, service
replacement and health. No production deployment, physical iPhone/Safari, ARM,
real Garmin account or unknown external server-wrapper test is claimed.

Legacy migration prerequisites and interpretation remain in
[UPGRADING.md](../docs/UPGRADING.md), [MEASUREMENTS.md](../docs/MEASUREMENTS.md)
and the retained historical schema guides. Frozen migrations, audit readers and
versioned release metadata are not removed by documentation cleanup.
