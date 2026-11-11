# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Large valid vector uploads, exact byte limits and schema-12 preservation.

All data is synthetic. HTTP tests use the actual bounded upload/sanitizer/SQLite
path; migration and restore tests never open an installed workout database.
"""
import io
import json
import sqlite3
import xml.etree.ElementTree as ET
from uuid import uuid4
from unittest.mock import patch
import pytest
from workout_tracker import create_app, exercise_icons as icons, catalog as c
from workout_tracker.storage import database_session, inspect_storage, StorageError
from workout_tracker.migrations import migrate_storage
from workout_tracker.maintenance import backup, restore
from test_phase15 import ui_root, ui_data, SVG
from test_phase8_deletion import token
from test_basis import basis_data


def sized_svg(size):
    """Build a real vector with many path segments and an exact UTF-8 byte size.

    Each path remains below the unchanged attribute-length bound. Only the final
    few bytes are XML whitespace; the bulk of the file is legitimate geometry.
    The root already has canonical attributes so boundary uploads do not expand.
    """
    opening = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256" preserveAspectRatio="xMidYMid meet">'
    closing = b'</svg>'
    parts = [opening]
    remaining = size - len(opening) - len(closing)
    while remaining >= 90:
        start = b'<path fill="var(--accent)" stroke="currentColor" d="M0 0 '
        end = b'" />'
        count = min(4000, (remaining - len(start) - len(end)) // 5)
        piece = start + b'L1 1 ' * count + end
        parts.append(piece)
        remaining -= len(piece)
    parts.extend((b' ' * remaining, closing))
    result = b''.join(parts)
    assert len(result) == size
    ET.fromstring(result)
    return result


@pytest.fixture
def icon_data(ui_data):
    """Upgrade disposable schema 11 explicitly before accepting larger artwork."""
    migrate_storage(ui_data['root'], 12)
    return ui_data


def upload(client, x, position, source):
    """Exercise the real multipart endpoint, including CSRF and safe redirects."""
    editor = f"/people/{x['a']}/exercises/{x['e']}/defaults"
    page = client.get(editor)
    return client.post(f"/people/{x['a']}/exercises/{x['e']}/icons/{position}",
        data=dict(csrf_token=token(page), action='upload', svg=(io.BytesIO(source), 'illustration.svg')),
        follow_redirects=True)


@pytest.mark.parametrize('position', ['start', 'end'])
@pytest.mark.parametrize('size', [85 * 1024, 150 * 1024, 250 * 1024, 307200])
def test_valid_large_svg_uploads_and_exact_boundary(icon_data, position, size):
    """Each slot independently accepts actual vector documents through 300 KiB."""
    x = icon_data
    client = create_app({'TESTING': True, 'WORKOUT_DATA_ROOT': x['root']}).test_client()
    source = sized_svg(size)
    response = upload(client, x, position, source)
    assert response.status_code == 200 and b'Shared exercise icon updated.' in response.data
    assert b'SVG only, up to 300 KiB per image.' in response.data
    with database_session(x['root']) as db:
        stored = db.execute('SELECT svg FROM exercise_icons WHERE exercise_id=? AND position=?', (x['e'], position)).fetchone()[0]
        assert stored.encode() == source
        assert icons.sanitize(stored) == stored
        assert 'var(--accent)' in str(icons.pairs(db, [x['e']])[x['e']][position]['svg'])


@pytest.mark.parametrize('position', ['start', 'end'])
def test_both_slots_replace_and_rejected_uploads_preserve_prior(icon_data, position):
    """Two full-sized slots coexist; byte/security/complexity failures change neither."""
    x = icon_data
    client = create_app({'TESTING': True, 'WORKOUT_DATA_ROOT': x['root']}).test_client()
    for slot in ('start', 'end'):
        assert b'Shared exercise icon updated.' in upload(client, x, slot, sized_svg(307200)).data
    assert b'Shared exercise icon updated.' in upload(client, x, position, sized_svg(150 * 1024)).data
    with database_session(x['root']) as db:
        before = [tuple(r) for r in db.execute('SELECT * FROM exercise_icons ORDER BY position')]
    failures = [
        (sized_svg(307201), b'300 KiB per image'),
        (b'<svg><script>alert(1)</script></svg>', b'unsupported element'),
        (b'<svg>' + b'<g/>' * 1024 + b'</svg>', b'too many elements (maximum 1024)'),
        (b'<svg><path d="M0 0 ' + b'L1 1 ' * 6600 + b'"/></svg>', b'attribute exceeds the complexity limit (maximum 32768 characters)'),
    ]
    for source, message in failures:
        response = upload(client, x, position, source)
        assert b'Icon unchanged:' in response.data and message in response.data
        with database_session(x['root']) as db:
            assert [tuple(r) for r in db.execute('SELECT * FROM exercise_icons ORDER BY position')] == before


def test_canonical_expansion_is_bounded_and_preserves_existing(icon_data):
    """A valid upload at the raw limit may expand; canonical bytes have the same cap."""
    x = icon_data
    namespace = b' xmlns="http://www.w3.org/2000/svg"'
    source = sized_svg(307200).replace(namespace, b'', 1)
    source = source[:-6] + b' ' * len(namespace) + source[-6:]
    assert len(source) == 307200
    ET.fromstring(source)
    with pytest.raises(c.ValidationError, match='Canonical SVG exceeds 300 KiB'):
        icons.sanitize(source)
    client = create_app({'TESTING': True, 'WORKOUT_DATA_ROOT': x['root']}).test_client()
    upload(client, x, 'start', SVG.encode())
    response = upload(client, x, 'start', source)
    assert b'Canonical SVG exceeds 300 KiB' in response.data
    with database_session(x['root']) as db:
        assert db.execute('SELECT svg FROM exercise_icons').fetchone()[0] == icons.sanitize(SVG)


def test_upload_read_is_bounded_at_limit_plus_one(icon_data):
    """Even an enormous incoming stream is read with one fixed-size request."""
    from werkzeug.datastructures import FileStorage
    x = icon_data
    client = create_app({'TESTING': True, 'WORKOUT_DATA_ROOT': x['root']}).test_client()
    page = client.get(f"/people/{x['a']}/exercises/{x['e']}/defaults")
    class OversizedStream:
        def read(self, size):
            """Refuse unbounded reads; supply only the requested overflow sentinel."""
            assert size == 307201
            return sized_svg(size)
    fake = FileStorage(stream=OversizedStream(), filename='large.svg')
    from werkzeug.datastructures import ImmutableMultiDict
    real_get = ImmutableMultiDict.get
    def files_only(fields, key, *args, **kwargs):
        """Substitute only the upload; preserve the real form/CSRF lookup behavior."""
        if key == 'svg':
            return fake
        return real_get(fields, key, *args, **kwargs)
    with patch.object(ImmutableMultiDict, 'get', files_only):
        result = client.post(f"/people/{x['a']}/exercises/{x['e']}/icons/start",
                             data=dict(csrf_token=token(page), action='upload'))
    assert result.status_code == 303


def test_schema11_requires_explicit_upgrade_without_losing_old_icon(ui_data):
    """Old installations remain readable; no upload silently changes their schema."""
    x = ui_data
    client = create_app({'TESTING': True, 'WORKOUT_DATA_ROOT': x['root']}).test_client()
    upload(client, x, 'start', SVG.encode())
    assert b'explicit upgrade to database schema 12' in upload(client, x, 'start', sized_svg(85 * 1024)).data
    assert inspect_storage(x['root'])['schema_version'] == 11
    with database_session(x['root']) as db:
        assert db.execute('SELECT svg FROM exercise_icons').fetchone()[0] == icons.sanitize(SVG)


def all_cells(db):
    """Snapshot every table so migration checks include histories, drafts and audits."""
    return {name: [tuple(row) for row in db.execute(f'SELECT * FROM {name} ORDER BY 1,2')]
            for name, in db.execute("SELECT name FROM sqlite_schema WHERE type='table' AND substr(name,1,7)!='sqlite_'")}


def test_candidate_migration_preserves_original_history_and_icons(basis_data):
    """Only icon DDL and the version marker change; every original cell is retained."""
    x = basis_data
    migrate_storage(x['root'], 11)
    with database_session(x['root'], write=True) as db:
        icons.update(db, x['e'], 'start', SVG)
        icons.update(db, x['e'], 'end', SVG)
        before = all_cells(db)
        ddl = dict(db.execute("SELECT name,sql FROM sqlite_schema WHERE substr(name,1,7)!='sqlite_'"))
    old = (x['root'] / 'data' / json.loads((x['root'] / 'config/active.json').read_text())['database'])
    original = old.read_bytes()
    migrate_storage(x['root'], 12)
    assert old.read_bytes() == original and (x['root'] / 'data' / json.loads((x['root'] / 'config/active.json').read_text())['database']) != old
    with database_session(x['root']) as db:
        after = all_cells(db)
        after['schema_migrations'] = after['schema_migrations'][:-1]
        assert before == after
        new_ddl = dict(db.execute("SELECT name,sql FROM sqlite_schema WHERE substr(name,1,7)!='sqlite_'"))
        assert [name for name in ddl if ddl[name] != new_ddl[name]] == ['exercise_icons']
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert not db.execute('PRAGMA foreign_key_check').fetchall()
    selection = (x['root'] / 'config/active.json').read_bytes()
    assert migrate_storage(x['root'], 12)['changed'] is False
    assert (x['root'] / 'config/active.json').read_bytes() == selection


@pytest.mark.parametrize('stage', ['upgrade', 'preservation', 'validation', 'activation', 'post_activation'])
def test_failed_candidate_preserves_schema11_and_selection(ui_data, stage):
    """Injected failures cannot publish an incomplete candidate or replace originals."""
    from workout_tracker import migrations as m, icon_size_schema
    x = ui_data
    with database_session(x['root'], write=True) as db:
        icons.update(db, x['e'], 'start', SVG)
    active = x['root'] / 'config/active.json'
    selection = active.read_bytes()
    original = (x['root'] / 'data' / json.loads((x['root'] / 'config/active.json').read_text())['database'])
    content = original.read_bytes()
    if stage == 'upgrade':
        fault = patch('workout_tracker.icon_size_schema.upgrade_icon_size', side_effect=RuntimeError('Synthetic failure'))
    elif stage == 'preservation':
        real = icon_size_schema.upgrade_icon_size
        def changed(db):
            """Corrupt only the disposable candidate to test exact-value preservation."""
            real(db)
            db.execute("UPDATE exercise_icons SET svg='<svg/>'")
        fault = patch('workout_tracker.icon_size_schema.upgrade_icon_size', side_effect=changed)
    elif stage == 'validation':
        fault = patch('workout_tracker.interface_schema.validate_interface', side_effect=StorageError('Synthetic failure'))
    elif stage == 'activation':
        fault = patch('workout_tracker.migrations._write_manifest', side_effect=OSError('Synthetic failure'))
    else:
        real = m._sync_directory
        def fail_after_switch(path):
            """Fail candidate publication durability, allowing original-pointer rollback."""
            if path.name == 'config' and b'schema-12-' in active.read_bytes():
                raise OSError('Synthetic activation durability failure')
            return real(path)
        fault = patch('workout_tracker.migrations._sync_directory', side_effect=fail_after_switch)
    with fault, pytest.raises(StorageError):
        migrate_storage(x['root'], 12)
    assert original.read_bytes() == content and active.read_bytes() == selection
    assert inspect_storage(x['root'])['schema_version'] == 11


def test_large_icons_backup_restore_and_byte_constraint(icon_data):
    """Both exact-limit vectors survive verified restore; SQL enforces bytes too."""
    x = icon_data
    with database_session(x['root'], write=True) as db:
        for slot in ('start', 'end'):
            icons.update(db, x['e'], slot, sized_svg(307200))
    record = backup(x['root'], uuid4().hex)
    assert record['status'] == 'verified' and record['schema_version'] == 12
    with database_session(x['root'], write=True) as db:
        icons.update(db, x['e'], 'start', SVG)
        icons.update(db, x['e'], 'end')
    assert restore(x['root'], record['id'], uuid4().hex, confirm=True)['status'] == 'succeeded'
    with database_session(x['root'], write=True) as db:
        assert [len(r[0].encode()) for r in db.execute('SELECT svg FROM exercise_icons')] == [307200, 307200]
        for source in (sized_svg(307201).decode(), '<svg><desc>' + 'é' * 154000 + '</desc></svg>'):
            with pytest.raises(sqlite3.IntegrityError):
                db.execute('UPDATE exercise_icons SET svg=? WHERE position=?', (source, 'start'))
