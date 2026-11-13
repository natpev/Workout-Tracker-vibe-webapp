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
response is a plain-text JWT. Access tokens last up to 24 hours or key expiry.
There are **no refresh tokens**: obtain another token from the same key. The
application treats JWT expiry only as a cache hint; Garmin over verified HTTPS
remains authoritative. It never treats local JWT decoding as signature validation.

The documented GET endpoint is:

`https://personal.connectapi.garmin.com/weight-service/weight/all/{startDate}/{endDate}`

Dates are inclusive `YYYY-MM-DD` local-calendar bounds. Send the access token in
`Authorization: Bearer TOKEN`. The response is an array of `DateWeightDTO`:
`weight` is **kilograms**, and `timestampGMT` is an aware measurement timestamp.
The API also exposes daily/range summaries; this application intentionally uses
individual readings, never those aggregates.

## Local storage and idempotency

SQLite stores each reading independently, including multiple readings per day.
Weights use integer thousandths of a pound. Convert with the exact definition
1 lb = 0.45359237 kg, rounding only to this stored precision; retain the original
kilogram decimal string. Manual records never participate in Garmin upserts.

The currently published DTO does **not** document a measurement ID. Use the
canonical UTC timestamp, including its fractional precision, as the source ID
within the selected person. Equal weights at different times stay separate.
An identical timestamp/measurement is a retry; a changed value at that source
identity appends a before/after audit. Conflicting same-timestamp values in one
response are ambiguous and refuse the whole import instead of guessing.
A person represents one Garmin account; changing that person's account is not an
account-merging feature. Imported data remains labeled Garmin after disconnect.

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
no redirects, atomic imports, short claims and safe backoff. A 429 Retry-After is
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
