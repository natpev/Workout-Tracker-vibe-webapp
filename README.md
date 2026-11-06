# Workout Tracker

> **SHAMEFULLY VIBE-CODED PROJECT.** This is intended to be an AI-generated, human-directed workout tracker. Do not assume it has been audited, secured, or tested for production use.

A simple self-hosted workout tracker planned for Python, Flask, SQLite, and Docker Compose. It will support independent household users and routines, copying routines between users, one-weight-per-exercise workout entry, past workout history and charts, database-safe updates, and server-side backups.

**Status: planning only. No application has been built or deployed.**

## Start here

- [`AGENTS.md`](AGENTS.md): persistent instructions for Codex and human contributors, including safety rules and beginner-friendly comments.
- [`PROJECT_SPEC.md`](PROJECT_SPEC.md): detailed approved requirements and clearly labeled open decisions.

## Core promises

- Private home-LAN access to start; remote exposure not enabled.
- User routines/history stay independent; copying a routine never links or shares historical results.
- A skipped exercise is saved as a record with SQL `NULL` weight, **not** 0, the old weight, or an omitted entry.
- Finish & Save saves and completes a workout; discarding a draft requires a checkbox confirmation.
- App updates with an unchanged DB schema leave the DB alone; schema upgrades preserve a separate unchanged original and validate the new copy before use.
- Manual and optional scheduled SQLite backups are saved to a server directory, never automatically downloaded.

## For Codex

Read **both** `AGENTS.md` and `PROJECT_SPEC.md`. **Do not begin implementation without explicit approval.** First review the design, identify unresolved decisions, and propose a phased, tested plan.

## Future deployment

Docker Compose on a home Linux host, possibly a Proxmox-managed VM, with durable host-mounted paths for databases, archives, backups, settings, and logs. Actual setup and update commands will be documented only after implementation exists and has been tested.
