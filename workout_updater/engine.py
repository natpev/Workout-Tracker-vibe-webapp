# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""Fixed-command host update engine, called by the Unix service and emergency CLI.

Only GitHub HTTPS/SSH origin for the fixed repository and fetched main commits are
approved. Browser input never supplies command text, repository, branch or image.
State/logs persist outside containers; all update commands run under one flock.
"""
import ast
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from uuid import uuid4

REPOSITORY='natpev/Workout-Tracker-vibe-webapp'
IMAGE='workout-tracker:local'
RUNNING={'Preparing update','Checking for updates','Validating storage','Backing up database',
         'Downloading release','Building image','Migrating database','Starting services','Verifying health'}


class UpdateError(RuntimeError):
    """Fixed safe operational failure; detailed command output remains host-private."""


def utc():
    """Return an aware UTC timestamp for persistent, timezone-independent events."""
    return datetime.now(timezone.utc).isoformat()


def read_json(path,default=None):
    """Read bounded regular JSON, refusing links and malformed existing state."""
    if not os.path.lexists(path): return default
    if path.is_symlink() or not path.is_file() or path.stat().st_size>1048576:
        raise UpdateError('Unsafe updater state file.')
    return json.loads(path.read_text())


def write_json(path,value):
    """Publish a private fsynced state file atomically without exposing partial JSON."""
    temporary=path.with_name(path.name+'.'+uuid4().hex+'.pending')
    fd=os.open(temporary,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,'w') as handle:
        json.dump(value,handle);handle.flush();os.fsync(handle.fileno())
    os.replace(temporary,path)
    directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try: os.fsync(directory)
    finally: os.close(directory)


class Engine:
    """Own fixed installation paths, command construction and persistent outcome."""
    def __init__(self,root,runner=None):
        """Select an existing installation; creation happens only in explicit install."""
        self.root=Path(root)
        if not self.root.is_absolute() or self.root.resolve()!=self.root or self.root.is_symlink():
            raise UpdateError('Installation root must be an absolute canonical directory.')
        self.app=self.root/'app';self.data=self.root/'data/storage';self.state_dir=self.root/'updater'
        if self.state_dir.is_symlink():raise UpdateError('Unsafe updater state directory.')
        self.state_path=self.state_dir/'status.json';self.runner=runner or subprocess.run
        self.config=read_json(self.state_dir/'config.json',{})
        self.compose=['docker','compose','--project-directory',str(self.app),'--env-file',str(self.root/'.env'),'-f',str(self.app/'compose.yaml')]
        self.raw_log=None

    def state(self):
        """Read status without a job lock; atomic publication makes polling safe."""
        return read_json(self.state_path,dict(status='Not yet checked',events=[],release=None,last_success=None,last_failure=None))

    def event(self,status,message=None,**fields):
        """Persist honest named stages and bounded safe events; never fake percentages."""
        state=self.state();state.update(status=status,updated_at=utc(),**fields)
        if status not in RUNNING:state['operation_pending']=False
        state['events']=(state.get('events',[])+[dict(time=utc(),status=status,message=message or status)])[-200:]
        write_json(self.state_path,state)
        print(status+': '+(message or status),flush=True)

    @contextmanager
    def locked(self):
        """Coordinate browser jobs, emergency CLI and updater service upgrades."""
        path=self.root/'.workout-update.lock'
        if path.is_symlink(): raise UpdateError('Unsafe updater lock.')
        with path.open('a') as lock:
            try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError as error: raise UpdateError('Another update/check is already running.') from error
            try: yield
            finally: fcntl.flock(lock,fcntl.LOCK_UN)

    def command(self,args,*,input=None,check=True,timeout=120):
        """Run an argv list, never a shell; keep stdout/stderr in private host logs.

        Remove ambient Compose/workout selectors so browser jobs cannot target a
        different installation. Credentials/proxy/CA variables are preserved.
        """
        env={k:v for k,v in os.environ.items() if not k.startswith(('WORKOUT_','COMPOSE_')) and k not in ('DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH')}
        env['GIT_TERMINAL_PROMPT']='0'
        env['BUILDX_BUILDER']='default'
        if args[0]=='docker': args=['docker','--host=unix:///var/run/docker.sock',*args[1:]]
        try: result=self.runner(args,input=input,capture_output=True,text=True,env=env,timeout=timeout)
        except (OSError,subprocess.TimeoutExpired) as error: raise UpdateError('Updater command unavailable or timed out.') from error
        if self.raw_log:
            with self.raw_log.open('a') as handle:
                if 'config' in args and '--format' in args:handle.write('<resolved Compose config/output withheld>\n')
                else:handle.write(result.stdout or '');handle.write(result.stderr or '')
        if check and result.returncode:
            label='Git '+next((part for part in args if part in ('fetch','merge','show','log','status','rev-parse','merge-base')),'verification') if args[0]=='git' else 'Docker '+next((part for part in args if part in ('build','stop','up','run','exec','config','image')),'verification')
            raise UpdateError(label+' failed (exit '+str(result.returncode)+') during '+self.state()['status']+'. Inspect the private operation log.')
        return result

    def git(self,*args,**kwargs):
        """Read/fetch only the fixed local checkout; no browser-provided Git options."""
        return self.command(['git','-C',str(self.app),*args],**kwargs)

    def preflight(self):
        """Refuse wrong origin, ambiguous config, unsafe mounts or dirty local history."""
        for path in (self.app,self.app/'.git',self.data,self.root/'.env'):
            if path.is_symlink() or path.resolve()!=path or not path.exists(): raise UpdateError('Installation paths missing or symlinked.')
        if (self.app/'.env').is_symlink():raise UpdateError('Refusing app/.env symlink before any update.')
        origin=self.git('remote','get-url','origin').stdout.strip()
        if origin not in ('https://github.com/'+REPOSITORY+'.git','https://github.com/'+REPOSITORY,'git@github.com:'+REPOSITORY+'.git'):
            raise UpdateError('Updater accepts only the configured Workout Tracker GitHub repository.')
        if self.git('branch','--show-current').stdout.strip()!='main' or self.git('status','--porcelain').stdout.strip():
            raise UpdateError('Clean main checkout required; local work is never discarded.')
        config=json.loads(self.command([*self.compose,'config','--format','json']).stdout)
        if set(config['services'])!={'web','scheduler'}: raise UpdateError('Unexpected Compose services.')
        users=[]
        for name in ('web','scheduler'):
            service=config['services'][name];users.append(service['user'])
            volumes=[v for v in service.get('volumes',[]) if v.get('target')=='/var/lib/workout-tracker']
            if service['image']!=IMAGE or len(volumes)!=1 or volumes[0].get('source')!=str(self.data) or volumes[0].get('type')!='bind':
                raise UpdateError('Unexpected image or persistent data mount.')
            if any(v.get('source')=='/var/run/docker.sock' for v in service.get('volumes',[])):
                raise UpdateError('Web/scheduler must not mount the Docker socket.')
        if users[0]!=users[1] or not re.fullmatch(r'[1-9][0-9]*:[1-9][0-9]*',users[0]):
            raise UpdateError('Matching non-root numeric writer IDs required.')
        return config

    def fetch_release(self):
        """Trust approved merged main over authenticated GitHub transport, pin its SHA.

        Metadata is parsed as Python literal assignments, never executed remotely.
        Installation rechecks release-info in the built image against this preview.
        """
        self.git('fetch','origin','refs/heads/main:refs/remotes/origin/main')
        sha=self.git('rev-parse','origin/main').stdout.strip()
        if not re.fullmatch(r'[0-9a-f]{40}',sha): raise UpdateError('Invalid fetched commit.')
        if self.git('merge-base','--is-ancestor','HEAD',sha,check=False).returncode:
            raise UpdateError('Local main contains unique/diverged work; reconcile manually.')
        source=self.git('show',sha+':workout_tracker/__init__.py').stdout
        values={}
        for node in ast.parse(source).body:
            if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id in ('APP_VERSION','TARGET_SCHEMA_VERSION'):
                values[node.targets[0].id]=ast.literal_eval(node.value)
        version=values.get('APP_VERSION');schema=values.get('TARGET_SCHEMA_VERSION')
        if not isinstance(version,str) or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+',version) or type(schema) is not int or schema<1:
            raise UpdateError('Approved release has no valid target metadata.')
        notes=self.git('log','-12','--format=%h %s',sha).stdout[:12000]
        return dict(id=sha,version=version,schema=schema,notes=notes,source='GitHub approved main',checked_at=utc())

    def check(self):
        """Check approved source explicitly, persist result without touching the database."""
        with self.locked():
            try:
                operation=uuid4().hex;self.raw_log=self.state_dir/(operation+'.private.log')
                self.raw_log.touch(mode=0o600,exist_ok=False)
                self.event('Checking for updates',operation=operation,operation_type='check');self.preflight();release=self.fetch_release()
                self.event('Available','Approved release metadata verified.',release=release)
                return release
            except Exception as error:
                message=str(error) if isinstance(error,UpdateError) else 'Approved release metadata validation failed.'
                self.event('Failed',message,last_failure=utc(),failure_stage='Checking for updates');raise
            finally:self.raw_log=None

    def storage(self):
        """Use the application's read-only verifier and exact manifest, never infer schema."""
        result=self.command([*self.compose,'run','--rm','--no-deps','web','python','-m','workout_tracker','check-storage','--data-root','/var/lib/workout-tracker'])
        match=re.search(r'schema version ([0-9]+)\.',result.stdout)
        if not match: raise UpdateError('Storage verification did not return a schema.')
        manifest=read_json(self.data/'config/active.json')
        name=manifest.get('database','')
        if not re.fullmatch(r'schema-[0-9]+-[0-9a-f]{32}(?:-[0-9a-f]{32})?\.sqlite3',name): raise UpdateError('Unsafe active selection.')
        path=self.data/'data'/name
        if path.is_symlink() or not path.is_file(): raise UpdateError('Selected database missing or unsafe.')
        return int(match[1]),manifest,path

    def health(self,version,schema):
        """Check real web versions and scheduler process, rather than container existence."""
        code="import json,sys,urllib.request; r=json.load(urllib.request.urlopen('http://127.0.0.1:8000/health/ready',timeout=5)); assert r==dict(status='ready',app_version=sys.argv[1],schema_version=int(sys.argv[2]))"
        result=self.command([*self.compose,'exec','-T','web','python','-c',code,version,str(schema)],check=False,timeout=15)
        services=self.command([*self.compose,'ps','--status','running','--services'],check=False).stdout.splitlines()
        return result.returncode==0 and {'web','scheduler'}<=set(services)

    def install(self,release_id,*,confirm=False,migration_confirm=False):
        """Run one approved, confirmed update; preserve sources and verified recovery.

        A failed pre-activation upgrade can restore the prior image only after its
        read-only verifier accepts the still-original selection. After activation
        of a new schema, no incompatible old image is started. Never auto-restore.
        """
        if not confirm: raise UpdateError('Explicit user update confirmation required.')
        expected=self.state().get('release')
        if not expected or release_id!=expected['id']: raise UpdateError('Review an approved release before installing.')
        with self.locked():
            stopped=False;original=None;old_image=None;old_commit=None;backup_id=None;original_manifest=None
            operation=uuid4().hex;self.raw_log=self.state_dir/(operation+'.private.log')
            self.raw_log.touch(mode=0o600,exist_ok=False)
            try:
                self.event('Preparing update',operation=operation,operation_type='install')
                before_config=self.preflight();release=self.fetch_release()
                if release['id']!=release_id or any(release[k]!=expected[k] for k in ('version','schema')):
                    raise UpdateError('Approved main changed; review the new release before installing.')
                schema,original_manifest,original=self.storage()
                if release['schema']<schema: raise UpdateError('Incompatible schema downgrade refused.')
                if release['schema']>schema and not migration_confirm: raise UpdateError('Explicit schema migration approval required.')
                old_commit=self.git('rev-parse','HEAD').stdout.strip()
                if old_commit==release_id and self.health(release['version'],schema) and schema==release['schema']:
                    self.event('Completed','No update available; installed release is already healthy.');return self.state()
                # Reserve space for source/candidate/backup and a conservative image allowance.
                required=original.stat().st_size*3+1024**3
                docker_root=self.command(['docker','info','--format','{{.DockerRootDir}}']).stdout.strip()
                try:
                    for directory in (self.root,Path(docker_root)):
                        if not directory.is_absolute() or not directory.is_dir() or shutil.disk_usage(directory).free<required:
                            raise UpdateError('Insufficient verified free disk space for update/recovery.')
                except OSError as error:
                    raise UpdateError('Cannot inspect Docker/storage filesystem space. Run through the installed root host service or inspect its filesystem permissions.') from error
                env_hash=hashlib.sha256((self.root/'.env').read_bytes()).hexdigest()
                old_image='workout-tracker:before-update-'+operation
                self.command(['docker','image','tag',IMAGE,old_image])
                self.event('Validating storage',previous_commit=old_commit,previous_image=old_image,previous_database=original.name)
                stopped=True;self.command([*self.compose,'stop','web','scheduler'])
                # Recheck under quiescence, then take a verified application backup.
                if self.storage()[:2]!=(schema,original_manifest): raise UpdateError('Selection changed during update preparation.')
                original_hash=hashlib.sha256(original.read_bytes()).hexdigest()
                self.event('Backing up database')
                code="import json; from uuid import uuid4; from workout_tracker.maintenance import backup; r=backup('/var/lib/workout-tracker',uuid4().hex); assert r['status']=='verified'; print(json.dumps(dict(id=r['id'],status=r['status'])))"
                backup=json.loads(self.command([*self.compose,'run','--rm','--no-deps','web','python','-c',code]).stdout)
                if backup.get('status')!='verified' or not re.fullmatch('[0-9a-f]{32}',backup.get('id','')): raise UpdateError('Backup verification failed.')
                backup_id=backup['id'];self.event('Downloading release',backup_id=backup_id)
                self.git('merge','--ff-only',release_id)
                if self.git('rev-parse','HEAD').stdout.strip()!=release_id: raise UpdateError('Checkout does not equal approved release.')
                if self.preflight()!=before_config: raise UpdateError('Resolved Compose configuration changed; operator review required.')
                self.event('Building image')
                self.command([*self.compose,'build'],timeout=1800)
                target=json.loads(self.command(['docker','run','--rm','--network=none','--read-only','--entrypoint','python',IMAGE,'-m','workout_tracker','release-info']).stdout)
                if target!=dict(app_version=release['version'],target_schema_version=release['schema']):
                    raise UpdateError('Built release metadata differs from reviewed source.')
                if release['schema']>schema:
                    self.event('Migrating database')
                    self.command([*self.compose,'run','--rm','--no-deps','web','python','-m','workout_tracker','migrate-storage','--data-root','/var/lib/workout-tracker','--target-version',str(release['schema']),'--confirm-upgrade'],timeout=1800)
                verified,selection,_=self.storage()
                if verified!=release['schema'] or hashlib.sha256(original.read_bytes()).hexdigest()!=original_hash:
                    raise UpdateError('Schema or original preservation verification failed.')
                if release['schema']>schema and selection==original_manifest: raise UpdateError('No distinct migration candidate activated.')
                if release['schema']==schema and selection!=original_manifest: raise UpdateError('Unexpected storage selection change.')
                if hashlib.sha256((self.root/'.env').read_bytes()).hexdigest()!=env_hash: raise UpdateError('Authoritative .env changed.')
                # Explicit Phase 8 requirement: synchronize the authoritative env,
                # privately and atomically, without changing any values.
                env_target=self.app/'.env'
                if env_target.is_symlink(): raise UpdateError('Refusing app/.env symlink.')
                pending=self.app/('.env.'+operation+'.pending')
                fd=os.open(pending,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
                with os.fdopen(fd,'wb') as handle:
                    handle.write((self.root/'.env').read_bytes());handle.flush();os.fsync(handle.fileno())
                os.replace(pending,env_target)
                self.event('Starting services');self.command([*self.compose,'up','-d','--no-build'])
                self.event('Verifying health')
                import time
                for attempt in range(20):
                    if self.health(release['version'],release['schema']): break
                    time.sleep(2)
                else: raise UpdateError('New web/scheduler health or versions did not verify.')
                stopped=False;self.event('Completed','Update verified.',last_success=utc(),installed_version=release['version'],installed_schema=verified)
                return self.state()
            except BaseException as error:
                import traceback
                with self.raw_log.open('a') as diagnostic:diagnostic.write(traceback.format_exc())
                failed_stage=self.state()['status'];recovered=False
                if stopped:
                    self.command([*self.compose,'stop','web','scheduler'],check=False)
                    # Safe automatic image recovery only before any selection
                    # change, on identical config with the preserved old DB bytes.
                    if original and old_image and original_manifest==read_json(self.data/'config/active.json'):
                        try:
                            if self.preflight()==before_config and hashlib.sha256(original.read_bytes()).hexdigest()==original_hash:
                                probe=self.command(['docker','run','--rm','--network=none','--read-only','--tmpfs','/tmp','--mount',f'type=bind,src={self.data},dst=/var/lib/workout-tracker,readonly','--entrypoint','python',old_image,'-m','workout_tracker','check-storage','--data-root','/var/lib/workout-tracker'],check=False)
                                if probe.returncode==0:
                                    self.command(['docker','image','tag',old_image,IMAGE]);self.command([*self.compose,'up','-d','--no-build'])
                                    old_version=self.command(['docker','run','--rm','--network=none','--read-only','--entrypoint','python',old_image,'-c','from workout_tracker import APP_VERSION; print(APP_VERSION)']).stdout.strip()
                                    import time
                                    for attempt in range(10):
                                        if self.health(old_version,schema):
                                            recovered=True;break
                                        time.sleep(1)
                                    if not recovered: self.command([*self.compose,'stop','web','scheduler'],check=False)
                        except Exception: recovered=False
                self.event('Failed','Failed during '+failed_stage+'. '+(str(error)+' ' if isinstance(error,UpdateError) else '')+('Preserved compatible image restarted and verified.' if recovered else 'Inspect preserved versions and private host log before restarting.'),last_failure=utc(),failure_stage=failed_stage,recovered=recovered)
                if isinstance(error,UpdateError): raise
                raise UpdateError('Update failed; inspect preserved operation diagnostics.') from error
            finally: self.raw_log=None
