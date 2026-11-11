# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Actual image preserves schema-10 audits/drafts and schema-11 SVG backups."""
import json
import os
import pytest
from test_basis import basis_data
from test_basis_docker import run_storage
pytestmark=pytest.mark.skipif(os.environ.get('WORKOUT_CONTAINER_TESTS')!='1',reason='Opt-in disposable Docker verification')


def test_schema10_candidate_icons_and_restore_inside_real_image(basis_data):
    x=basis_data;root=x['root'];manifest=root/'config/active.json'
    source=root/'data'/json.loads(manifest.read_text())['database'];original=source.read_bytes()
    run_storage(root,'-m','workout_tracker','migrate-storage','--data-root','/var/lib/workout-tracker','--target-version','11','--confirm-upgrade')
    script=f'''
from uuid import uuid4
from workout_tracker.storage import database_session,inspect_storage
from workout_tracker import exercise_icons as icons,history as h,workouts as w
from workout_tracker.maintenance import backup,restore
root='/var/lib/workout-tracker'
assert inspect_storage(root)['schema_version']==11
with database_session(root,write=True) as db:
 assert h.effective(db,{x['a']!r},{x['first']!r})[1][0]['actual_weight_tenths_lb']==250
 assert w.entries(db,{x['a']!r},w.active(db,{x['a']!r})['id'])[0]['actual_weight_tenths_lb']==410
 icons.update(db,{x['e']!r},'start','<svg xmlns="http://www.w3.org/2000/svg"><circle cx="128" cy="128" r="90" fill="var(--accent)"/></svg>')
result=backup(root,uuid4().hex)
assert result['status']=='verified'
with database_session(root,write=True) as db:icons.update(db,{x['e']!r},'start')
assert restore(root,result['id'],uuid4().hex,confirm=True)['status']=='succeeded'
'''
    run_storage(root,'-c',script)
    # A second brand-new container reads the same persistent artwork and audits.
    run_storage(root,'-c',f"from workout_tracker.storage import database_session; from workout_tracker import exercise_icons as i; from workout_tracker.maintenance import backup; from uuid import uuid4; db=database_session('/var/lib/workout-tracker'); c=db.__enter__(); assert i.pairs(c,[{x['e']!r}])[{x['e']!r}]['start']['custom']; db.__exit__(None,None,None); assert backup('/var/lib/workout-tracker',uuid4().hex)['status']=='verified'")
    assert source.read_bytes()==original
