# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Consistent read-only-source SQLite download using backup API, never raw file copying.

The returned open temporary file has already been unlinked. The WSGI response
owns its lifetime, so downloads, disconnects and failures leave no retained file.
"""
import os
import sqlite3
import tempfile
import time
from pathlib import Path
from .storage import storage_lock, _inspect_unlocked, StorageError
from .maintenance import logical_check


def snapshot(value):
    """Copy under the existing selection/read lock, verify, then release all database locks."""
    descriptor, path = tempfile.mkstemp(prefix="workout-download-", suffix=".sqlite3")
    os.close(descriptor)
    path = Path(path)
    try:
        with storage_lock(value) as root:
            details = _inspect_unlocked(root)
            source = sqlite3.connect(
                details["database"].as_uri() + "?mode=ro", uri=True
            )
            target = sqlite3.connect(path)
            deadline = time.monotonic() + 60

            def progress(status, remaining, total):
                """A busy/slow source cannot hold household writes indefinitely."""
                if time.monotonic() > deadline:
                    raise StorageError(
                        "Database download timed out; the active database was not changed."
                    )

            try:
                source.backup(target, pages=128, progress=progress, sleep=0.01)
            finally:
                target.close()
                source.close()
            _inspect_unlocked(root, database_override=path)
            logical_check(path, details["schema_version"])
        handle = path.open("rb")
        path.unlink()
        return handle
    finally:
        if path.exists():
            path.unlink()
