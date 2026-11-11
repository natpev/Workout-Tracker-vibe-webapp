# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Synthetic Phase 15 storage, SVG allowlist, sorting, drafts and mode corrections.

Only temporary databases/files are used. Archived conversion fixtures come from
Phase 14; every migration preserves originals and effective historical values.
"""
import io
import json
import sqlite3
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch
import pytest
from workout_tracker import create_app,catalog as c,workouts as w,history as h
from workout_tracker import exercise_icons as icons,measurement_rules as rules
from workout_tracker.storage import initialize_storage,database_session,inspect_storage,StorageError
from workout_tracker.migrations import migrate_storage
from workout_tracker.defaults_views import save
from workout_tracker.maintenance import backup,restore
from workout_tracker.weight_statistics import summary,workout_total
from test_basis import basis_data
from test_phase8_deletion import token,approval

SVG='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256"><title>Custom vector</title><rect x="20" y="20" width="120" height="100" fill="var(--accent)" stroke="currentColor" stroke-width="4"/></svg>'


@pytest.fixture
def ui_root(tmp_path):
    root=tmp_path/'ui';initialize_storage(root);migrate_storage(root,11);return root


@pytest.fixture
def ui_data(ui_root):
    with database_session(ui_root,write=True) as db:
        a=c.create_person(db,'Alice');b=c.create_person(db,'Bob')
        r=c.create_routine(db,a,'Session')
        ids={}
        for name in ('Plank','beta','Alpha','zebra'):
            ids[name]=c.create_definition(db,a,name,dict(measurement_type='weight',target_sets='3',target_reps='12',weight_basis='total'))
        ids['Duration']=c.create_definition(db,a,'Duration',dict(measurement_type='time',target_sets='2',seconds='45'))
        for name in ('Plank','beta'):c.add_entry(db,a,r,dict(exercise_id=ids[name],use_library_defaults='yes'))
        rb=c.copy_routine(db,a,r,b,'Other routine')
    return dict(root=ui_root,a=a,b=b,r=r,rb=rb,e=ids['Plank'],ids=ids)


def config(kind='weight',basis='total',**changes):
    values=dict(name='Plank',measurement_type=kind,target_sets='3',target_reps='12',seconds='45',unit='lb',weight_basis=basis)
    values.update(changes);return values


def draft(db,x,**changes):
    identity,_=w.start(db,x['a'],x['r'],'UTC');row=w.entries(db,x['a'],identity)[0]
    parent=w.session(db,x['a'],identity)
    values=dict(revision=str(parent['revision']),entry_id=row['id'],current_position='0',weight='40',reps_0='',reps_1='',reps_2='')
    values.update(changes);return identity,row,values


def record(db,x,day='2020-01-01',**values):
    form=h.prepare(db,x['a'],x['r'],dict(workout_date=day,workout_time=''),'UTC')
    raw=dict(weight_0='40',reps_0_0='12',reps_0_1='10',reps_0_2='0');raw.update(values)
    return h.complete_historical(db,x['a'],form,raw)


def test_baseline_upgrade_preserves_every_cell_audit_draft_and_total(basis_data):
    x=basis_data;root=x['root']
    with database_session(root) as db:
        before={name:[tuple(row) for row in db.execute(f'SELECT * FROM {name} ORDER BY 1')] for name, in db.execute("SELECT name FROM sqlite_schema WHERE type='table' AND substr(name,1,7)!='sqlite_'")}
        columns={name:','.join('"'+r[1]+'"' for r in db.execute(f'PRAGMA table_info({name})')) for name in before}
        totals={person:summary(h.all_completed(db,person)) for person in (x['a'],x['other'])}
    original=root/'data'/json.loads((root/'config/active.json').read_text())['database'];data=original.read_bytes()
    migrate_storage(root,11)
    assert original.read_bytes()==data
    with database_session(root) as db:
        for name,old in before.items():
            current=[tuple(row) for row in db.execute(f'SELECT {columns[name]} FROM {name} ORDER BY 1')]
            if name=='schema_migrations':current=[row for row in current if row[0]<=10]
            assert current==old,name
        assert {person:summary(h.all_completed(db,person)) for person in totals}==totals
        active=w.active(db,x['a']);assert active
        assert w.entries(db,x['a'],active['id'])[0]['actual_weight_tenths_lb']==410
        assert h.effective(db,x['a'],x['first'])[1][0]['actual_weight_tenths_lb']==250


@pytest.mark.parametrize('stage',['upgrade','preservation','logical','activation','post_activation'])
def test_failed_schema11_candidate_keeps_source(basis_data,stage):
    from workout_tracker import migrations as m,interface_schema
    root=basis_data['root'];active=root/'config/active.json';manifest=active.read_bytes()
    source=root/'data'/json.loads(manifest)['database'];data=source.read_bytes()
    if stage=='upgrade':fault=patch('workout_tracker.interface_schema.upgrade_interface',side_effect=RuntimeError('fault'))
    elif stage=='preservation':
        real=interface_schema.upgrade_interface
        def changed(db):real(db);db.execute("UPDATE exercise_defaults SET notes='bad'")
        fault=patch('workout_tracker.interface_schema.upgrade_interface',side_effect=changed)
    elif stage=='logical':fault=patch('workout_tracker.interface_schema.validate_interface',side_effect=StorageError('fault'))
    elif stage=='activation':fault=patch('workout_tracker.migrations._write_manifest',side_effect=OSError('fault'))
    else:
        real=m._sync_directory;raised=[]
        def once(path):
            if path.name=='config' and b'schema-11-' in active.read_bytes() and not raised:
                raised.append(True);raise OSError('fault')
            return real(path)
        fault=patch('workout_tracker.migrations._sync_directory',side_effect=once)
    with fault,pytest.raises(StorageError):migrate_storage(root,11)
    assert source.read_bytes()==data and active.read_bytes()==manifest
    assert inspect_storage(root)['schema_version']==10


@pytest.mark.parametrize('start,end',[('weight','time'),('time','weight'),('weight','weight_duration'),('weight_duration','weight'),('time','weight_duration'),('weight_duration','time')])
@pytest.mark.parametrize('update_routines',[False,True])
def test_confirmed_measurement_type_changes_preserve_history_and_person_scopes(ui_data,start,end,update_routines):
    x=ui_data
    with database_session(x['root'],write=True) as db:
        if start!='weight':save(db,x['a'],x['e'],config(start),True,confirmed_type_change=True)
        historical=record(db,x,**({'seconds_0':'45','weight_0':''} if start=='time' else {'seconds_0':'45'} if start=='weight_duration' else {}))
        identity,_,_=draft(db,x)
        snapshot=[dict(row) for row in w.entries(db,x['a'],identity)]
        old=h.original(db,x['a'],historical);old_total=workout_total(h.effective(db,x['a'],historical)[1])
        foreign=[tuple(row) for row in db.execute('SELECT * FROM routine_exercises WHERE person_id=?',(x['b'],))]
        values=config(end)
        with pytest.raises(c.ValidationError,match='Confirm'):save(db,x['a'],x['e'],values,update_routines)
        save(db,x['a'],x['e'],values,update_routines,confirmed_type_change=True)
        assert c.exercise_defaults(db,x['a'],x['e'])['measurement_type']==end
        assert rules.assigned(db,x['e'])=='total'
        assert [dict(row) for row in w.entries(db,x['a'],identity)]==snapshot
        assert h.original(db,x['a'],historical)==old
        assert workout_total(h.effective(db,x['a'],historical)[1])==old_total
        assert [tuple(row) for row in db.execute('SELECT * FROM routine_exercises WHERE person_id=?',(x['b'],))]==foreign
        current=db.execute('SELECT measurement_type FROM routine_exercises WHERE routine_id=? AND exercise_id=?',(x['r'],x['e'])).fetchone()[0]
        assert current==(end if update_routines else start)


def test_plank_weight_duration_weight_cannot_change_permanent_basis(ui_data):
    x=ui_data
    with database_session(x['root'],write=True) as db:
        save(db,x['a'],x['e'],config('time'),True,confirmed_type_change=True)
        with pytest.raises(c.ValidationError,match='permanent'):save(db,x['a'],x['e'],config('weight','per_side'),True,confirmed_type_change=True)
        save(db,x['a'],x['e'],config('weight'),True,confirmed_type_change=True)
        assert rules.assigned(db,x['e'])=='total'
        for sql in ("UPDATE exercise_weight_basis SET basis='per_side'",'DELETE FROM exercise_weight_basis'):
            with pytest.raises(sqlite3.IntegrityError):db.execute(sql)


def test_duration_first_basis_assignment_required_once(ui_data):
    x=ui_data;e=x['ids']['Duration']
    with database_session(x['root'],write=True) as db:
        values=config('weight',name='Duration');values.pop('weight_basis')
        with pytest.raises(c.ValidationError,match='initial permanent'):save(db,x['a'],e,values,confirmed_type_change=True)
        save(db,x['a'],e,dict(values,weight_basis='per_side'),confirmed_type_change=True)
        assert rules.assigned(db,e)=='per_side'
        save(db,x['a'],e,config('time','per_side',name='Duration'),confirmed_type_change=True)
        assert c.exercise_defaults(db,x['a'],e)['weight_basis']=='per_side'


@pytest.mark.parametrize('values',[[None,None,None],[12,None,None],[12,0,None],[12,10,0]])
def test_blank_partial_drafts_persist_and_navigation_requires_complete(ui_data,values):
    x=ui_data
    with database_session(x['root'],write=True) as db:
        identity,row,raw=draft(db,x)
        assert row['actual_reps']==[None,None,None]
        raw.update({f'reps_{i}':'' if value is None else str(value) for i,value in enumerate(values)})
        w.update(db,x['a'],identity,raw)
        assert w.entries(db,x['a'],identity)[0]['actual_reps']==values
    with database_session(x['root'],write=True) as db:
        parent=w.session(db,x['a'],identity);raw.update(revision=str(parent['revision']),navigation_action='next',current_position='1')
        if None in values:
            with pytest.raises(w.MeasurementError,match='Set'):w.update(db,x['a'],identity,raw)
        else:w.update(db,x['a'],identity,raw)
    with database_session(x['root']) as db:assert w.entries(db,x['a'],identity)[0]['actual_reps']==values


def test_skipping_requires_no_reps_and_new_totals_never_use_targets(ui_data):
    x=ui_data
    with database_session(x['root'],write=True) as db:
        identity,row,raw=draft(db,x,weight='',confirm_all_skipped='yes')
        w.finish(db,x['a'],identity,raw)
        effective=h.effective(db,x['a'],identity)[1][0]
        assert effective['actual_reps'] is None and effective['actual_weight_tenths_lb'] is None
        raw=dict(workout_date=w.session(db,x['a'],identity)['workout_date'],workout_time='',correction_revision='0',confirm='yes',weight_0='40')
        with pytest.raises(c.ValidationError,match='incomplete'):h.correct(db,x['a'],identity,raw)


@pytest.mark.parametrize('bad',['-1','1.5','x','10001'])
def test_bad_reps_do_not_overwrite_partial_draft(ui_data,bad):
    x=ui_data
    with database_session(x['root'],write=True) as db:
        identity,row,raw=draft(db,x,reps_0='12');w.update(db,x['a'],identity,raw)
    with pytest.raises(c.ValidationError):
        with database_session(x['root'],write=True) as db:
            raw.update(revision='1',reps_1=bad);w.update(db,x['a'],identity,raw)
    with database_session(x['root']) as db:assert w.entries(db,x['a'],identity)[0]['actual_reps']==[12,None,None]


@pytest.mark.parametrize('fragment',[
 '<script>alert(1)</script>','<foreignObject><div>bad</div></foreignObject>',
 '<a href="javascript:alert(1)"><rect/></a>','<image href="https://example.com/a.svg"/>',
 '<rect onload="alert(1)"/>','<rect onclick="alert(1)"/>','<style>rect{fill:red}</style>',
 '<rect style="fill:red"/>','<rect fill="url(https://example.com/a)"/>',
 '<use href="#x"/>','<animate attributeName="x"/>','<set attributeName="x"/>',
 '<rect xmlns="http://www.w3.org/1999/xhtml"/>','<iframe/>','<svg/>',
 '<rect id="x"/>','<rect fill="var(--other)"/>','<rect width="1e999"/>',
 '<rect transform="url(https://example.com)"/>','<filter/>','<text>unsupported</text>',
 '<title><script/></title>',
])
def test_malicious_or_unsupported_svg_rejected(fragment):
    with pytest.raises(c.ValidationError):icons.sanitize('<svg xmlns="http://www.w3.org/2000/svg">'+fragment+'</svg>')


@pytest.mark.parametrize('value',['<!DOCTYPE svg [<!ENTITY x "bad">]><svg/>','<?xml-stylesheet href="https://example.com"?><svg/>','<svg/> trailing','not XML',b'\xff','<svg>'+(' '*(icons.MAX_BYTES+1))+'</svg>'])
def test_svg_parser_and_size_guards(value):
    with pytest.raises(c.ValidationError):icons.sanitize(value)


def test_exactly_two_vector_defaults_and_canonical_accent():
    files=list((Path(__file__).parents[1]/'workout_tracker/static/exercise-icons').glob('*.svg'))
    assert {p.name for p in files}=={'start.svg','end.svg'}
    assert 'Pair of dumbbells' in icons.default('start') and 'Barbell with weight plates' in icons.default('end')
    for p in files:
        value=icons.sanitize(p.read_bytes());assert 'var(--accent)' in value and 'viewBox="0 0 256 256"' in value
    value=icons.sanitize(SVG);assert icons.sanitize(value)==value
    assert 'var(--accent)' in str(icons.artwork(value)['svg'])


def test_icon_independent_slots_backup_restore_and_deletion(ui_data):
    x=ui_data
    with database_session(x['root'],write=True) as db:
        icons.update(db,x['e'],'start',SVG);icons.update(db,x['e'],'end',SVG)
        icons.update(db,x['ids']['Alpha'],'start',SVG)
        before=icons.pairs(db,[x['e']])[x['e']]
        assert before['start']['custom'] and before['end']['custom']
    saved=backup(x['root'],uuid4().hex);assert saved['status']=='verified'
    with database_session(x['root'],write=True) as db:
        icons.update(db,x['e'],'start')
        pair=icons.pairs(db,[x['e']])[x['e']];assert not pair['start']['custom'] and pair['end']['custom']
    assert restore(x['root'],saved['id'],uuid4().hex,confirm=True)['status']=='succeeded'
    with database_session(x['root'],write=True) as db:
        assert icons.pairs(db,[x['e']])[x['e']]['start']['custom']
        from workout_tracker.deletions import delete_exercise
        delete_exercise(db,x['a'],x['e'],approval(db,'exercise',x['e'],x['a']))
        assert not db.execute('SELECT 1 FROM exercise_icons WHERE exercise_id=?',(x['e'],)).fetchone()
        assert db.execute('SELECT 1 FROM exercise_icons WHERE exercise_id=?',(x['ids']['Alpha'],)).fetchone()


def test_icon_upload_csrf_malicious_rollback_and_shared_preview(ui_data):
    x=ui_data;client=create_app({'TESTING':True,'WORKOUT_DATA_ROOT':x['root']}).test_client()
    editor=f"/people/{x['a']}/exercises/{x['e']}/defaults";page=client.get(editor)
    endpoint=f"/people/{x['a']}/exercises/{x['e']}/icons/start"
    assert client.post(endpoint,data={'action':'remove'}).status_code==400
    assert client.post(endpoint,data=dict(csrf_token=token(page),action='upload',svg=(io.BytesIO(SVG.encode()),'../../icon.svg'))).status_code==303
    with database_session(x['root']) as db:before=db.execute('SELECT svg FROM exercise_icons').fetchone()[0]
    assert client.post(endpoint,data=dict(csrf_token=token(client.get(editor)),action='upload',svg=(io.BytesIO(b'<svg><script/></svg>'),'evil.svg'))).status_code==303
    with database_session(x['root']) as db:assert db.execute('SELECT svg FROM exercise_icons').fetchone()[0]==before
    shared=client.get(f"/people/{x['b']}/exercises/{x['e']}/defaults")
    assert b'Custom vector' in shared.data


def test_creation_error_reopens_and_preserves_raw_fields(ui_data):
    x=ui_data;client=create_app({'TESTING':True,'WORKOUT_DATA_ROOT':x['root']}).test_client()
    path=f"/people/{x['a']}/exercises";page=client.get(path)
    assert b'add-exercise" open' not in page.data
    response=client.post(path,data=dict(csrf_token=token(page),action='create',name='Unsaved name',measurement_type='weight',target_sets='4',target_reps='9'))
    assert response.status_code==400 and b'add-exercise" open' in response.data and b'value="Unsaved name"' in response.data
    assert b'value="4"' in response.data and b'value="9"' in response.data


def test_progress_sorting_all_time_zero_skips_and_people(ui_data):
    from workout_tracker.exercise_listing import ordering,chart_order
    x=ui_data
    with database_session(x['root'],write=True) as db:
        record(db,x,weight_0='0')
        completed=h.all_completed(db,x['a']);rows,names,recorded=ordering(db,x['a'],completed)
        assert list(names)[0]==x['e'] and x['e'] in recorded and x['ids']['beta'] not in recorded
        assert [row['name'] for row in rows][1:]==['Alpha','beta','Duration','zebra']
        _,other,_=ordering(db,x['b']);assert list(other.values())==['Alpha','beta','Duration','Plank','zebra']
        charts=chart_order(db,x['a'],dict(**{'from':'2025-01-01'}),completed,names)
        assert charts[0]['exercise_id']==x['e'] and all(not chart['points'] for chart in charts)
        assert {chart['exercise_id'] for chart in charts}==set(names)

@pytest.mark.parametrize('scope',['defaults','apply'])
def test_signed_type_confirmation_http_and_scope(ui_data,scope):
    import re
    x=ui_data;client=create_app({'TESTING':True,'WORKOUT_DATA_ROOT':x['root']}).test_client()
    url=f"/people/{x['a']}/exercises/{x['e']}/defaults";page=client.get(url)
    revision=re.search(r'name="revision" value="([^"]+)"',page.text).group(1)
    preview=client.post(url,data=dict(config('time'),csrf_token=token(page),revision=revision,action=scope))
    assert preview.status_code==200 and 'Change Plank from Weight to Duration?' in preview.text
    signed=re.search(r'name="preview" value="([^"]+)"',preview.text).group(1)
    with database_session(x['root']) as db:assert c.exercise_defaults(db,x['a'],x['e'])['measurement_type']=='weight'
    failed=client.post(url,data=dict(csrf_token=token(preview),action='confirm',preview=signed))
    assert failed.status_code==400
    result=client.post(url,data=dict(csrf_token=token(preview),action='confirm',preview=signed,confirm='yes'))
    assert result.status_code==303
    with database_session(x['root']) as db:
        assert c.exercise_defaults(db,x['a'],x['e'])['measurement_type']=='time'
        mine=db.execute('SELECT measurement_type FROM routine_exercises WHERE routine_id=? AND exercise_id=?',(x['r'],x['e'])).fetchone()[0]
        assert mine==('time' if scope=='apply' else 'weight')
        assert db.execute('SELECT measurement_type FROM routine_exercises WHERE routine_id=? AND exercise_id=?',(x['rb'],x['e'])).fetchone()[0]=='weight'
    assert client.post(url,data=dict(csrf_token=token(preview),action='confirm',preview=signed,confirm='yes')).status_code==409


def test_sql_partial_repetitions_cannot_complete(ui_data):
    x=ui_data
    with database_session(x['root'],write=True) as db:
        identity,row,values=draft(db,x,reps_0='0');w.update(db,x['a'],identity,values)
        with pytest.raises(sqlite3.IntegrityError):db.execute("UPDATE workout_sessions SET status='completed' WHERE id=?",(identity,))
        assert w.session(db,x['a'],identity)['status']=='draft'


def test_svg_complexity_and_upload_limit_keep_prior(ui_data):
    with pytest.raises(c.ValidationError):icons.sanitize('<svg>'+'<g/>'*1024+'</svg>')
    x=ui_data;client=create_app({'TESTING':True,'WORKOUT_DATA_ROOT':x['root']}).test_client()
    page=client.get(f"/people/{x['a']}/exercises/{x['e']}/defaults")
    url=f"/people/{x['a']}/exercises/{x['e']}/icons/start"
    with database_session(x['root'],write=True) as db:icons.update(db,x['e'],'start',SVG)
    response=client.post(url,data=dict(csrf_token=token(page),action='upload',svg=(io.BytesIO(b'X'*(icons.MAX_BYTES+1)),'../unsafe.svg')),content_type='multipart/form-data')
    assert response.status_code==303
    with database_session(x['root']) as db:assert db.execute('SELECT svg FROM exercise_icons').fetchone()[0]==icons.sanitize(SVG)


def test_routine_only_type_correction_service_preserves_global_and_draft(ui_data):
    x=ui_data
    with database_session(x['root'],write=True) as db:
        identity,row,values=draft(db,x)
        entry=db.execute('SELECT id FROM routine_exercises WHERE routine_id=? AND exercise_id=?',(x['r'],x['e'])).fetchone()[0]
        with pytest.raises(c.ValidationError):c.update_entry(db,x['a'],x['r'],entry,config('time'))
        c.update_entry(db,x['a'],x['r'],entry,config('time'),confirmed_type_change=True)
        assert c.exercise_defaults(db,x['a'],x['e'])['measurement_type']=='weight'
        assert c.entry(db,x['a'],x['r'],entry)['measurement_type']=='time'
        assert w.entries(db,x['a'],identity)[0]['measurement_type']=='weight'
        c.update_entry(db,x['a'],x['r'],entry,config(),confirmed_type_change=True)
        with pytest.raises(c.ValidationError):c.update_entry(db,x['a'],x['r'],entry,config(basis='per_side'))


def test_routine_type_correction_signed_web_flow(ui_data):
    import re
    x=ui_data;client=create_app({'TESTING':True,'WORKOUT_DATA_ROOT':x['root']}).test_client()
    with database_session(x['root']) as db:entry=db.execute('SELECT id FROM routine_exercises WHERE routine_id=? AND exercise_id=?',(x['r'],x['e'])).fetchone()[0]
    url=f"/people/{x['a']}/routines/{x['r']}/items/{entry}";page=client.get(url)
    revision=re.search(r'name="revision" value="([^"]+)"',page.text).group(1)
    preview=client.post(url,data=dict(config('time'),csrf_token=token(page),revision=revision,action='save'))
    assert preview.status_code==200 and 'Change Plank from Weight to Duration?' in preview.text
    signed=re.search(r'name="preview" value="([^"]+)"',preview.text).group(1)
    response=client.post(url,data=dict(csrf_token=token(preview),revision=revision,action='confirm_type',preview=signed,confirm='yes'))
    assert response.status_code==303
    with database_session(x['root']) as db:
        assert c.entry(db,x['a'],x['r'],entry)['measurement_type']=='time'
        assert c.exercise_defaults(db,x['a'],x['e'])['measurement_type']=='weight'


def test_old_conversion_audit_then_schema11_repetition_correction(basis_data):
    from test_history import correction_payload
    x=basis_data;migrate_storage(x['root'],11)
    with database_session(x['root'],write=True) as db:
        parent,rows=h.effective(db,x['a'],x['first']);original=h.original(db,x['a'],x['first'])
        prior=[tuple(row) for row in db.execute('SELECT * FROM workout_corrections WHERE workout_id=? ORDER BY revision',(x['first'],))]
        values=correction_payload(db,x['a'],x['first'])
        actual=[max(0,12-index) for index in range(rows[0]['target_sets'])]
        values.update({f'reps_0_{i}':str(rep) for i,rep in enumerate(actual)})
        h.correct(db,x['a'],x['first'],values)
        effective=h.effective(db,x['a'],x['first'])[1]
        assert effective[0]['actual_weight_tenths_lb']==250 and effective[0]['actual_reps']==actual
        assert h.original(db,x['a'],x['first'])==original
        assert [tuple(row) for row in db.execute('SELECT * FROM workout_corrections WHERE workout_id=? ORDER BY revision',(x['first'],))][:-1]==prior
        assert workout_total(effective)==250*sum(actual)*2/10


def test_failed_personal_apply_rolls_back_global_type_and_all_settings(ui_data):
    x=ui_data
    with database_session(x['root']) as db:
        original={table:[tuple(row) for row in db.execute(f'SELECT * FROM {table} ORDER BY 1')] for table in ('exercise_defaults','routine_exercises','exercise_weight_basis')}
    with pytest.raises(StorageError):
        with database_session(x['root'],write=True) as db:
            db.execute("CREATE TEMP TRIGGER synthetic_failure BEFORE UPDATE ON routine_exercises BEGIN SELECT RAISE(ABORT,'Synthetic failure'); END")
            save(db,x['a'],x['e'],config('time'),True,confirmed_type_change=True)
    with database_session(x['root']) as db:
        assert {table:[tuple(row) for row in db.execute(f'SELECT * FROM {table} ORDER BY 1')] for table in original}==original
