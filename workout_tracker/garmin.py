# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Official Garmin Personal API transport, private credentials and idempotent sync.

Official references and limits are recorded in docs/GARMIN.md. Network work runs
outside the storage lock; only a short validated import transaction blocks writers.
Secrets live in private external JSON, never in SQLite or downloadable snapshots.
"""
import base64
import json
import os
import re
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_EVEN
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError
from uuid import uuid4
from zoneinfo import ZoneInfo
from . import catalog as c, workouts as w, body_weight as b
from .storage import (
    storage_lock,
    database_session,
    _regular_file,
    _sync_directory,
    StorageError,
)

BASE = "https://personal.connectapi.garmin.com"
TOKEN = "/personalapitoken-service/personal-api/personal-api-key/token"
WEIGHTS = "/weight-service/weight/all/{start}/{end}"
STATE_FILE = "garmin-private.json"


class GarminError(c.ValidationError):
    """Only fixed nonsecret messages may cross the browser/log boundary."""

    def __init__(self, message, *, unauthorized=False, retry_after=900):
        """Carry safe display text and retry hints without credentials or raw API data."""
        super().__init__(message)
        self.unauthorized = unauthorized
        self.retry_after = retry_after


class NoRedirect(HTTPRedirectHandler):
    """Authorization headers must never follow redirects to another origin."""

    def redirect_request(self, *args, **kwargs):
        """Refuse redirects so an Authorization header cannot leave the official origin."""
        return None


def request(path, authorization, *, method="GET"):
    """Fixed official HTTPS origin, no redirects, bounded time and response bytes."""
    if not path.startswith("/") or "\n" in authorization or "\r" in authorization:
        raise GarminError("Invalid Garmin request configuration.")
    # Token exchange returns a plain-text JWT; weight endpoints return JSON.
    # Choose by the fixed endpoint, without changing credentials or token caching.
    accept = "*/*" if path == TOKEN else "application/json"
    req = Request(
        BASE + path,
        data=b"" if method == "POST" else None,
        headers={"Authorization": authorization, "Accept": accept},
        method=method,
    )
    try:
        with build_opener(NoRedirect()).open(req, timeout=10) as response:
            chunks = []
            length = 0
            deadline = time.monotonic() + 20
            while True:
                if time.monotonic() > deadline:
                    raise GarminError("Garmin timed out. Local records are unchanged.")
                block = response.read1(65536)
                if not block:
                    break
                length += len(block)
                if length > 2 * 1024 * 1024:
                    raise GarminError(
                        "Garmin returned too much data; use a shorter synchronization range."
                    )
                chunks.append(block)
            return b"".join(chunks).decode("utf-8")
    except HTTPError as error:
        # Only the numeric status is safe to publish. Never include the remote
        # reason, URL, headers or response body, which could echo credentials.
        status = f"HTTP {error.code}"
        if error.code in (401, 403):
            raise GarminError(
                f"Garmin rejected the credentials ({status}). Replace or verify the Personal API key.",
                unauthorized=True,
            ) from None
        delay = 900
        if error.code == 429:
            header = (error.headers or {}).get("Retry-After", "")
            if re.fullmatch(r"[0-9]{1,8}", header):
                delay = max(delay, int(header))
            else:
                from email.utils import parsedate_to_datetime

                try:
                    delay = max(
                        delay,
                        int((parsedate_to_datetime(header) - w.now()).total_seconds()),
                    )
                except (ValueError, TypeError, OverflowError):
                    pass
            raise GarminError(
                f"Garmin is limiting requests ({status}). Synchronization will retry later.",
                retry_after=delay,
            ) from None
        if error.code == 406:
            raise GarminError(
                f"Garmin rejected the requested response format ({status}). Local records are unchanged."
            ) from None
        raise GarminError(
            f"Garmin is unavailable ({status}). Local records are unchanged."
        ) from None
    except (URLError, TimeoutError, OSError, UnicodeError):
        raise GarminError(
            "Garmin could not be reached. Local records are unchanged."
        ) from None


def obtain(key):
    """Garmin returns a plain JWT, not JSON; re-obtain rather than refresh a token."""
    token = request(TOKEN, "ApiKey " + key, method="POST").strip()
    try:
        payload = token.split(".")[1]
        payload += "=" * ((-len(payload)) % 4)
        expiration = json.loads(base64.urlsafe_b64decode(payload))["exp"]
        if (
            type(expiration) not in (int, float)
            or not w.now().timestamp() < expiration <= w.now().timestamp() + 86460
        ):
            raise ValueError()
    except (ValueError, KeyError, IndexError, TypeError):
        raise GarminError("Garmin returned an invalid access token.") from None
    # Reading exp is only a cache expiry hint. HTTPS/official API authentication
    # remains authoritative; this does not claim local JWT signature verification.
    return token, expiration


def read(root):
    """Read private state without mutation; callers already own the root lock."""
    path = root / "config" / STATE_FILE
    if not os.path.lexists(path):
        return {"version": 1, "people": {}}
    try:
        _regular_file(path)
        if path.stat().st_mode & 0o077 or path.stat().st_size > 2 * 1024 * 1024:
            raise ValueError()
        state = json.loads(path.read_text())
        if state.get("version") != 1 or not isinstance(state.get("people"), dict):
            raise ValueError()
        for person, item in state["people"].items():
            if not re.fullmatch("[0-9a-f]{32}", person) or not isinstance(item, dict):
                raise ValueError()
            if (
                type(item.get("connected", False)) is not bool
                or type(item.get("automatic", False)) is not bool
            ):
                raise ValueError()
            for secret in ("key", "token"):
                if secret in item and (
                    not isinstance(item[secret], str) or len(item[secret]) > 16384
                ):
                    raise ValueError()
            if item.get("connected") and (
                not item.get("key")
                or not re.fullmatch("[0-9a-f]{32}", item.get("generation", ""))
            ):
                raise ValueError()
            for field in (
                "last_attempt",
                "last_success",
                "next_attempt",
                "retry_not_before",
            ):
                if (
                    item.get(field)
                    and datetime.fromisoformat(item[field]).tzinfo is None
                ):
                    raise ValueError()
            if "interval_hours" in item and (
                type(item["interval_hours"]) is not int
                or not 1 <= item["interval_hours"] <= 168
            ):
                raise ValueError()
        return state
    except (OSError, ValueError, TypeError):
        raise StorageError(
            "Private Garmin configuration cannot be verified; it was preserved."
        ) from None


def write(root, state):
    """Publish a mode-0600 replacement atomically; never put secrets in backup names."""
    pending = root / "config" / ("garmin-" + uuid4().hex + ".pending")
    try:
        descriptor = os.open(
            pending, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
        )
        with os.fdopen(descriptor, "w") as handle:
            json.dump(state, handle, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(pending, root / "config" / STATE_FILE)
        _sync_directory(root / "config")
    finally:
        if pending.exists():
            pending.unlink()


def public(value, person):
    """Allowlist status fields only; saved keys/tokens never reach a template/JSON API."""
    with storage_lock(value) as root:
        item = read(root)["people"].get(person, {})
    return {
        key: item.get(key)
        for key in (
            "connected",
            "last_attempt",
            "last_success",
            "error",
            "automatic",
            "interval_hours",
            "next_attempt",
        )
    }


def connect(value, person, key, zone="Etc/UTC"):
    """Verify a new key outside locks, then atomically store only that person's secret."""
    if (
        not isinstance(key, str)
        or not 1 <= len(key.strip()) <= 4096
        or any(ord(c) < 32 for c in key)
    ):
        raise GarminError("Enter a valid Personal API key.")
    with database_session(value, minimum_version=13) as db:
        c.person(db, person)
    try:
        token, expires = obtain(key.strip())
    except GarminError as error:
        with storage_lock(value, exclusive=True) as root:
            state = read(root)
            item = state["people"].setdefault(
                person, dict(connected=False, generation=uuid4().hex)
            )
            item.update(last_attempt=w.now().isoformat(), error=str(error))
            write(root, state)
        raise error from None
    with storage_lock(value, exclusive=True) as root:
        state = read(root)
        old = state["people"].get(person, {})
        state["people"][person] = dict(
            key=key.strip(),
            token=token,
            expires=expires,
            generation=uuid4().hex,
            connected=True,
            last_attempt=w.now().isoformat(),
            last_success=old.get("last_success"),
            error=None,
            automatic=old.get("automatic", False),
            interval_hours=old.get("interval_hours", 6),
            timezone=zone,
            next_attempt=w.now().isoformat(),
            claim=None,
        )
        write(root, state)


