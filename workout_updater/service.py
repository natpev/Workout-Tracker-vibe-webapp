# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""Restricted Unix controls and independent read-only LAN HTTP status, no login/TLS.

Control socket mode 0660 and Linux peer UID restrict host operations to the app
writer/root. Only fixed reviewed actions are accepted. LAN HTTP has read-only
status/log pages on an explicitly configured private interface, never command API.
"""
import fcntl
import ipaddress
import json
import os
import socket
import socketserver
import struct
import threading
from urllib.parse import urlsplit
from datetime import datetime
from flask import Flask,render_template_string,jsonify
from werkzeug.serving import make_server
from .engine import Engine,UpdateError,RUNNING,utc


class Controller:
    """Validate fixed requests and serialize jobs independently of web lifetime."""
    def __init__(self,engine):
        """Keep a process mutex alongside the cross-process operation file lock."""
        self.engine=engine;self.lock=threading.Lock();self.busy=False

    def handle(self,value):
        """Reject unknown fields/commands and unreviewed releases before scheduling."""
        if not isinstance(value,dict):raise UpdateError('A fixed JSON object is required.')
        action=value.get('action')
        fields={'status':{'action'},'check':{'action'},'install':{'action','release','confirm','migration'}}
        if action not in fields or set(value)!=fields[action]:raise UpdateError('Only predefined update operations are allowed.')
        with self.lock:
            if action=='status':return self.engine.state()
            if self.busy:raise UpdateError('An updater operation is already running.')
            if action=='install':
                known=self.engine.state().get('release')
                if value['confirm'] is not True or type(value['migration']) is not bool or not known or value['release']!=known['id']:
                    raise UpdateError('Review and confirm the known approved release.')
            self.busy=True
            # The engine publishes progress only after acquiring the cross-process
            # lock. A browser request must not overwrite an emergency CLI job's
            # live status when that job already owns the installation.
            threading.Thread(target=self.work,args=(value,),daemon=True).start()
            return self.engine.state()

    def work(self,value):
        """Run the approved engine in a host thread that survives stopping Flask."""
        try:
            if value['action']=='check':self.engine.check()
            else:self.engine.install(value['release'],confirm=value['confirm'],migration_confirm=value['migration'])
        except UpdateError as error:
            # A concurrent CLI owns its own status. Reject this request without
            # falsely marking that still-running operation as failed.
            if 'Another update/check is already running.' not in str(error) and self.engine.state().get('status')!='Failed':
                self.engine.event('Failed','Operation refused; inspect host diagnostics.',last_failure=utc())
        except Exception:
            if self.engine.state().get('status')!='Failed':self.engine.event('Failed','Operation refused; inspect host diagnostics.',last_failure=utc())
        finally:
            with self.lock:self.busy=False


class UnixServer(socketserver.ThreadingUnixStreamServer):
    """Linux-only local control server with no TCP command listener."""
    daemon_threads=True


class Handler(socketserver.StreamRequestHandler):
    """Check OS peer UID, bound requests/time and return only safe state/errors."""
    def handle(self):
        """Read a single local JSON operation; never interpret command text."""
        self.request.settimeout(5)
        try:
            _,uid,_=struct.unpack('3i',self.request.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
            if uid not in (0,self.server.writer_uid):raise UpdateError('Unexpected local socket peer.')
            line=self.rfile.readline(16385)
            if len(line)>16384 or not line.endswith(b'\n'):raise UpdateError('Invalid bounded request.')
            result=dict(ok=True,state=self.server.controller.handle(json.loads(line)))
        except (ValueError,TypeError,KeyError,UpdateError,OSError):
            result=dict(ok=False,error='Host updater refused invalid, unexpected-peer or overlapping operation.')
        self.wfile.write(json.dumps(result).encode()+b'\n')


STATUS_TEMPLATE='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">{% if state.status in running %}<meta http-equiv="refresh" content="5">{% endif %}<title>Workout Tracker update progress</title></head><body><h1>Independent Update Progress</h1><p>{{ state.status }}</p><p>Last successful update: {{ state.last_success|timestamp or 'None' }} · Last failed update: {{ state.last_failure|timestamp or 'None' }}</p>{% for event in state.events|reverse %}<p>{{ event.time|timestamp }} · {{ event.status }} · {{ event.message }}</p>{% endfor %}<p>This read-only page stays available while the application restarts. No progress percentages are guessed.</p><p>Trusted private LAN only. No login or password is required.</p><a href="{{ app_url }}/settings/updates">Reconnect to Application Updates</a><a href="/status.json">Read status JSON</a></body></html>'''


def status_app(engine):
    """Expose GET-only safe status on the configured interface, never control calls."""
    address=urlsplit(engine.config['status_url']).hostname
    ip=ipaddress.ip_address(address)
    if not ip.is_private or ip.is_unspecified or ip.is_multicast:raise UpdateError('Explicit private status interface required.')
    app=Flask('workout-updater-status')
    app.config.update(TRUSTED_HOSTS=[address],MAX_CONTENT_LENGTH=1024)

    @app.template_filter('timestamp')
    def status_timestamp(value):
        """Render precise UTC diagnostic times in 24-hour form, never browser locale."""
        if not value:return ''
        try:return datetime.fromisoformat(str(value).replace('Z','+00:00')).strftime('%Y-%m-%d %H:%M:%S %Z')
        except ValueError:return str(value)

    @app.get('/status')
    def page():
        """Render actual persistent progress and safe logs without authentication."""
        return render_template_string(STATUS_TEMPLATE,state=engine.state(),running=RUNNING,app_url=engine.config['app_url'].rstrip('/'))

    @app.get('/status.json')
    def status():
        """Read-only status data; no action parameter is accepted or executed."""
        return jsonify(engine.state())

    @app.after_request
    def protected(response):
        """Prevent caching/framing and external assets; there are no login cookies."""
        response.headers.update({'Cache-Control':'no-store','X-Content-Type-Options':'nosniff',
          'Content-Security-Policy':"default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"})
        return response
    return app


def serve(root):
    """Run fixed Unix controls and read-only LAN HTTP; never update on startup."""
    engine=Engine(root)
    instance=(engine.state_dir/'service.lock').open('a')
    try:fcntl.flock(instance,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError as error:raise UpdateError('Host updater service is already running.') from error
    try:
        with engine.locked():
            if engine.state().get('status') in RUNNING:
                if engine.state().get('operation_type')=='install':
                    engine.command([*engine.compose,'stop','web','scheduler'],check=False)
                engine.event('Failed','Interrupted operation: inspect preserved source, image, storage and private log. No automatic replay or data restore.',last_failure=utc())
    except UpdateError:pass
    path=engine.data/'config/updater-bridge/control.sock'
    if len(os.fsencode(path))>=104:raise UpdateError('Installation path is too long for the Unix control socket.')
    if os.path.lexists(path):
        import stat
        if not stat.S_ISSOCK(path.lstat().st_mode):raise UpdateError('Unsafe existing control socket.')
        path.unlink()
    server=UnixServer(str(path),Handler);server.controller=Controller(engine);server.writer_uid=engine.config['uid']
    os.chmod(path,0o660);os.chown(path,-1,engine.config['gid'])
    threading.Thread(target=server.serve_forever,daemon=True).start()
    url=urlsplit(engine.config['status_url'])
    if url.scheme!='http':raise UpdateError('Only configured LAN HTTP status is supported.')
    http=make_server(url.hostname,url.port or 8001,status_app(engine),threaded=True)
    try:http.serve_forever()
    finally:server.shutdown();server.server_close();http.server_close();instance.close()
