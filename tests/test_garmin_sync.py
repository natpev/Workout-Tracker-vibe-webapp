# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Realistic Garmin wire regressions; all accounts/readings/storage are synthetic."""
import json
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from workout_tracker import garmin as g, body_weight as b, catalog as c
from workout_tracker.storage import database_session
from workout_tracker.maintenance import logical_check_connection
from test_garmin import response
from test_unified_measurements import unified_root


def connected(root):
    """Create one disposable person and verify a synthetic cached credential."""
    with database_session(root, write=True) as db:
        person = c.create_person(db, "Synthetic person")
        b.manual(db, person, dict(date="2020-01-01", time="08:00", weight="220"), "UTC")
    with patch.object(g, "request", side_effect=response):
        g.connect(root, person, "synthetic-a")
    return person


def private(root, person):
    """Inspect private state only inside tests, never print its credential contents."""
    with g.storage_lock(root) as locked:
        return dict(g.read(locked)["people"][person])


@pytest.mark.parametrize(
    "timestamp",
    [
        1577865600123,
        Decimal("1577865600123.456"),
        "2020-01-01T08:00:00.123Z",
        "2020-01-01T03:00:00.123-05:00",
        "2020-01-01T08:00:00.1230000+0000",
    ],
)
def test_utc_identity_preserves_numeric_milliseconds_and_iso_offsets(timestamp):
    """Equivalent timestamp formats use the same source identity, not ingestion time."""
    actual = g.measurement_time(timestamp)
    expected = (
        "2020-01-01T08:00:00.123456+00:00"
        if isinstance(timestamp, Decimal)
        else "2020-01-01T08:00:00.123000+00:00"
    )
    assert actual == expected


@pytest.mark.parametrize(
    "timestamp",
    [
        None,
        True,
        [],
        {},
        "not a timestamp",
        "2020-01-01",
        "2020-01-01T08:00:00",
        "2020-01-01T08:00:00.1234567Z",
        "2099-01-01T00:00:00Z",
        1577865600,
        -1,
        Decimal("1e999999"),
        Decimal("NaN"),
        Decimal("1577865600000.0001"),
        Decimal("1577865600000.0000000000000000001"),
    ],
)
def test_bad_timestamp_never_creates_a_guessed_measurement(timestamp):
    """Reject seconds-as-ms, unzoned dates and unsupported precision without raw data."""
    with pytest.raises((ValueError, ArithmeticError)):
        g.measurement_time(timestamp)


@pytest.mark.parametrize(
    "grams,expected",
    [
        (100000, 220462),
        (85000, 187393),
        (45359.237, 100000),
        (1000, 2205),
        (700000, 1543236),
    ],
)
def test_gram_conversion_is_exact_until_stored_precision_and_preserves_source(
    grams, expected
):
    """Use the exact 453.59237 grams/lb definition; store source units explicitly."""
    row = g.decoded_weights(
        json.dumps([dict(timestampGMT=1577865600000, weight=grams)])
    )[0]
    assert row["weight_milli_lb"] == expected
    source = json.loads(row["source_value"])
    assert source["unit"] == "g" and Decimal(source["value"]) == Decimal(str(grams))


@pytest.mark.parametrize(
    "row",
    [
        None,
        [],
        7,
        {},
        dict(timestampGMT=None, weight=100000),
        dict(timestampGMT=1577865600000),
        *[
            dict(timestampGMT=1577865600000, weight=value)
            for value in (
                None,
                True,
                "100000",
                {},
                -1,
                0,
                100,
                999,
                700001,
                float("nan"),
                float("inf"),
            )
        ],
    ],
)
def test_malformed_missing_unrealistic_rows_refuse_the_whole_batch(row):
    """One bad reading invalidates the batch; body values never enter error messages."""
    with pytest.raises(g.GarminError) as caught:
        g.decoded_weights(
            json.dumps([dict(timestampGMT=1577865600000, weight=100000), row])
        )
    assert "100000" not in str(caught.value) and "1577865600000" not in str(
        caught.value
    )


