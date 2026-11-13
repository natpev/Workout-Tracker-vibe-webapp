# Garmin Personal API

**SHAMELESSLY VIBE-CODED 🤖**

This application was built with a healthy dose of AI, questionable amounts of confidence, and minimal human supervision. It appears to work, but don’t mistake that for a warranty. Use at your own risk, and keep backups.

## Official contract verified for this release

Reviewed Garmin's current official documentation on 2026-11-13:

- [Program overview](https://developer.garmin.com/gc-developer-program/overview/).
- [Personal key and authentication](https://developer.garmin.com/gc-developer-program/personal/personal-api/).
- [Personal API FAQ](https://developer.garmin.com/gc-developer-program/personal/personal-faq/).
- [Official OpenAPI reference](https://developer.garmin.com/gc-developer-program/personal/swagger-docs/).
- [Garmin's official Python example](https://github.com/garmin/connect-personal-api-python).

Garmin Personal API is for individuals accessing their own data, not commercial
multi-user integrations. Each household person must configure their own key for
their own account. Do not reuse one household key across people.

Create a key in Garmin Connect Web → Settings → Personal API Key. Garmin displays
it once; key expiry choices are 30/90/180 days or one year. A key is not itself a
bearer token. The documented POST endpoint is:

`https://personal.connectapi.garmin.com/personalapitoken-service/personal-api/personal-api-key/token`

Send `Authorization: ApiKey KEY`. Garmin's official Python example confirms the
response is a plain-text JWT. Token exchange sends `Accept: */*`; weight-data
requests retain `Accept: application/json`. HTTP failures expose only a safe numeric
status and fixed explanation, never response bodies, reasons, URLs or credentials.
Access tokens last up to 24 hours or key expiry.
There are **no refresh tokens**: obtain another token from the same key. The
application treats JWT expiry only as a cache hint; Garmin over verified HTTPS
remains authoritative. It never treats local JWT decoding as signature validation.

The documented GET endpoint is:

`https://personal.connectapi.garmin.com/weight-service/weight/all/{startDate}/{endDate}`

Dates are inclusive `YYYY-MM-DD` local-calendar bounds. Send the access token in
`Authorization: Bearer TOKEN`. Only individual readings are imported, not daily
averages or summaries.

### Public reference versus reported wire format

The public Swagger asset was downloaded again on 2026-11-13; its `DateWeightDTO`
still describes kilograms and an ISO timestamp. Garmin's current official Python
SDK calls `/weight-service/weight/range/...?...includeAll=true`, returning JSON
without interpreting weight units. Neither reference proves the reported `/all`
wire values are kilograms. The numeric timestamp crash reported for 1.0.1 and the
reported gram-valued responses expose a mismatch with that published DTO prose.
No real Garmin account or private API payload was accessed in this repair.

Version 1.0.2 explicitly interprets the `/all` individual-reading `weight` as **grams**
and accepts `timestampGMT` as Unix epoch **milliseconds** or aware ISO 8601 text.
Units never depend on timestamp representation or magnitude. It does not guess
that a small invalid gram value must be kilograms. If Garmin changes this wire
contract, reject the response and review the adapter rather than guessing units.
The public documentation discrepancy remains an upstream limitation, not a claim
that the public Swagger now documents grams. Integration tests model both
supported timestamp representations with the reported gram-valued wire format.

## Local storage and idempotency

SQLite stores each reading independently, including multiple readings per day.
Weights use integer thousandths of a pound. Convert with exact decimal arithmetic:
**1 lb = 453.59237 g**, rounding half-even only at the stored thousandth-pound
boundary. Preserve the original numeric source value and explicit `g` unit as
JSON text in the existing `source_value` column; no schema change is needed.

All rows must validate before importing. Accept finite numeric weights within
**1–700 kg (1,000–700,000 grams)**, never booleans, numeric strings, zero/negative
weights or unsupported units. This conservative import envelope deliberately
rejects values outside its bounds instead of silently importing a unit mistake.
Accept aware ISO timestamps or numeric milliseconds, with exact UTC microsecond
identities. Supported dates begin 1980-01-01 and cannot be in the future. Reject
Unix seconds, timezone-naive text and nonzero sub-microsecond precision rather
than silently losing identity. A bad row refuses the entire batch atomically.
Errors contain fixed explanations, not private readings, timestamps or payloads.

The currently published DTO does **not** document a stable measurement ID. The
existing canonical UTC timestamp remains the source identity within each person.
Changing ISO offsets or numeric/ISO representation does not create duplicates.
Equal weights at different times stay separate. Conflicting values at the same
instant refuse the batch instead of guessing. Updated gram-tagged source readings
retain the existing record ID and append before/after audits. Manual readings
never participate in Garmin reconciliation.

**Earlier imports are not automatically repaired or reinterpreted.** Untagged
source values from older releases keep their original rows and audits. If a new
reading matches the stored weight, leave it unchanged. If it conflicts, refuse the
entire import with an older-format review message. This patch supplies no automatic
repair tool; investigate any suspect old imported values deliberately, from a
verified backup, rather than deleting history or editing SQLite to unblock sync.
A person represents one Garmin account; this is not an account-merging feature.

## Secrets, scheduling and recovery

Private keys and cached tokens live in `config/garmin-private.json`, mode 0600,
outside SQLite. Never put them in Compose, URLs, reports or logs. Download Database
and database backups omit this file. Protect/recover the entire external storage
tree separately, including this private file and signing/settings material.
Disconnect removes the selected person's key/token, retaining imported readings.
Do not share this file or diagnostic dumps. The passwordless trusted-LAN model
does not stop another LAN user from changing/disconnecting an integration.
Key entry uses the application’s ordinary HTTP connection on that trusted LAN,
so that local connection is not encrypted. Outbound Garmin API requests use
verified HTTPS. No login or HTTPS requirement is introduced.

Manual Sync Now is available in the selected person's Settings. Automatic sync is
explicitly enabled, default interval six hours (configurable 1–168 hours), importing
the last 30 local calendar days. No polling is required for viewing local history.
Errors do not erase local records. Attempts use bounded response sizes/timeouts,
no redirects, atomic imports, short claims and safe backoff. All failures, including
unexpected programming errors and Python cancellation, release only their owned
claim and preserve saved credentials. A hard-killed process cannot execute cleanup;
its five-minute claim expires and the next sync can reclaim it. Generation/claim
checks prevent an older worker from importing after a replacement takes ownership.
Storage permission/disk failures can prevent writing cleanup status; the same
bounded lease remains the fallback. Never delete private state to clear a claim. A 429 Retry-After is
respected. One expired-token rejection can obtain a new token and retry once.

The existing dedicated scheduler remains offline by default for older installs.
To enable its optional outbound Garmin requests, add this setting to the private
parent `.env` and recreate the scheduler during a planned update:

```text
WORKOUT_SCHEDULER_NETWORK_MODE=bridge
```

No ports are published for the scheduler. The default `none` resolves to the same
Compose configuration as earlier releases, preserving ordinary browser-update
compatibility. Manual sync uses the web service's existing outbound network.
Ordinary workout and body-weight history never require internet access. The home
server needs outbound HTTPS/DNS for `personal.connectapi.garmin.com` only when
Garmin synchronization is configured. Do not expose application ports publicly.

All automated Garmin tests use mocked official-contract responses and synthetic
keys. No real Garmin account or credentials are used during development/testing.
