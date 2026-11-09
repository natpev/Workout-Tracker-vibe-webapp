# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""Synthetic effective-history CSV layout, ownership, quoting and no-write checks."""
import csv
from io import StringIO
from unittest.mock import patch
import pytest
from workout_tracker import create_app, catalog as c, history as h
from workout_tracker.storage import database_session
from workout_tracker.csv_export import wide_csv, spreadsheet_text
from test_phase9 import phase9_root
from test_history import seed, manual, correction_payload
from test_phase8_deletion import token


def rows(text):
    """Parse with the standard CSV reader, including a possible Excel UTF-8 BOM."""
    return list(csv.reader(StringIO(text.lstrip('\ufeff'))))


@pytest.fixture
def csv_data(phase9_root):
    """Mix zero, truncated decimals, skipped actuals and two same-date workouts."""
    root=phase9_root
    with database_session(root,write=True) as db:
        a,b,r,item=seed(db)
        weight=db.execute('SELECT exercise_id FROM routine_exercises WHERE id=?',(item,)).fetchone()[0]
        timed=db.execute("SELECT exercise_id FROM routine_exercises WHERE measurement_type='time'").fetchone()[0]
        one,_=manual(db,a,r,'2020-01-01',weight_0='0',seconds_1='45')
        two,_=manual(db,a,r,'2020-01-01',weight_0='40.99')
        c.update_entry(db,a,r,item,dict(measurement_type='weight',target_sets='4',target_reps='8',weight_meaning='per dumbbell'))
        three,_=manual(db,a,r,'2021-01-01',weight_0='42.56',seconds_1='60')
        h.correct(db,a,three,correction_payload(db,a,three,weight_0='45.99'))
    return root,a,b,r,weight,timed,one,two,three


def test_wide_columns_zero_skips_prescriptions_corrections_and_chronology(csv_data):
    """One workout per row; actual NULL stays blank and historical targets stay exact."""
    root,a,b,r,weight,timed,one,two,three=csv_data
    with database_session(root) as db:
        before='\n'.join(db.iterdump())
        data=rows(wide_csv(db,a,{},[weight,timed]))
        assert data[0][:4]==['Date','Time','Routine','Workout ID']
        assert data[0][4:]==['Bench (per dumbbell) — Weight (lb)','Bench (per dumbbell) — Sets × Reps','Plank — Duration','Plank — Sets × Target Duration']
        assert len(data)==4 and [row[0] for row in data[1:]]==['2020-01-01','2020-01-01','2021-01-01']
        assert data[1][4:]==['0','3 × 12','0:45','3 × 0:45']
        assert data[2][4:]==['40.9','3 × 12','','3 × 0:45']
        assert data[3][4:]==['45.9','4 × 8','1:00','3 × 0:45']
        assert len({row[3] for row in data[1:]})==3 and '\n'.join(db.iterdump())==before
        single=rows(wide_csv(db,a,{'from':'2021-01-01','to':'2021-01-01'},[weight]))
        assert len(single)==2 and len(single[0])==6 and single[1][4]=='45.9'
        with pytest.raises(c.ValidationError):wide_csv(db,b,{},[weight])
        with pytest.raises(c.ValidationError):wide_csv(db,a,{},[])
        with pytest.raises(c.ValidationError):wide_csv(db,a,{'from':'2022-01-01'},[weight])


def test_missing_exercise_blanks_and_duplicate_occurrences(csv_data):
    """An absent exercise has two blanks; repeated rows never overwrite one another."""
    root,a,b,r,weight,timed,one,two,three=csv_data
    with database_session(root,write=True) as db:
        c.add_entry(db,a,r,dict(exercise_id=weight,measurement_type='weight',target_sets='2',target_reps='15',weight_meaning='per dumbbell'))
        four,_=manual(db,a,r,'2022-01-01',weight_0='50',weight_2='20')
        data=rows(wide_csv(db,a,{},[weight]))
        assert 'occurrence 2' in data[0][6] and data[1][6:]==['','']
        assert data[-1][4:]==['50','4 × 8','20','2 × 15']


def test_distinct_same_names_mixed_types_and_csv_escaping(csv_data):
    """Synthetic legacy snapshots remain ID-distinct; no library reconciliation runs."""
    root,a,b,r,weight,timed,one,two,three=csv_data
    with database_session(root) as db:
        original=h.listing(db,a,{})
        # A read-layer fixture models historical matching names without changing
        # real definitions, investigating orphan data, or bypassing DB guards.
        for _,entries in original:
            for entry in entries:entry['name']='Bench, "quoted"'
        names={weight:'Bench, "quoted"',timed:'Bench, "quoted"'}
        with patch('workout_tracker.csv_export.h.choices',return_value=({},names)),patch('workout_tracker.csv_export.h.listing',return_value=original):
            text=wide_csv(db,a,{},[weight,timed]);data=rows(text)
            assert weight in data[0][4] and timed in data[0][6] and '""quoted""' in text
            assert 'Weight (lb)' in data[0][4] and 'Duration' in data[0][6]