def disconnect(value, person):
    """Remove credentials/token; keep SQLite readings and nonsecret sync history."""
    with storage_lock(value, exclusive=True) as root:
        state = read(root)
        old = state["people"].get(person, {})
        state["people"][person] = dict(
            connected=False,
            generation=uuid4().hex,
            last_attempt=old.get("last_attempt"),
            last_success=old.get("last_success"),
            error=None,
            automatic=False,
            interval_hours=6,
            next_attempt=None,
            claim=None,
        )
        write(root, state)


def schedule(value, person, enabled, hours):
    """Persist explicit opt-in and a bounded interval; scheduled errors back off safely."""
    hours = c.integer(hours, "Sync interval hours", 1, 168)
    with storage_lock(value, exclusive=True) as root:
        state = read(root)
        item = state["people"].get(person)
        if not item or not item.get("connected"):
            raise GarminError(
                "Connect Garmin before enabling automatic synchronization."
            )
        item.update(
            automatic=enabled, interval_hours=hours, next_attempt=w.now().isoformat()
        )
        write(root, state)


def decoded_weights(raw):
    """Official DateWeightDTO: kilograms + aware timestampGMT; no stable ID is documented.

    The permanent source identity is the canonical UTC measurement timestamp per
    person. Conflicting duplicate timestamps in one response are refused, never
    collapsed by weight/name. Updates retain original source values in an audit.
    """
    try:
        rows = json.loads(raw, parse_float=Decimal)
        if not isinstance(rows, list) or len(rows) > 20000:
            raise ValueError()
        result = {}
        for row in rows:
            moment = datetime.fromisoformat(row["timestampGMT"].replace("Z", "+00:00"))
            if moment.tzinfo is None or moment > w.now():
                raise ValueError()
            instant = moment.astimezone(timezone.utc).isoformat(timespec="microseconds")
            kilos = Decimal(str(row["weight"]))
            if not kilos.is_finite() or kilos <= 0:
                raise ValueError()
            # The exact pound definition is 0.45359237 kg. Only the stored
            # body-weight precision is rounded; original kilograms are retained.
            milli = int(
                (kilos * Decimal(1000) / Decimal("0.45359237")).to_integral_value(
                    rounding=ROUND_HALF_EVEN
                )
            )
            if not 1 <= milli <= w.MAX_INTEGER:
                raise ValueError()
            measurement = dict(
                measured_at=instant, weight_milli_lb=milli, source_value=str(kilos)
            )
            if instant in result and result[instant] != measurement:
                raise GarminError(
                    "Garmin returned conflicting measurements at one timestamp; nothing was imported."
                )
            result[instant] = measurement
        return list(result.values())
    except GarminError:
        raise
    except (ValueError, KeyError, TypeError, ArithmeticError):
        raise GarminError(
            "Garmin returned invalid weight data; nothing was imported."
        ) from None


