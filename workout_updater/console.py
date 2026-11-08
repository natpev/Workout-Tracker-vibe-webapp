# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""Bounded browser-safe output, never a view of private command logs or files.

Only recognized Git/build/container/storage output becomes structured safe text.
Unrecognized text, URLs, commands, config and exception bodies stay private.
Each operation has an atomic bounded ring; only the newest 20 safe rings remain.
"""
from datetime import datetime,timezone
import json
import os
import re
from .engine import read_json,write_json,UpdateError

MAX_LINES=500
MAX_TEXT=500
KEEP_OPERATIONS=20
OPERATION=re.compile(r'[0-9a-f]{32}')
FILE=re.compile(r'([0-9a-f]{32})\.console\.json')


def safe_line(kind,line):
    """Default-deny parser: return recognized output only, discarding free-form data."""
    line=re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]','',line).strip()
    if len(line)>4096:return None
    if kind=='git':
        match=re.fullmatch(r'(?:remote: )?(Enumerating|Counting|Compressing|Receiving|Resolving) (objects|deltas): ([0-9%(),./ KiBMs]+)(?:done\.)?',line)
        if match:return 'Git '+match[1].lower()+' '+match[2]+': '+match[3].strip()
        if re.fullmatch(r'[0-9a-f]{40}',line):return 'Git revision '+line
        if line.startswith('From '):return 'Git received the approved repository response.'
        if line in ('Already up to date.','Fast-forward'):return 'Git: '+line
    if kind=='build':
        match=re.fullmatch(r'#([0-9]+) (DONE(?: [0-9.]+s)?|CACHED)',line)
        if match:return 'Build step '+match[1]+': '+match[2]
        if re.match(r'#[0-9]+ ERROR:',line):return 'Build step failed; details remain in private diagnostics.'
        if 'Installing collected packages:' in line:return 'Installing application dependencies.'
        if re.search(r'\bSuccessfully installed\b',line):return 'Application dependency installation completed.'
        if re.match(r'#[0-9]+ (?:[0-9.]+ )?(?:Collecting|Downloading) ',line):return 'Application dependency download in progress.'
    if kind in ('build','stop','start'):
        match=re.fullmatch(r'(?:Container )?[^\s]+-(web|scheduler)-[0-9]+\s+(Creating|Created|Starting|Started|Stopping|Stopped|Running|Recreate|Recreated|Healthy|Waiting)',line)
        if match:return match[1]+': '+match[2]
    if kind=='storage':
        match=re.fullmatch(r'Storage verified; schema version ([0-9]+)\.',line)
        if match:return 'Storage verified; schema '+match[1]+'.'
        match=re.match(r'Schema ([0-9]+) verified',line)
        if match:return 'Candidate schema '+match[1]+' verified.'
    if kind=='backup':
        try:value=json.loads(line)
        except ValueError:return None
        if isinstance(value,dict) and set(value)=={'id','status'} and value['status']=='verified' and isinstance(value['id'],str) and OPERATION.fullmatch(value['id']):
            return 'Database backup verified: '+value['id']
    return None


def retained(directory):
    """List only regular bounded safe-operation files; no request pathname is accepted."""
    rows=[]
    for path in directory.glob('*.console.json'):
        match=FILE.fullmatch(path.name)
        if match and not path.is_symlink() and path.is_file() and path.stat().st_size<=1048576:
            rows.append((path.stat().st_mtime_ns,match[1]))
    return [identity for _,identity in sorted(rows,reverse=True)[:KEEP_OPERATIONS]]


def read_console(directory,operation,after=0):
    """Read one allowlisted safe ring, rejecting private files, links and bad cursors."""
    if not isinstance(operation,str) or not OPERATION.fullmatch(operation) or operation not in retained(directory):
        raise UpdateError('Choose a current or retained safe operation.')
    if type(after) is not int or not 0<=after<=10**12:raise UpdateError('Invalid console cursor.')
    value=read_json(directory/(operation+'.console.json'))
    if not isinstance(value,dict) or value.get('operation')!=operation or not isinstance(value.get('lines'),list) or len(value['lines'])>MAX_LINES:
        raise UpdateError('Safe operation output could not be verified.')
    previous=0
    if type(value.get('sequence')) is not int or not 0<=value['sequence']<=10**12:
        raise UpdateError('Safe operation output could not be verified.')
    for row in value['lines']:
        if not isinstance(row,dict) or set(row)!={'sequence','time','text'} or type(row['sequence']) is not int or not previous<row['sequence']<=value['sequence'] or not isinstance(row['text'],str) or len(row['text'])>MAX_TEXT or not isinstance(row['time'],str):
            raise UpdateError('Safe operation output could not be verified.')
        try:stamp=datetime.fromisoformat(row['time'])
        except ValueError as error:raise UpdateError('Safe operation output could not be verified.') from error
        if stamp.utcoffset() is None or stamp.utcoffset().total_seconds()!=0:
            raise UpdateError('Safe operation output could not be verified.')
        previous=row['sequence']
    if value['lines'] and previous!=value['sequence']:
        raise UpdateError('Safe operation output could not be verified.')
    return dict(operation=operation,lines=[r for r in value['lines'] if r['sequence']>after],
                first=value['lines'][0]['sequence'] if value['lines'] else 0,last=value.get('sequence',0))


class Console:
    """One updater-owned ring, written only while the host operation lock is held."""
    def __init__(self,directory,operation):
        """Create a fresh private safe-output ring and prune only older safe rings."""
        if not OPERATION.fullmatch(operation):raise UpdateError('Invalid operation identifier.')
        self.path=directory/(operation+'.console.json');self.value=dict(operation=operation,sequence=0,lines=[])
        if os.path.lexists(self.path):raise UpdateError('Operation output already exists.')
        write_json(self.path,self.value)
        keep=set(retained(directory))
        for path in directory.glob('*.console.json'):
            match=FILE.fullmatch(path.name)
            if match and match[1] not in keep and not path.is_symlink():path.unlink()

    def append(self,text):
        """Persist one short safe event atomically; private logs are never touched."""
        text=re.sub(r'[\x00-\x1f\x7f]','',str(text).encode('ascii','replace').decode())[:MAX_TEXT]
        if self.value['lines'] and self.value['lines'][-1]['text']==text:return
        self.value['sequence']+=1
        self.value['lines']=(self.value['lines']+[dict(sequence=self.value['sequence'],time=datetime.now(timezone.utc).isoformat(),text=text)])[-MAX_LINES:]
        write_json(self.path,self.value)
