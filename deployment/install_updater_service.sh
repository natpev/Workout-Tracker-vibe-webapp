#!/usr/bin/env bash
# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
# Explicit root-only host service installation; never called by Flask startup.
# Provision a restricted Unix socket bridge and a read-only private LAN HTTP
# status listener. No accounts, passwords, certificates, TLS or proxy are created.
set -Eeuo pipefail
umask 077
ROOT_DIR=/root/WorkoutTracker
LAN_ADDRESS=10.0.69.9
APP_URL=http://10.0.69.9:8000
STATUS_PORT=8001
while (( $# )); do
    [[ $# -ge 2 ]] || { echo 'Installer options require values.' >&2; exit 2; }
    case "$1" in
        --root) ROOT_DIR=$2 ;;
        --lan-address) LAN_ADDRESS=$2 ;;
        --app-url) APP_URL=$2 ;;
        --status-port) STATUS_PORT=$2 ;;
        *) echo 'Unknown installer argument' >&2; exit 2 ;;
    esac
    shift 2
done
[[ "$(id -u)" == 0 ]] || { echo 'One-time host installation requires root over SSH.' >&2; exit 1; }
for cmd in python3 docker systemctl install cp flock; do command -v "$cmd" >/dev/null; done
[[ "$ROOT_DIR" == /* && -d "$ROOT_DIR/app/.git" && ! -L "$ROOT_DIR/app" && ! -L "$ROOT_DIR/app/.git" && -f "$ROOT_DIR/.env" && ! -L "$ROOT_DIR/.env" && -d "$ROOT_DIR/data/storage/config" ]] || { echo 'Existing installation required; storage will not be initialized.' >&2; exit 1; }
python3 - "$ROOT_DIR" "$LAN_ADDRESS" "$APP_URL" "$STATUS_PORT" <<'PY'
# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
# Validate fixed operator paths/interface before provisioning any host files.
import ipaddress,sys
from pathlib import Path
from urllib.parse import urlsplit
root,address,url,port=sys.argv[1:];path=Path(root)
assert path.resolve()==path and not path.is_symlink(), 'Canonical root required'
assert all(c not in root for c in ('\n','\r',' ','%','"')), 'Use a simple canonical installation path'
ip=ipaddress.ip_address(address)
assert ip.version==4 and ip.is_private and not ip.is_unspecified and not ip.is_multicast, 'Explicit private IPv4 required'
parsed=urlsplit(url)
assert parsed.scheme=='http' and parsed.hostname in (address,'127.0.0.1','localhost') and not parsed.username and not parsed.password and parsed.path in ('','/') and not parsed.query and not parsed.fragment, 'Fixed local HTTP app origin required'
assert 1024<=int(port)<=65535 and int(port)!=(parsed.port or 80), 'Separate private status port required'
PY
exec 9>"$ROOT_DIR/.workout-update.lock"
flock -n 9 || { echo 'An updater operation is running. Retry service installation later.' >&2; exit 1; }
STATE="$ROOT_DIR/updater"
[[ ! -L "$STATE" ]] || { echo 'Updater state directory must not be a symlink.' >&2; exit 1; }
install -d -o 0 -g 0 -m 0700 "$STATE"
# Installation stops only the independent updater, never workout containers.
systemctl stop workout-tracker-updater.service 2>/dev/null || true
python3 -m venv "$STATE/venv"
"$STATE/venv/bin/python" -m pip install -r "$ROOT_DIR/app/requirements.txt"
install -d -m 0700 "$STATE/runtime" "$STATE/docker"
# Docker buildx needs writable client state under the updater's allowed tree.
# Preserve an existing registry/proxy config privately; never print its contents.
SOURCE_DOCKER_CONFIG="${DOCKER_CONFIG:-/root/.docker}"
if [[ ! -e "$STATE/docker/config.json" && -f "$SOURCE_DOCKER_CONFIG/config.json" && ! -L "$SOURCE_DOCKER_CONFIG/config.json" ]]; then
    install -m 0600 "$SOURCE_DOCKER_CONFIG/config.json" "$STATE/docker/config.json"
fi
cp -a "$ROOT_DIR/app/workout_updater" "$STATE/runtime/"
"$STATE/venv/bin/python" - "$ROOT_DIR" "$LAN_ADDRESS" "$APP_URL" "$STATUS_PORT" <<'PY'
# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
# Provision fixed paths and OS permissions; no user credentials or secrets exist.
import json,os,subprocess,sys
from pathlib import Path
root=Path(sys.argv[1]);state=root/'updater';address,app_url,port=sys.argv[2:]
prefix=['docker','--host=unix:///var/run/docker.sock','compose','--project-directory',str(root/'app'),'--env-file',str(root/'.env'),'-f',str(root/'app/compose.yaml')]
cfg=json.loads(subprocess.run([*prefix,'config','--format','json'],check=True,capture_output=True,text=True).stdout)
users=[cfg['services'][name]['user'] for name in ('web','scheduler')];assert users[0]==users[1]
uid,gid=map(int,users[0].split(':'));assert uid>0 and gid>0
for name in ('web','scheduler'):
 service=cfg['services'][name]
 assert service['image']=='workout-tracker:local'
 volumes=[v for v in service['volumes'] if v.get('target')=='/var/lib/workout-tracker']
 assert len(volumes)==1 and volumes[0]['type']=='bind' and volumes[0]['source']==str(root/'data/storage'), 'Wrong storage mount'
 assert all(v.get('source')!='/var/run/docker.sock' for v in service['volumes']), 'Docker socket in app refused'
assert (root/'data/storage').resolve()==root/'data/storage', 'Symlinked data root refused'
bridge=root/'data/storage/config/updater-bridge'
assert not bridge.is_symlink();bridge.mkdir(mode=0o750,exist_ok=True);os.chown(bridge,0,gid);bridge.chmod(0o750)
config=dict(root=str(root),uid=uid,gid=gid,status_url=f'http://{address}:{port}/status',app_url=app_url)
for path,value in ((state/'config.json',config),(bridge/'client.json',{'status_url':config['status_url']})):
 assert not path.is_symlink()
 path.write_text(json.dumps(value));path.chmod(0o640 if path.parent==bridge else 0o600)
 os.chown(path,0,gid if path.parent==bridge else 0)
PY
cat > /etc/systemd/system/workout-tracker-updater.service <<EOF
# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
# Independent fixed-operation host worker and read-only LAN HTTP progress.
[Unit]
Description=Workout Tracker trusted LAN host updater and status
After=docker.service network-online.target
Requires=docker.service
[Service]
Type=simple
User=root
Group=root
WorkingDirectory=$STATE/runtime
Environment=PYTHONPATH=$STATE/runtime
Environment=PYTHONDONTWRITEBYTECODE=1
Environment=DOCKER_CONFIG=$STATE/docker
Environment=BUILDX_BUILDER=default
ExecStart=$STATE/venv/bin/python -m workout_updater serve --root $ROOT_DIR
Restart=on-failure
RestartSec=5
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=$ROOT_DIR /var/run/docker.sock
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
flock -u 9
systemctl enable --now workout-tracker-updater.service
printf 'Host updater installed. Application remains at %s.\nRead-only progress: http://%s:%s/status\n' "$APP_URL" "$LAN_ADDRESS" "$STATUS_PORT"
printf 'No application migration/startup or configuration change was performed. Anyone on the trusted LAN who can reach the app may confirm updates and deletion.\n'
