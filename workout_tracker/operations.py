# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""External operations state shared by Settings, maintenance and scheduler.

Callers hold the existing exclusive storage-root lock before writing this JSON.
Atomic private files persist settings and idempotency without changing SQLite.
Missing state means disabled defaults; malformed existing state is never replaced.
"""
import json
import os
import re
from datetime import datetime, timezone
from uuid import uuid4

from .storage import StorageError, _regular_file, _sync_directory, _unique_object, DIRECTORIES


def now():
    """Return aware UTC; tests replace this clock without sleeping."""
    return datetime.now(timezone.utc)


def defaults():
    """Return fresh disabled settings; reading does not create any files."""
    return dict(version=1, schedule=dict(enabled=False, days=1, time='02:00', timezone='Etc/UTC',
                anchor=None, revision=0, next=None, last_attempt=None, last_success=None, result='Never attempted'),
                retention_days=30, backups={}, restores={})


def layout(root):
    """Refuse missing or linked subdirectories even when damaged SQLite prevents startup."""
    for name in DIRECTORIES:
        if (root/name).is_symlink() or not (root/name).is_dir():
            raise StorageError('Persistent operations layout is incomplete or unsafe.')


def read_state(root):
    """Load bounded, private operator metadata; fail closed on unexpected contents."""
    layout(root)
    path=root/'config'/'operations.json'
    if not os.path.lexists(path):
        return defaults()
    try:
        _regular_file(path)
        if path.stat().st_size>32*1024*1024 or path.stat().st_mode & 0o077:
            raise ValueError('Unsafe operations metadata')
        state=json.loads(path.read_text(),object_pairs_hook=_unique_object)
        if set(state)!=set(defaults()) or state['version']!=1 or not isinstance(state['backups'],dict) or not isinstance(state['restores'],dict):
            raise ValueError('Invalid operations metadata')
        if set(state['schedule'])!=set(defaults()['schedule']) or type(state['retention_days']) is not int or not 1<=state['retention_days']<=36500:
            raise ValueError('Invalid operations settings')
        schedule=state['schedule']
        from datetime import time,date
        from zoneinfo import ZoneInfo
        if type(schedule['enabled']) is not bool or type(schedule['days']) is not int or not 1<=schedule['days']<=3650:
            raise ValueError('Invalid scheduling values')
        if type(schedule['revision']) is not int or schedule['revision']<0 or not isinstance(schedule['result'],str):
            raise ValueError('Invalid schedule revision/result')
        if not re.fullmatch(r'[0-9]{2}:[0-9]{2}',schedule['time']): raise ValueError('Invalid schedule time')
        time.fromisoformat(schedule['time']);ZoneInfo(schedule['timezone'])
        if schedule['anchor'] is not None: date.fromisoformat(schedule['anchor'])
        for key in ('next','last_attempt','last_success'):
            if schedule[key] is not None and datetime.fromisoformat(schedule[key]).tzinfo is None:
                raise ValueError('Schedule timestamp must be aware')
        if schedule['enabled'] and (schedule['anchor'] is None or schedule['next'] is None):
            raise ValueError('Enabled schedule is incomplete')
        for key,record in state['backups'].items():
            identity(key)
            if record['id']!=key or record['status'] not in ('in_progress','verified','failed','deleted','deletion_pending') or record['source'] not in ('manual','automatic'):
                raise ValueError('Invalid backup metadata')
            if type(record['size']) is not int or record['size']<0: raise ValueError('Invalid backup size')
            if record['status']=='verified' and not re.fullmatch('[0-9a-f]{64}',record['sha256']): raise ValueError('Invalid backup hash')
        for key,record in state['restores'].items():
            identity(key);identity(record['backup_id'])
            if record['id']!=key or record['status'] not in ('in_progress','succeeded','failed','uncertain'):
                raise ValueError('Invalid restore metadata')
        return state
    except (OSError, ValueError, TypeError, KeyError) as error:
        raise StorageError('Operations metadata cannot be verified; it was not replaced.') from error


def write_state(root,state):
    """Sync a separate JSON file before atomic publication; root lock serializes writers."""
    layout(root)
    pending=root/'config'/f'operations-{uuid4().hex}.pending'
    descriptor=os.open(pending,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
    with os.fdopen(descriptor,'w') as handle:
        json.dump(state,handle,sort_keys=True,allow_nan=False)
        handle.flush();os.fsync(handle.fileno())
    os.replace(pending,root/'config'/'operations.json')
    _sync_directory(root/'config')


def identity(value):
    """Only unguessable server-issued IDs may select operation records/files."""
    if not isinstance(value,str) or not re.fullmatch('[0-9a-f]{32}',value):
        raise StorageError('Choose an existing server-listed operation.')
    return value
