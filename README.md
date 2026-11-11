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

Current application: **0.13.0**. Database schema: **9**. Existing schema-8
installations need an explicitly confirmed migration to a **separate database
candidate**. The original is preserved. Your Phase 12 host updater needs no
additional refresh. See [updating](#updating-the-application); never initialize
an existing installation again.

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
your firewall, or a physical iPhone/Safari. See [verification limits](INSTALLATION_REVIEW.md).

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
  --confirm-upgrade --target-version 9

docker compose --env-file ../.env run --rm --no-deps web \
  python -m workout_tracker check-storage --data-root /var/lib/workout-tracker
```

Initialization starts with the foundation schema. The second command creates
and verifies a separate schema-9 database, preserving the original. The final
command should report **Storage verified; schema version 9.** Stop at any error;
never delete storage or initialize again to make an error disappear.

### 6. Start Workout Tracker

```sh
cd /root/WorkoutTracker/app
docker compose --env-file ../.env up -d --no-build
docker compose --env-file ../.env ps
```

Two services should run: **web** serves the application; **scheduler** handles
configured backups and log retention without an open browser. Web should become
**healthy** after a health check. Scheduler has no separate HTTP health endpoint.
Verify the actual application inside the container:

```sh
docker compose --env-file ../.env exec -T web python -c \
  'import json,urllib.request; r=json.load(urllib.request.urlopen("http://127.0.0.1:8000/health/ready",timeout=10)); print(r); assert r==dict(status="ready",app_version="0.13.0",schema_version=9)'
```

If startup is still in progress, retry after a few seconds. Both containers use
`restart: unless-stopped`. On a standard systemd-based server, enable Docker at
boot with `systemctl enable --now docker`. A deliberately stopped container stays
stopped until you run `up -d` again. Reboot behavior on your server needs checking.

### 7. Open it on your phone or computer

In a browser on the same trusted home network, open **http://192.168.1.100:8000**,
substituting your server address. Do not use `localhost` on your phone: that means
the phone itself. The People screen should appear. Settings/About and the footer
should report **0.13.0 / database 9**. Check all three themes in Settings.

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

## Using Workout Tracker

Open the app, choose a person, choose a routine, and press **Start workout**.
Record one exercise per screen. Today's fields start blank; previous results are
shown prominently for reference alongside the exercise targets. Weight text stays
unchanged while you type, even during autosave. A valid weight normalizes to one
decimal place when you leave the field or use Next; extra digits truncate. Invalid
text stays visible with an error. **Next** advances navigation progress, including skipped
exercises. Typing and autosaving do not advance it. **Back**, revisits, refresh
and Resume retain the furthest Next checkpoint without double-counting.

Wait for **Saved** before leaving. **Finish & Save** completes the workout.
**Exit Workout** saves a resumable draft; only one draft is allowed per person.
**Discard** requires confirmation and affects only the unfinished workout.
Closing a browser before acknowledgment cannot guarantee unsaved input survives.

## Managing people

People are household profiles, not accounts. Select another person through the
People screen; each has independent routines, drafts, history and recommendations.
Rename or archive people through their menus. Archived people retain their records.
Settings has Auto/Light/Dark themes and a separate accent color per person.

## Creating routines

Create a routine, add exercises from the shared Library, and adjust its sets and
targets. Copy or duplicate routines to get independent settings with shared exercise
identities. Copied routines inherit no workout results or increase recommendations.
Removing an exercise from a routine does not remove its Library definition/history.
Deleting a routine preserves completed history; active drafts block deletion.

## Exercise Library

Open the **⋯** menu beside an exercise, then choose **Edit Defaults** to edit its
name and defaults. Long names shorten visually to keep the menu accessible; the
complete name stays in the editor and its tooltip. Its Library
ID is shown only on that detail screen, for troubleshooting. Ordinary selectors
show names; matching names get numbered options without changing their identities.

Renaming updates the shared name and current routine displays for everyone.
Historical workouts keep their original names. Defaults apply only when an exercise
is newly added to a routine; changing them does not change existing routine settings.
**Delete Exercise** in the menu opens a separate permanent-deletion review: it deliberately erases that identity
and its history across all people after an impact preview and confirmation. Older
backups can resurrect deleted records on deliberate compatible restore.


### Weight Basis — temporary transition (Update 1)

Weight and Weight + Duration exercises now have **Not Configured**, **Total
Weight (×1)** and **Per Hand / Side (×2)** radio choices. Choose how you record
weight; the app never guesses from exercise names or equipment. Duration-only
exercises do not need this setting. Existing exercises start Not Configured, and
the old **Weight Meaning** text remains for reference.

In Edit Defaults:

- **Save Defaults Only** saves the shared name/defaults for future routine additions.
  Existing routines and history do not change.
- **Save Defaults & Update My Routines** previews replacing all exercise settings
  in the selected person's routines, and any historical classification/conversion.
  Confirm explicitly. Other people's existing settings and measurements stay intact.

First assignment of unclassified history keeps its weights unchanged. Later
Total → Per Hand divides recorded weights by exactly 2; Per Hand → Total multiplies
by exactly 2. Repeated saves do not repeat a conversion. Each person's actual
history basis is tracked separately from shared defaults; independently configured
new snapshots keep their own basis until deliberately included in a transition.

If halving needs more than one decimal (25.5 → 12.75), or doubling exceeds storage
limits, **nothing is saved**. Review the identified workout for accuracy; do not
round a true measurement just to force a conversion. Originals and correction
audits remain retained. Dates, durations and historical prescriptions never change.
Finish or deliberately discard your draft through the existing workflow before
bulk-changing an exercise it uses. An incompatible pending historical review must
be prepared again; its submitted fields remain visible on error.

History, charts, previous results and CSV use current effective values. Different
bases stay separate for comparisons. Today's measurement still starts blank, and
the value you type is never automatically doubled/halved. Setup counters show
shared defaults, your routines and your history independently. Update 2 and
Estimated Total Weight Lifted statistics are **not implemented** in this update.

## Weight, Duration, and Weight + Duration exercises

| Type | Configure | Record once per exercise |
| --- | --- | --- |
| Weight | Sets, target reps, pounds, optional weight meaning | One weight |
| Time (Duration) | Sets and target duration per set | One actual duration |
| Weight + Duration | Sets, target duration, pounds and weight meaning | One weight **and** duration |

Weights use pounds, keep one decimal place, and truncate extra digits rather than
rounding: 40.99 becomes 40.9. Zero weight is valid. Durations accept minutes,
seconds, or both; 90 seconds becomes 1:30. Actual duration must be positive.
Set count never multiplies actual measurements.

Blank means skipped, stored as SQL NULL rather than zero or a previous result.
For combined exercises, leave **both** measurements blank to skip; otherwise both
are required. Partial pairs stay unsaved until corrected. Use the manual
**Increase weight next time** checkbox for Weight/combined exercises, or
**Increase duration next time** for Time. Nothing increases automatically.

## Workout history

History lists completed workouts by when they happened. Ordinary dates/times omit
time-zone names; the stored zone and DST handling stay unchanged. Open Timing
diagnostics on a saved workout when troubleshooting. History date filters stack
on narrow phones and sit side by side when there is room. Open a saved workout to
view its
original exercise order, prescriptions, actual measurements and skips. Enter older
workouts through **Enter historical workout**, choosing a routine, date and optional
time. Unknown time stays unknown. Saved-workout corrections require confirmation;
originals and the correction audit remain retained. Editing routines does not
rewrite saved snapshots or active drafts.

## Progress charts

Progress defaults to **3 Months** and offers **6 Months, 12 Months, 24 Months,
All Time, Custom Range**. Month ranges use the configured local calendar, not
fixed numbers of days. Select an exercise; refresh and History/Progress navigation
retain the range. Older day-based links still work and show their original bounds
as Custom Range.

Weight and duration have separate axes. Combined exercises show both charts
together. Tap, hover or focus a point for its date/result. Historical duration
targets remain per workout; a single target line appears only when targets agree.
Skipped measurements stay in the underlying data list, never as zero points.

## CSV exports

On Progress, choose a range, open **CSV export — choose exercises**, select one or
more exercises, then **Export CSV**. Select All/Clear help with larger lists.
Each completed workout gets its own row, oldest first: Date, Time, Routine,
Workout ID, then adjacent columns per exercise:

- Weight: Weight (lb), Sets × Reps.
- Duration: Duration, Sets × Target Duration.
- Combined: Weight (lb), Duration, Sets × Target Duration.

Prescriptions come from historical snapshots, actuals from the latest corrections.
Skipped actuals are blank; absent exercises have blank cells; valid zero stays 0.
Time uses total minutes:seconds (for example 61:05). UTF-8 CSV uses standard quoting
and protects formula-like text. No cloud service or Excel installation is needed.

## Backup and restore

Backup Now and configured schedules produce verified, separate copies. Restore
requires inspecting a listed backup, acknowledging the warning and typing RESTORE.
It preserves the previous database and activates a verified separate candidate.
Restore accepts the same storage identity and exact schema; it does not merge
later workouts, migrate older backups or silently downgrade the database.

Do not restore casually to repair an update. Keep originals and failed candidates
for diagnosis. See [detailed recovery instructions](deployment/README.md#emergency-ssh-checks-and-failure-recovery).

## Updating the application

### Normal browser update

Once the host updater is installed: **Settings → Administration → Application
Updates → Check for Updates**. Read the plain-English notes, confirm installation
(and migration only if required), then **Install Update**. An independent progress
tab remains available while the app restarts. Notes and logs scroll within their
boxes. Reopen the app and verify Settings/footer and `/health/ready` versions.

For 0.13.0, an existing schema-8 installation needs a confirmed upgrade to schema
9. The updater backs up verified storage, migrates a separate candidate, checks
its integrity and audits, then switches selection atomically. Original database
versions remain available. Never initialize or restore storage as an update shortcut.
After success, make a new verified schema-9 backup. Older schema-8 backups remain
retained but cannot be silently restored into schema 9.
See [Phase 13 upgrade steps](PHASE_13_REVIEW.md#existing-installation-upgrade).

### One-time browser updater installation

SSH administrator access is required for this separate host service. On the server,
with no update job running, install the matching Python venv package (for example
`apt-get install --yes python3-venv`; Python 3.12 may need `python3.12-venv`). Then:

```sh
bash /root/WorkoutTracker/app/deployment/update_workout_tracker_v4.sh \
  --install-service --lan-address 192.168.1.100 \
  --app-url http://192.168.1.100:8000 --status-port 8001
```

Replace the address with the one in your `.env`. This installs the independent
service; it does not initialize/migrate workout storage or replace app containers.
Root's Git credentials must allow noninteractive repository fetch. Keep port 8001
restricted to trusted LAN devices too.

### Existing host service: Phase 12 one-time upgrade

Container updates cannot replace the separately installed host code/assets.
To enable versioned notes and the new console scrolling, follow
[the exact Phase 12 service upgrade](deployment/README.md#phase-12-host-service-upgrade).
Older hosts can still install approved updates safely, but the app hides their
raw Git-log notes and explains the required host upgrade. V4 remains supported;
there is no new updater script.

### Emergency updating or recovery

Over SSH, use the repository's existing v4 entry point:

```sh
bash /root/WorkoutTracker/app/deployment/update_workout_tracker_v4.sh
```

Read and confirm the release. If v4 is not installed or source is older, use the
[detailed deployment guide](deployment/README.md), including clean-main checks,
service setup and failure recovery. Do not assume an external root-level wrapper
has the same behavior. Never force-reset local Git work, delete data, initialize
replacement storage, or automatically restore an old backup after a failed update.

## Common troubleshooting

| Problem | What to check |
| --- | --- |
| Phone cannot connect | Same trusted Wi-Fi, correct server IP/port, `.env` bind/hosts, LAN firewall and VM firewall. Do not expose the app publicly. |
| Missing/corrupt storage | Stop writers and investigate the actual disk/mount. Never initialize an empty replacement. |
| Web not healthy | From `/root/WorkoutTracker/app`, run `docker compose --env-file ../.env ps` and `docker compose --env-file ../.env logs --tail 100 web scheduler`. |
| No automatic backups | They start disabled. Check enabled/time/zone, next run, scheduler status and its persistent Logs entries. |
| Save failed | Stay on the exercise, correct inputs and retry. A combined exercise needs both measurements. Stale pages must reload before saving. |
| Readable notes/scrolling missing | Upgrade the independent host service once; container replacement alone does not update it. |
| Docker build certificate error | Check trusted CA/proxy settings. Never disable HTTPS verification. |
| Updater venv/ensurepip error | Install your distribution's matching Python venv package, then rerun the explicit service installer. |

## Security and limitations

This is passwordless, HTTP-only household software. It has not had a professional
security audit. Trusted hosts/CSRF and safe database handling do not make it safe
for the public internet. No accounts, HTTPS requirement, telemetry or external
chart service is introduced. Backups on the same disk are not disaster recovery.
Use local POSIX storage, not NFS/SMB/cloud-sync folders. Rootless Docker and ARM
installation are not validated by this guide. No offline saving or guarantee for
input closed before Saved. Do not casually remove schema archives or old backups.

## Technical/developer information

See [AGENTS.md](AGENTS.md), [PROJECT_SPEC.md](PROJECT_SPEC.md),
[measurement design](MEASUREMENT_DESIGN.md), [release-note format](releases/README.md),
[deployment/recovery](deployment/README.md), [developer reference](docs/DEVELOPER_REFERENCE.md),
[Phase 12 verification](PHASE_12_REVIEW.md), and
[Library menu verification](LIBRARY_MENU_REVIEW.md) and
[workout/history verification](WORKOUT_HISTORY_UI_REVIEW.md) and
[current Phase 13 verification](PHASE_13_REVIEW.md). Older phase reviews retain their
historical results and limitations. Current release verification is recorded in
PHASE_13_REVIEW.md; no physical-server or live-data testing is implied.

Before **every** release—including patches—review this README against actual
features, installation/update commands, versions, links and filenames. Keep this
beginner-friendly opening and disclosure. Verify accurate human-readable release
notes in the approved release source. These are permanent release requirements.