def import_weights(db, person, rows):
    """Idempotent person/source/timestamp upsert; Manual readings are never touched."""
    c.person(db, person)
    count = 0
    stamp = w.now().isoformat()
    for row in rows:
        external = "timestamp:" + row["measured_at"]
        old = db.execute(
            "SELECT * FROM body_weights WHERE person_id=? AND source='garmin' AND external_id=?",
            (person, external),
        ).fetchone()
        if old:
            before = dict(old)
            if all(before[key] == row[key] for key in row):
                continue
            db.execute(
                "UPDATE body_weights SET weight_milli_lb=?,source_value=?,updated_at=?,revision=revision+1 WHERE id=?",
                (row["weight_milli_lb"], row["source_value"], stamp, old["id"]),
            )
            identity = old["id"]
        else:
            before = None
            identity = uuid4().hex
            db.execute(
                "INSERT INTO body_weights(id,person_id,weight_milli_lb,measured_at,source,external_id,source_value,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    identity,
                    person,
                    row["weight_milli_lb"],
                    row["measured_at"],
                    "garmin",
                    external,
                    row["source_value"],
                    stamp,
                    stamp,
                ),
            )
        b.audit(db, person, identity, before, b.record(db, person, identity))
        count += 1
    return count


def sync(value, person, zone, *, scheduled=False):
    """Claim briefly, release lock for HTTPS, then import atomically if still connected."""
    with database_session(value, minimum_version=13) as db:
        c.person(db, person)
    with storage_lock(value, exclusive=True) as root:
        state = read(root)
        item = state["people"].get(person, {})
        if not item.get("connected"):
            raise GarminError("Connect Garmin before synchronizing.")
        if item.get("claim") and datetime.fromisoformat(
            item["last_attempt"]
        ) > w.now() - timedelta(minutes=5):
            raise GarminError("A Garmin synchronization is already in progress.")
        if (
            item.get("retry_not_before")
            and datetime.fromisoformat(item["retry_not_before"]) > w.now()
        ):
            raise GarminError(
                "Garmin retry is deferred until the displayed next attempt; local records remain available."
            )
        if scheduled and (
            not item.get("automatic")
            or datetime.fromisoformat(item["next_attempt"]) > w.now()
        ):
            return 0
        claim = uuid4().hex
        item.update(claim=claim, last_attempt=w.now().isoformat(), error=None)
        settings = dict(item)
        write(root, state)
    try:
        token = settings.get("token")
        if not token or settings.get("expires", 0) <= w.now().timestamp() + 3600:
            token, expires = obtain(settings["key"])
        else:
            expires = settings["expires"]
        day = w.now().astimezone(ZoneInfo(settings.get("timezone", zone))).date()
        path = WEIGHTS.format(
            start=(day - timedelta(days=29)).isoformat(), end=day.isoformat()
        )
        try:
            raw = request(path, "Bearer " + token)
        except GarminError as error:
            if not error.unauthorized:
                raise error from None
            token, expires = obtain(settings["key"])
            raw = request(path, "Bearer " + token)
        rows = decoded_weights(raw)
        with database_session(value, write=True, minimum_version=13) as db:
            latest = read(root)["people"].get(person, {})
            if (
                latest.get("generation") != settings["generation"]
                or latest.get("claim") != claim
            ):
                raise GarminError(
                    "Garmin connection changed; synchronization was canceled."
                )
            count = import_weights(db, person, rows)
        with storage_lock(value, exclusive=True) as root:
            state = read(root)
            item = state["people"].get(person, {})
            if (
                item.get("generation") == settings["generation"]
                and item.get("claim") == claim
            ):
                item.update(
                    token=token,
                    expires=expires,
                    claim=None,
                    retry_not_before=None,
                    failures=0,
                    last_success=w.now().isoformat(),
                    error=None,
                    next_attempt=(
                        w.now() + timedelta(hours=item["interval_hours"])
                    ).isoformat(),
                )
                write(root, state)
        return count
    except (GarminError, StorageError, sqlite3.Error, OSError) as failure:
        # SQL failures roll back the whole import. Clear the short claim and
        # publish only a fixed message, never database paths, tokens or payloads.
        error = failure if isinstance(failure, GarminError) else GarminError(
            'Garmin synchronization could not be saved. Local records are preserved; retry later.'
        )
        with storage_lock(value, exclusive=True) as root:
            state = read(root)
            item = state["people"].get(person, {})
            if (
                item.get("generation") == settings["generation"]
                and item.get("claim") == claim
            ):
                failures = item.get("failures", 0) + 1
                delay = max(
                    error.retry_after, min(21600, 900 * 2 ** min(failures - 1, 5))
                )
                retry = (w.now() + timedelta(seconds=delay)).isoformat()
                item.update(
                    claim=None,
                    error=str(error),
                    failures=failures,
                    retry_not_before=retry,
                    next_attempt=retry,
                )
                if error.unauthorized:
                    item["connected"] = False
                write(root, state)
        raise error from None


def tick(value, zone):
    """Independent scheduler calls network jobs after releasing its backup lock."""
    with database_session(value) as db:
        if db.execute("PRAGMA user_version").fetchone()[0] < 13:
            return
        people = [r[0] for r in db.execute("SELECT id FROM people WHERE archived=0")]
    for person in people:
        info = public(value, person)
        if (
            not info.get("connected")
            or not info.get("automatic")
            or (
                info.get("next_attempt")
                and datetime.fromisoformat(info["next_attempt"]) > w.now()
            )
        ):
            continue
        try:
            sync(value, person, zone, scheduled=True)
        except (GarminError, StorageError):
            pass
