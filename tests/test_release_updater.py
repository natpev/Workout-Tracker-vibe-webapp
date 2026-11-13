# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Version-1 target failure boundaries with real synthetic SQLite and host engine.

Git/Docker are controlled adapters; real Docker coverage is separate. No remote
server, actual update deployment or production database is involved.
"""
import json
import os
from unittest.mock import patch
import pytest
from workout_updater.engine import Engine,UpdateError
from workout_tracker.storage import inspect_storage
from test_phase8_updater import fixture


@pytest.mark.parametrize('fault',['ok','fetch','build','migration','startup','readiness'])
def test_release13_update_failure_preserves_original_and_never_restarts_incompatible_image(tmp_path,fault):
    """Before activation retain schema12; after activation refuse old-image recovery."""
    root,env=fixture(tmp_path,12)
    env.update(METADATA_VERSION='1.0.1',METADATA_SCHEMA='13',MODE='ok')
    manifest=root/'data/storage/config/active.json';original=root/'data/storage/data'/json.loads(manifest.read_text())['database'];content=original.read_bytes();selection=manifest.read_bytes()
    with patch.dict(os.environ,env,clear=True),patch('time.sleep'):
        engine=Engine(root);release=engine.check()
        os.environ['MODE']=fault
        if fault=='ok':
            state=engine.install(release['id'],confirm=True,migration_confirm=True)
            assert state['status']=='Completed' and state['installed_version']=='1.0.1' and state['installed_schema']==13
        else:
            with pytest.raises(UpdateError):engine.install(release['id'],confirm=True,migration_confirm=True)
            state=engine.state();assert state['status']=='Failed'
            if fault in ('startup','readiness'):
                assert state['recovered'] is False
                assert inspect_storage(root/'data/storage')['schema_version']==13
                assert manifest.read_bytes()!=selection
            else:
                assert manifest.read_bytes()==selection
                assert inspect_storage(root/'data/storage')['schema_version']==12
            if fault in ('build','migration'):assert state['recovered'] is True
    assert original.read_bytes()==content
    if fault!='fetch':assert list((root/'updater').glob('*.recovery.json'))
