# Workout Tracker

> **SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.** Human-directed AI-generated software; not audited or approved for production.


## Installation & Setup Guide

### Quick overview

Install on a Linux home server with Docker Engine and the **Docker Compose
plugin** (`docker compose`). Docker runs the Python application and SQLite;
**host Python, pip and a separate SQLite installation are not required**.
Two containers run together: **web** serves the site; **scheduler** handles
configured backups and log retention without a browser. Both run as the same
non-root user and keep data in a host directory outside the code checkout.
Automatic backups start **disabled**.

Current application version: **0.11.0**. Current full-feature database schema:
**8**. Application and schema versions are different numbers. Initialization and
migration are explicit one-time steps, never automatic startup actions.

Follow the numbered steps in order from a **normal, non-root Linux account**
with `sudo` and permission to use Docker. Examples use Bash, `/opt`, and local
storage. Do not run initialization against an existing installation. Stop at
any failed command and use [Troubleshooting](#10-troubleshooting); never delete
storage to make a command work.

**Guide contents**

1. [Requirements and version checks](#1-requirements-and-version-checks)
2. [Install the application code](#2-install-the-application-code)
3. [Configure Compose](#3-configure-compose)
4. [Build the image and prepare the storage parent](#4-build-the-image-and-prepare-the-storage-parent)
5. [Initialize and verify schema 8](#5-initialize-and-verify-schema-8)
6. [Start services and verify readiness](#6-start-services-and-verify-readiness)
7. [Local and home-network access](#7-local-and-home-network-access)
8. [First-run checks and everyday operations](#8-first-run-checks-and-everyday-operations)
9. [Safe application updates](#9-safe-application-updates)
10. [Troubleshooting](#10-troubleshooting)
11. [What was verified](#what-was-verified)

### 1. Requirements and version checks

| Item | Requirement and verification boundary |
| --- | --- |
| Linux | A maintained Linux distribution supported by Docker Engine. Debian/Ubuntu with systemd are the reference instructions below. Actual verification used Debian 13, x86-64, in the managed test environment; a clean physical server install/reboot was not exercised. Windows/macOS hosts are outside this guide. |
| CPU architecture | `linux/amd64` is tested. The pinned Python base-image manifest also publishes `linux/arm64/v8` (for example, a 64-bit Raspberry Pi OS host), but this application's ARM build/runtime is **not tested**. Other architectures are not validated or recommended here merely because a base image exists. |
| Practical capacity | Start with 1 CPU core, 1 GiB RAM (2 GiB gives more build headroom), and 5 GiB free local disk **plus** room for growing databases, retained candidates and indefinite backups. These are planning recommendations, not measured minimums or performance guarantees; large histories need more space. |
| Docker Engine | Standard Linux Engine, access to its local daemon, and BuildKit/buildx with `RUN --mount=type=secret` support. Use a maintained release from Docker's supported packages. Tested Engine **29.9.2**, buildx **0.31.0**. The repository does not declare or test an oldest compatible Engine version; no numeric minimum is claimed. Docker Desktop is not required. Rootless Docker/user-namespace-remapped setups are not covered by the verified ownership procedure. |
| Compose | The plugin invoked as `docker compose`, with build secrets, long bind mounts and `bind.create_host_path: false` support. Tested **v2.40.3**. No oldest compatible plugin version is established; an old `docker-compose` binary is not the documented workflow. Use a current supported plugin and validate its configuration below. |
| Python and SQLite | The image pins `python:3.12-slim` by digest; runtime Python is **3.12**. SQLite is supplied by Python inside that image and must be **3.37+** for `STRICT` tables. Exact tested patch versions are recorded in [INSTALLATION_REVIEW.md](INSTALLATION_REVIEW.md). No host interpreter, virtual environment or database server is mandatory. |
| Git | Required to clone/fetch approved code. Tested **2.52.0**; no project-specific numeric minimum is declared. A maintained Git supporting the commands below is sufficient. Private repositories also require your GitHub access; use your normal Git credential helper/SSH setup, never embed tokens in the clone URL or `.env`. |
| Filesystem | Local POSIX storage with SQLite file locking, `flock`, hard links, atomic same-filesystem rename, `fsync` and directory syncing. Ordinary local ext4/XFS are appropriate choices; no network-filesystem testing is claimed. Do not use NFS/SMB, cloud-sync folders, symlinked storage paths, or an existing WAL/sidecar-bearing database. Preserve correct numeric ownership and private permissions. |
| Network/build tools | Initial clone/build needs DNS and HTTPS to GitHub, Docker Hub and Python package indexes (`pypi.org`, `files.pythonhosted.org`). Docker build needs a valid CA bundle; the default path is `/etc/ssl/certs/ca-certificates.crt`. Keep any required proxy and CA settings. Runtime requires no cloud service/CDN and the scheduler has no network. |
| Host utilities | Bash, `sudo`, standard `id`, `test`, `install`, `chmod`, and a way to edit text files. Browser access is needed for household use. `curl`, `jq`, `sqlite3`, host Python and Chromium/pytest development tools are **optional**, not installation dependencies. |

Install Docker Engine, buildx and the Compose plugin using Docker's official
instructions for [Debian](https://docs.docker.com/engine/install/debian/) or
[Ubuntu](https://docs.docker.com/engine/install/ubuntu/), and install Git through
your distribution (on Debian/Ubuntu, `sudo apt-get update` then
`sudo apt-get install --yes git ca-certificates`). Those OS/package-manager steps depend on your host version;
do not paste commands for a different distribution. Then check:

```sh
docker --version
docker compose version
docker buildx version
docker info
git --version
uname -m
id
```

`docker info` must succeed. Follow Docker's
[Linux post-installation instructions](https://docs.docker.com/engine/install/linux-postinstall/)
if your account cannot access the daemon. Membership in the `docker` group gives
root-equivalent host control; grant it only to trusted administrators. After a
group change, log out and back in. The commands below assume `docker` works
without `sudo`; do not fix this by making the Docker socket world-writable.

### 2. Install the application code

The example layout is:

```text
/opt/workout-tracker/              # Git checkout; replaceable code and private .env
/opt/workout-tracker-data/         # parent used only to bootstrap a new storage root
  storage/                        # WORKOUT_DATA_ROOT; must NOT exist before init-storage
    data/                         # selected SQLite DB and retained schema/recovery versions
    config/active.json            # selects one existing DB, not necessarily the newest filename
    config/session.key            # private signing key, created by explicit migration
    config/operations.json        # schedules, backup history and restore audit; created on use
    archives/                     # previous selection manifests
    backups/                      # timestamped verified copies and retained failed evidence
    logs/                         # private structured application logs
```

An update can replace the code or containers without replacing this host data.
Keep the **whole** storage tree protected; database-only backups do not contain
signing keys or external settings. Do not put `storage/` inside the Git checkout.

For a **new** code checkout, this block refuses any existing destination. If it
already exists, inspect it and follow [Safe updates](#9-safe-application-updates)
instead. Run as your ordinary non-root account:

```sh
(
  set -eu
  test "$(id -u)" -ne 0
  if [ -e /opt/workout-tracker ] || [ -L /opt/workout-tracker ]; then
    echo 'Code directory already exists; stop and inspect it instead of replacing it.' >&2
    exit 1
  fi
  sudo install -d -m 0755 -o "$(id -u)" -g "$(id -g)" /opt/workout-tracker
  git clone --branch main https://github.com/natpev/Workout-Tracker-vibe-webapp.git /opt/workout-tracker
)
cd /opt/workout-tracker
```

If cloning fails, keep the evidence and resolve repository access; no data
initialization has happened yet.

### 3. Configure Compose

Create `.env` in the checkout. This is a **complete, ready-to-run example**:
`$(id -u)` and `$(id -g)` are expanded by the shell into your actual non-root
numeric IDs, avoiding ownership guessing. The block refuses to overwrite an
existing `.env` and creates it privately. If you already have one, edit it instead.

```sh
cd /opt/workout-tracker
(
  set -eu
  test "$(id -u)" -ne 0
  umask 077
  set -C
  cat > .env <<EOF
# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
WORKOUT_DATA_ROOT=/opt/workout-tracker-data/storage
WORKOUT_PORT=8000
WORKOUT_BIND_ADDRESS=127.0.0.1
WORKOUT_UID=$(id -u)
WORKOUT_GID=$(id -g)
WORKOUT_TIMEZONE=America/Indiana/Indianapolis
WORKOUT_TRUSTED_HOSTS=localhost,127.0.0.1,[::1]
WORKOUT_BUILD_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
# WORKOUT_SECRET_KEY is intentionally unset: use the generated private signing file.
EOF
)
chmod 600 .env
```

Choose your own installed IANA timezone if needed, for example `Europe/London`.
Workout-entry timezone and the automatic-backup timezone in Settings are separate;
set both deliberately. New timezone settings do not rewrite historical snapshots.
Do not add real secrets to Git. `.env` is ignored by Git and excluded from image
build context. Shell-exported variables take precedence over `.env`; avoid stale
exports when changing an installation. `docker compose config` can reveal an
explicit secret override, so keep its output private.

| Variable | Required/default | Example and when to change; security considerations |
| --- | --- | --- |
| `WORKOUT_DATA_ROOT` | Required; no default | Host `/opt/workout-tracker-data/storage`, outside the checkout. Compose binds this to **`/var/lib/workout-tracker` inside both containers** and passes that internal value to Python. Use the internal path in `compose run/exec` CLI commands. Never point at an unrelated/existing database to initialize it. |
| `WORKOUT_PORT` | Optional; `8000` | Host HTTP port, e.g. `8080` if 8000 is occupied. Container port stays 8000; use the chosen host port in browser URLs/firewall rules. |
| `WORKOUT_BIND_ADDRESS` | Optional; `127.0.0.1` | Host publishing address. Keep loopback for local-only use; explicitly choose a **private LAN interface address**, e.g. `192.168.1.100`, for phone access. Never publish to an internet-facing address. |
| `WORKOUT_UID` | Optional; `10001` | Non-root numeric process UID for both services. This guide writes your `id -u`; use that same account during bootstrap. If you choose another UID, arrange ownership deliberately before starting; never use 0 or world-writable data. |
| `WORKOUT_GID` | Optional; `10001` | Numeric process GID, matching data ownership. The example uses your `id -g`. Both services must have the same access to private storage. |
| `WORKOUT_TIMEZONE` | Optional; Compose `Etc/UTC` | Example `America/Indiana/Indianapolis`; controls workout occurrence dates. Invalid/uninstalled zone names prevent web startup. Direct Python execution outside Compose otherwise follows server-local timezone, then UTC. |
| `WORKOUT_TRUSTED_HOSTS` | Optional; `localhost,127.0.0.1,[::1]` | Comma-separated accepted hostnames/IPs, **without scheme, port or spaces**. Add the exact private server IP/hostname used in browsers. Keep localhost entries for health checks. Host-header validation is not authentication or a firewall. |
| `WORKOUT_SECRET_KEY` | Optional; unset/empty → private `config/session.key` | Normally leave unset. Explicit migration generates and preserves a private key. An advanced operator may provide a securely generated signing secret instead; Compose forwards it to web only. Environment values are visible to Docker administrators. Never use an example/shared key; keep all workers consistent. Changing it invalidates browser sessions/CSRF, not workout records. |
| `WORKOUT_BUILD_CA_BUNDLE` | Optional; `/etc/ssl/certs/ca-certificates.crt` | Path to an existing trusted host CA bundle, mounted as build secret `pip_ca`. Change for a different distro path or approved corporate proxy CA. It is not stored in image layers. Never disable TLS verification to fix build errors. |

No other application installation variables are read by this release.
`WORKOUT_CHROMIUM`, `WORKOUT_CONTAINER_TESTS` and `WORKOUT_UX_SCREENSHOTS` are optional **test-only** controls,
covered below. The image fixes Python bytecode/unbuffered-output settings; they
do not require `.env` entries. Backup schedules/log retention are configured in
Settings, not through invented environment variables.

Validate interpolation now; this does not start containers and does not require
the storage destination to exist yet:

```sh
docker compose config --quiet
```

Both services share the local image **`workout-tracker:local`**. Web runs
Flask/Gunicorn with a read-only container root, private `/tmp`, dropped
capabilities and no-new-privileges; its external data mount stays writable.
Scheduler uses the same protections and storage, no network/ports, and runs
`python -m workout_tracker scheduler`. Both have `restart: unless-stopped`.

### 4. Build the image and prepare the storage parent

```sh
docker compose build
```

The build installs the pinned runtime dependencies inside the image, not on the
host. The first build needs internet access and may take several minutes.
BuildKit/buildx must be available; certificate errors require the correct CA
bundle/proxy, not an insecure pip option.

Now create only the **parent** directory. This block refuses an existing parent
so you cannot accidentally adopt another installation. The actual destination
`/opt/workout-tracker-data/storage` must remain absent until the next step:

```sh
(
  set -eu
  if sudo test -e /opt/workout-tracker-data || sudo test -L /opt/workout-tracker-data; then
    echo 'Storage parent already exists; stop and inspect it. Do not reinitialize.' >&2
    exit 1
  fi
  sudo install -d -m 0700 -o "$(id -u)" -g "$(id -g)" /opt/workout-tracker-data
)
```

This matches the generated `.env` UID/GID. No blanket permission changes or
recursive ownership changes to an existing installation are needed.

### 5. Initialize and verify schema 8

**Run once, only for a new installation.** Initialization refuses an existing
destination, even an empty directory. Normal Compose mounts refuse a missing
host directory. The temporary parent mount below resolves both requirements:
Docker mounts the existing parent as `/bootstrap`, and the application creates
its previously nonexistent child `/bootstrap/storage` itself.

```sh
docker run --rm --network=none --read-only --tmpfs /tmp \
  --cap-drop=ALL --security-opt=no-new-privileges:true \
  --user "$(id -u):$(id -g)" \
  --mount type=bind,src=/opt/workout-tracker-data,dst=/bootstrap \
  --entrypoint python workout-tracker:local \
  -m workout_tracker init-storage --data-root /bootstrap/storage --confirm-new-storage
```

It reports foundation storage initialized; **schema 1 is only the first step**.
The new child now exists for Compose. Explicitly migrate a **separate candidate**
to schema 8, then verify it:

```sh
docker compose run --rm --no-deps web python -m workout_tracker migrate-storage \
  --data-root /var/lib/workout-tracker --confirm-upgrade --target-version 8

docker compose run --rm --no-deps web python -m workout_tracker check-storage \
  --data-root /var/lib/workout-tracker
```

Expect `Schema 8 verified` / `Storage verified; schema version 8.` The migration
retains the schema-1 original, creates schema 8 in another file, provisions the
private signing key, and atomically selects only a verified candidate. Do not
omit `--target-version 8`: the CLI's backward-compatible default is **3**.
`compose run` does not publish web ports unless explicitly requested; these are
one-off maintenance containers, not started web/scheduler services.

Confirm numeric ownership and key permissions without printing the key:

```sh
docker compose run --rm --no-deps web python -c \
  'import os; from pathlib import Path; p=Path("/var/lib/workout-tracker"); k=p/"config/session.key"; print("process UID/GID:",os.getuid(),os.getgid()); print("storage UID/GID:",p.stat().st_uid,p.stat().st_gid); print("key permissions:",oct(k.stat().st_mode & 0o777))'
```

Process and storage IDs should match your `.env`; key permissions should be
`0o600`. Both containers need write access to the storage tree. Do not make it
world-readable/writable. Stop if initialization/migration fails; preserve all
files and use the diagnostics below. Never rerun initialization to repair an
existing, missing, damaged or incompatible installation.

### 6. Start services and verify readiness

```sh
docker compose up -d --no-build
docker compose ps
docker compose ps --status running --services
docker compose logs --tail 100 web scheduler
```

Both `web` and `scheduler` should be **Up/running**. Web should become **healthy**
after its next 30-second health check; scheduler has no HTTP health endpoint and
is shown running rather than healthy. File-based scheduler INFO events may not
appear in `compose logs`; inspect Settings → Administration → Logs → category Scheduler for
`Scheduler process started`. No automatic backup runs until you enable it.

Verify the live web endpoint using Python **inside** the container:

```sh
docker compose exec -T web python -c \
  'import json,urllib.request; d=json.load(urllib.request.urlopen("http://127.0.0.1:8000/health/ready",timeout=10)); print(d); assert d["status"]=="ready" and d["app_version"]=="0.11.0" and d["schema_version"]==8'
```

Expected fields are `status: ready`, `app_version: 0.11.0`, `schema_version: 8`.
If startup is still in progress, wait a few seconds and retry. From a browser on
the Linux host, open **http://127.0.0.1:8000** (substitute `WORKOUT_PORT` if changed).
Optional host utility: `curl --fail --show-error http://127.0.0.1:8000/health/ready`.
On a headless host, use the next section for phone/PC access instead.

For standard systemd-based Debian/Ubuntu, enable Docker itself at boot:

```sh
sudo systemctl enable --now docker
systemctl is-enabled docker
systemctl is-active docker
```

Both services' `unless-stopped` policies restart already-created containers when
Docker/server restarts. No extra application systemd unit is needed. A container
you **explicitly stopped** stays stopped across reboot until you run
`docker compose up -d` again. After a planned server reboot, reconnect and run:

```sh
cd /opt/workout-tracker
docker compose ps
docker compose logs --tail 50 web scheduler
docker compose exec -T web python -c \
  'import urllib.request; print(urllib.request.urlopen("http://127.0.0.1:8000/health/ready",timeout=10).read().decode())'
```

Also confirm the scheduler's startup entry in Settings → Administration → Logs. If data lives on a separate disk, ensure it is mounted before Docker starts; a
missing mount is a reason to stop and investigate, not initialize again. A reboot should
not initialize storage, copy the database or create a backup unless a configured
scheduled slot is due.

### 7. Local and home-network access

**Local host only:** keep `WORKOUT_BIND_ADDRESS=127.0.0.1` and open
`http://127.0.0.1:8000` on that host. Loopback intentionally prevents phone access.

**Home LAN / iPhone:** find your server's actual private LAN address (for example,
with `ip -br address`) and reserve it in your router/DHCP configuration if possible.
Replace these two existing `.env` lines, substituting your real private address:

```dotenv
WORKOUT_BIND_ADDRESS=192.168.1.100
WORKOUT_TRUSTED_HOSTS=localhost,127.0.0.1,[::1],192.168.1.100
```

Then recreate containers so environment/port changes take effect:

```sh
docker compose config --quiet
docker compose up -d --no-build --force-recreate
docker compose ps
```

Compose now publishes **`192.168.1.100:8000` → container `8000`**, instead of the
host loopback address. Use **http://192.168.1.100:8000** on the server and phone;
`http://127.0.0.1:8000` on the host is no longer the published address. The general
format is **`http://SERVER-IP:8000`**. `SERVER-IP` means a placeholder, not text to
paste unchanged. Change the URL port too if you changed `WORKOUT_PORT`.
Container-local readiness checks continue using their own loopback address.
If using a private hostname, add that exact hostname to `WORKOUT_TRUSTED_HOSTS`
and make sure household DNS resolves it to the same private IP. Do not include
`http://`, `:8000` or comma-adjacent spaces in that variable.

Connect the iPhone to the **same trusted home Wi-Fi**, not cellular/isolated guest
Wi-Fi. Your firewall/router must permit the chosen TCP port **only from trusted
LAN devices**. Check the host's firewall and any Proxmox/VM firewall; do not
forward the port through your router or enable UPnP publication. Docker-published
ports can bypass ordinary UFW rules: use Docker-aware firewall policy appropriate
to your installed backend, following
[Docker's firewall documentation](https://docs.docker.com/engine/network/packet-filtering-firewalls/).
Do not assume a generic UFW allow/deny rule alone isolates a published container.
Keep the specific private bind address; do not switch to a public/all-interface
binding to solve a phone connection problem.

There is **no authentication or HTTPS** in this application. Anyone who can reach
it can select household people and change their data. LAN access is not public-
internet security. Do not expose it directly to the internet. VPN access can be
planned separately later; it is not installed or configured by this guide.

### 8. First-run checks and everyday operations

Run this checklist **with synthetic/disposable records before entering real
workouts**. If you already have real records, use a separate disposable storage
tree/Compose project for restore rehearsal; never test restore over them.

1. Open the site and create a household test person in People.
2. Create a routine with one Weight exercise and one Time exercise. Select sets,
   target reps or minutes/seconds. Check Auto, Light and Dark appearance.
3. Start a workout. Save a weight such as `40.99` (it becomes `40.9 lb`) and a
   positive duration; separately try a skipped blank and explicit zero pounds.
4. Finish & Save. Check History, saved prescriptions and separate Progress charts.
5. Open Settings → Backup Now. Wait for **verified** in Backup details/history.
6. **On this disposable dataset only**, select that backup, read the restore
   warning, check acknowledgment, type `RESTORE`, and verify success. The old
   dataset remains preserved; later records are not automatically merged.
7. In Settings, explicitly enable automatic backups, choose frequency/time and
   **backup IANA timezone**, then Save. Set a convenient upcoming time for a
   disposable test; the scheduler polls every 30 seconds. After it is due, inspect
   last attempt/result/success and the verified automatic backup in history.
8. View Settings → Administration → Logs, filter by Scheduler/Backup, and inspect safe error details.
9. Run `docker compose restart`, reopen the site, and confirm saved history,
   backup records and schedule settings remain. Server-confirmed drafts also
   survive; input never acknowledged as Saved may still need resubmission.

Everyday commands from `/opt/workout-tracker`:

```sh
docker compose ps
docker compose logs --tail 100 web scheduler
# Stop both services safely; leave data and containers intact.
docker compose stop
# Resume them in the background.
docker compose up -d --no-build
# Restart both existing containers (does not reload changed .env values).
docker compose restart
```

Use `up -d --force-recreate` after changing `.env`, rather than `restart` alone.
Settings → Administration → Logs reads persistent structured files; `compose logs` also shows
container/Gunicorn startup diagnostics. Database backups stay on this server and
are not automatically downloaded or rotated. Retention applies only to logs.
**Same-server backups do not protect against complete server/storage loss** and
do not replace Proxmox machine backups or a separately protected offsite copy.

### 9. Safe application updates

Updating code/image is different from migrating a database. Before an update,
review the approved release notes, verify available backups and preserve your
private `.env`. Use the existing checkout and the same persistent data root.
If you make a manual backup as a precaution, that is an explicit separate action;
an ordinary compatible update does not automatically copy/back up the database.

**Existing browser updater:** first follow the [Phase 10 one-time host-service upgrade](deployment/README.md#phase-10-existing-installation-upgrade) for live output.

**Manual Docker update, already schema 8 only:** use the normal-update block below. Existing schema-4/5/6/7
installations must instead follow [the confirmed upgrade procedure](deployment/README.md#first-upgrade-from-schema-6) before restarting.

First inspect local work; if `git status --short` lists changes, stop and reconcile
them instead of discarding them. Once the tree is clean:

```sh
cd /opt/workout-tracker
git status --short
git fetch origin
git merge --ff-only origin/main
docker compose config --quiet
# Retain a named copy of the current image before replacing the local tag.
docker image tag workout-tracker:local "workout-tracker:before-update-$(date -u +%Y%m%dT%H%M%SZ)"
docker compose build
# Stop writers before compatibility verification/maintenance.
docker compose stop
docker compose run --rm --no-deps web python -m workout_tracker check-storage \
  --data-root /var/lib/workout-tracker
# Continue only after the check succeeds.
docker compose up -d --no-build
docker compose ps
docker compose exec -T web python -c \
  'import urllib.request; print(urllib.request.urlopen("http://127.0.0.1:8000/health/ready",timeout=10).read().decode())'
```

`--ff-only` refuses diverged local history. Do not force-reset local work.
Keep the old image/release available until verification completes. If the new
release's compatibility check fails, leave both services stopped and follow its
explicit upgrade instructions; never initialize replacement storage.

**Only when an approved release actually requires a schema upgrade**, run its
specified candidate-only migration with writers and external SQLite tools stopped.
For this release, an older supported schema 1/2/3/4/5/6/7 needs the following explicit
upgrade to **8**; an already compatible schema 8 needs **no migration**:

```sh
docker compose stop
docker compose run --rm --no-deps web python -m workout_tracker migrate-storage \
  --data-root /var/lib/workout-tracker --confirm-upgrade --target-version 8
docker compose run --rm --no-deps web python -m workout_tracker check-storage \
  --data-root /var/lib/workout-tracker
# Only after both commands succeed:
docker compose up -d --no-build
```

Original database files and old selection manifests are retained for recovery;
never remove them as routine cleanup. Selecting an older version later will not
merge newer workouts automatically. Never delete persistent storage, reinitialize
an installed database, remove persistent volumes, or restore automatically during
an update. See [database safeguards](#storage-and-explicit-migration-safety) for
failure/rollback details.

### 10. Troubleshooting

Run commands in `/opt/workout-tracker`; keep private `.env`, keys and full
configuration output out of public support messages. Inspect failures before
changing anything. No troubleshooting step below deletes data or disables checks.

| Symptom | Safe checks and next step |
| --- | --- |
| Docker or Compose missing | Run `docker --version`, `docker compose version`, `docker buildx version`. Install the official distribution-compatible Engine/buildx/plugin packages linked above. Host Python does not replace Docker. |
| Docker permission denied | Run `id`, `docker info`; correct trusted administrator access to Docker and log in again. Do not `chmod 666` the socket or storage. |
| Missing bind source / storage not initialized | Check `test -d /opt/workout-tracker-data/storage` and `.env`'s host path. On a genuinely new install, follow steps 4–5 exactly. If previously installed storage disappeared, stop and investigate the mount/disk; never initialize an empty substitute. |
| UID/GID mismatch / key permissions | Run `id` and the step-5 in-container ownership command. `.env` IDs must match private storage ownership; key mode must be 0600. Stop both services before deliberately correcting ownership of the **identified existing** tree. Do not use blanket world permissions, create a new key casually, or change owners of unrelated directories. |
| Explicit migration required | `docker compose stop`, then use `compose run --rm --no-deps web ... check-storage` as in step 9. Current full functionality needs schema 8. Only run the release's confirmed candidate migration; never `init-storage` on installed data. |
| Invalid/wrong timezone | Check the IANA spelling in `.env`, use `docker compose logs --tail 100 web`, correct it and recreate containers. Set the backup schedule timezone separately in Settings. |
| Port already in use | Use optional `ss -ltn` to inspect listeners; change `WORKOUT_PORT` to a free port and recreate containers. Adjust your browser URL/firewall. Do not stop an unrelated service without identifying it. |
| Works on server, not phone | Loopback is expected by default. Follow step 7, verify the actual private interface IP, trusted hosts, same trusted Wi-Fi, port, VM/host firewalls and router isolation. `docker compose ps` shows the published address. Never fix this by publicly exposing it. |
| Untrusted Host / HTTP 400 | Add the exact browser hostname/IP to `WORKOUT_TRUSTED_HOSTS` with no scheme/port/spaces, retain localhost entries, then `docker compose up -d --no-build --force-recreate`. |
| Web unhealthy / not running | `docker compose ps -a`, `docker compose logs --tail 100 web`, and the in-container readiness command in step 6. If web exited, use one-off `check-storage` with services stopped. Missing/corrupt/unsupported storage is deliberately refused, not repaired at boot. |
| Scheduler absent/restarting | `docker compose ps -a scheduler`, `docker compose logs --tail 100 scheduler`; start both with `docker compose up -d --no-build`. Inspect Scheduler events in Settings → Administration → Logs. It has no web page/health endpoint and needs the same writable data mount/IDs. |
| No automatic backups | They are disabled until configured in Settings. Check enabled/frequency/time/zone, next UTC time, last attempted/result, and scheduler status. After a missed run it attempts once, skips the backlog and does not retry a failed slot repeatedly. |
| Backup/restore verification failure | Inspect Settings backup/restore audit and safe Logs details. Stop writers for inspection; retain original databases, backup, failed candidates and metadata. Do not bypass validation, edit schema markers or delete evidence. Use the [recovery procedure](#backups-restore-scheduling-and-logs) below; older-schema/foreign/missing storage requires deliberate operator review. |
| Build TLS or disk error | Verify the host CA file and approved proxy settings; use the correct `WORKOUT_BUILD_CA_BUNDLE`. Check `df -h` for space. Never turn off certificate verification or automatically delete retained data/backups to free space. |

### What was verified

The disposable installation verification record is in
[INSTALLATION_REVIEW.md](INSTALLATION_REVIEW.md). It distinguishes exercised
container/CLI/Compose commands from untested host provisioning, reboot, firewall,
phone and architecture scenarios. No real Proxmox deployment or household
storage was used. The architecture, development workflow and database safety
reference continue below.

---

## Project status and implementation reference

Phase 11 is implemented and verified. Current release: **application 0.11.0 / schema 8**.
Latest verification: **476 passed, 0 failed, 0 skipped** (402 backend/script, 57 Chromium, 17 Docker).
See [PHASE_11_REVIEW.md](PHASE_11_REVIEW.md).
Previous release verification: **439 passed, 0 failed, 0 skipped** (375 backend/script, 51 Chromium, 13 Docker).
Previous verification: **416 passed, 0 failed, 0 skipped**.
Previous progress/CSV verification is recorded in [PROGRESS_CSV_REVIEW.md](PROGRESS_CSV_REVIEW.md).
Previous patch verification: **406 passed, 0 failed, 0 skipped**.
Previous Phase 10 verification: **384 passed, 0 failed, 0 skipped**.
Routine-order patch 0.10.1 verification is in [PATCH_0_10_1_REVIEW.md](PATCH_0_10_1_REVIEW.md);
menu patch 0.10.2 verification is in [MENU_POSITION_REVIEW.md](MENU_POSITION_REVIEW.md).
The header/date patch 0.10.3 is recorded in [HEADER_ROUTINE_DATES_REVIEW.md](HEADER_ROUTINE_DATES_REVIEW.md).
Phase 10 results and known limits are recorded in
[PHASE_10_REVIEW.md](PHASE_10_REVIEW.md). Existing Phase 1–9 functionality remains;
Phase 10 adds form-preserving historical errors, structured optional time,
Progress range controls/tooltips and independent live update output. No accounts,
passwords or HTTPS. The application stays **http://10.0.69.9:8000**; independent
read-only progress stays **http://10.0.69.9:8001/status**.

Read [deployment/README.md](deployment/README.md#phase-10-existing-installation-upgrade)
for exact existing-installation commands and the required one-time host-service
upgrade for live console output. V4 remains supported. Initial host setup needs
Python/venv/systemd, separately from the core Docker-only install. Schema 7 does
not require migration. No real database/server operation is performed in development.
The user explicitly authorizes verified direct main merge, with **no PR attempt**.

Read [PHASE_6_UX_REVIEW.md](PHASE_6_UX_REVIEW.md) for the current redesign,
screenshots, tests and existing-installation update steps. Read [AGENTS.md](AGENTS.md), [PROJECT_SPEC.md](PROJECT_SPEC.md), and
[MEASUREMENT_DESIGN.md](MEASUREMENT_DESIGN.md). Earlier recovery implementation evidence
and limitations are in [PHASE_5_REVIEW.md](PHASE_5_REVIEW.md).
[PHASE_4_REVIEW.md](PHASE_4_REVIEW.md) retains the approved history/correction record.
[PHASE_3_REVIEW.md](PHASE_3_REVIEW.md) retains the prior implementation evidence.
[PHASE_2_REVIEW.md](PHASE_2_REVIEW.md) and the earlier
[PHASE_1_REVIEW.md](PHASE_1_REVIEW.md) are retained as historical records.

## Architecture and data flow

- `workout_tracker/__init__.py`: Flask factory, configuration, readiness, safe errors and browser protections.
- `storage.py`: external-path validation, explicit first install, schema verification and per-transaction locking. Every database connection enables foreign keys.
- `schema.py`: exact schema-2 definitions; no performance tables.
- `workout_schema.py`: schema-3 session/entry snapshots, one-draft index and immutable-finalized-record triggers.
- `operations.py`, `maintenance.py`: private external settings/history and verified backup/restore candidates; schema upgrades remain in the separate migrator.
- `scheduler.py`: dedicated background CLI process, independent of Gunicorn/browser.
- `diagnostics.py`, `settings_views.py`: protected structured logs, safe paginated viewer and confirmed maintenance forms.
- `library_schema.py`: schema-5 global references and candidate-only table rebuilds, preserving every original cell and trigger.
- `history_schema.py`: additive schema-4 history, preparations, registry and append-only audit objects; no Phase 3 protection is removed.
- `history.py`, `history_views.py`: shared effective values, chronology/filters, chart preparation, historical completion and deliberate corrections.
- `migrations.py`, `combined_schema.py`: explicit candidate-only upgrades through schema 8, preserving every original row/NULL and verifying registry consistency.
- `workouts.py`, `workout_views.py`, `static/workout.js`: exact measurements, server drafts, serialized autosave, revision conflicts and atomic finalization.
- `catalog.py`: parameterized SQL and rules for people, identities, ordering, typed targets, and independent copies.
- `views.py`: CSRF-protected forms, ownership checks and stale-routine conflict detection.
- `__main__.py`: operator initialization, verification and migration commands.
- `templates/` and `static/`: server-rendered HTML, local responsive CSS, native segmented radios, and browser-local Auto/Light/Dark themes. No CDN or analytics.
- `tests/`: temporary fixtures only; never point tests at household storage.

Browser → Flask CSRF/ownership validation → catalog service → locked SQLite
transaction → redirect to refreshed page. A failed operation rolls back as a
whole. User selection is instant navigation, **not authentication**: anyone who
can reach this passwordless household app can choose another person.

## Local development with disposable storage

Requires Linux, Python 3.12+, local POSIX storage supporting SQLite, flock, hard
links and directory syncing, and SQLite 3.37+ for STRICT tables. Dependencies and
the Docker base-image digest are pinned. Phase 4 adds no third-party dependencies or external chart resources; timezone handling uses Python zoneinfo.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q tests/test_foundation.py tests/test_migrations.py tests/test_catalog.py tests/test_management.py tests/test_workouts.py tests/test_workout_http.py tests/test_history.py tests/test_history_http.py
```

For a **disposable local review**, explicitly create a new, nonexistent external
path. Initialization refuses every existing directory, including empty ones.
It creates schema 1 first; a separate explicit command copies/upgrades it.

```sh
export WORKOUT_DATA_ROOT="$(mktemp -d)/review-storage"
.venv/bin/python -m workout_tracker init-storage --data-root "$WORKOUT_DATA_ROOT" --confirm-new-storage
.venv/bin/python -m workout_tracker check-storage --data-root "$WORKOUT_DATA_ROOT"
.venv/bin/python -m workout_tracker migrate-storage --data-root "$WORKOUT_DATA_ROOT" --confirm-upgrade --target-version 8
.venv/bin/python -m workout_tracker check-storage --data-root "$WORKOUT_DATA_ROOT"
.venv/bin/gunicorn --bind 127.0.0.1:8000 --workers 1 --threads 2 'workout_tracker:create_app()'
```

These commands are for synthetic review data only, not deployment permission.
Stop the server with Ctrl+C. The readiness endpoint is `/health/ready`; verify
`status: ready`, app version `0.11.0`, and schema version `8`. Schema 1 still opens
the foundation shell; schema 2 supports existing management but not workout
recording. Schema 3 supports tracking but history/corrections need an explicit
target-4 upgrade. Startup never migrates these automatically. Stop workers before
explicit upgrade, then restart them to reload configuration/signing keys.
Missing/damaged/incompatible storage is an error, never permission to initialize
another database or replace an existing one.

## Phase 6 navigation and appearance

Open app → choose a person → choose a routine → Start workout. Existing people
precede Add person; their hamburger menus separate selection from management.
Routine cards start workouts directly; Edit routine and Manage routines remain
secondary. The compact header/selected-page pills replace crowded text links.

Active workouts have no unrestricted person-switch control. More contains jump,
overview, date/time/notes, **Exit Workout**, and confirmed Discard. Exit validates
and saves current input before returning to routines, preserving the draft for
Resume later. Finish/Discard also allow switching afterward. A per-tab marker
assists Back/reload navigation without locking other browser sessions; this is
workflow assistance, not authentication. Native unload warnings explain the risk
of leaving unacknowledged input; no offline/hard-close persistence is claimed.

Appearance now lives **only in Settings**. Auto/Light/Dark changes immediately and
persists for that browser. Choose **Person appearance** from a person’s menu (or
Settings while that person is selected) to save Blue, Teal, Green, Purple, Orange
or Red across devices. Dark backgrounds are neutral charcoal/navy; accents color
primary controls and progress. Person colors live in private external
`config/person-preferences.json`, default blue when absent. No SQLite schema or
migration change is required. Database backups do not include this file; protect
the whole external tree separately. A corrupted preference file is preserved;
read-only pages fall back to blue and writes report an error.

The repeated visible AI banner is removed from pages; mandatory disclosures remain
in this README, all developer notes and every supported source-file header.
Browser review images are in [docs/phase-6](docs/phase-6). Tests save screenshots
under `/tmp/workout-ux-screenshots` by default; set `WORKOUT_UX_SCREENSHOTS` to an
absolute artifact directory when collecting review evidence. This variable does
not affect production containers.

## People, exercise names, and routines

Keep the approved user-switching interface: create/select people through the
People screen, without a redesigned selector or browser-style tabs; rename, archive or reactivate them there.
Archiving always retains their IDs and records. Each person has independent
routines and workout histories. Exercise definitions are shared globally on schemas 5–6.
On schema 6, confirmed routine deletion permanently removes its definition/settings
while retaining completed snapshots and global exercises. Active drafts block deletion.
Retained schemas 2–5 use their earlier archive behavior.

Within a routine, register a new global exercise or select an existing library ID.
Exercise Library renames definitions across everyone’s current routines, preserving
historical snapshot names. Copies reuse the original IDs but keep independent
targets/notes/order. On schema 6, the separate confirmed Permanently Delete Exercise
action erases that identity and its history across everyone; Remove From Routine
affects only that routine. Older schema-5 archive rules remain unchanged. Legacy
same-name definitions retain distinct IDs; new case-insensitive duplicate names
are rejected rather than merged. Existing archives can be permanently removed
on schema 6, but there is no exercise unarchive interface.

Choose Weight or Time in the segmented control. Both use positive-integer sets.
Weight configures reps and defaults to pounds; Time configures whole minutes and
seconds. Three sets × 45 seconds stores a target of 45 seconds, not 135. Switching
mode clears incompatible stored fields. Optional notes belong to the routine
configuration. Numeric inputs provide the approved simple set controls.

Configuration limits: sets 1–1000, reps 1–10000, target duration 1–359999 seconds
(normalized total; seconds may exceed 59); names 100 characters, notes 2000 and weight
meaning 200. These are configuration bounds. Schema 3 adds separate actual
measurement/flag columns without altering retained schema-2 files.

Phase 3 stores pounds as **integer tenths**, truncate additional decimal
digits **without rounding**, and display one decimal place: 40.99 → 40.9
(stored 409), 42.56 → 42.5 (425), 40 → 40.0 (400). Explicit zero is valid
(stored 0); empty weight is SQL NULL. Actual time is one duration per exercise
regardless of set count, stored as integer seconds with minimum 1; zero is
invalid and empty is SQL NULL. Every skipped exercise retains a saved entry
with NULL measurements, never zero or prior results. Historical snapshots
preserve tracking type and measurements even after routine edits. For performed
durations either part may be blank and seconds may exceed 59: blank+120 → 02:00,
1+90 → 02:30, 2+blank → 02:00. Two blanks skip; negative, fractional, malformed
and zero-total performed durations are rejected. Actual
measurements are bounded by SQLite signed 64-bit integers; input strings are
limited to 100 characters. Previous values never prefill a new workout.

Use the routine's up/down controls to reorder routines or exercises. Duplicate
within a person or use Copy a routine to copy between people. Every copy gets
fresh routine/item identities and reuses global exercise IDs and independent settings, with no workout
history, results or increase state. Routine edit forms reject stale submissions
with 409; reload before retrying if another page has changed the routine.

## Start, save, resume, finish, and discard

Choose a person through People, open their routine, and choose Start workout.
An empty routine must first get exercises. Starting copies every configuration
into a separate snapshot with blank actual values and records the local date,
UTC timestamp and configured IANA zone. Only one active draft is allowed per
person; another start offers Resume or explicit Discard, never replacement.
Routine editing/removal cannot change this draft or a completed snapshot.

One exercise appears at a time with target sets/reps or duration, optional notes,
previous comparable performance and increase recommendation. If the previous
session skipped it, the last performed result is shown separately. Comparisons
require the same person, permanent exercise identity, measurement type and
unit/weight meaning. Drafts/discarded workouts are excluded from comparisons.

Enter one measurement per exercise, independent of sets. Back/Next, the jump
selector and expandable overview (inside More) navigate without marking blank entries done.
Progress tracks the furthest acknowledged Next destination, including skipped exercises.
Typing/autosaving measurements or flags does not move it; Back/Jump do not add
progress, and revisits cannot count twice. Actual performed counts remain separate. Save draft
is available manually. With JavaScript, input automatically saves after a short
debounce. The compact ✓ Saved indicator, progress and overview change only on a valid
post-commit acknowledgment. Values typed during a pending save are preserved and
sent next; saved weights are normalized to one decimal place.

Navigation and Finish wait for pending saves. Validation/network errors leave
input visible and preserve earlier committed values. A stale tab receives a
conflict and cannot overwrite newer data; copy any unsaved text before reloading.
An acknowledgment can be lost after the server committed: reload to inspect the
persisted result rather than assuming a failed response means no commit.
Server-confirmed drafts survive refresh, browser closure and application/container
restart. Closing/force-killing a browser before acknowledgment cannot guarantee
unsaved input persistence; a before-unload warning is provided. There is no
offline client queue. Without JavaScript, use Save draft before navigating;
autosave, jump interaction and the acknowledgment-gated discard UI require JS.

Finish & Save validates current input again and commits the whole snapshot and
completion status atomically. Skips keep their rows with SQL NULL values. An
entirely skipped workout needs the additional confirmation checkbox. Repeated
Finish requests return the same saved session without duplicate completion.
The completion page shows this single saved workout; it is not a history browser.

Discard Workout opens “Are you sure?” with an explicit warning and acknowledgment
checkbox. OK stays disabled until checked. Cancel/Escape preserve the draft.
Confirmed discard changes only that unfinished session's status, retains its
snapshot, and never deletes completed history. Completed/discarded snapshots are
immutable as original records. Schema-4 correction workflows append effective
actual/date/time revisions rather than updating these snapshots.

## History, progress and historical entry

The hamburger menu opens History & Progress, with History | Progress tabs only
inside that area; both retain the person and original URLs. People menus also
provide direct history access. History lists completed native and historical sessions by
actual effective workout date/time, newest first. Active/discarded drafts are
excluded. Filter by inclusive date range, original routine identity or permanent
exercise identity. Saved detail shows every original prescription in original
order, notes, actual values, skips and increase flags. Renaming/archiving/removing
routine definitions does not change history or remove its filter choices.

Progress charts are locally rendered SVG with accessible data lists and no CDN,
third-party services or new dependencies. Each permanent exercise/type/unit/
weight-meaning combination gets its own series, so pounds never mix with seconds
or incompatible weight meanings. NULL is excluded from numeric plotting; zero
pounds remains a plotted result. Durations are raw seconds labeled minutes:seconds
and never multiplied by sets. Statistics mean highest logged weight/longest
logged duration **within the selected range**. They are not inferred strength or
other performance claims. The expandable data list retains skipped rows.

Enter historical workout from History, choose a routine and its past date and
optional time, then review copied prescriptions and fill measurements before
Save. To recreate a different old prescription, create or duplicate/configure a
separate routine first in the existing routine editor. Preparation freezes its
snapshot, so later routine edits do not change the review form. Historical
completion uses separate tables and a unique preparation token, never a live
draft. Repeated submissions return the same saved workout and do not overwrite
measurements. All-skipped completion needs explicit confirmation. Historical
form measurements are saved atomically on submission, not live-autosaved.

Occurrence is separate from when entered into the system. Unknown time remains
NULL and is labeled Time unknown; no midnight timestamp is invented. Within one
date unknown-time records sort before known-time records, with entry-time/ID
as deterministic tiebreaks. DST gaps are rejected; repeated-hour times require
an earlier/later choice. Future occurrence values are rejected. Backdated entry
and effective date corrections affect charts and previous-performance lookups,
which use occurrence chronology rather than entry/correction time.

## Correcting a saved workout and the audit

Open a saved workout and choose Correct saved workout. Change actual values,
increase flags and/or actual date/optional time, then explicitly acknowledge the
correction. Names, identities, order, tracking type, targets, units/meaning and
notes remain immutable snapshots. The application appends full before/after
actual-value states, occurrence, correction timestamp and sequence; it never
updates the original completed rows or disables the Phase 3 protection triggers.
An all-skipped corrected workout also needs skipped-workout confirmation.

History, chart statistics, saved confirmation and previous-performance reads all
use the latest effective correction. Original saved values and every correction
remain visible in the audit. Two stale forms cannot overwrite each other: a
revision conflict returns 409 and requires reloading. This is a shared-household
audit without authenticated author attribution, consistent with passwordless
People selection. No completed-workout deletion is offered.

## Storage and explicit migration safety

```text
external-storage/
  data/schema-1-<identity>.sqlite3              # unchanged original
  data/schema-2-<identity>-<candidate>.sqlite3  # retained Phase 2 original
  data/schema-3-<identity>-<candidate>.sqlite3  # retained original workout schema
  data/schema-4-<identity>-<candidate>.sqlite3  # retained pre-library schema
  data/schema-5-<identity>-<candidate>.sqlite3  # retained shared-library schema
  data/schema-6-<identity>-<candidate>.sqlite3  # retained deletion-capable original
  data/schema-7-<identity>-<candidate>.sqlite3  # retained global defaults schema
  data/schema-8-<identity>-<candidate>.sqlite3  # current combined measurement schema
  config/active.json                          # active database selection
  config/session.key                         # private session signing material
  archives/selection-before-<candidate>.json   # original selection
  backups/<UTC-timestamp>-<id>.sqlite3         # verified copies and retained failed evidence
  config/operations.json                     # settings, backup history, restore attempts
  logs/events-YYYY-MM-DD.jsonl                # protected structured UTC logs
```

The CLI takes the same persistent-root lock used by all app connections. It
refuses maintenance while a request holds a connection; stop workers and all
external SQLite tools before migration. External tools do not follow our lock
protocol. Known schema 1/2/3/4/5/6/7 can explicitly upgrade to 8; targets 2/3/4/5/6 remain
available for compatible tooling. Select `--target-version 8` for the current release.
The CLI keeps its target-3 default for backward compatibility; its programmatic
helper keeps the existing target-2 default for backward-compatible callers.

Migration opens the original read-only and creates a distinct candidate using
SQLite's backup API. DDL changes only the candidate. Checks cover application
identity, exact schema, integrity, foreign keys, schema/migration versions,
equality of every pre-existing table row including NULLs, new historical/audit
tables being empty, and original file hashes. The new registry must match exactly
the existing completed native sessions. Exact tables/indexes/triggers and
migration records are verified. Schema 5 changes only exercise FK constraints; all protection triggers are retained identically, and all original cell values remain unchanged.
The candidate and selection files are synced before atomic manifest replacement.
A post-switch sync failure attempts atomic restoration of the original selection;
if that also fails, the CLI reports uncertainty and requires inspection. No
original database is overwritten or removed. Previous versions stay in `data/`
and their selection manifests in `archives/`; failed candidates stay for diagnosis.

All eight supported schemas use rollback journals. WAL headers and any journal/WAL/SHM
sidecars are refused **before** SQLite opens a source; there is no implicit
recovery. Unknown, damaged, missing, symlinked or incompatible storage never
becomes an empty replacement. A migration request matching the selected schema version is a
read-only no-op. Ordinary compatible application updates just replace code/image
and never trigger a copy, migration, or backup.

Keep the generated `config/session.key` private (0600); explicit migration
provisions it and startup only reads it. It signs CSRF session cookies, not user
passwords. Losing it blocks normal configured startup rather than silently
replacing it. An operator may supply private `WORKOUT_SECRET_KEY` explicitly
instead; never commit key values or use a shared example key. Cookies are
HttpOnly/SameSite=Lax; Secure is not enabled for the current loopback HTTP review.

## Development container checks

Installation variables, security settings and service commands are documented
in the [installation guide](#3-configure-compose) above. The checks below are for
contributors using disposable fixtures, not a second installation procedure.
Containers never initialize or migrate storage at startup.

For isolated image review, build `workout-tracker:phase8-review` with build secret
`pip_ca` set to a trusted system CA bundle. Managed cloud proxy/CA configuration
must be preserved. Run container tests only against the local Docker daemon:

```sh
docker build --secret id=pip_ca,src=/etc/ssl/certs/ca-certificates.crt -t workout-tracker:phase8-review .
WORKOUT_CONTAINER_TESTS=1 .venv/bin/python -m pytest -q
```

They use disposable fixtures, no network or published ports, and remove their
own containers. Browser tests need Chromium and optional pinned dependencies:

```sh
.venv/bin/python -m pip install -r requirements-browser.txt
.venv/bin/python -m pytest -q -k browser
```

Install Chromium or use `.venv/bin/python -m playwright install chromium`. Set
`WORKOUT_CHROMIUM` to its executable if needed. Browser tests need loopback socket
access. Without optional tools, their skipped status is distinct from a pass.

## Backups, restore, scheduling and logs

Open **Settings → Administration** from the hamburger menu. Database status, Backup Now, scheduling,
backup history/details, restore audit and Logs are available without changing
People-screen switching. The history links retain all prior functionality.

**Backup Now** makes a uniquely named SQLite backup-API copy in external
`backups/`, verifies integrity, foreign keys, application/storage identity, exact
schema, complete snapshot/order/registry/audit consistency, and every original
row/NULL/zero before showing Verified. Size, source, schema, SHA-256 and timestamps
are recorded in private `config/operations.json`. It never downloads a file.
The button waits for completion; retrying the same form reuses its operation ID.
A new form is a new intentional backup. Failed/interrupted attempts stay visible
and their files remain unverified evidence. No backups are rotated automatically.
Inspect a backup to deliberately delete its file with checkbox confirmation;
its metadata remains in history. These are SQLite data backups, not bundles of
signing keys, schedule settings or diagnostic files: protect the whole external
tree separately with host/offsite backups.

**Automatic backups are disabled by default.** Settings requires an explicit
enable, whole-day frequency (1–3650, default 1), HH:MM time (default 02:00), IANA
zone (default Etc/UTC) and log retention (1–36500 days, default 30). The schedule
zone is independent of workout-entry zone: choose it explicitly. Changes take
effect on the next 30-second scheduler check and schedule the next future slot.
Day cadence is anchored to the local configuration date, not 24-hour intervals.
Repeated times run at the earlier occurrence only; skipped times advance to the
first valid minute after the gap. A late restart handles at most one missed run,
then advances beyond the current time without replaying the backlog. Failures
are recorded, not immediately retried; the next scheduled slot can try again.
Settings shows last automatic attempt/success/result and next UTC scheduled time.

Compose now defines separate **web** and **scheduler** services using the same
image, external bind mount and UID/GID. The scheduler runs
`python -m workout_tracker scheduler`, with no ports or network and restart policy
`unless-stopped`; Gunicorn workers never start schedulers. Persisted claims and
the root-directory OS lock prevent overlapping/duplicate jobs across processes
and restarts. `scheduler --once --data-root /absolute/disposable/storage` performs
one due check for diagnostics. No new environment variables are required: the
scheduler uses `WORKOUT_DATA_ROOT`; `WORKOUT_UID/GID`, CA build secret and web
variables above remain in effect. No services have been deployed by this task. The image sets a 300-second web
worker timeout for synchronous maintenance; exceptionally large operations can
still exceed it and need operator inspection after an interruption.

**Restore Backup** requires a checkbox plus typing RESTORE. It warns that later
workouts/corrections are not merged. The service rechecks the selected backup,
requires the same storage identity and exact selected schema (2–8), copies to a
unique candidate, compares all values and audits, syncs it, retains the original
file/selection, then atomically selects the verified candidate. Original and
backup files are never overwritten. Failure before activation keeps the original;
a post-activation sync or result-metadata failure attempts atomic rollback.
If rollback durability also fails, the result is Uncertain: stop writers and
inspect retained files/manifests before doing anything else. Reusing an attempt
ID never runs restore twice. Forms opened before a restore are rejected; reload
other browser tabs before editing. Existing requests serialize with maintenance,
so saves cannot target a partially prepared candidate. Full verification can
pause other requests; this is conservative household maintenance, not zero downtime.

Older-schema backups are not migrated/downgraded by Restore. Keep them for a
separately reviewed offline recovery; never edit their version marker. A missing,
foreign/newer, symlinked or sidecar-bearing active file/manifest is refused.
A present damaged file with a valid selection can be preserved during explicit
recovery. Normal startup still refuses damaged storage and never restores,
initializes, migrates or replaces it automatically.

If a running worker detects corruption, Settings can still show backup history.
If corruption prevents startup, stop **both** web and scheduler and all external
SQLite tools, preserve the whole tree, then use the same explicit recovery service
from an operator shell with the configured storage owner:

```sh
python -m workout_tracker list-backups --data-root /absolute/disposable/storage
python -c 'from uuid import uuid4; print(uuid4().hex)'  # new operation identifier
python -m workout_tracker restore-backup --data-root /absolute/disposable/storage \
  --backup-id LISTED_VERIFIED_ID --operation-id NEW_32_HEX_ID --confirm-restore
python -m workout_tracker check-storage --data-root /absolute/disposable/storage
```

Use only disposable storage for rehearsals. Restart workers/reload forms after
successful verification. If an attempt remains In progress after process loss,
do not replay it: inspect `operations.json`, protected logs, candidate and archived
selection with writers stopped. The scheduler labels interrupted backup attempts
failed on its next cycle; interrupted restores require operator inspection.
No automatic reconciliation guesses which selection an interrupted restore used.
If metadata is damaged, preserve it and seek operator review; it is never replaced
with defaults. A missing signing key still requires explicit operator recovery;
restoring SQLite does not invent a replacement key.

**Logs** are private daily JSONL files under external `logs/`, with structured UTC
time, severity, category and event IDs. The viewer supports newest-first text,
severity/category/date filters, Refresh, 50-entry pages and expandable safe error
details. Private paths/stack frames stay in protected server files; raw form bodies,
keys/cookies/tokens and database values are not logged. Exception messages/locals
are omitted from private traces; fixed safe messages, exception type and bounded
frames provide diagnostics. Log failures warn on stderr and do not undo a workout
commit. Ordinary startup/shutdown and failures append diagnostics, but compatible
updates never copy/migrate/back up the workout database. Abrupt SIGKILL cannot
write a shutdown event. Retention runs on Settings save and scheduler cycles;
only named UTC log files older than the retention window are removed. Disable
backups independently; keep the scheduler running for automatic log cleanup.

Local backups do **not** protect against complete server/storage failure or
replace Proxmox/offsite backups. There is no cloud backup/synchronization,
remote authentication or public exposure in this phase. See
[PHASE_5_REVIEW.md](PHASE_5_REVIEW.md) for validation and remaining limits.


## Application and database versioning

The application uses semantic versions, currently **0.11.0**: major.minor.patch.
After 1.0, breaking public-contract changes increment major, compatible features
increment minor, and compatible fixes increment patch. During 0.x development,
feature releases increment minor and compatible fixes increment patch; any
breaking changes require explicit release notes. SQLite schema is
separate, currently **8**, and increments only when persistent structures change.
A code release does not automatically require a migration. Settings About and
the small document-flow footer read the running application version and verified
active DB schema; /health/ready reports the same source values.

### Existing /root/WorkoutTracker schema-4/5 installations

Use [deployment/README.md](deployment/README.md#first-upgrade-from-schema-6) for
this release's explicit schema-8 upgrade and one-time passwordless host updater
installation. Do not use the historical Phase 7/schema-5 guide as the current
release target. Existing databases, root .env and original versions are preserved.
The app remains HTTP port 8000; read-only updater progress is private LAN port 8001.

### Machine-readable release target for Docker updaters

After building the new image, an updater can detect its release target without
mounting data, starting Flask, or triggering migration:

```sh
docker run --rm --network=none --read-only --entrypoint python \
  workout-tracker:local -m workout_tracker release-info
```

Expected JSON: `{"app_version": "0.11.0", "target_schema_version": 8}`.
The target is release metadata; `/health/ready` and Settings/footer report the
actual active schema instead. Parse JSON rather than scraping templates or the
foundation initialization constant. Stop writers and explicitly back up/verify
installed storage before updating; compare installed schema with this target,
request confirmation if an upgrade is needed, then run the separate migration.
Never infer consent from release detection or automatically initialize storage.
The actual available v3 was inspected; its schema-5 limit is incompatible with
this release. Use v4 and the operator sequence in deployment/README.md. The live
server copy was not accessed.


## Phase 8 — permanent deletion and LAN updates

The dedicated **Permanently Delete Exercise** preview shows the exact global ID,
affected people/routines/entries and requires typed DELETE (or exact name), an
acknowledgment and CSRF. It removes that ID and its recorded history for everyone,
retaining other measurements. Active drafts block deletion. Empty saved/discarded
workouts disappear; mixed workouts keep remaining entries and consistent audits.
A new definition gets a new ID, with no prior results. Older backups/database
versions remain and may restore deleted records on deliberate compatible recovery.

**Permanently Delete Routine** removes current definition/configuration, keeps all
global exercises and completed history, and blocks active drafts. **Remove From
Routine** still removes only one configuration. Older schema-5 archives remain
readable; full hard-delete behavior requires schema 6. Previously archived entries
are available for deliberate cleanup after upgrade. No deletion requires login.

The selected person/accent stays in a compact sticky header across management,
history/charts and Settings. Workouts also show the original routine name while
retaining existing save/exit/switch safeguards.

Settings → **Application Updates** checks fixed approved main, reviews version,
schema and notes, then confirms installation/migration. A separate host service
owns Docker/Git; the web container has no Docker socket. Control is a restricted
Unix socket with fixed actions and OS peer checks; independent progress is GET-
only HTTP bound to the configured private interface. There is no password/TLS
infrastructure. Network isolation and trusted-host/CSRF controls remain essential.

The executable [v4 updater](deployment/update_workout_tracker_v4.sh) shares the
same host engine for emergency SSH use. It always verifies a backup for a confirmed
update, preserves old image/commit/database, uses the existing candidate migration,
privately recopies the authoritative parent .env into app/.env, and validates real
health/versions/scheduler. It never initializes or silently restores storage.
Exact **schema-5→6 and one-time host installation** commands are in
[deployment/README.md](deployment/README.md). Do not use an old schema-5-only v3
script unchanged for this release. No service is installed at application startup.


## Phase 9 defaults, Administration and input rules

Settings contains personal appearance and an Administration entry point. The
compact Administration area groups updates, logs, versions, diagnostics, backup
settings/history and confirmed restore. Every application maintenance route
shares one currently allow-all boundary. Future authentication can be introduced
there after review; no login or unused account system is shipped today. Existing
CSRF, typed confirmations and updater source/command restrictions remain.

The hamburger menu offers Routines, Exercise Library, History & Progress and
Settings. Before choosing a person, scoped destinations return to People. There
are no global top tabs; only History & Progress shows its two tabs. Exercise
deletion and Cancel return to the refreshed Library; a successful committed
deletion shows a brief message. Routine deletion still retains completed history.

Schema 7 adds a separate exercise_defaults table, preserving all old cells,
NULL/zero measurements, snapshots, drafts and corrections. Existing exercises
receive neutral 3 sets × 12 reps, Weight/pounds, empty meaning/notes; no personal
routine is chosen as the global standard. Edit defaults in Library, then Add
library exercise to copy the preset into a routine once. Edit that routine for
independent overrides. Later default edits never propagate to existing routines,
and copied routines retain their actual configurations and global IDs. Pounds
remains the supported weight unit; there is no conversion feature.

The six existing color keys retain their exact soft palettes; six vibrant-* keys
add visibly saturated options. All 12 are independent per person and stored in
the same external preference file. Appearance stays separate from Administration.

Measurement labels are **Weight (lb)**, **Minutes**, **Seconds**. Historical forms
use named exercise groups for accessible context. Duration parts accept whole
nonnegative numbers in either/both fields and normalize to total seconds; targets
retain 359999-second limits, actuals retain the signed-64-bit limit, and two blank
actual fields remain SQL NULL. Saved duration displays use MM:SS; blank weight
and valid zero remain distinguishable and decimal weights still truncate.

Workout clocks use explicit **HH:mm** 24-hour text fields and displays. Internal
seconds/microseconds and IANA zones remain intact, including during measurement-
only corrections. Installation timezone remains America/Indiana/Indianapolis,
not a fixed UTC offset. Diagnostic timestamps may retain seconds in explicit
24-hour UTC; log date filters remain UTC. Original local SVG, ICO, 16/32 PNG and
180 PNG Apple touch icons are served without external requests or new runtime
dependencies. See static/icons/README.md for the original artwork/export details.

## Phase 10 historical entry, Progress and live updates

Historical Phase 10 targeted **0.10.0 / schema 7**. That release needed **no database migration for an existing schema-7 installation**. No exercise
identity or chart calculation changes are made; the separately reported duplicate/
orphaned exercise issue is explicitly untouched.

Historical entry/correction now keeps typed values on the same form after an
error. A red, linked summary appears immediately above Save, with accessible
field messages. Failed submissions save nothing; concurrent corrections show a
conflict and retain input. Existing snapshots, SQL NULL skips, valid zero and
append-only audit records remain protected. Optional workout time has an explicit
24-hour hour/minute picker; type **0930** and leave the field to get **09:30**, or
leave it blank when unknown. No AM/PM or seconds are displayed.

Progress starts with **30 Days** and offers 60/90 Days, 6/12 calendar Months,
All Time and Custom Range. The configured server IANA zone supplies today's date;
days include today and the prior N−1 dates. Months start one day after the clamped
calendar-month anniversary. Exercise/range choices survive History/Progress tabs,
refresh and Back. Invalid custom dates retain input and the last valid graph
where available. Hover, keyboard-focus or tap a graph dot for its date/measurement
and known time. Skipped measurements stay in the accessible data list, never as
zero-valued graph points.

**Install Update** opens the independent progress tab automatically, keeping the
app tab. Confirm installation and any required migration first. If a popup blocker
intervenes, use the displayed fallback link. Check for Updates opens no tab. Review
independent status before retrying a submission during an outage.

The independent host page now has a scrolling **sanitized live console** from real
Git/Docker/backup/verification/startup activity, plus status events. It stays online
while Flask restarts. Scroll up without losing your place, use Scroll to Latest,
refresh/reconnect, or select a retained operation. Only recognized safe messages
are shown: arbitrary command output, environment values, Compose config, secrets,
URLs and private logs are withheld. The newest 500 safe lines per operation and
20 operations are retained; detailed SSH logs and backups are not pruned by this
viewer. It is read-only, not a terminal. The trusted-LAN/no-password model remains.

**Existing Phase 9 host service needs a one-time explicit upgrade for live logs.**
Updating only the web image leaves the old separately copied runtime in place.
See [exact installed-server steps](deployment/README.md#phase-10-existing-installation-upgrade)
and [PHASE_10_REVIEW.md](PHASE_10_REVIEW.md) for implementation, tests and limits.
V4 remains the emergency script; no v5 script, deployment or startup migration is
introduced. Keep your existing Compose/.env and timezone settings.


## Patch 0.10.1 — routine selection order

The selected person's routine cards now show the most recently completed workout
first. Actual workout date is primary; live Finish timestamps and known historical
occurrence times resolve same-day ties. Corrections to occurrence date/time apply.
Equal timestamps and unknown times use alphabetical routine names; routines never
completed appear last, alphabetically. Names are compared without case, with the
exact name and permanent ID as deterministic fallbacks.

Only completed live/historical workouts count. Drafts, discarded workouts and
unfinished historical preparations do not. Each person and routine ID has an
independent history; copies do not inherit completion rank. Deleted/archived routine
definitions do not appear as cards. Card controls/layout and exercise ordering are
unchanged. This is a read-only server listing, not a rewrite of stored positions
or workout dates. Schema stays **7** and requires **no migration** for schema 7.

The existing browser updater/v4 supports this code-only patch. If already using
the Phase 10 host runtime, no additional host-service upgrade is required. Older
hosts still need the previously documented Phase 10 upgrade for live console logs.
See [patch review and tests](PATCH_0_10_1_REVIEW.md).


## Patch 0.10.2 — viewport-safe hamburger menu

The hamburger dropdown stays inside the screen in portrait and landscape. It is
positioned relative to the full sticky header instead of the narrow button. With
a selected person it opens from the header's left edge; without a selection it
retains right alignment. Its width is capped by the header, with iPhone safe-area
insets reserved on both sides. All four navigation links and existing keyboard/
outside-click behavior remain. Person context, accents and themes are unchanged.

This is a CSS-only positioning fix plus the patch-version update. Schema is still
7; no database migration, server configuration or host-updater upgrade is needed
when already using Phase 10. The existing browser updater/v4 can install it. See
[MENU_POSITION_REVIEW.md](MENU_POSITION_REVIEW.md) for the measured cause, viewport
coverage, full-suite results and limits.


## Patch 0.10.3 — rightmost navigation and routine activity dates

The hamburger stays at the far right of one compact sticky header row. Branding
is unchanged; the selected person's accent and name use the remaining space. Long
names truncate with an ellipsis and retain the full name in a title/accessibility
text instead of moving or wrapping the button. Header and dropdown reserve iPhone
safe-area insets; the menu opens to the right below the header with all four links.
Existing keyboard, focus and outside-click behavior is unchanged. Focused active
workouts keep their existing restricted header rather than gaining global navigation.

Routine cards show **Last completed: November 6, 2026**, or **Never completed**, in
a compact muted row below the name/actions. The exact completed-workout record
used by sorting supplies its ISO date and English label. Live and historical dates,
corrections, person ownership, unique routine IDs and independent copies follow the
existing rules. Drafts/discards/unfinished preparations do not count; deleted
definitions stay absent. No new history query or stored completion field is added.
The full-width date row avoids a tall narrow column beside Start Workout.

Application **0.10.3**, schema **7 unchanged**. Use the existing browser updater or
v4; no migration or additional host upgrade is needed on a Phase 10 installation.
[Review and test evidence](HEADER_ROUTINE_DATES_REVIEW.md).


## Patch 0.10.4 — workout navigation and selected CSV export

The workout bar now follows **Next**, not populated measurements. It retains the
furthest Next destination across Back, revisits, refresh and resume, using the
existing saved cursor without migration. Jump changes the viewed exercise, not
the bar; Next from that view sets the following destination as a checkpoint.
Measurement/flag autosaves retain their existing validation and save status.
Resume opens the saved checkpoint; Save draft keeps the current viewed page.
Skipped exercises still save true SQL NULL, and entirely skipped completion still
requires confirmation. JavaScript provides acknowledged Next tracking.

Exercise forms now explain whether settings apply to this routine only or are
Library defaults copied into newly added routine exercises. These notes do not
change the existing independent settings or historical snapshots.

On **Progress**, choose a date preset/custom range, open **CSV export — choose
exercises**, check one or more exercises (or Select All), then **Export CSV**.
The export chooser is independent of the single exercise chart filter. Choices
persist through range changes and validation errors. No selection/no matching
workouts shows a helpful message. Export downloads locally, without cloud services
or changes to application data. The existing browser updater/v4 supports 0.10.4
with schema 7; no migration or new host upgrade is required after Phase 10.

The CSV is a wide paper-style sheet: **Date, Time, Routine, Workout ID**, then two
adjacent columns per selected exercise: **Weight (lb)** + **Sets × Reps**, or
**Duration** + **Sets × Target Duration**. Each row is a completed workout, oldest
first; same-date workouts stay separate. Dates/times and actuals use latest
effective corrections and historical occurrence, not entry time. Sets/reps/duration
targets are snapshots of the prescription, not actual per-set repetition records.
Missing exercises have both cells blank; skipped actuals are blank with their
prescription retained. Valid zero is 0. Decimal weights retain exact tenths; time
values use total **m:ss** (e.g. 0:45, 61:05), never multiplied by sets.

Distinct IDs with matching names have ID-labeled headers. Weight/Time and incompatible
weight meanings stay separate; repeated instances get occurrence-number columns.
UTF-8 BOM, normal CSV quoting and CRLF support Excel/Numbers/Sheets import. Formula-
like text is prefixed with an apostrophe for safety; commas/quotes are escaped.
The first row is always the header, with no decorative rows. See
[PROGRESS_CSV_REVIEW.md](PROGRESS_CSV_REVIEW.md) for detailed tests and limitations.

Selected exercises absent throughout a range still retain blank column pairs, using their historical configurations for headings; no out-of-range data rows are added.


## Phase 11 — combined Weight + Duration (0.11.0 / schema 8)

Choose **Weight + Duration** in Library defaults or routine settings for any
exercise needing both resistance and time (for example a weighted plank or carry).
Configure sets, target duration per set, pounds, optional weight meaning (such as
per hand or total weight), and notes. There is no fixed target-weight field.
Library defaults copy once when added; existing routines remain independent.

One exercise screen records one actual weight and one actual duration, regardless
of set count. Both start blank. Both blank means skipped: both SQL measurements
and the increase flag remain NULL. A performed entry requires both values; a
partial pair shows field errors and cannot be saved or navigated away as Saved.
Zero pounds is valid, duration must be positive, either duration part can be blank,
and seconds above 59 normalize. Weight truncates to integer tenths as before.
Only **Increase weight next time** is offered, entirely manual even below target.
Previous performance shows both actuals and the previous weight recommendation.
The Next-only progress checkpoint and revision-checked autosave remain unchanged.

History, summaries and append-only corrections show both values and preserve
original snapshots/audits. Progress groups two separate local charts under the
exercise heading: pounds and seconds labeled m:ss. Targets come from each snapshot;
a dashed duration reference appears only when the range has one common target.
Varying targets remain in each point tooltip/data row, never one misleading line.
Existing filters, NULL exclusions, zero, person/ID/meaning isolation remain.

CSV keeps the existing first four columns and wide layout. Combined exercises
have three adjacent columns: **Weight (lb), Duration, Sets × Target Duration**.
Durations use total m:ss; prescriptions are historical targets. Skipped actuals
are both blank; absent exercises have all three cells blank. Ordinary Weight/Time
exports, quoting, formula protection and effective corrected values are unchanged.

**Existing schema 7 requires explicit candidate-only upgrade to 8.** Use the
existing browser updater, review 0.11.0/schema 8, confirm migration and Install.
Or use the existing v4 script over SSH; see the exact installed-server commands in
[deployment/README.md#phase-11-schema-7-to-8-upgrade](deployment/README.md#phase-11-schema-7-to-8-upgrade).
No new updater, Compose/.env changes or Phase-11 host-service upgrade is required
for an already working Phase 10 updater. Startup never migrates. Original schema-7
files remain unchanged; schema-7 backups stay retained but cannot restore over
schema 8. Make new verified schema-8 backups after upgrading. Do not initialize or
restore to force an update. See [PHASE_11_REVIEW.md](PHASE_11_REVIEW.md) for migration,
tests, recovery and limitations. Earlier patch sections are historical records.
