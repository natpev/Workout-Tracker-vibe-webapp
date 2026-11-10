# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Phase 10 synthetic inline errors, clock/range boundaries and safe live output.

No real workout data or exercise identity cleanup is used. Existing schema 7
services remain the transaction source; tests compare exact rows on failed forms.
"""
from datetime import date,datetime,timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from unittest.mock import patch
from uuid import uuid4

import pytest
from workout_tracker import create_app,history as h,catalog as c,workouts as w
from workout_tracker import progress_ranges as ranges
from workout_tracker.storage import database_session
from test_phase9 import phase9_root
from test_phase8_deletion import household,manual,token
from workout_updater.engine import Engine,UpdateError
from workout_updater.console import Console,safe_line,read_console,retained,MAX_LINES
from workout_updater.service import status_app


def snapshot(root):
    """Compare every workout/preparation/audit row to detect partial saves."""
    with database_session(root) as db:
        return {table:[tuple(row) for row in db.execute(f'SELECT * FROM {table} ORDER BY 1')] for table in ('historical_forms','historical_workouts','historical_entries','workout_corrections')}


@pytest.fixture
def historical_client(phase9_root):
    """Seed owned snapshots with valid zero and a skipped duration, never live data."""
    root=phase9_root
    with database_session(root,write=True) as db:
        a,b,r,other,e=household(db)
        saved,form=manual(db,a,r,'2020-01-01',weight_0='0',seconds_1='45')
        pending=h.prepare(db,a,r,dict(workout_date='2020-02-02',workout_time='09:30'),'America/Indiana/Indianapolis')
    app=create_app({'TESTING':True,'WORKOUT_DATA_ROOT':root,'WORKOUT_TIMEZONE':'America/Indiana/Indianapolis'})
    return app.test_client(),root,a,b,r,saved,pending


def test_multiple_inline_errors_keep_all_raw_fields_and_no_writes(historical_client):
    """Invalid rows stay on the same form and valid resubmission commits once."""
    client,root,a,b,r,saved,pending=historical_client;path=f'/people/{a}/historical/{pending}'
    page=client.get(path);before=snapshot(root)
    values=dict(csrf_token=token(page),weight_0='bad<script>',minutes_1='1',seconds_1='-5',increase_0='1',increase_1='1')
    response=client.post(path,data=values);body=response.get_data(as_text=True)
    assert response.status_code==400 and 'Review historical workout' in body
    assert 'aria-invalid="true"' in body and 'error-weight_0' in body and 'error-seconds_1' in body
    assert 'bad&lt;script&gt;' in body and 'value="-5"' in body and 'Please correct the following errors' in body
    assert body.index('error-summary')<body.index('<button>Save historical workout')
    assert body.count('value="1" checked')>=2 and snapshot(root)==before
    values.update(csrf_token=token(response),weight_0='40.99',seconds_1='90')
    response=client.post(path,data=values);assert response.status_code==303
    with database_session(root) as db:
        parent,rows=h.effective(db,a,response.location.rsplit('/',1)[-1])
        assert rows[0]['actual_weight_tenths_lb']==409 and rows[1]['actual_duration_seconds']==150


def test_correction_conflicts_confirmations_and_raw_context_are_inline(historical_client):
    """Date/time/fold/actuals/revision persist while confirmation and stale writes fail."""
    client,root,a,b,r,saved,pending=historical_client;path=f'/people/{a}/history/{saved}/correct'
    page=client.get(path);before=snapshot(root)
    values=dict(csrf_token=token(page),correction_revision='0',workout_date='2020-01-02',workout_time='2560',fold='1',weight_0='42.56',seconds_1='120',increase_1='1')
    response=client.post(path,data=values);body=response.get_data(as_text=True)
    assert response.status_code==400 and 'Correct saved workout' in body and 'value="2560"' in body
    assert 'value="2020-01-02"' in body and 'value="42.56"' in body and 'value="120"' in body
    assert 'value="1" selected' in body and 'error-confirm' in body and snapshot(root)==before
    values.update(csrf_token=token(response),confirm='yes',workout_time='0930')
    assert client.post(path,data=values).status_code==303
    after=snapshot(root);response=client.post(path,data=values)
    assert response.status_code==409 and b'Your inputs are retained' in response.data
    assert b'value="42.56"' in response.data and b'value="0"' in response.data and snapshot(root)==after


@pytest.mark.parametrize('clock',['','0000','0930','1445','2359','09:30'])
def test_initial_structured_clock_values(historical_client,clock):
    """Unknown and four-digit 24-hour time entry preserve the IANA occurrence."""
    client,root,a,b,r,saved,pending=historical_client;path=f'/people/{a}/historical';page=client.get(path)
    response=client.post(path,data=dict(csrf_token=token(page),routine_id=r,workout_date='2020-01-03',workout_time=clock))
    assert response.status_code==303
    with database_session(root) as db:
        parent,rows=h.prepared(db,a,response.location.rsplit('/',1)[-1])
        assert parent['timezone']=='America/Indiana/Indianapolis'
        assert parent['workout_time'] is None if not clock else parent['workout_time'][:5]==(clock[:2]+':'+clock[2:] if len(clock)==4 else clock)


@pytest.mark.parametrize('clock',['2400','0960','-100','ab:cd'])
def test_bad_initial_time_and_dst_remain_inline(historical_client,clock):
    """Invalid time preserves date/selection and never creates a preparation."""
    client,root,a,b,r,saved,pending=historical_client;path=f'/people/{a}/historical';page=client.get(path);before=snapshot(root)
    response=client.post(path,data=dict(csrf_token=token(page),routine_id=r,workout_date='2020-01-03',workout_time=clock))
    assert response.status_code==400 and clock.encode() in response.data and b'error-workout_time' in response.data
    assert snapshot(root)==before


@pytest.mark.parametrize('token,first,last',[
    ('30','2024-03-02','2024-03-31'),('60','2024-02-01','2024-03-31'),('90','2024-01-02','2024-03-31'),
    ('6m','2023-10-01','2024-03-31'),('12m','2023-04-01','2024-03-31'),('all','',''),
])
def test_inclusive_ranges_calendar_months_and_local_dates(token,first,last):
    """Calendar-day/month presets include both endpoints and leap-year boundaries."""
    values,selected,description=ranges.selection({'range':token},date(2024,3,31))
    assert values['from']==first and values['to']==last and selected==('custom' if token in ('30','60','90') else token)
    assert ranges.month_before(date(2024,8,31),6)==date(2024,2,29)


def test_progress_default_local_timezone_custom_errors_and_isolation(historical_client):
    """Default local-day bounds, all-time and invalid ranges retain ownership/exercise."""
    client,root,a,b,r,saved,pending=historical_client
    with patch.object(w,'now',return_value=datetime(2024,4,1,2,tzinfo=timezone.utc)):
        response=client.get(f'/people/{a}/progress')
        assert b'2024-01-01 through 2024-03-31' in response.data
    assert b'class="progress-series"' in client.get(f'/people/{a}/progress?range=all').data
    assert b'class="progress-series"' not in client.get(f'/people/{b}/progress?range=all').data
    with database_session(root) as db:exercise=db.execute('SELECT exercise_id FROM historical_entries WHERE measurement_type=?',('weight',)).fetchone()[0]
    response=client.get(f'/people/{a}/progress?range=custom&from=2021-02-01&to=2020-01-01&exercise={exercise}&previous_range=all')
    assert response.status_code==400 and b'2021-02-01' in response.data and exercise.encode() in response.data
    assert b'class="progress-series"' in response.data
    valid=client.get(f'/people/{a}/progress?range=custom&from=2020-01-01&to=2020-01-01&exercise={exercise}')
    assert b'0.0 lb' in valid.data and valid.data.count(b'class="chart-point"')==1


def test_safe_output_is_not_raw_private_logs(tmp_path):
    """Only recognized structure is exposed; arbitrary secrets/HTML/config are dropped."""
    for line in ('SECRET=hidden','https://user:password@example.com/path','<script>alert(1)</script>','session_key=hidden','#2 RUN echo TOP_SECRET','arbitrary command text'):
        assert safe_line('build',line) is None
    assert safe_line('build','#2 DONE 1.5s')=='Build step 2: DONE 1.5s'
    assert safe_line('storage','Storage verified; schema version 7.')=='Storage verified; schema 7.'
    op=uuid4().hex;console=Console(tmp_path,op)
    for i in range(MAX_LINES+10):console.append('safe '+str(i))
    read=read_console(tmp_path,op)
    assert len(read['lines'])==MAX_LINES and read['first']==11
    with pytest.raises(UpdateError):read_console(tmp_path,'../../private.log')
    for i in range(21):Console(tmp_path,uuid4().hex)
    assert len(retained(tmp_path))==20 and not (tmp_path/(op+'.console.json')).exists()


def test_real_process_output_arrives_before_exit_and_secrets_stay_private(tmp_path):
    """Actual Popen streams safe Docker-like output before completion, with full private logs."""
    root=tmp_path/'install';(root/'updater').mkdir(parents=True);(root/'app').mkdir()
    bins=tmp_path/'bin';bins.mkdir();fake=bins/'docker'
    fake.write_text('#!/usr/bin/env python3\nimport time\nprint("#2 DONE 0.1s",flush=True)\nprint("SESSION_SIGNING_KEY=NEVER_BROWSER_SECRET",flush=True)\ntime.sleep(1)\nprint("#3 DONE 0.2s",flush=True)\n')
    fake.chmod(0o700);engine=Engine(root);op=uuid4().hex
    engine.console=Console(root/'updater',op);engine.raw_log=root/'updater'/('operation.private.log')
    def run():
        """Run the actual streaming implementation in parallel with a read-only poll."""
        with patch.dict(os.environ,{'PATH':str(bins)+os.pathsep+os.environ['PATH'],'SESSION_SIGNING_KEY':'NEVER_BROWSER_SECRET'}):engine.command(['docker','build'])
    thread=threading.Thread(target=run);thread.start()
    deadline=time.monotonic()+3
    while True:
        rows=read_console(root/'updater',op)['lines']
        if any('Build step 2' in row['text'] for row in rows):break
        assert time.monotonic()<deadline;time.sleep(.02)
    assert thread.is_alive()
    thread.join(4);assert not thread.is_alive()
    assert 'NEVER_BROWSER_SECRET' in engine.raw_log.read_text()
    assert 'NEVER_BROWSER_SECRET' not in json.dumps(read_console(root/'updater',op))
    engine.config=dict(status_url='http://127.0.0.1:8001/status',app_url='http://127.0.0.1:8000')
    status=status_app(engine);status.config['SERVER_NAME']='127.0.0.1:8001'
    client=status.test_client()
    assert client.get('/console.json?operation='+op).status_code==200
    assert client.get('/console.json?path=/etc/passwd').status_code==400
    assert client.get('/console.json?operation=../../private.log').status_code==404
    assert client.post('/console.json').status_code==405


def test_valid_fields_and_skipped_confirmation_survive_other_errors(historical_client):
    """One bad duration never erases a valid typed weight or prior increase choices."""
    client,root,a,b,r,saved,pending=historical_client;path=f'/people/{a}/historical/{pending}'
    page=client.get(path);before=snapshot(root)
    response=client.post(path,data=dict(csrf_token=token(page),weight_0='42.56',seconds_1='0',increase_0='1',confirm_all_skipped='yes'))
    assert response.status_code==400 and b'value="42.56"' in response.data
    assert b'name="confirm_all_skipped" value="yes" checked' in response.data and snapshot(root)==before
    response=client.post(path,data=dict(csrf_token=token(response)))
    assert response.status_code==400 and b'error-confirm_all_skipped' in response.data and snapshot(root)==before


@pytest.mark.parametrize('day,clock,field',[('bad','0930','workout_date'),('2020-03-08','0230','workout_time'),('2020-11-01','0130','fold')])
def test_initial_date_and_dst_errors_are_accessible_and_atomic(historical_client,day,clock,field):
    """Bad dates, missing local instants and ambiguous folds stay on the initial form."""
    client,root,a,b,r,saved,pending=historical_client;path=f'/people/{a}/historical';page=client.get(path);before=snapshot(root)
    response=client.post(path,data=dict(csrf_token=token(page),routine_id=r,workout_date=day,workout_time=clock))
    assert response.status_code==400 and ('error-'+field).encode() in response.data
    assert day.encode() in response.data and clock.encode() in response.data and snapshot(root)==before
    if field=='fold':
        response=client.post(path,data=dict(csrf_token=token(response),routine_id=r,workout_date=day,workout_time=clock,fold='1'))
        assert response.status_code==303


def test_stream_timeout_large_pipes_and_nonzero_keep_bounds():
    """Both real pipes drain under a size limit, failed exits survive, and timeouts stop."""
    from workout_updater.process_output import stream_run
    lines=[]
    script='import sys;sys.stdout.write("x"*2200000);sys.stderr.write("end\\n");sys.exit(3)'
    result=stream_run([sys.executable,'-c',script],env=os.environ.copy(),timeout=5,on_line=lines.append)
    assert result.returncode==3 and len(result.stdout)==2097152 and result.stderr=='end\n'
    assert len(lines)>1 and max(map(len,lines))<=24576
    with pytest.raises(subprocess.TimeoutExpired):
        stream_run([sys.executable,'-c','import time;time.sleep(3)'],env=os.environ.copy(),timeout=.1)


def test_console_rejects_symlinks_malformed_rows_and_bad_cursors(tmp_path):
    """Even bounded safe files must have valid UTC sequence metadata; no path fallback."""
    op=uuid4().hex;console=Console(tmp_path,op);console.append('Verified safe message.')
    for cursor in (-1,True,10**13):
        with pytest.raises(UpdateError):read_console(tmp_path,op,cursor)
    value=json.loads(console.path.read_text());value['lines'][0]['time']='not-a-timestamp'
    console.path.write_text(json.dumps(value))
    with pytest.raises(UpdateError):read_console(tmp_path,op)
    console.path.unlink();private=tmp_path/'private.log';private.write_text('PRIVATE_SECRET')
    console.path.symlink_to(private)
    assert op not in retained(tmp_path)
    with pytest.raises(UpdateError):read_console(tmp_path,op)
    assert private.read_text()=='PRIVATE_SECRET'


def test_config_output_and_environment_shaped_hash_never_reach_console(tmp_path):
    """Known secret values remain private even if shaped like an allowed Git revision."""
    root=tmp_path/'install';(root/'updater').mkdir(parents=True)
    secret='a'*40
    runner=lambda *args,**kwargs:subprocess.CompletedProcess(args[0],0,secret+'\n','#1 DONE 0.1s\n')
    engine=Engine(root,runner=runner);op=uuid4().hex;engine.console=Console(engine.state_dir,op)
    engine.raw_log=engine.state_dir/'private.log'
    with patch.dict(os.environ,{'SESSION_SIGNING_KEY':secret}):engine.command(['git','rev-parse','HEAD'])
    assert secret not in json.dumps(read_console(engine.state_dir,op)) and secret in engine.raw_log.read_text()
    engine.command(['docker','compose','config','--format','json'])
    assert 'Build step' not in json.dumps(read_console(engine.state_dir,op))
    assert '<resolved Compose config/output withheld>' in engine.raw_log.read_text()


@pytest.mark.parametrize('start,end',[('bad','2020-01-01'),('20200101','2020-01-01'),('2020-02-30','2020-03-01')])
def test_invalid_custom_dates_remain_inline_with_previous_points(historical_client,start,end):
    """Malformed custom filters retain raw dates/exercise and the last all-time graph."""
    client,root,a,b,r,saved,pending=historical_client
    response=client.get(f'/people/{a}/progress',query_string={'range':'custom','from':start,'to':end,'previous_range':'all'})
    assert response.status_code==400 and start.encode() in response.data and b'valid From and To dates' in response.data
    assert b'type="text" aria-invalid="true"' in response.data
    assert response.data.count(b'class="chart-point"')==2


def test_safe_console_failure_does_not_reverse_storage_or_stage(tmp_path):
    """A broken optional console and its fallback log cannot raise into maintenance."""
    from unittest.mock import Mock
    root=tmp_path/'install';(root/'updater').mkdir(parents=True)
    engine=Engine(root);engine.console=Mock();engine.console.append.side_effect=OSError('disk full')
    engine.raw_log=root/'missing-parent/private.log'
    engine.console_line('Completed')
    assert engine.console is None


def test_json_update_submit_keeps_csrf_release_and_migration_consent(historical_client):
    """The fetch response changes only presentation; all server consent gates remain."""
    client,root,a,b,r,saved,pending=historical_client
    release=dict(id='c'*40,version='0.10.0',schema=8,source='Synthetic approved main',notes='fixture')
    state=dict(status='Available',release=release,events=[],console_protocol=1)
    calls=[]
    def call(root,action,**values):
        """Record fixed operations only, without executing a host update."""
        calls.append((action,values));return state
    with patch('workout_tracker.update_client.bridge',return_value=(root,{'status_url':'http://127.0.0.1:8001/status'})),patch('workout_tracker.update_client.call',side_effect=call):
        path=f'/settings/updates?person_id={a}';page=client.get(path)
        assert client.post(path,data={'action':'install'},headers={'Accept':'application/json'}).status_code==400
        values=dict(csrf_token=token(page),action='install',release=release['id'])
        response=client.post(path,data=values,headers={'Accept':'application/json'})
        assert response.status_code==400 and 'confirmation' in response.json['error']
        values['confirm']='yes';response=client.post(path,data=values,headers={'Accept':'application/json'})
        assert response.status_code==400 and 'candidate' in response.json['error']
        assert not any(action=='install' for action,_ in calls)
        values['migration']='yes';response=client.post(path,data=values,headers={'Accept':'application/json'})
        assert response.status_code==202 and calls[-1]==('install',dict(release=release['id'],confirm=True,migration=True))