def test_multiple_daily_weighins_deduplicate_across_wire_timestamp_formats(
    unified_root,
):
    """Same weight at different times is distinct; ISO/ms retries retain IDs and audits."""
    person = connected(unified_root)
    with patch.object(g, "request", side_effect=response):
        assert g.sync(unified_root, person, "UTC") == 2
    with database_session(unified_root) as db:
        before = [dict(r) for r in db.execute("SELECT * FROM body_weights ORDER BY id")]
    payload = json.dumps(
        [
            dict(timestampGMT="2020-01-01T03:00:00-05:00", weight=100000),
            dict(timestampGMT="2020-01-01T18:00:00Z", weight=100000),
        ]
    )
    with patch.object(g, "request", return_value=payload):
        assert g.sync(unified_root, person, "UTC") == 0
    with database_session(unified_root) as db:
        assert [
            dict(r) for r in db.execute("SELECT * FROM body_weights ORDER BY id")
        ] == before
        assert db.execute("SELECT count(*) FROM body_weight_audit").fetchone()[0] == 3
        logical_check_connection(db, 13)


@pytest.mark.parametrize(
    "failure",
    [
        AttributeError("synthetic-a secret-token 100000"),
        RuntimeError("synthetic-a secret-token 100000"),
        KeyboardInterrupt(),
        SystemExit(),
    ],
)
def test_unexpected_errors_and_cancellation_release_claim_without_secrets(
    unified_root, failure
):
    """Roll back imports and clear claims even for errors outside the old exception list."""
    person = connected(unified_root)
    before = private(unified_root, person)
    with patch.object(g, "request", side_effect=response), patch.object(
        b, "audit", side_effect=failure
    ):
        expected = (
            type(failure) if not isinstance(failure, Exception) else g.GarminError
        )
        with pytest.raises(expected):
            g.sync(unified_root, person, "UTC")
    after = private(unified_root, person)
    assert after["claim"] is None and after["retry_not_before"]
    for field in ("key", "token", "generation", "connected", "expires"):
        assert after[field] == before[field]
    assert all(
        secret not in after["error"]
        for secret in ("synthetic-a", "secret-token", "100000")
    )
    with database_session(unified_root) as db:
        assert len(b.records(db, person, "UTC")) == 1
        logical_check_connection(db, 13)


def test_validation_failure_clears_claim_and_preserves_entire_existing_database(
    unified_root,
):
    """Malformed API timestamps cannot leave progress stuck or partially import good rows."""
    person = connected(unified_root)
    with patch.object(
        g,
        "request",
        return_value=json.dumps(
            [
                dict(timestampGMT=1577865600000, weight=100000),
                dict(timestampGMT={}, weight=100000),
            ]
        ),
    ):
        with pytest.raises(g.GarminError, match="invalid weight data"):
            g.sync(unified_root, person, "UTC")
    assert private(unified_root, person)["claim"] is None
    with database_session(unified_root) as db:
        assert len(b.records(db, person, "UTC")) == 1


def test_killed_worker_lease_recovers_and_concurrent_current_claim_is_protected(
    unified_root,
):
    """A hard-killed worker cannot run finally; its bounded claim expires on retry."""
    person = connected(unified_root)
    with g.storage_lock(unified_root, exclusive=True) as root:
        state = g.read(root)
        state["people"][person].update(
            claim="abandoned-synthetic",
            last_attempt=(g.w.now() - timedelta(minutes=6)).isoformat(),
        )
        g.write(root, state)
    with patch.object(g, "request", side_effect=response):
        assert g.sync(unified_root, person, "UTC") == 2
    assert private(unified_root, person)["claim"] is None
    with g.storage_lock(unified_root, exclusive=True) as root:
        state = g.read(root)
        state["people"][person].update(
            claim="active-synthetic", last_attempt=g.w.now().isoformat()
        )
        g.write(root, state)
    with patch.object(g, "request") as remote:
        with pytest.raises(g.GarminError, match="already in progress"):
            g.sync(unified_root, person, "UTC")
        remote.assert_not_called()
    assert private(unified_root, person)["claim"] == "active-synthetic"


