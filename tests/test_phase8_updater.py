# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""Actual v4 wrapper/host engine tests with fake Git/Docker and real SQLite services.

All paths and environment selectors are synthetic. No command reaches a server,
real Docker daemon or GitHub. Distinct tests exercise the restricted Unix API.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch
from uuid import uuid4

import pytest
from workout_tracker.storage import initialize_storage,database_session
from workout_tracker.migrations import migrate_storage
from workout_tracker import catalog as c,history as h
from workout_updater.engine import Engine,UpdateError,write_json
from workout_updater.service import Controller

REPO=Path(__file__).resolve().parents[1]
ADAPTER='''#!/usr/bin/env python3
# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
# Isolated test adapter; forwards only application storage calls to fixture data.
import json,os,subprocess,sys
from pathlib import Path
args=sys.argv[1:];root=Path(os.environ['FIXTURE']);mode=os.environ.get('MODE','ok');name=Path(sys.argv[0]).name
with (root/'calls.jsonl').open('a') as f:f.write(json.dumps([name,args])+'\\n')
if name=='git':
 if 'remote' in args:print('https://github.com/natpev/Workout-Tracker-vibe-webapp.git')
 elif 'branch' in args:print('main')
 elif 'status' in args:pass
 elif 'fetch' in args:sys.exit(1 if mode=='fetch' else 0)
 elif 'rev-parse' in args:print('a'*40 if args[-1]=='origin/main' or (root/'merged').exists() or mode=='no-update' else 'b'*40)
 elif 'show' in args:print('APP_VERSION="0.8.0"\\nTARGET_SCHEMA_VERSION=6')
 elif 'log' in args:print('Approved synthetic release notes')
 elif 'merge-base' in args:pass
 elif 'merge' in args:(root/'merged').touch()
 sys.exit(0)
if args[0].startswith('--host='):args=args[1:]
if args[:1]==['info']:print(root);sys.exit(0)
if args[:2] in (['image','tag'],['image','inspect']):sys.exit(0)
if args[0]=='compose':
 args=args[args.index('-f')+2:];cmd=args[0]
 if cmd=='config':
  print(json.dumps({'services':{k:{'image':'workout-tracker:local','user':'10001:10001','environment':{'WORKOUT_DATA_ROOT':'/var/lib/workout-tracker'},'volumes':[{'type':'bind','source':str(root/'data/storage'),'target':'/var/lib/workout-tracker'}]} for k in ('web','scheduler')}}));sys.exit(0)
 if cmd=='stop':(root/'stopped').touch();sys.exit(0)
 if cmd=='build':sys.exit(1 if mode=='build' else 0)
 if cmd=='up':(root/'started').touch();sys.exit(1 if mode=='startup' else 0)
 if cmd=='ps':print('web\\nscheduler');sys.exit(0)
 if cmd=='exec':sys.exit(1 if mode=='readiness' else 0)
 if cmd=='run':args=args[args.index('python')+1:]
 else:raise RuntimeError(args)
else:
 args=args[args.index('--entrypoint')+3:]
if 'release-info' in args:print(json.dumps(dict(app_version='0.8.0',target_schema_version=6)));sys.exit(0)
if '-c' in args and 'print(APP_VERSION)' in args[args.index('-c')+1]:print('0.8.0');sys.exit(0)
if 'check-storage' in args and mode=='database':sys.exit(1)
if 'migrate-storage' in args and mode=='migration':sys.exit(1)
if '-c' in args and 'maintenance import backup' in args[args.index('-c')+1] and mode=='backup':sys.exit(1)
args=[v.replace('/var/lib/workout-tracker',str(root/'data/storage')) for v in args]
env=os.environ.copy();env['PYTHONPATH']=os.environ['APP_SOURCE']
sys.exit(subprocess.run([os.environ['APP_PYTHON'],*args],env=env).returncode)
'''


