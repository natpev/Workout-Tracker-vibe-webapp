# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Official-contract Garmin mocks only: no real keys, accounts or remote API calls."""
import base64
import json
from datetime import timedelta
from unittest.mock import patch
import pytest
from workout_tracker import (
    garmin as g,
    catalog as c,
    workouts as w,
    body_weight as b,
    create_app,
)
from workout_tracker.storage import database_session
from test_unified_measurements import unified_root


def token():
    """Synthetic JWT expiry is sufficient for the official plain-text response contract."""
    payload = (
        base64.urlsafe_b64encode(
            json.dumps(
                {"exp": int((w.now() + timedelta(hours=12)).timestamp())}
            ).encode()
        )
        .decode()
        .rstrip("=")
    )
    return "synthetic." + payload + ".not-a-real-signature"


def response(path, auth, **kwargs):
    """Use individual wire readings in grams and Unix epoch milliseconds."""
    if path == g.TOKEN:
        assert auth in ("ApiKey synthetic-a", "ApiKey synthetic-b")
        return token()
    assert path.startswith("/weight-service/weight/all/") and auth.startswith(
        "Bearer synthetic."
    )
    return json.dumps(
        [
            {"timestampGMT": 1577865600000, "weight": 100000},
            {"timestampGMT": 1577901600000, "weight": 100000},
        ]
    )


def test_independent_credentials_sync_idempotency_multiple_readings_and_secrecy(
    unified_root,
):
    """Person-specific timestamp IDs never merge Manual readings or leak saved secrets."""
    with database_session(unified_root, write=True) as db:
        a = c.create_person(db, "A")
        other = c.create_person(db, "B")
        b.manual(db, a, dict(date="2020-01-01", time="08:00", weight="220"), "UTC")
    with patch.object(g, "request", side_effect=response):
        g.connect(unified_root, a, "synthetic-a")
        g.connect(unified_root, other, "synthetic-b")
        assert g.sync(unified_root, a, "UTC") == 2
        assert g.sync(unified_root, a, "UTC") == 0
        with database_session(unified_root) as db:
            assert len(b.records(db, a, "UTC")) == 3 and not b.records(db, other, "UTC")
        assert g.sync(unified_root, other, "UTC") == 2
    private = unified_root / "config" / g.STATE_FILE
    assert private.stat().st_mode & 0o777 == 0o600
    assert "synthetic-a" not in json.dumps(g.public(unified_root, a))
    app = create_app({"TESTING": True, "WORKOUT_DATA_ROOT": unified_root})
    for url in (f"/people/{a}/garmin", f"/people/{a}/weight"):
        page = app.test_client().get(url)
        assert (
            page.status_code == 200
            and b"synthetic-a" not in page.data
            and token().encode() not in page.data
        )
    g.disconnect(unified_root, a)
    assert (
        not g.public(unified_root, a)["connected"]
        and g.public(unified_root, other)["connected"]
    )
    with database_session(unified_root) as db:
        assert len(b.records(db, a, "UTC")) == 3


def test_garmin_failure_preserves_local_records_and_records_safe_status(unified_root):
    """Timeouts/auth failure never erase locally stored data or disclose API credentials."""
    with database_session(unified_root, write=True) as db:
        person = c.create_person(db, "A")
    with patch.object(g, "request", side_effect=response):
        g.connect(unified_root, person, "synthetic-a")
    with patch.object(
        g,
        "request",
        side_effect=g.GarminError(
            "Garmin could not be reached. Local records are unchanged."
        ),
    ):
        with pytest.raises(g.GarminError):
            g.sync(unified_root, person, "UTC")
    state = g.public(unified_root, person)
    assert state["last_attempt"] and state["last_success"] is None and state["error"]
    with database_session(unified_root) as db:
        assert not b.records(db, person, "UTC")


def test_conflicting_source_timestamps_refuse_without_guessing():
    """The official DTO exposes timestamps but no ID; ambiguous conflicting pairs fail."""
    rows = [
        dict(timestampGMT="2020-01-01T08:00:00Z", weight=100000),
        dict(timestampGMT="2020-01-01T08:00:00Z", weight=90000),
    ]
    with pytest.raises(g.GarminError, match="conflicting"):
        g.decoded_weights(json.dumps(rows))


