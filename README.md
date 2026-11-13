# Workout Tracker

A simple workout log for everyone in your household. Plan routines, record
workouts, look back at exercise history, and follow your progress. Workout Tracker
runs on your private home server and opens in a phone or computer browser.
There are no application accounts or passwords.

**SHAMELESSLY VIBE-CODED 🤖**

This application was built with a healthy dose of AI, questionable amounts of confidence, and minimal human supervision. It appears to work, but don’t mistake that for a warranty. Use at your own risk, and keep backups.

## Installation — Start Here

**New installation only.** If Workout Tracker is already installed, skip to
[Updating the application](#updating-the-application). Never initialize an existing
database again, delete its storage, or overwrite its configuration to update it.

Current application: **1.0.1**. Database schema: **13**. This patch fixes Garmin
connection requests and adds safe HTTP error codes. Existing schema-13 installations
need no migration; saved connections and weight history remain intact. Existing schema-12
installations need an explicitly confirmed migration to a **separate database
candidate**. The original is preserved. Your Phase 12 host updater needs no
additional refresh. See [updating](#updating-the-application); never initialize
an existing installation again. Older unclassified installations must first complete the
[Weight Basis prerequisite](docs/UPGRADING.md#older-unclassified-installations).

### 1. Choose a server

Use a small Linux computer, home server, or Linux virtual machine that stays on
when you want to record workouts. A maintained Debian or Ubuntu installation is
a practical choice. Plan for 1 CPU core, 1–2 GB RAM, and at least 5 GB free disk
space **plus growing workout history, backups, and update images**. These are
planning suggestions, not measured minimums.

Your server and phone should use the same trusted home network. Do not forward
Workout Tracker's ports to the internet. Anyone who can reach it can select people
and change their data; person selection is not a login.

Tests use Linux x86-64, disposable Docker containers and Chromium. We have not
tested a clean physical server installation, ARM/Raspberry Pi, server reboot,
your firewall, or a physical iPhone/Safari. See [actual release testing and limits](RELEASE_1_0_0_TEST_REPORT.md).

### 2. Connect to the server and install the required software

Open Terminal on your computer (PowerShell also works for SSH), then run:

```sh
ssh YOUR_LINUX_USER@SERVER_IP
```

Replace `YOUR_LINUX_USER` with your **Linux** username and `SERVER_IP` with the
server's home-network address, for example `192.168.1.100`. These are server
credentials, not Workout Tracker accounts. If you are already at the server's
keyboard, use its terminal instead. Get an administrator shell:

```sh
sudo -i
```

The following installation commands run **on the server in that administrator
shell**, not on your phone or everyday computer. They use `/root/WorkoutTracker`,
the same layout supported by the browser updater. Application containers run as
the separate non-root numeric user `10001`, not as root.

Install Docker Engine, its Compose plugin and buildx using Docker's official
instructions for your distribution:

- [Debian installation](https://docs.docker.com/engine/install/debian/)
- [Ubuntu installation](https://docs.docker.com/engine/install/ubuntu/)

Follow the distribution's **apt repository** installation section, then return
here. Do not mix Debian and Ubuntu commands. Install Git and check Docker:

```sh
apt-get update
apt-get install --yes git ca-certificates
docker --version
docker compose version
docker buildx version
docker info
```

Docker runs the application, Python and SQLite for you. Host Python/venv is
needed only for the separate browser updater described later. If any check fails,
stop and fix it before continuing; never make the Docker socket world-writable.

### 3. Download the application

This block refuses an existing installation. It creates a place for replaceable
application code (`app`) and a separate place for durable workout data (`data`).
The database itself does not exist yet.

```sh
(
  set -eu
  test "$(id -u)" = 0
  if [ -e /root/WorkoutTracker ] || [ -L /root/WorkoutTracker ]; then
    echo 'Installation already exists. Stop and use the update instructions.' >&2
    exit 1
  fi
  install -d -m 0755 /root/WorkoutTracker
  git clone --branch main https://github.com/natpev/Workout-Tracker-vibe-webapp.git /root/WorkoutTracker/app
  install -d -m 0700 -o 10001 -g 10001 /root/WorkoutTracker/data
)
```

If the repository asks for access, use your normal GitHub authentication for Git.
Never paste a token into these commands, the application, or a public support
message. After a failed download, inspect the existing directory before retrying.

### 4. Choose your address and time zone

Create the settings file below **once**. `set -C` prevents overwriting an existing
file. Replace **both** occurrences of `192.168.1.100` with your server's actual
private address. Keep the same address reserved in your router when possible.

`America/Indiana/Indianapolis` is an example IANA time zone. Replace it with your
own, such as `Europe/London`; do not use a fixed UTC offset or an abbreviation.

```sh
(
  set -eu
  umask 077
  set -C
  cat > /root/WorkoutTracker/.env <<'CONFIG'
# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
WORKOUT_DATA_ROOT=/root/WorkoutTracker/data/storage
WORKOUT_PORT=8000
WORKOUT_BIND_ADDRESS=192.168.1.100
WORKOUT_UID=10001
WORKOUT_GID=10001
WORKOUT_TIMEZONE=America/Indiana/Indianapolis
WORKOUT_TRUSTED_HOSTS=localhost,127.0.0.1,[::1],192.168.1.100
WORKOUT_BUILD_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
WORKOUT_SCHEDULER_NETWORK_MODE=none
CONFIG
)
```

The app is available only on the chosen address. Keep localhost entries for
container health checks. Trusted hosts contain no scheme or port. Leave
`WORKOUT_SECRET_KEY` unset: explicit initialization/migration provisions a private
signing file. The application never invents a replacement if that file is lost.

Run all remaining Docker commands from the application directory. The explicit
`--env-file ../.env` reads the settings you just created:

```sh
cd /root/WorkoutTracker/app
docker compose --env-file ../.env config --quiet
docker compose --env-file ../.env build
```

The first build needs internet access to download dependencies. Certificate
errors require a correct trusted CA bundle/proxy, not disabled verification.

### 5. Create a brand-new database

**Do not run this step on an existing installation.** The initialization command
refuses any existing destination, including an empty directory. It mounts only
the already-created data parent, then creates its new `storage` child.

```sh
cd /root/WorkoutTracker/app
docker run --rm --network=none --read-only --tmpfs /tmp \
  --cap-drop=ALL --security-opt=no-new-privileges:true \
  --user 10001:10001 \
  --mount type=bind,src=/root/WorkoutTracker/data,dst=/bootstrap \
  --entrypoint python workout-tracker:local \
  -m workout_tracker init-storage --data-root /bootstrap/storage --confirm-new-storage

docker compose --env-file ../.env run --rm --no-deps web \
  python -m workout_tracker migrate-storage --data-root /var/lib/workout-tracker \
  --confirm-upgrade --target-version 13

docker compose --env-file ../.env run --rm --no-deps web \
  python -m workout_tracker check-storage --data-root /var/lib/workout-tracker
```

Initialization starts with the foundation schema. The second command creates
and verifies a separate schema-13 database, preserving the original. The final
command should report **Storage verified; schema version 13.** Stop at any error;
never delete storage or initialize again to make an error disappear.

### 6. Start Workout Tracker

```sh
cd /root/WorkoutTracker/app
docker compose --env-file ../.env up -d --no-build
docker compose --env-file ../.env ps
```

Two services should run: **web** serves the application; **scheduler** handles
configured backups, log retention and optional Garmin synchronization without an open browser. Web should become
**healthy** after a health check. Scheduler has no separate HTTP health endpoint.
Verify the actual application inside the container:

```sh
docker compose --env-file ../.env exec -T web python -c \
  'import json,urllib.request; r=json.load(urllib.request.urlopen("http://127.0.0.1:8000/health/ready",timeout=10)); print(r); assert r==dict(status="ready",app_version="1.0.1",schema_version=13)'
```

If startup is still in progress, retry after a few seconds. Both containers use
`restart: unless-stopped`. On a standard systemd-based server, enable Docker at
boot with `systemctl enable --now docker`. A deliberately stopped container stays
stopped until you run `up -d` again. Reboot behavior on your server needs checking.

### 7. Open it on your phone or computer

In a browser on the same trusted home network, open **http://192.168.1.100:8000**,
substituting your server address. Do not use `localhost` on your phone: that means
the phone itself. The People screen should appear. Settings/About and the footer
should report **1.0.1 / database 13**. Check all three themes in Settings.

Your router, server and any VM firewall must allow TCP 8000 from trusted LAN
devices only. Docker publishing can bypass ordinary UFW rules; use Docker-aware
firewall rules. Do not publish on a public address, forward router ports, or
disable firewalls to solve connection problems. See [network details](deployment/README.md).

### 8. Configure backups before using real data

Use a disposable test person/routine to check recording, history, and CSV first.
Then open **Settings → Administration**:

1. Choose **Backup Now**, then inspect its **Verified** result.
2. Enable automatic backups only when ready. Choose frequency, time and the
   backup IANA time zone, then save. They start disabled.
3. Confirm the next run and later inspect its successful result.
4. Keep the whole `/root/WorkoutTracker/data/storage` tree and private `.env`
   protected with a separate machine/offsite backup too.

Database backups stay on the server, are not automatically deleted, and do not
include external settings or signing keys. Same-server backups do not protect
against losing the server/disk. Rehearse Restore only with disposable data,
never over real workouts just to test it.

## Features

- Separate routines and histories for everyone in the household, without accounts.
- Shared exercises, custom illustrations and flexible weight/reps/duration tracking.
- Independent set results, explicit skips, autosaved drafts and historical corrections.
- Progress charts, lifting estimates, training consistency and PDF/CSV reports.
- Local body-weight history with optional per-person Garmin synchronization.
- Verified backups, safe updates and consistent database downloads.

## Using Workout Tracker

Choose a person, choose a routine, and press **Start workout**. If there is no
body-weight measurement for today, an optional weigh-in screen appears. Continue
with a weight or Skip; skipping saves no body-weight record and does not ask again
for that workout. Garmin availability never blocks starting a workout.

Record one exercise per screen. There is **one weight for the whole exercise**.
Each set has its own repetitions, duration and status, depending on its enabled
measurements. Targets are references, never prefilled actual results.

- **Incomplete**: not yet recorded; partial inputs remain resumable.
- **Completed**: explicitly valid values for every enabled measurement.
- **Skipped**: explicitly chosen; that set's measurements remain NULL, not zero.

An entirely skipped exercise has NULL exercise weight. Zero weight and zero reps
are valid; duration must be positive. Extra exercise-weight decimals truncate to
one place: 40.99 becomes 40.9. Typing stays untouched during autosave; valid weight
formatting occurs on blur or Next. Seconds above 59 normalize into minutes.
**Next** advances the navigation bar; typing, autosave and Back do not.
Unresolved sets block Next/completion. An all-skipped workout needs confirmation.

Wait for **Saved** before leaving. **Exit Workout** saves a resumable draft; one
active draft is allowed per person. **Discard** requires confirmation and affects
only the unfinished workout. Refresh/Resume restores saved values. Closing before
acknowledgment cannot guarantee unsaved input survives.

## Managing people

People are household profiles, not accounts. Switch through the People screen.
Each person has independent routines, drafts, recommendations, workout history,
body weights and Garmin connection. Menus rename/archive people; archived profiles
retain their history. Settings offers Auto/Light/Dark and personal accent colors.

## Creating exercises and routines

The shared **Exercise Library** has a read-only summary when you tap an exercise
name. **Edit Exercise** or **⋯ → Edit Defaults** opens editing and renaming.
The three-dot menu sits at the top right, above the full-width exercise name.
Names truncate visually only; permanent IDs remain unchanged and are available
on deliberate detail/edit screens. Renaming changes current displays globally;
saved workouts keep their original names.

Select any nonempty combination of **Weight, Repetitions, Duration**. All seven
combinations work, including weight only and repetitions only. Configure sets and
applicable target repetitions/duration. Weight requires a permanent **Total
Weight (×1)** or **Per Hand / Side (×2)** basis; the app never guesses from equipment
or names. Disabling Weight cannot unlock an assigned basis.

- **Save Defaults Only** changes shared defaults for future additions.
- **Save Defaults & Update My Routines** previews and confirms overwriting the
  selected person's existing routine configurations atomically.

Other people's routines, active draft snapshots and completed history stay
independent. Routine copying shares exercise IDs but copies configuration only,
never measurements or completion history. Deleting a routine preserves history.
**Delete Exercise** is different: its confirmed impact review permanently erases
that exercise identity/history across all people. Read the preview carefully.

Start and End illustrations each allow **300 KiB (307,200 bytes)** of passive SVG.
Unsafe/oversized/over-complex uploads preserve the previous image. Removing a
custom illustration restores the default. See [SVG rules](docs/EXERCISE_ICONS.md).

## Workout history and progress

History uses the date the workout occurred, newest first. Date/routine/exercise
filters are person-specific. Enter older workouts using **Enter historical
workout**; this does not interfere with an active draft. Unknown historical time
remains unknown. Corrections require confirmation and append an audit; original
records/configuration snapshots remain unchanged.

Progress offers **3, 6, 12, 24 Months, All Time, Custom Range**, defaulting to
three calendar months in the configured time zone. Selections survive refresh and
exercise changes. Weight, actual reps and actual set duration use separate charts
with dates/units/tooltips and accessible data. Incompatible configurations remain
separate. Skips stay visible in history but are never plotted as zero.

Old workouts retain their original representation. A historical exercise-level
duration is never divided across sets. Unknown legacy set status stays unknown.
Legacy actual reps remain actual; missing historical reps use original targets
only for clearly labeled estimates, not invented actual results.

## Training consistency and estimated weight lifted

Routine selection shows 12 Monday-based calendar weeks and 12 calendar months,
including periods with zero workouts, in the selected person's accent color.
Only completed live/manual historical workouts count.

Pounds and tons appear together. Weighted repetitions use one exercise weight ×
actual completed repetitions × Weight Basis multiplier. Weighted exercises without
reps count one lift per completed set, never elapsed seconds. Exercises without
weight and skipped sets contribute zero. Legacy estimates preserve their original
conventions. Corrections and earlier basis conversions are counted once.

Imperial short tons equal **2,000 lb**; all ton scales have at most one decimal,
with automatic kiloton/megaton/larger scaling. These are estimates of logged
lifting volume, not physiological measurements.

## Body-weight tracking

Open **☰ → Weight** for the selected person's weigh-ins. Add a date/time and
positive weight; manual readings support up to three decimal places. Multiple
readings on one day remain separate. Manual records can be edited or removed
with confirmation and stale-edit protection. Garmin readings remain source-labeled
and read-only here.

The chart shows actual readings plus 7-day and 30-day moving averages. Averages
first average readings within each local calendar day, then equally average the
observed days in each trailing window. Days without readings are omitted, not
zero. Filtering/averaging never deletes individual measurements.

## Connecting Garmin

Each person opens **Settings → Garmin** and enters their own official Garmin
Personal API key, then **Connect and verify**. Saved keys never appear again.
Use **Sync Now** or explicitly enable an automatic interval (six hours by default).
Synchronization imports the latest 30 local calendar days. Repeated syncs do not
create duplicates. Local history stays available when Garmin is offline.

For automatic sync only, change `WORKOUT_SCHEDULER_NETWORK_MODE=none` to `bridge`
in `/root/WorkoutTracker/.env`, then during a planned maintenance window run:

```sh
cd /root/WorkoutTracker/app
docker compose --env-file ../.env up -d --no-build scheduler
```

Manual sync already uses the web container's network. No scheduler port is
published. Never put Garmin keys in `.env` or chat. Keys/tokens are stored separately
in private `storage/config/garmin-private.json`, **not in SQLite downloads or
database backups**. Protect the whole storage tree separately for private-key
recovery. Anyone on the trusted LAN can replace/disconnect integrations; there is
no per-person security boundary against LAN users. See [Garmin details](docs/GARMIN.md).

## CSV exports and workout reports

**Progress CSV** remains a wide paper-log-style sheet: Date, Time, Routine,
Workout ID, then selected exercises across columns. Existing legacy weight/time
formats remain compatible. New capability-based exercises include exercise-level
weight where enabled, per-set actual reps/durations, historical targets and set
statuses. Per-set lists use semicolons in set order. Skipped actuals are blank,
zero stays 0, absent exercises stay blank. Durations use total minutes:seconds.

**History → Workout Reports** creates a locally generated PDF or detailed CSV for
a selected date range. Reports include lifting estimates, set results, training
frequency, compatible records, weight progress and the preceding equal-length
period comparison. Historical assumptions/unknown set detail are labeled.
Detailed CSV is a separate stable format, one new set per row, with workout and
exercise IDs, status, actual values, targets and origin labels. Legacy durations
remain exercise-level. Both exports use effective corrections, person isolation,
UTF-8 quoting and spreadsheet-formula protection. Generated reports are not stored.

## Backups, database downloads and restoring data

**Settings → Administration → Backup Now** creates a verified database backup.
Automatic backups start disabled. Configure their schedule explicitly and check
successful results. Keep off-machine protection of the whole storage tree too.

**Download Database** creates a consistent current SQLite snapshot, even while the
application is running. It contains household workouts/body weights/icons/audits
and the schema, **not Garmin secrets or external settings/signing keys**. It is
not a complete application backup and is private household data.

Restore requires a listed verified backup, warning acknowledgment and typing
RESTORE. A verified separate candidate is selected; originals are retained.
Restore requires matching storage identity and exact schema. It does not merge
later workouts, migrate old backups or silently downgrade. Never restore casually
to repair an update. See [storage and recovery](docs/STORAGE.md).

## Updating the application

**Existing installations: Never initialize an existing database again.** Make a
verified backup and protect the complete storage tree before updating.

### Normal browser update

Open **Settings → Application Updates → Check for Updates**. Read the release
notes, confirm installation and any required schema migration, then Install.
The independent status tab stays available while the app restarts. After success,
verify Settings/footer and `/health/ready`: **1.0.1 / schema 13 / ready**. Make a new
verified backup. Existing schema-12 installations require candidate migration.

Your already upgraded Phase 12 independent updater supports this release; a new
updater script is not required. Changing Flask containers alone never upgrades
the independent host service.

### One-time independent updater installation

If not installed, connect over SSH as your server administrator:

```sh
apt-get update
apt-get install --yes python3 python3-venv
cd /root/WorkoutTracker/app
bash deployment/update_workout_tracker_v4.sh --install-service   --lan-address 192.168.1.100 --app-url http://192.168.1.100:8000 --status-port 8001
```

Replace both addresses. Restrict status port 8001 to your trusted LAN too. This
installs the host service, not workout storage or application containers. For an
older installed host use the documented [explicit host upgrade](deployment/README.md#phase-12-host-service-upgrade).

### Emergency update over SSH

```sh
bash /root/WorkoutTracker/app/deployment/update_workout_tracker_v4.sh
```

Read and explicitly confirm the release and migration. V4 uses the same protected
host engine. [Upgrade and recovery instructions](docs/UPGRADING.md) cover older
unclassified installations, manual maintenance and failed updates. Do not reset
Git, overwrite `.env`, initialize replacement storage or silently restore a backup.

## Starting, stopping and storage locations

Run these commands on the server, from the application folder:

```sh
cd /root/WorkoutTracker/app
docker compose --env-file ../.env ps
docker compose --env-file ../.env stop
docker compose --env-file ../.env up -d --no-build
```

`stop` pauses both services; `up` starts them. Data stays in the host storage tree.
`app/` is replaceable source; `data/storage/` contains databases, selection,
archives, backups, logs, settings and private credentials. `.env` is private host
configuration; `updater/` is the independent service/runtime/recovery state.
Never delete these to fix startup. Use local POSIX storage, not a network/cloud
sync folder. More configuration details: [deployment guide](deployment/README.md).

### Environment variables

| Setting | Purpose |
| --- | --- |
| `WORKOUT_DATA_ROOT` | Absolute existing host storage path; Compose mounts it inside containers. |
| `WORKOUT_BIND_ADDRESS`, `WORKOUT_PORT` | Private server address and browser port. |
| `WORKOUT_TRUSTED_HOSTS` | Allowed hostnames/IPs, no scheme/port; retain health-check localhost entries. |
| `WORKOUT_UID`, `WORKOUT_GID` | Numeric storage writer; default 10001/10001. |
| `WORKOUT_TIMEZONE` | IANA local time zone, default Etc/UTC; used for calendar dates/DST. |
| `WORKOUT_BUILD_CA_BUNDLE` | Host CA bundle for verified package downloads. |
| `WORKOUT_SCHEDULER_NETWORK_MODE` | `none` by default; `bridge` only for optional automatic Garmin. |
| `WORKOUT_SECRET_KEY` | Normally unset; use the persistent provisioned signing file. |

## Common troubleshooting

| Problem | What to check |
| --- | --- |
| Phone cannot connect | Same trusted Wi-Fi, correct IP/port, bind/hosts/firewall. Never publish publicly. |
| No visible update | Check actual `/health/ready` version; fetching code alone does not rebuild containers. |
| Storage missing/damaged | Stop writers and investigate mounts/disk. Never initialize a replacement. |
| Unhealthy service | Run `docker compose --env-file ../.env logs --tail 100 web scheduler` in the app directory. |
| Incomplete workout | Record every enabled set value or explicitly choose Skipped; zero reps/weight are valid. |
| No scheduled Garmin sync | Enable a schedule and optional scheduler bridge network; inspect safe status. Local history still works. |
| No backups | They start disabled; inspect configured schedule/time zone/scheduler logs. |
| ensurepip error | Install the matching distribution Python venv package, then repeat the explicit host installer. |
| Certificate error | Fix CA/proxy settings; never disable TLS verification. |

## Security and limitations

Passwordless trusted-LAN software is not safe for public exposure. Anyone who can
reach it can select people, read household data, change integrations and confirm
deletion. CSRF/host checks and safe storage do not provide authentication. No
professional security audit or warranty is claimed. Ordinary workouts work without
internet; only optional Garmin/updates/dependency installation need it.

Backups on the same disk are not disaster recovery. Preserve private external
configuration separately. No physical iPhone/Safari, ARM hardware, server firewall
or reboot claims are made; see [actual verification](RELEASE_1_0_0_TEST_REPORT.md).

## Technical/developer information

Read [AGENTS.md](AGENTS.md), [PROJECT_SPEC.md](PROJECT_SPEC.md),
[measurement model](docs/MEASUREMENTS.md), [storage](docs/STORAGE.md),
[upgrade paths](docs/UPGRADING.md), [Garmin](docs/GARMIN.md),
[testing](docs/TESTING.md), [release-note format](releases/README.md), and
[release test report](RELEASE_1_0_0_TEST_REPORT.md).

Before every release, review README features, commands, configuration, versions,
links and upgrade instructions. Keep this beginner-first opening and disclosure.
Accurate plain-English versioned release notes are mandatory for every release.
