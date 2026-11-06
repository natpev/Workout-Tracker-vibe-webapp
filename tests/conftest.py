# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""Shared Phase 2 pytest fixtures; all paths are temporary and disposable.

Initialize schema 1 explicitly, migrate its separate candidate, then give tests
an application using only that new storage. No production config is consulted.
"""

import pytest

from workout_tracker import create_app
from workout_tracker.migrations import migrate_storage
from workout_tracker.storage import initialize_storage


@pytest.fixture
def phase2_root(tmp_path):
    """Return a verified migrated fixture while retaining its schema-1 original."""
    root = tmp_path / "phase2"
    initialize_storage(root)
    migrate_storage(root)
    return root


@pytest.fixture
def phase2_app(phase2_root):
    """Create an app with explicit disposable storage and exception propagation."""
    return create_app({"WORKOUT_DATA_ROOT": phase2_root, "TESTING": True})


@pytest.fixture
def phase2_client(phase2_app):
    """Use Flask's isolated browser cookie jar, including its signed CSRF state."""
    return phase2_app.test_client()


@pytest.fixture
def phase3_root(phase2_root):
    """Upgrade a disposable populated-capable schema 2 through a separate candidate."""
    migrate_storage(phase2_root, target_version=3)
    return phase2_root


@pytest.fixture
def phase3_app(phase3_root):
    """Use an explicit DST-aware test zone, never household configuration/data."""
    return create_app({'WORKOUT_DATA_ROOT': phase3_root, 'WORKOUT_TIMEZONE': 'America/Indiana/Indianapolis', 'TESTING': True})