def fixture(tmp_path,schema=5):
    """Provision an explicitly installed host-runtime fixture with synthetic history."""
    root=tmp_path/'install';(root/'app/.git').mkdir(parents=True);(root/'data').mkdir()
    for name in ('compose.yaml','Dockerfile'):(root/'app'/name).write_text('# fixture')
    (root/'.env').write_text('AUTHORITATIVE=true\n');(root/'app/.env').write_text('OLD_COPY=true\n')
    storage=root/'data/storage';initialize_storage(storage);migrate_storage(storage,schema)
    with database_session(storage,write=True) as db:
        a=c.create_person(db,'Fixture');r=c.create_routine(db,a,'Fixture')
        c.add_entry(db,a,r,dict(name='Zero',measurement_type='weight',target_sets='3',target_reps='12'))
        c.add_entry(db,a,r,dict(name='Skip',measurement_type='weight',target_sets='3',target_reps='12'))
        form=h.prepare(db,a,r,dict(workout_date='2020-01-01',workout_time=''),'UTC');h.complete_historical(db,a,form,{'weight_0':'0'})
    state=root/'updater';(state/'runtime').mkdir(parents=True);(state/'venv/bin').mkdir(parents=True)
    (state/'venv/bin/python').symlink_to(sys.executable)
    (state/'runtime/workout_updater').symlink_to(REPO/'workout_updater',target_is_directory=True)
    write_json(state/'config.json',{'root':str(root)})
    bins=tmp_path/'bin';bins.mkdir()
    for name in ('git','docker'):
        path=bins/name;path.write_text(ADAPTER);path.chmod(0o700)
    env=os.environ.copy();env.update(PATH=str(bins)+os.pathsep+env['PATH'],FIXTURE=str(root),APP_PYTHON=sys.executable,APP_SOURCE=str(REPO))
    return root,env


@pytest.mark.parametrize('mode,schema,extra,ok',[
    ('ok',5,['--confirm','--allow-migration'],True),
    ('ok',6,['--confirm'],True),('no-update',6,['--confirm'],True),
    ('fetch',5,['--confirm','--allow-migration'],False),('build',5,['--confirm','--allow-migration'],False),
    ('database',5,['--confirm','--allow-migration'],False),('migration',5,['--confirm','--allow-migration'],False),
    ('backup',5,['--confirm','--allow-migration'],False),('startup',5,['--confirm','--allow-migration'],False),
    ('readiness',5,['--confirm','--allow-migration'],False),('ok',5,['--confirm'],False),
])
def test_actual_v4_script(tmp_path,mode,schema,extra,ok):
    """Run real executable Bash -> host CLI -> application backup/migration on fixtures."""
    root,env=fixture(tmp_path,schema);env['MODE']=mode
    manifest=root/'data/storage/config/active.json';original=root/'data/storage/data'/json.loads(manifest.read_text())['database'];before=original.read_bytes()
    result=subprocess.run(['bash',str(REPO/'deployment/update_workout_tracker_v4.sh'),'--root',str(root),*extra],
                          env=env,input='NO\n',text=True,capture_output=True,timeout=65)
    assert (result.returncode==0)==ok,result.stdout+result.stderr
    assert original.read_bytes()==before
    state=json.loads((root/'updater/status.json').read_text())
    if ok:
        assert state['status']=='Completed'
        if mode=='no-update':assert not (root/'stopped').exists() and not (root/'data/storage/config/operations.json').exists()
        else:assert (root/'app/.env').read_bytes()==(root/'.env').read_bytes()
    else:
        assert state['status']!='Completed'
        if mode in ('startup','readiness'):
            assert state['recovered'] is False
            assert json.loads(manifest.read_text())['database']!=original.name
        if mode=='migration':assert json.loads(manifest.read_text())['database']==original.name
        if mode in ('build','backup','migration'):assert state['recovered'] is True
    with database_session(root/'data/storage') as db:
        assert [row[0] for row in db.execute('SELECT actual_weight_tenths_lb FROM historical_entries ORDER BY position')]==[0,None]


def test_local_boundary_rejects_arbitrary_commands_sources_and_overlap(tmp_path):
    """Only fixed operations and a known approved release can reach the engine."""
    root,env=fixture(tmp_path);engine=Engine(root);controller=Controller(engine)
    for value in ([],None,dict(action='shell',command='id'),dict(action='check',repository='https://evil.example'),dict(action='install',release='b'*40,confirm=True,migration=True)):
        with pytest.raises(UpdateError):controller.handle(value)
    assert controller.handle(dict(action='status'))['status']=='Not yet checked'
    controller.busy=True
    with pytest.raises(UpdateError):controller.handle(dict(action='check'))
    with engine.locked(),pytest.raises(UpdateError):
        with Engine(root).locked():pass
    # A simultaneous emergency CLI job retains its exact live status when a
    # browser worker is refused by the cross-process lock.
    engine.event('Building image',operation='existing-cli',operation_type='install')
    before=engine.state()
    with engine.locked():controller.work(dict(action='check'))
    assert engine.state()==before


def test_declined_or_unapproved_install_and_disk_guard(tmp_path):
    """Only a known reviewed ID may install; the root job lock is never bypassed."""
    root,env=fixture(tmp_path);engine=Engine(root)
    with pytest.raises(UpdateError):engine.install('a'*40)
    with pytest.raises(UpdateError):engine.install('a'*40,confirm=True,migration_confirm=True)


