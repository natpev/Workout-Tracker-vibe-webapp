# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""Dedicated server-side scheduler; Gunicorn workers never start job threads.

External settings persist an anchor local date and the next UTC occurrence.
Claiming a due slot and backup intent happens under the same root lock used by
workouts/restores. A crash is at-most-once, recorded as interrupted, not replayed.
"""
import hashlib
import signal
import threading
from datetime import date,datetime,time,timedelta,timezone
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError

from . import operations as o
from .maintenance import backup_locked,event
from .storage import storage_lock,StorageError,_inspect_unlocked
from .catalog import ValidationError,integer
from .diagnostics import retain


def local_slot(day,clock,zone):
    """Choose earlier repeated-hour instant; nonexistent time advances to first valid minute."""
    naive=datetime.combine(day,time.fromisoformat(clock));z=ZoneInfo(zone)
    for _ in range(181):
        candidate=naive.replace(tzinfo=z,fold=0)
        if candidate.astimezone(timezone.utc).astimezone(z).replace(tzinfo=None)==naive:
            return candidate.astimezone(timezone.utc)
        naive+=timedelta(minutes=1)
    raise StorageError('Scheduled local time could not be resolved.')


def next_slot(schedule,after):
    """Find the next anchor-based day strictly after UTC after; frequency is calendar days."""
    z=ZoneInfo(schedule['timezone']);day=after.astimezone(z).date();anchor=date.fromisoformat(schedule['anchor'])
    if day<anchor: day=anchor
    difference=(day-anchor).days
    day+=timedelta(days=(-difference)%schedule['days'])
    candidate=local_slot(day,schedule['time'],schedule['timezone'])
    if candidate<=after:
        candidate=local_slot(day+timedelta(days=schedule['days']),schedule['time'],schedule['timezone'])
    return candidate.isoformat()


def configure(value,values):
    """Validate browser settings and atomically replace schedule/retention under root lock."""
    enabled=values.get('enabled')=='yes'
    days=integer(values.get('days'),'Frequency in days',1,3650)
    clock=values.get('time','');zone=values.get('timezone','')
    try:
        if len(clock)!=5 or time.fromisoformat(clock).strftime('%H:%M')!=clock: raise ValueError()
        ZoneInfo(zone)
    except (ValueError,ZoneInfoNotFoundError): raise ValidationError('Choose HH:MM and a valid installed IANA timezone.')
    retention=integer(values.get('retention_days'),'Log retention days',1,36500)
    with storage_lock(value,exclusive=True) as root:
        _inspect_unlocked(root);state=o.read_state(root);old=state['schedule']
        schedule=dict(old,enabled=enabled,days=days,time=clock,timezone=zone,revision=old['revision']+1,
                      anchor=o.now().astimezone(ZoneInfo(zone)).date().isoformat())
        schedule['next']=next_slot(schedule,o.now()) if enabled else None
        state.update(schedule=schedule,retention_days=retention);o.write_state(root,state)
        event(root,'INFO','Scheduler','Schedule and log retention settings updated')
    retain(value,retention)


def tick(value):
    """Claim at most one overdue run, skip backlog, and persist outcome before releasing lock."""
    with storage_lock(value,exclusive=True) as root:
        _inspect_unlocked(root);state=o.read_state(root);schedule=state['schedule'];stamp=o.now()
        # The previous owner released this root lock (possibly by crashing).
        # Pending operations are not replayed: preserve evidence and make failure visible.
        changed=False
        for record in state['backups'].values():
            if record['status']=='in_progress':
                record.update(status='failed',error='Interrupted attempt; retained file is not verified.');changed=True
                if record['source']=='automatic': schedule['result']='Failed: interrupted attempt'
        if schedule['result']=='In progress':
            schedule['result']='Failed: interrupted before result was persisted';changed=True
        if changed: o.write_state(root,state)
        if not schedule['enabled'] or not schedule['next'] or datetime.fromisoformat(schedule['next'])>stamp:
            retention=state['retention_days']
        else:
            slot=schedule['next']
            token=hashlib.sha256(f"{schedule['revision']}:{slot}".encode()).hexdigest()[:32]
            schedule.update(last_attempt=stamp.isoformat(),result='In progress',next=next_slot(schedule,stamp))
            o.write_state(root,state)
            event(root,'INFO','Scheduler','Due backup slot claimed; missed backlog is skipped')
            result=backup_locked(root,state,token,'automatic')
            schedule['result']='Verified' if result['status']=='verified' else 'Failed'
            if result['status']=='verified': schedule['last_success']=result['verified_at']
            o.write_state(root,state);retention=state['retention_days']
    retain(value,retention)


def run(value,interval=30):
    """CLI/container loop with graceful SIGTERM shutdown and no browser dependency."""
    stop=threading.Event()
    for signum in (signal.SIGTERM,signal.SIGINT):
        signal.signal(signum,lambda *_:stop.set())
    event(value,'INFO','Scheduler','Scheduler process started')
    try:
        while not stop.is_set():
            try: tick(value)
            except Exception as error: event(value,'ERROR','Scheduler','Scheduler cycle failed; no unsafe replacement attempted',error)
            stop.wait(interval)
    finally: event(value,'INFO','Scheduler','Scheduler process stopped')