def test_legacy_imports_are_not_blindly_reinterpreted_or_rewritten(unified_root):
    """Preserve old source values/audits and atomically refuse an ambiguous old mismatch."""
    person = connected(unified_root)
    old = dict(
        measured_at="2020-01-01T08:00:00.000000+00:00",
        weight_milli_lb=220462262,
        source_value="100000",
    )
    with database_session(unified_root, write=True) as db:
        g.import_weights(db, person, [old])
    with database_session(unified_root) as db:
        before = [dict(r) for r in db.execute("SELECT * FROM body_weights ORDER BY id")]
        audits = [
            dict(r) for r in db.execute("SELECT * FROM body_weight_audit ORDER BY id")
        ]
    with patch.object(g, "request", side_effect=response):
        with pytest.raises(g.GarminError, match="older import format"):
            g.sync(unified_root, person, "UTC")
    with database_session(unified_root) as db:
        assert [
            dict(r) for r in db.execute("SELECT * FROM body_weights ORDER BY id")
        ] == before
        assert [
            dict(r) for r in db.execute("SELECT * FROM body_weight_audit ORDER BY id")
        ] == audits
        logical_check_connection(db, 13)


def test_conflicting_measurements_at_one_timestamp_are_rejected_but_equal_decimals_retry():
    """Normalize source timestamps without collapsing conflicting or distinct readings."""
    first = dict(timestampGMT=1577865600000, weight=100000)
    assert (
        len(
            g.decoded_weights(
                json.dumps(
                    [first, dict(timestampGMT="2020-01-01T08:00:00Z", weight=100000.0)]
                )
            )
        )
        == 1
    )
    with pytest.raises(g.GarminError, match="conflicting"):
        g.decoded_weights(
            json.dumps([first, dict(timestampGMT="2020-01-01T08:00:00Z", weight=99000)])
        )


def test_newer_claim_is_never_cleared_or_overwritten_by_an_older_worker(unified_root):
    """A reclaimed/disconnected request cannot import or clear someone else's claim."""
    person = connected(unified_root)

    def replaced_request(*args, **kwargs):
        """Simulate a newer owner taking over while the old HTTPS request is in flight."""
        with g.storage_lock(unified_root, exclusive=True) as root:
            state = g.read(root)
            state["people"][person]["claim"] = "newer-owner"
            g.write(root, state)
        return response(*args, **kwargs)

    with patch.object(g, "request", side_effect=replaced_request):
        with pytest.raises(g.GarminError, match="changed"):
            g.sync(unified_root, person, "UTC")
    assert private(unified_root, person)["claim"] == "newer-owner"
    with database_session(unified_root) as db:
        assert len(b.records(db, person, "UTC")) == 1


def test_matching_untagged_legacy_reading_remains_byte_for_byte_unchanged(unified_root):
    """Correct older imports need no metadata rewrite or new audit just to sync again."""
    person = connected(unified_root)
    old = dict(
        measured_at="2020-01-01T08:00:00.000000+00:00",
        weight_milli_lb=220462,
        source_value="100",
    )
    with database_session(unified_root, write=True) as db:
        g.import_weights(db, person, [old])
    with database_session(unified_root) as db:
        before = [dict(r) for r in db.execute("SELECT * FROM body_weights ORDER BY id")]
        audits = [
            dict(r) for r in db.execute("SELECT * FROM body_weight_audit ORDER BY id")
        ]
    with patch.object(
        g,
        "request",
        return_value=json.dumps([dict(timestampGMT=1577865600000, weight=100000)]),
    ):
        assert g.sync(unified_root, person, "UTC") == 0
    with database_session(unified_root) as db:
        assert [
            dict(r) for r in db.execute("SELECT * FROM body_weights ORDER BY id")
        ] == before
        assert [
            dict(r) for r in db.execute("SELECT * FROM body_weight_audit ORDER BY id")
        ] == audits


@pytest.mark.parametrize(
    "timestamp",
    ["2020-01-01T08:00Z", "20200101T080000+0000", "2020-W01-3T08:00:00+00:00"],
)
def test_valid_iso_forms_do_not_require_fractional_seconds(timestamp):
    """The ISO parser accepts valid minute/basic/week forms and normalizes the same instant."""
    assert g.measurement_time(timestamp) == "2020-01-01T08:00:00.000000+00:00"