@pytest.mark.parametrize('value',['=SUM(A1:A2)','+cmd','-formula','@SUM(1)','  =cmd','\ttext','\rtext','\ntext'])
def test_spreadsheet_formula_text_is_inert(value):
    """Potential spreadsheet commands are exported as explicit text, never formulas."""
    assert spreadsheet_text(value)=="'"+value
    assert spreadsheet_text('0')=='0' and spreadsheet_text('40.9')=='40.9'


def test_csv_http_errors_keep_filters_and_download_is_utf8(csv_data):
    """Invalid choices stay inline; successful GET downloads with proper headers/BOM."""
    root,a,b,r,weight,timed,one,two,three=csv_data
    client=create_app({'TESTING':True,'WORKOUT_DATA_ROOT':root,'WORKOUT_TIMEZONE':'UTC'}).test_client()
    path=f'/people/{a}/progress.csv'
    response=client.get(path,query_string={'range':'all'})
    assert response.status_code==400 and b'Select at least one exercise' in response.data
    response=client.get(path,query_string={'range':'custom','from':'2021-01-01','to':'2020-01-01','export_exercise':weight})
    assert response.status_code==400 and weight.encode() in response.data and b'2021-01-01' in response.data
    response=client.get(path,query_string={'range':'all','export_exercise':weight})
    assert response.status_code==200 and response.mimetype=='text/csv' and response.data.startswith(b'\xef\xbb\xbf')
    assert 'attachment; filename="workout-progress-' in response.headers['Content-Disposition']
    assert len(rows(response.data.decode('utf-8-sig')))==4


def test_type_changes_and_meanings_keep_incompatible_columns_separate(csv_data):
    """One permanent ID can have historical Weight and Time configurations safely."""
    root,a,b,r,weight,timed,one,two,three=csv_data
    with database_session(root,write=True) as db:
        item=db.execute('SELECT id FROM routine_exercises WHERE exercise_id=? AND routine_id=?',(weight,r)).fetchone()[0]
        c.update_entry(db,a,r,item,dict(measurement_type='time',target_sets='2',minutes='1',seconds='0'))
        manual(db,a,r,'2022-01-01',minutes_0='2')
        data=rows(wide_csv(db,a,{},[weight]))
        assert len(data[0])==8 and 'Duration' in data[0][4] and 'Weight (lb)' in data[0][6]
        assert data[1][4:]==['','','0','3 × 12']
        assert data[-1][4:]==['2:00','2 × 1:00','','']


def test_csv_formula_injection_in_headers_and_routine_fields(csv_data):
    """Real CSV construction protects both header and row text without losing numbers."""
    root,a,b,r,weight,timed,one,two,three=csv_data
    with database_session(root) as db:
        source=h.listing(db,a,{})
        for parent,_ in source:parent['routine_name']='\t=HYPERLINK("evil")'
        with patch('workout_tracker.csv_export.h.choices',return_value=({}, {weight:'=1+2'})),patch('workout_tracker.csv_export.h.listing',return_value=source):
            data=rows(wide_csv(db,a,{},[weight]))
            assert data[0][4].startswith("'=1+2") and data[1][2].startswith("'\t=")
            assert data[1][4]=='0'


def test_known_time_and_chart_filter_do_not_override_export_selection(csv_data):
    """Export selection is independent of a single chart filter; known clocks use HH:mm."""
    root,a,b,r,weight,timed,one,two,three=csv_data
    with database_session(root,write=True) as db:
        h.correct(db,a,one,correction_payload(db,a,one,workout_time='23:59'))
    client=create_app({'TESTING':True,'WORKOUT_DATA_ROOT':root}).test_client()
    response=client.get(f'/people/{a}/progress.csv',query_string={'range':'all','exercise':weight,'export_exercise':timed})
    assert response.status_code==200
    data=rows(response.data.decode('utf-8-sig'));by_id={row[3]:row for row in data[1:]}
    assert 'Duration' in data[0][4] and not any('Weight' in field for field in data[0])
    assert by_id[one][1]=='23:59' and by_id[two][1]==''
    assert data[1][3]==two and data[2][3]==one


def test_selected_exercise_without_range_records_keeps_blank_columns(csv_data):
    """Choosing two exercises never silently drops one that is absent in this range."""
    root,a,b,r,weight,timed,one,two,three=csv_data
    with database_session(root,write=True) as db:
        other=c.create_routine(db,a,'Other')
        item=c.add_entry(db,a,other,dict(name='Curl',measurement_type='weight',target_sets='2',target_reps='15'))
        curl=c.entry(db,a,other,item)['exercise_id']
        manual(db,a,other,'2023-01-01',weight_0='20')
        data=rows(wide_csv(db,a,{'from':'2020-01-01','to':'2020-12-31'},[weight,curl]))
        assert len(data)==3 and len(data[0])==8 and 'Curl — Weight (lb)' in data[0][6]
        assert all(row[6:]==['',''] for row in data[1:])
