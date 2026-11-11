# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Release checklist: README structure, real commands, links and source disclosures.

These checks are read-only. Shell blocks are syntax-checked, never executed on a
server. Actual CLI/Compose behavior is covered by disposable integration tests.
"""
import json
from pathlib import Path
import re
import subprocess
from workout_tracker import APP_VERSION,TARGET_SCHEMA_VERSION
from workout_updater.release_notes import read_notes
ROOT=Path(__file__).resolve().parents[1]


def test_readme_friendly_order_versions_commands_and_links():
    """The beginner guide opens before technical material and names actual CLI flags."""
    text=(ROOT/'README.md').read_text()
    assert text.startswith('# Workout Tracker\n\nA simple workout log')
    assert text.index('Installation — Start Here')<text.index('## Using Workout Tracker')<text.index('## Technical/developer information')
    assert 'healthy dose of AI, questionable amounts of confidence' in text
    assert APP_VERSION in text and TARGET_SCHEMA_VERSION==12
    assert 'New installation only.' in text and '#updating-the-application' in text
    assert '## Updating the application' in text and 'Never initialize an existing' in text
    for fragment in ('--target-version 12','--confirm-new-storage','--env-file ../.env','WORKOUT_UID=10001','WORKOUT_DATA_ROOT=/root/WorkoutTracker/data/storage','WORKOUT_BUILD_CA_BUNDLE='):
        assert fragment in text
    cli=(ROOT/'workout_tracker/__main__.py').read_text();compose=(ROOT/'compose.yaml').read_text()
    for flag in ('--confirm-new-storage','--confirm-upgrade','--target-version'):assert flag in cli
    for name in re.findall(r'^(WORKOUT_[A-Z_]+)=',text,re.M):assert name in compose or name=='WORKOUT_BUILD_CA_BUNDLE'
    for destination in re.findall(r'\]\(([^)]+)\)',text):
        if destination.startswith(('http:','https:','#')):continue
        assert (ROOT/destination.split('#')[0]).exists(),destination
    for block in re.findall(r'```(?:sh|bash)\n(.*?)```',text,re.S):
        result=subprocess.run(['bash','-n'],input=block,text=True,capture_output=True)
        assert result.returncode==0,result.stderr


def test_disclosure_and_permanent_release_rules():
    """Old wording is absent without altering historical database values or Git history."""
    old='SHAME'+'FULLY VIBE-CODED'
    files=subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines()
    for name in files:
        path=ROOT/name
        try:text=path.read_text()
        except (UnicodeDecodeError,OSError):continue
        assert old not in text,name
    for name in ('AGENTS.md','PROJECT_SPEC.md'):
        text=(ROOT/name).read_text()
        assert 'PERMANENT' in text.upper() and 'README' in text and 'every' in text.lower()
        assert 'release notes' in text.lower() and 'mandatory' in text.lower()
    for name in ('workout_tracker','workout_updater'):
        for path in (ROOT/name).rglob('*'):
            if path.suffix not in ('.py','.html','.js','.css','.svg'):continue
            assert 'SHAMELESSLY VIBE-CODED' in path.read_text()[:500],str(path)


def test_current_release_notes_and_readme_review_record_exist():
    """Every release has version-matched user notes and a documented review checklist."""
    note=(ROOT/'releases'/f'{APP_VERSION}.json').read_text()
    data=json.loads(note);assert data['version']==APP_VERSION and len(data['notes'])>=1
    assert read_notes(APP_VERSION,note).startswith('• ')
    # Retain the original Phase 12 content checks independently of newer releases.
    original=(ROOT/'releases/0.12.0.json').read_text()
    assert len(json.loads(original)['notes'])>=4
    assert 'Simplified exercise' in read_notes('0.12.0',original)
    assert not re.search(r'[0-9a-f]{40}',note)
    for technical in ('schema','workout_tracker/','git commit'):assert technical not in note.lower()
    assert 'Commands were checked against Compose' in (ROOT/'PHASE_12_REVIEW.md').read_text()
