# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""Deterministic scheduler/log tests use fake UTC clocks and disposable storage.

They cover disabled defaults, DST, durable slot claims, interruption and filters.
No scheduler thread, real time wait, household data or external network is used.
"""
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone,timedelta,date
from uuid import uuid4

import pytest
from click.testing import CliRunner
from workout_tracker import scheduler as s,operations as o,maintenance as m,diagnostics as d
from workout_tracker.__main__ import main
from workout_tracker.storage import storage_lock,StorageError
from workout_tracker.catalog import ValidationError


def clock(monkeypatch,value):
    """Replace the shared operations/log/scheduler UTC clock deterministically."""
    instant=datetime.fromisoformat(value)
    monkeypatch.setattr(o,'now',lambda:instant)
    return instant


def settings(**changes):
    """Return valid explicit settings; callers change only the scenario under test."""
    return dict(dict(enabled='yes',days='1',time='10:30',timezone='Etc/UTC',retention_days='30'),**changes)


def state(root):
    """Read external metadata under the same shared lock used by Settings."""
    with storage_lock(root): return o.read_state(root)


def test_disabled_defaults_never_create_backup_or_config(phase4_root):
    """A scheduler can start/restart without configuring or touching any database."""
    root=phase4_root;before={p:p.read_bytes() for p in (root/'data').iterdir()}
    for _ in range(3): s.tick(root)
    assert not (root/'config'/'operations.json').exists() and list((root/'backups').iterdir())==[]
    assert state(root)['schedule']['enabled'] is False
    assert all(p.read_bytes()==value for p,value in before.items())
    result=CliRunner().invoke(main,['scheduler','--data-root',str(root),'--once'])
    assert result.exit_code==0


@pytest.mark.parametrize('days',['1','3'])
def test_daily_multiday_customtime_missed_once_and_persistence(phase4_root,monkeypatch,days):
    """Multi-day cadence survives new readers and coalesces a long missed backlog."""
    root=phase4_root;clock(monkeypatch,'2026-01-01T09:00:00+00:00');s.configure(root,settings(days=days))
    assert state(root)['schedule']['next']=='2026-01-01T10:30:00+00:00'
    s.tick(root);assert not state(root)['backups']
    clock(monkeypatch,'2026-01-01T10:30:00+00:00');s.tick(root);s.tick(root)
    first=state(root);assert len(first['backups'])==1 and first['schedule']['result']=='Verified'
    assert first['schedule']['last_success']==first['schedule']['last_attempt']
    expected_day=1+int(days)
    assert first['schedule']['next']==f'2026-01-{expected_day:02}T10:30:00+00:00'
    clock(monkeypatch,'2026-02-20T18:00:00+00:00')
    s.tick(root);s.tick(root)
    current=state(root);assert len(current['backups'])==2
    assert datetime.fromisoformat(current['schedule']['next'])>o.now()
    assert all(row['source']=='automatic' and row['status']=='verified' for row in current['backups'].values())


def test_competing_scheduler_processes_claim_one_slot(phase4_root,monkeypatch):
    """Independent invocations serialize at the OS lock and cannot duplicate a due job."""
    clock(monkeypatch,'2026-01-01T09:00:00+00:00');s.configure(phase4_root,settings())
    clock(monkeypatch,'2026-01-01T11:00:00+00:00')
    with ThreadPoolExecutor(4) as pool: list(pool.map(s.tick,[phase4_root]*4))
    assert len(state(phase4_root)['backups'])==1


def test_failed_automatic_backup_and_interrupted_claim_are_visible(phase4_root,monkeypatch):
    """Failed/aborted jobs never become successful or replay their already claimed slot."""
    root=phase4_root;clock(monkeypatch,'2026-01-01T09:00:00+00:00');s.configure(root,settings())
    def fail(*args):
        """Inject a persistent-copy failure, preserving the selected source."""
        raise OSError('injected full disk')
    monkeypatch.setattr(m,'copy_database',fail)
    clock(monkeypatch,'2026-01-01T11:00:00+00:00');s.tick(root)
    current=state(root);assert current['schedule']['result']=='Failed' and current['schedule']['last_success'] is None
    assert next(iter(current['backups'].values()))['status']=='failed'
    # Simulate process loss after the durable claim but before the outcome write.
    with storage_lock(root,exclusive=True):
        current['schedule']['result']='In progress'
        row=next(iter(current['backups'].values()));row['status']='in_progress';o.write_state(root,current)
    s.tick(root);current=state(root)
    assert 'interrupted' in current['schedule']['result'] and len(current['backups'])==1
    assert next(iter(current['backups'].values()))['status']=='failed'


def test_dst_gap_fold_and_calendar_day_frequency():
    """Spring gaps use first valid minute; fall folds run once at the earlier instant."""
    zone='America/New_York'
    assert s.local_slot(date(2026,3,8),'02:30',zone).isoformat()=='2026-03-08T07:00:00+00:00'
    assert s.local_slot(date(2026,11,1),'01:30',zone).isoformat()=='2026-11-01T05:30:00+00:00'
    schedule=dict(anchor='2026-10-31',days=1,time='01:30',timezone=zone)
    assert s.next_slot(schedule,datetime.fromisoformat('2026-11-01T05:31:00+00:00'))=='2026-11-02T06:30:00+00:00'


@pytest.mark.parametrize('change',[dict(days='0'),dict(days='1.5'),dict(time='25:00'),dict(time='1:00'),dict(timezone='Not/AZone'),dict(retention_days='0')])
def test_invalid_schedule_never_changes_settings(phase4_root,change):
    """Server-side validation precedes any persistent state write."""
    before=state(phase4_root)
    with pytest.raises(ValidationError): s.configure(phase4_root,settings(**change))
    assert state(phase4_root)==before


def test_schedule_disable_and_changes_replace_next_slot(phase4_root,monkeypatch):
    """Saved settings take effect on the next cycle rather than a worker-local cached copy."""
    clock(monkeypatch,'2026-01-01T09:00:00+00:00');s.configure(phase4_root,settings())
    s.configure(phase4_root,settings(time='12:45',timezone='America/New_York'))
    assert state(phase4_root)['schedule']['next']=='2026-01-01T17:45:00+00:00'
    s.configure(phase4_root,settings(enabled=''))
    clock(monkeypatch,'2026-02-01T09:00:00+00:00');s.tick(phase4_root)
    assert not state(phase4_root)['backups'] and state(phase4_root)['schedule']['next'] is None


def test_logging_persistence_pagination_filters_and_private_details(phase4_root,monkeypatch):
    """Independent readers see newest events without returning stack paths or secrets."""
    root=phase4_root;clock(monkeypatch,'2026-01-01T12:00:00+00:00')
    for index in range(65): assert d.emit(root,'INFO','Application',f'Fixture event {index}')
    try: raise RuntimeError('password=hidden csrf_token=hidden /private/data secret=hidden')
    except RuntimeError as error:
        assert d.emit(root,'ERROR','Backup','Backup failed password=hidden secret=hidden /private/data',error=error)
    rows,more=d.query(root,{'from':'2026-01-01','to':'2026-01-01'})
    assert len(rows)==50 and more and rows[0]['severity']=='ERROR' and 'technical' not in rows[0]
    assert 'hidden' not in json.dumps(rows) and '/private' not in json.dumps(rows)
    second,more=d.query(root,{'from':'2026-01-01','to':'2026-01-01'},2)
    assert len(second)==16 and not more
    assert len(d.query(root,{'severity':'ERROR','category':'Backup'})[0])==1
    assert len(d.query(root,{'q':'Fixture event 64'})[0])==1
    assert not d.query(root,{'from':'2026-01-02','to':'2026-01-03'})[0]
    log=(root/'logs'/'events-2026-01-01.jsonl').read_text()
    assert 'hidden' not in log and 'RuntimeError' in log and 'technical' in log
    assert (root/'logs'/'events-2026-01-01.jsonl').stat().st_mode & 0o077==0


@pytest.mark.parametrize('filters',[{'severity':'BAD'},{'category':'../config'},{'from':'invalid'},{'from':'2026-02-01','to':'2026-01-01'}])
def test_log_filter_validation(phase4_root,filters):
    """User filters select structured fields, never arbitrary files."""
    with pytest.raises(ValidationError): d.query(phase4_root,filters)


def test_log_retention_only_deletes_old_log_files(phase4_root,monkeypatch):
    """Thirty-day default cleanup cannot rotate backups, archives or arbitrary log files."""
    root=phase4_root;clock(monkeypatch,'2026-01-01T12:00:00+00:00');d.emit(root,'INFO','Application','Old event')
    backup=m.backup(root,uuid4().hex);before=m.backup_path(root,backup).read_bytes()
    (root/'logs'/'keep.txt').write_text('operator note')
    clock(monkeypatch,'2026-02-01T12:00:00+00:00');d.emit(root,'INFO','Application','Current event');d.retain(root,30)
    assert not (root/'logs'/'events-2026-01-01.jsonl').exists()
    assert (root/'logs'/'events-2026-02-01.jsonl').exists() and (root/'logs'/'keep.txt').exists()
    assert m.backup_path(root,backup).read_bytes()==before


def test_logging_failure_does_not_prevent_database_operations(phase4_root,monkeypatch):
    """A read-only/full log destination degrades diagnostics, never a committed backup."""
    def fail(*args,**kwargs):
        """Simulate failed log lock access only; storage locks remain available."""
        raise OSError('simulated log storage failure')
    monkeypatch.setattr(d,'log_lock',fail)
    assert d.emit(phase4_root,'ERROR','Database','Fixed message') is False
    assert m.backup(phase4_root,uuid4().hex)['status']=='verified'


def test_corrupt_external_metadata_is_not_reinitialized(phase4_root):
    """Malformed existing settings fail closed instead of losing operations/audit state."""
    path=phase4_root/'config'/'operations.json';path.write_text('broken');path.chmod(0o600)
    with pytest.raises(StorageError): s.tick(phase4_root)
    assert path.read_text()=='broken'


def test_due_backup_of_damaged_storage_records_failed_attempt(phase4_root,monkeypatch):
    """A corrupt source is a visible failed automatic backup, never a replacement or silent skip."""
    from workout_tracker.storage import _inspect_unlocked
    root=phase4_root;clock(monkeypatch,'2026-01-01T09:00:00+00:00');s.configure(root,settings())
    with storage_lock(root): original=_inspect_unlocked(root)['database']
    original.write_bytes(b'corrupt active remains preserved')
    clock(monkeypatch,'2026-01-01T11:00:00+00:00');s.tick(root)
    current=state(root)
    assert current['schedule']['result']=='Failed' and current['schedule']['last_attempt']==o.now().isoformat()
    assert next(iter(current['backups'].values()))['status']=='failed'
    assert original.read_bytes()==b'corrupt active remains preserved'
    s.configure(root,settings(enabled=''))
    assert state(root)['schedule']['enabled'] is False
