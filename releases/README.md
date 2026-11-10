# Release notes for people using Workout Tracker

**SHAMELESSLY VIBE-CODED 🤖**

This application was built with a healthy dose of AI, questionable amounts of confidence, and minimal human supervision. It appears to work, but don’t mistake that for a warranty. Use at your own risk, and keep backups.

Every release, including a patch or bug fix, must include `releases/VERSION.json`
in the same approved commit as APP_VERSION. JSON cannot contain comments; this
adjacent document provides the disclosure. Example shape:

```json
{"version":"0.12.0","notes":["Made exercise editing easier."]}
```

Use 1–20 short, single-line plain-text bullets, each at most 500 characters.
The file is limited to 32 KiB. Its version must exactly match the release's
application version. Duplicate keys, malformed fields and mismatched versions
are rejected. Do not include Git hashes, filenames, schema discussions, internal
function names, vague promises, or changes that were not actually made. Prefer
ordinary language about features, improvements and fixes. Never infer notes from
arbitrary commit messages. Keep technical details in the phase review/developer
documents. Do not mark any note content as trusted HTML.

The independent host updater reads the file with `git show` from the exact
approved main SHA used for version metadata, before installation. It validates
and persists plain display text in its private state. Flask escapes notes; the
independent page escapes them too. Notes therefore remain visible while the
application stops. Main source/commit pinning and install consent are unchanged.

New releases from 0.12.0 onward must provide valid notes or release checking fails
safely. Older releases without a file show a neutral unavailable message, never
raw commit-log summaries. Older installed host code continues its existing safe
update flow; the new app hides legacy Git-log notes and explains the one-time
[host service upgrade](../deployment/README.md#phase-12-host-service-upgrade).

Before merging **any** release, Codex must open/review README, validate commands,
configuration, update instructions, current version, links and filenames, preserve
its friendly opening/installation/disclosure, and verify these notes against the
actual user-facing diff. Report README review even when no edit was needed.
This is mandatory for major/minor/patch, UI, database and deployment changes.
