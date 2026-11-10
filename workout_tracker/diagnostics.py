# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Private daily JSONL diagnostics, independent of workout SQLite transactions.

App/CLI/scheduler call emit with fixed event messages. A separate logs-directory
lock coordinates processes without reentering the storage-root lock. Failures
fall back to stderr and never roll back a successful workout. Browser readers
receive safe summaries only, never protected stack frames or filesystem paths.
"""
import fcntl
import json
import os
import re
import sys
import traceback
from contextlib import contextmanager
from datetime import date, timedelta
from uuid import uuid4

from . import operations as o
from .storage import storage_root, StorageError, _sync_directory

LEVELS=('DEBUG','INFO','WARNING','ERROR','CRITICAL')
CATEGORIES=('Application','Workout','Database','Backup','Restore','Scheduler','Security')
FILE=re.compile(r'events-(\d{4}-\d{2}-\d{2})\.jsonl')


@contextmanager
def log_lock(value,exclusive=False):
    """Use the existing log directory as the cross-process lock; never create paths."""
    directory=storage_root(value)/'logs'
    descriptor=os.open(directory,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        fcntl.flock(descriptor,fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
        yield directory
    finally: os.close(descriptor)


def redact(message):
    """Remove accidental credential assignments and path strings from fixed summaries."""
    message=re.sub(r'(?i)(password|secret|signing.?key|session.?cookie|csrf.?token|authorization|cookie)\s*[:=]\s*\S+',r'\1=[REDACTED]',str(message))
    message=re.sub(r'(?<!\w)/(?:[^\s/]+/)*[^\s]*','[private path]',message)
    return message[:1000]


def emit(value,level,category,message,*,error=None):
    """Append one durable bounded event; never accept raw form bodies or SQL rows.

    Protected technical frames omit exception messages/locals, which may contain
    secrets. Browser details are separately constructed from an allowlisted type.
    """
    if level not in LEVELS or category not in CATEGORIES: return False
    try:
        stamp=o.now()
        frames=[] if error is None else [dict(file=f.filename,function=f.name,line=f.lineno) for f in traceback.extract_tb(error.__traceback__)]
        row=dict(id=uuid4().hex,timestamp=stamp.isoformat(),severity=level,category=category,message=redact(message),
                 detail=None if error is None else ((redact(str(error))+' ' if isinstance(error,StorageError) else '')+'Operation failed. Inspect protected server logs for technical frames.'),
                 technical=None if error is None else dict(type=type(error).__name__,frames=frames[-20:]))
        encoded=(json.dumps(row,ensure_ascii=True)+'\n').encode()
        with log_lock(value,True) as directory:
            path=directory/f'events-{stamp.date().isoformat()}.jsonl'
            descriptor=os.open(path,os.O_WRONLY|os.O_APPEND|os.O_CREAT|os.O_NOFOLLOW,0o600)
            with os.fdopen(descriptor,'ab') as handle:
                handle.write(encoded);handle.flush();os.fsync(handle.fileno())
            _sync_directory(directory)
        return True
    except Exception:
        print('Persistent diagnostic write unavailable; operation outcome is unchanged.',file=sys.stderr)
        return False


def reverse_lines(path):
    """Read large files backward in bounded blocks instead of loading all history."""
    descriptor=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(descriptor,'rb') as handle:
        handle.seek(0,2);position=handle.tell();tail=b''
        while position:
            size=min(65536,position);position-=size;handle.seek(position)
            pieces=(handle.read(size)+tail).split(b'\n');tail=pieces[0]
            for line in reversed(pieces[1:]):
                if line and len(line)<=32768: yield line
            if len(tail)>32768: tail=b''
        if tail: yield tail


def query(value,filters,page=1):
    """Stream newest-first entries and return one 50-row page plus a next-page flag."""
    from .catalog import ValidationError
    if filters.get('severity','') not in ('',*LEVELS) or filters.get('category','') not in ('',*CATEGORIES):
        raise ValidationError('Choose a listed severity/category.')
    start,end=filters.get('from',''),filters.get('to','')
    try:
        for part in (start,end):
            if part and date.fromisoformat(part).isoformat()!=part: raise ValueError()
        if start and end and start>end: raise ValueError()
        page=int(page)
        if not 1<=page<=10000: raise ValueError()
    except (ValueError,TypeError): raise ValidationError('Choose valid dates and page number.')
    text=filters.get('q','')[:200].casefold();rows=[];seen=0;offset=(page-1)*50
    with log_lock(value) as directory:
        paths=sorted((p for p in directory.iterdir() if FILE.fullmatch(p.name)),reverse=True)
        for path in paths:
            day=FILE.fullmatch(path.name)[1]
            if start and day<start or end and day>end: continue
            for line in reverse_lines(path):
                try: row=json.loads(line)
                except (ValueError,UnicodeDecodeError): continue
                if filters.get('severity') and row['severity']!=filters['severity'] or filters.get('category') and row['category']!=filters['category']: continue
                if text and text not in (row['message']+' '+(row['detail'] or '')).casefold(): continue
                seen+=1
                if seen<=offset: continue
                # Deliberately omit protected technical data, even in expandable details.
                rows.append({k:row[k] for k in ('id','timestamp','severity','category','message','detail')})
                if len(rows)==51: return rows[:50],True
    return rows,False


def retain(value,days):
    """Delete only named daily log files older than retention; never touch backups/data."""
    cutoff=(o.now().date()-timedelta(days=days-1)).isoformat()
    with log_lock(value,True) as directory:
        changed=False
        for path in directory.iterdir():
            match=FILE.fullmatch(path.name)
            if match and match[1]<cutoff and not path.is_symlink() and path.is_file():
                path.unlink();changed=True
        if changed: _sync_directory(directory)