def test_interrupted_status_is_persistent_and_never_replayed(tmp_path):
    """A new engine can read pending/failed history independently of any web worker."""
    root,env=fixture(tmp_path);engine=Engine(root);engine.event('Migrating database',operation='fixture')
    restarted=Engine(root);assert restarted.state()['status']=='Migrating database'
    assert restarted.state()['operation']=='fixture'
    restarted.event('Failed','Operator inspection required; no automatic replay.',last_failure='fixture')
    assert Engine(root).state()['status']=='Failed'


def test_engine_refuses_insufficient_disk_without_stopping_services(tmp_path):
    """The shared engine checks both filesystems before backups, build or shutdown."""
    from collections import namedtuple
    root,env=fixture(tmp_path);env['MODE']='ok'
    with patch.dict(os.environ,env,clear=True):
        engine=Engine(root);release=engine.check()
        Usage=namedtuple('Usage','total used free')
        with patch('workout_updater.engine.shutil.disk_usage',return_value=Usage(1000,999,1)),pytest.raises(UpdateError,match='free disk'):
            engine.install(release['id'],confirm=True,migration_confirm=True)
    assert not (root/'stopped').exists()
    assert Engine(root).state()['status']=='Failed'


def test_http_update_controls_are_passwordless_but_confirmation_and_csrf_required(tmp_path):
    """Normal anonymous household sessions can review; missing consent cannot install."""
    from workout_tracker import create_app
    from test_phase8_deletion import token
    root,env=fixture(tmp_path,6);data=root/'data/storage'
    bridge=data/'config/updater-bridge';bridge.mkdir()
    write_json(bridge/'client.json',dict(status_url='http://127.0.0.1:8001/status'))
    state=dict(status='Available',events=[],release=dict(id='a'*40,version='0.8.0',schema=6,source='fixture',notes='fixture'))
    client=create_app({'WORKOUT_DATA_ROOT':data,'TESTING':True}).test_client()
    with patch('workout_tracker.update_client.call',return_value=state) as host:
        page=client.get('/settings/updates')
        assert page.status_code==200 and b'type="password"' not in page.data
        assert client.get('/admin/login').status_code==404
        assert client.post('/settings/updates',data={'action':'install','release':'a'*40}).status_code==400
        response=client.post('/settings/updates',data={'csrf_token':token(page),'action':'install','release':'a'*40})
        assert response.status_code==400
        assert all(call.args[1]!='install' for call in host.call_args_list)
        response=client.post('/settings/updates',data={'csrf_token':token(page),'action':'install','release':'a'*40,'confirm':'yes'})
        assert response.status_code==303
        assert host.call_args_list[-1].args[1]=='install'
        assert host.call_args_list[-1].kwargs['confirm'] is True


def test_generated_systemd_unit_is_syntactically_valid_and_scoped(tmp_path):
    """Inspect the actual installer's unit without installing or starting host services."""
    import re
    installer=(REPO/'deployment/install_updater_service.sh').read_text()
    unit=re.search(r'cat > /etc/systemd/system/workout-tracker-updater.service <<EOF\n(.*?)\nEOF',installer,re.S).group(1)
    state=tmp_path/'updater';(state/'runtime').mkdir(parents=True);(state/'venv/bin').mkdir(parents=True)
    (state/'venv/bin/python').symlink_to(sys.executable)
    rendered=unit.replace('$STATE',str(state)).replace('$ROOT_DIR',str(tmp_path))
    path=tmp_path/'workout-tracker-updater.service';path.write_text(rendered+'\n')
    assert 'ReadWritePaths='+str(tmp_path)+' /var/run/docker.sock' in rendered
    assert 'ProtectSystem=strict' in rendered and 'NoNewPrivileges=true' in rendered
    assert 'DOCKER_CONFIG='+str(state/'docker') in rendered
    assert 'openssl' not in installer and 'ssl_context' not in (REPO/'workout_updater/service.py').read_text()
    import shutil
    if shutil.which('systemd-analyze'):
        runtime=tmp_path/'runtime';runtime.mkdir(mode=0o700)
        (tmp_path/'docker.service').write_text('# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.\n# Dependency stub for offline syntax validation only.\n[Service]\nType=oneshot\nExecStart=/usr/bin/true\nRemainAfterExit=yes\n')
        env={**os.environ,'XDG_RUNTIME_DIR':str(runtime),'SYSTEMD_UNIT_PATH':str(tmp_path)+':'}
        result=subprocess.run(['systemd-analyze','--user','verify',str(path)],text=True,capture_output=True,env=env)
        assert result.returncode==0,result.stderr
