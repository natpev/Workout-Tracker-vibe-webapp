# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Real schema-11-to-12 CLI and large-artwork persistence in disposable containers."""
import inspect
import json
import os
import pytest
from test_phase15 import ui_root, ui_data
from test_basis_docker import run_storage
from test_icon_upload_size import sized_svg

pytestmark = pytest.mark.skipif(os.environ.get('WORKOUT_CONTAINER_TESTS') != '1', reason='Opt-in disposable Docker verification')


def test_schema12_real_image_migration_two_full_icons_backup_and_restart(ui_data):
    """Separate containers preserve the original and read both restored 300-KiB slots."""
    x = ui_data
    source = x['root'] / 'data' / json.loads((x['root'] / 'config/active.json').read_text())['database']
    original = source.read_bytes()
    run_storage(x['root'], '-m', 'workout_tracker', 'migrate-storage', '--data-root', '/var/lib/workout-tracker', '--target-version', '12', '--confirm-upgrade')
    script = '''
import xml.etree.ElementTree as ET
from uuid import uuid4
from workout_tracker.storage import database_session,inspect_storage
from workout_tracker import exercise_icons as icons
from workout_tracker.maintenance import backup,restore
root='/var/lib/workout-tracker'
assert inspect_storage(root)['schema_version']==12
'''+inspect.getsource(sized_svg)+f'''
with database_session(root,write=True) as db:
 for slot in ('start','end'):icons.update(db,{x['e']!r},slot,sized_svg(307200))
record=backup(root,uuid4().hex)
assert record['status']=='verified' and record['schema_version']==12
with database_session(root,write=True) as db:
 for slot in ('start','end'):icons.update(db,{x['e']!r},slot)
assert restore(root,record['id'],uuid4().hex,confirm=True)['status']=='succeeded'
'''
    run_storage(x['root'], '-c', script)
    run_storage(x['root'], '-c', f"from workout_tracker.storage import database_session; from workout_tracker.exercise_icons import pairs; c=database_session('/var/lib/workout-tracker'); db=c.__enter__(); rows=list(db.execute('SELECT svg FROM exercise_icons')); assert len(rows)==2 and all(len(r[0].encode())==307200 for r in rows); assert pairs(db,[{x['e']!r}])[{x['e']!r}]['end']['custom']; c.__exit__(None,None,None)")
    assert source.read_bytes() == original
