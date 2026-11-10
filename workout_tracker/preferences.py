# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Person accent preferences, separate from immutable workout records and schedules.

Settings writes a private atomic JSON file under the existing storage-root lock.
GET never creates it. Defaults work with existing installations and schemas;
SQLite files, backups and original migration versions are never changed here.
"""
import json
import os
import sqlite3
from contextlib import closing
from uuid import uuid4

from . import catalog
from .storage import storage_lock,_inspect_unlocked,_regular_file,_unique_object,_sync_directory,StorageError

SOFT=('blue','teal','green','purple','orange','red')
PALETTE=SOFT+tuple('vibrant-'+color for color in SOFT)


def read(root):
    """Read validated preferences; a missing file means blue for every existing person."""
    path=root/'config'/'person-preferences.json'
    if not os.path.lexists(path): return {'version':1,'people':{}}
    try:
        _regular_file(path)
        if path.stat().st_size>1024*1024 or path.stat().st_mode & 0o077: raise ValueError()
        value=json.loads(path.read_text(),object_pairs_hook=_unique_object)
        if set(value)!= {'version','people'} or value['version']!=1 or not isinstance(value['people'],dict): raise ValueError()
        for identity,color in value['people'].items():
            if len(identity)!=32 or any(ch not in '0123456789abcdef' for ch in identity) or color not in PALETTE: raise ValueError()
        return value
    except (OSError,ValueError,TypeError,KeyError) as error:
        raise StorageError('Person preferences cannot be verified; existing file was preserved.') from error


def colors(value):
    """Load person-owned UUID/color mappings read-only under the shared root lock."""
    with storage_lock(value) as root: return read(root)['people']


def set_color(value,person_id,color):
    """Verify the person then atomically persist an allowlisted color, without SQL writes."""
    if color not in PALETTE: raise catalog.ValidationError('Choose a listed accent color.')
    with storage_lock(value,exclusive=True) as root:
        selected=_inspect_unlocked(root)
        if selected['schema_version']<2: raise StorageError('People require an explicit schema upgrade.')
        with closing(sqlite3.connect(selected['database'].as_uri()+'?mode=ro',uri=True)) as db:
            db.row_factory=sqlite3.Row
            db.execute('PRAGMA foreign_keys=ON');db.execute('PRAGMA trusted_schema=OFF');db.execute('PRAGMA query_only=ON')
            catalog.person(db,person_id,archived=True)
        settings=read(root);settings['people'][person_id]=color
        pending=root/'config'/f'person-preferences-{uuid4().hex}.pending'
        descriptor=os.open(pending,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
        with os.fdopen(descriptor,'w') as handle:
            json.dump(settings,handle,sort_keys=True);handle.flush();os.fsync(handle.fileno())
        os.replace(pending,root/'config'/'person-preferences.json');_sync_directory(root/'config')
