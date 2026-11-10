# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Passwordless LAN app -> permission-restricted host Unix socket, fixed JSON actions.

The browser never controls commands, repositories, URLs or images. The operator
installs the socket/config explicitly. Missing setup is reported, not invented.
There are no user credentials, tokens, accounts, login or TLS components here.
"""
import ipaddress
import json
import os
import socket
from urllib.parse import urlsplit
from .storage import storage_root,_regular_file,StorageError


def bridge(value):
    """Read operator-installed HTTP status metadata, never secrets or user URLs."""
    directory=storage_root(value)/'config/updater-bridge';config=directory/'client.json'
    if directory.is_symlink():raise StorageError('Unsafe updater bridge directory.')
    if not os.path.lexists(config): raise StorageError('Host updater is not installed. Follow deployment/README.md for the one-time SSH setup.')
    _regular_file(config)
    if config.stat().st_size>8192: raise StorageError('Invalid updater bridge file.')
    settings=json.loads(config.read_text());url=urlsplit(settings['status_url'])
    try: address=ipaddress.ip_address(url.hostname)
    except ValueError as error: raise StorageError('Status URL requires an explicit private LAN interface.') from error
    if url.scheme!='http' or url.username or url.password or not address.is_private or address.is_unspecified or address.is_multicast:
        raise StorageError('Status URL must be operator-configured private LAN HTTP.')
    return directory,settings


def call(value,action,**fields):
    """Send one bounded fixed operation; host validates peer UID and request schema."""
    directory,settings=bridge(value)
    body=json.dumps(dict(action=action,**fields),separators=(',',':')).encode()+b'\n'
    try:
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as stream:
            stream.settimeout(5);stream.connect(str(directory/'control.sock'));stream.sendall(body)
            response=b''
            while not response.endswith(b'\n'):
                chunk=stream.recv(65536)
                if not chunk or len(response)>262144: raise StorageError('Invalid updater response.')
                response+=chunk
        result=json.loads(response)
        if not result.get('ok'): raise StorageError(result.get('error','Host updater refused request.'))
        return result['state']
    except (OSError,ValueError,KeyError) as error:
        raise StorageError('Host updater unavailable. Use its independent LAN status page or emergency v4 CLI.') from error
