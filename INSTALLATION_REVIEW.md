# Installation guide verification

> **SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.** Documentation and disposable checks do not constitute a real-server deployment or an independent audit.

> Historical record: this verifies the pre-redesign 0.5.0 installation. Current
> mobile UX/version 0.6.0 evidence is in [PHASE_6_UX_REVIEW.md](PHASE_6_UX_REVIEW.md).

## Authorized scope

The documentation branch starts from approved main
`2ac92173eb0ff5fa23f81e39533de09bd7991bdb` (Phases 1–5 merged).
This task adds the README installation/setup guide and minor Compose configuration
improvements. The user explicitly authorized testing, fast-forward merge, push
and cleanup without another approval. It does not authorize actual Proxmox
installation, real household database operations or unrelated Phase 6 development.

The guide appears immediately after the title/disclosure. Existing architecture,
local development, measurement/history behavior, migration safeguards and recovery
reference sections remain below it. The duplicated configuration table was replaced
with a link to the installation table. AGENTS and PROJECT_SPEC record this narrow
authorization without claiming full Phase 6 completion.

## Compose changes

- Both services use `image: workout-tracker:local`, so the separately run bootstrap
  has an explicit stable image name after `docker compose build`.
- Web now has `restart: unless-stopped`, matching scheduler. An intentional manual
  stop still requires explicit resume; no application systemd unit was added.
- `WORKOUT_BIND_ADDRESS` defaults to loopback. LAN access requires explicitly
  choosing a private interface IP and adding that IP to trusted hosts.
- The already-supported optional `WORKOUT_SECRET_KEY` is forwarded to web. Empty
  defaults retain generated private-file behavior. No real secret is committed.
- Non-root UID/GID, read-only root filesystems, private temporary directories,
  capability drops, no-new-privileges, missing-bind refusal and scheduler's
  network/port isolation remain in place.
- No application Python, template, database schema, migration/restore algorithm,
  measurement, scheduler or logging behavior was changed.

## Actual verification environment

| Component | Observed |
| --- | --- |
| Managed Linux executor | Debian GNU/Linux 13, x86-64 |
| Docker Engine | 29.9.2 |
| Compose plugin | v2.40.3 |
| buildx | v0.31.0 |
| Git | 2.52.0 |
| Image Python | 3.12.16 |
| Image SQLite | 3.46.1; source requires at least 3.37 for STRICT tables |
| Application/schema | 0.5.0 / 4 |
| Runtime build | Digest-pinned Dockerfile/application source unchanged; local image built and exercised through Compose |

The pinned base-image manifest publishes amd64 and arm64/v8 among other platforms.
Only amd64 was built/run here; ARM support is not claimed verified. No numerical
oldest-compatible Engine/Compose/Git versions are declared/tested in this repository.
The guide explicitly requires relevant BuildKit/Compose capabilities, recommends
maintained vendor packages and states tested versions rather than inventing minima.
CPU/RAM/disk figures are planning recommendations, not benchmarked minimums.

## Exercised commands and behavior

`WORKOUT_CONTAINER_TESTS=1 /workspace/phase1-venv/bin/python -m pytest -q tests/test_container.py`
completed with **9 passed in 105.96 seconds**, no skips or failures.

The new integration test creates a disposable parent and a previously nonexistent
storage child, substituting temporary paths for the README's `/opt` paths. It uses
the actual modified Compose file and image, with a test-only override removing
web networking and published ports. No household storage, public service, real
LAN interface, Proxmox host or production Docker daemon was used.

It exercises:

1. Actual `docker compose config --format json` / `config --quiet` for `.env`
   interpolation, default loopback, explicit private-IP publishing and trusted
   hosts, and optional secret forwarding using a synthetic test value.
2. `docker compose build` for both services and the documented shared image name.
3. The documented non-root `docker run` parent-mount bootstrap with read-only root,
   no network, temporary `/tmp`, dropped capabilities and explicit init confirmation.
4. Repeated initialization refusal, with original bytes unchanged.
5. Actual `docker compose run --rm --no-deps web python -m workout_tracker
   migrate-storage --data-root /var/lib/workout-tracker --confirm-upgrade
   --target-version 4` and `check-storage`.
6. Matching non-root storage/process ownership and 0600 signing-key permissions.
7. Actual `docker compose up -d --no-build`, both running services, web healthy,
   and readiness reporting app 0.5.0/schema 4. Restart policies/security controls
   are inspected from the running containers.
8. A synthetic HTTP person write, `docker compose restart`, stop/start, preserved
   records and unchanged database/config/archive bytes (expected logs excluded).
9. The persisted scheduler-start event, proving the scheduler process starts
   without an open browser. Existing Docker tests also cover backup/restore,
   correction persistence, independent scheduled backups and graceful exit.
10. Safe cleanup of only test-project containers; no persistent-volume deletion.

Additional verification:

- `python -m pytest -q tests/test_foundation.py tests/test_migrations.py`:
  **60 passed in 1.10 seconds**. This covers empty/existing-destination refusal,
  explicit CLI confirmation, original preservation and candidate migration failures.
- **22 README shell blocks** passed `bash -n` without executing host-provisioning
  examples. All internal README anchors and linked local files resolved.
- Required disclosures/function explanations, `git diff --check` and dependency
  consistency checks passed.
- The documented timestamped pre-update `docker image tag` command was executed
  against the local image; only the temporary alias was then removed.
- No application Python/templates/Dockerfile changed. Chromium was not rerun for
  this documentation/Compose-only task; the relevant Docker and storage checks
  above were rerun instead. These results do not claim a new full-suite run.

## Boundaries and remaining installation considerations

- OS package installation, `/opt` provisioning with sudo, GitHub private-account
  authentication, Docker group changes, systemd enable/reboot and actual host
  firewall/phone access were not executed. These are host-specific instructions,
  not claimed end-to-end tests on a clean home-server VM.
- The guide's LAN binding/trusted-host values were validated through Compose;
  tests deliberately publish no ports. It explains Docker/UFW interaction and
  does not prescribe an unsafe universal firewall rule or internet exposure.
- Builds used the available cache; the actual build command/CA-secret wiring was
  exercised, but a fresh offline/uncached installation was not simulated. Initial
  image/dependency fetching requires approved outbound network access.
- Alternative Linux distributions, ARM, rootless/remapped Docker, NFS/SMB and
  external-disk boot ordering are not verified here. Use local POSIX storage and
  ensure its disk is mounted before Docker. Exact oldest-compatible tool versions
  remain unestablished.
- Existing Phase 1–5 operating limits remain: no authentication, local-only
  backups, synchronous locked maintenance, explicit migration and retained failed
  evidence. Restore rehearsal must use disposable data. No application behavior
  or safety protections were relaxed by this guide.
