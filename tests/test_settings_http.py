# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""Settings integration verifies real CSRF/generation tokens and safe operation results.

Every route uses Flask's synthetic browser cookie jar and disposable schema 4.
No endpoint accepts arbitrary file paths or downloads private backups/log files.
"""
import re
from uuid import uuid4

from workout_tracker import maintenance as m,diagnostics as d,operations as o,create_app
from workout_tracker.storage import storage_lock,database_session
from workout_tracker import catalog as c


def fields(response):
    """Extract server-issued hidden fields from a real rendered form."""
    return dict(re.findall(r'name="(csrf_token|operation_id)" value="([^"]*)"',response.get_data(as_text=True)))


def test_settings_backup_restore_delete_and_stale_dataset_forms(phase4_app,phase4_root):
    """Review/confirm restore keeps audit, forbids old open forms and supports explicit deletion."""
    client=phase4_app.test_client();root=phase4_root
    settings=client.get('/settings');assert settings.status_code==200 and b'Schema 4' in settings.data
    payload=fields(settings)
    assert client.post('/settings/backup',data={}).status_code==400
    response=client.post('/settings/backup',data=payload)
    assert response.status_code==303
    assert client.post('/settings/backup',data=payload).location==response.location
    detail=client.get(response.location);assert b'id="backup-status">verified' in detail.data
    with database_session(root,write=True) as db: c.create_person(db,'After backup')
    before=client.get('/people');stale=fields(before)
    restore_path=response.location+'/restore';restore_fields=fields(detail)
    assert client.post(restore_path,data=restore_fields).status_code==503
    # A failed unconfirmed token is not claimed; confirmation can still submit it.
    restored=client.post(restore_path,data=dict(restore_fields,confirm='yes',confirmation='RESTORE'))
    assert restored.status_code==303
    restored=client.get(restored.headers['Location'])
    assert restored.status_code==200 and b'succeeded' in restored.data
    assert client.post('/people',data=dict(stale,name='Stale write')).status_code==400
    with database_session(root) as db: assert db.execute('SELECT count(*) FROM people').fetchone()[0]==0
    detail=client.get(response.location)
    deleted=client.post(response.location+'/delete',data=dict(fields(detail),confirm='yes'))
    assert deleted.status_code==303
    assert b'id="backup-status">deleted' in client.get(response.location).data
    with storage_lock(root):
        state=o.read_state(root);assert len(state['backups'])==1 and len(state['restores'])==1
    # A replacement factory sees the same external metadata, not reset defaults.
    replacement=create_app({'WORKOUT_DATA_ROOT':root,'TESTING':True}).test_client()
    assert b'deleted' in replacement.get('/settings').data


def test_settings_validation_logs_filters_and_no_arbitrary_paths(phase4_app,phase4_root):
    """Logs offer bounded pages/safe details, and browser errors expose no private paths."""
    root=phase4_root;client=phase4_app.test_client();page=client.get('/settings');payload=fields(page)
    invalid=dict(payload,days='0',time='02:00',timezone='Etc/UTC',retention_days='30')
    assert client.post('/settings',data=invalid).status_code==400
    valid=dict(payload,enabled='yes',days='2',time='14:05',timezone='America/New_York',retention_days='40')
    assert client.post('/settings',data=valid).status_code==303
    with storage_lock(root): assert o.read_state(root)['schedule']['days']==2
    try: raise ValueError('secret=never-expose /private/database')
    except ValueError as error: d.emit(root,'ERROR','Restore','Explicit test error',error=error)
    logs=client.get('/settings/logs?severity=ERROR&category=Restore&q=Explicit')
    assert logs.status_code==200 and b'Error details' in logs.data and b'Explicit test error' in logs.data
    assert b'never-expose' not in logs.data and str(root).encode() not in logs.data and b'"technical"' not in logs.data
    assert client.get('/settings/logs?page=-1').status_code==400
    assert client.get('/settings/logs?category=../../config').status_code==400
    assert client.get('/settings/logs?path=/etc/passwd').status_code==200
    assert client.get('/settings/backups/'+'a'*32).status_code==404
    assert client.get('/settings/backups/../../config/active.json').status_code==404
    # A failed backup is shown as failed, never a success redirect label.
    record=m.backup(root,uuid4().hex)
    m.backup_path(root,record).write_bytes(b'corrupted')
    detail=client.get('/settings/backups/'+record['id'])
    failed=client.post('/settings/backups/'+record['id']+'/restore',data=dict(fields(detail),confirm='yes',confirmation='RESTORE'))
    assert failed.status_code==303
    failed=client.get(failed.headers['Location'])
    assert failed.status_code==503 and b'failed' in failed.data and str(root).encode() not in failed.data


def test_existing_settings_remains_available_when_database_is_damaged(phase4_app,phase4_root):
    """A running worker can offer explicit recovery without silently repairing startup."""
    from workout_tracker.storage import _inspect_unlocked
    client=phase4_app.test_client();root=phase4_root;record=m.backup(root,uuid4().hex)
    with storage_lock(root): path=_inspect_unlocked(root)['database']
    path.write_bytes(b'broken active data')
    page=client.get('/settings');assert page.status_code==200 and b'Database unavailable' in page.data
    detail=client.get('/settings/backups/'+record['id'])
    response=client.post('/settings/backups/'+record['id']+'/restore',data=dict(fields(detail),confirm='yes',confirmation='RESTORE'))
    assert response.status_code==303
    response=client.get(response.headers['Location'])
    assert response.status_code==200 and b'succeeded' in response.data
    assert path.read_bytes()==b'broken active data'


def test_unexpected_exceptions_are_private_and_do_not_log_raw_sensitive_text(phase4_app,phase4_root,capsys):
    """Flask production-style handling stores frames/type, never raw exception bodies."""
    phase4_app.config.update(TESTING=False)
    @phase4_app.get('/synthetic-error')
    def simulated_failure():
        """Raise synthetic secret-bearing content to verify the logging boundary."""
        raise RuntimeError('secret=must-not-appear /private/data')
    response=phase4_app.test_client().get('/synthetic-error')
    assert response.status_code==500 and b'must-not-appear' not in response.data
    logs=''.join(p.read_text() for p in (phase4_root/'logs').glob('events-*.jsonl'))
    assert 'RuntimeError' in logs and 'must-not-appear' not in logs
    assert 'must-not-appear' not in capsys.readouterr().err