def test_automatic_sync_uses_independent_scheduler_and_expired_token_renews(
    unified_root,
):
    """Explicit schedules import once; an expired cached token is obtained again."""
    with database_session(unified_root, write=True) as db:
        person = c.create_person(db, "A")
    with patch.object(g, "request", side_effect=response) as calls:
        g.connect(unified_root, person, "synthetic-a")
        g.schedule(unified_root, person, True, "6")
        g.tick(unified_root, "UTC")
        first = calls.call_count
        g.tick(unified_root, "UTC")
        assert calls.call_count == first
        with g.storage_lock(unified_root, exclusive=True) as root:
            state = g.read(root)
            state["people"][person]["expires"] = 0
            g.write(root, state)
        assert g.sync(unified_root, person, "UTC") == 0
        assert calls.call_count == first + 2


def test_revised_garmin_record_is_audited_not_duplicated(unified_root):
    """Stable timestamp updates one imported record; equal weight at other times stays distinct."""
    with database_session(unified_root, write=True) as db:
        person = c.create_person(db, "A")
    with patch.object(g, "request", side_effect=response):
        g.connect(unified_root, person, "synthetic-a")
        g.sync(unified_root, person, "UTC")
    changed = json.dumps([dict(timestampGMT="2020-01-01T08:00:00Z", weight=99000)])
    with patch.object(g, "request", return_value=changed):
        assert g.sync(unified_root, person, "UTC") == 1
    with database_session(unified_root) as db:
        assert len(b.records(db, person, "UTC")) == 2
        assert db.execute("SELECT count(*) FROM body_weight_audit").fetchone()[0] == 3
        from workout_tracker.maintenance import logical_check_connection

        logical_check_connection(db, 13)


def test_rate_limit_and_disconnect_during_request_are_safe(unified_root):
    """Backoff blocks immediate retries; connection generation cancels stale imports."""
    with database_session(unified_root, write=True) as db:
        person = c.create_person(db, "A")
    with patch.object(g, "request", side_effect=response):
        g.connect(unified_root, person, "synthetic-a")
    with patch.object(
        g,
        "request",
        side_effect=g.GarminError("Garmin is limiting requests.", retry_after=3600),
    ):
        with pytest.raises(g.GarminError):
            g.sync(unified_root, person, "UTC")
    with patch.object(g, "request") as remote:
        with pytest.raises(g.GarminError, match="deferred"):
            g.sync(unified_root, person, "UTC")
        remote.assert_not_called()
    with patch.object(g, "request", side_effect=response):
        g.connect(unified_root, person, "synthetic-a")

    def disconnecting(*args, **kwargs):
        g.disconnect(unified_root, person)
        return response(*args, **kwargs)

    with patch.object(g, "request", side_effect=disconnecting):
        with pytest.raises(g.GarminError, match="changed"):
            g.sync(unified_root, person, "UTC")
    with database_session(unified_root) as db:
        assert not b.records(db, person, "UTC")


@pytest.mark.parametrize(
    "raw",
    [
        "not json",
        "{}",
        '[{"weight":0,"timestampGMT":"2020-01-01T00:00:00Z"}]',
        '[{"weight":100,"timestampGMT":"2020-01-01T00:00:00"}]',
    ],
)
def test_malformed_official_responses_do_not_guess_measurements(raw):
    """No missing units, zero body weights or timezone-naive identities enter storage."""
    with pytest.raises(g.GarminError):
        g.decoded_weights(raw)


def test_failed_import_rolls_back_all_rows_and_releases_retry_claim(unified_root):
    """A storage failure midway through import cannot retain half a batch or a stuck claim."""
    from workout_tracker.storage import StorageError
    with database_session(unified_root,write=True) as db:person=c.create_person(db,'A')
    with patch.object(g,'request',side_effect=response):
        g.connect(unified_root,person,'synthetic-a')
        with patch.object(b,'audit',side_effect=StorageError('Synthetic private path')):
            with pytest.raises(g.GarminError,match='preserved'):g.sync(unified_root,person,'UTC')
    with database_session(unified_root) as db:assert not b.records(db,person,'UTC')
    with g.storage_lock(unified_root) as root:
        item=g.read(root)['people'][person]
        assert item['claim'] is None and item['retry_not_before']
        assert 'Synthetic private path' not in item['error'] and 'synthetic-a' not in item['error']
