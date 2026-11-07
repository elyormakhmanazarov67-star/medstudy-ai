"""User-provided lesson calendar and strictly separated content sources."""
from app.core import load_catalog


def test_all_subjects_and_teacher_source_separation():
    data=load_catalog()
    assert len(data['subjects'])==6
    expected={'stom_prerest':31,'stom_kirish':12,'odam_anatomiyasi_1':14,'medical_english':5,'biofizika':4,'lotin_tili_tibbiy_terminologiya':15}
    for subject in data['subjects']:
        assert len(subject['lessons'])==expected[subject['id']]
        assert all(isinstance(l.get('teacher_materials'),list) for l in subject['lessons'])
        for lesson in subject['lessons']:
            assert not any(key in lesson for key in ('supplementary','supplement_sections','supplement_questions','sammu_books'))
            assert all(not item.get('url') for item in lesson['teacher_materials'])
            for question in lesson['questions']:
                assert len(question['options'])==4
    assert sum(len(s['lessons']) for s in data['subjects'])==81


def test_preclinical_calendar_and_no_invented_content():
    data=load_catalog()
    course=data['subjects'][0]
    assert course['id']=='stom_prerest'
    assert [l['session_number'] for l in course['lessons']]==list(range(1,32))
    assert course['lessons'][0]['id']=='ergonomika'
    assert sum(bool(l['sections']) for l in course['lessons']) == 28
    assert sum(not l['sections'] for l in course['lessons']) == 3
    assert len(set(sec['body'] for l in course['lessons'] for sec in l['sections'])) == sum(len(l['sections']) for l in course['lessons'])
    assert not any(sec['heading'] == 'Manba va chegaralar' for l in course['lessons'] for sec in l['sections'])
    assert all(not l['questions'] for l in course['lessons'] if not l['sections'])
    assert course['total_sessions'] == 31
    assert course['lessons'][0]['teacher_materials'][0]['filename'].startswith('Calendar_plan-')


def test_user_source_teaching_material_counts():
    data=load_catalog()
    e=next(s for s in data['subjects'] if s['id']=='medical_english')
    b=next(s for s in data['subjects'] if s['id']=='biofizika')
    assert len(e['lessons'])==5
    assert len(b['lessons'])==4
    assert all(len(l['teacher_materials'])>0 for l in e['lessons']+b['lessons'])
    assert all(len(l['sections']) >= 7 for l in e['lessons'])
    assert all(len(l['questions']) == 10 for l in e['lessons'])
    assert sum(len(l['questions']) for l in e['lessons']+b['lessons'])==110
    assert all(len(l['questions'])==15 for l in b['lessons'])
    assert all(len(l['sections'])>=12 for l in b['lessons'])
    assert len(set(sec['body'] for l in b['lessons'] for sec in l['sections'])) == sum(len(l['sections']) for l in b['lessons'])
    assert [l['id'] for l in b['lessons']] == ['bio_l1','bio_l2','bio_l3','bio_l4']

def test_only_required_information_is_present():
    data=load_catalog()
    assert all('supplementary' not in l and 'sammu_books' not in l
               for s in data['subjects'] for l in s['lessons'])


def test_latin_lessons_follow_uploaded_curriculum_and_alphabet():
    data=load_catalog()
    s=next(x for x in data['subjects'] if x['id']=='lotin_tili_tibbiy_terminologiya')
    assert s['title']=='Lotin tili va tibbiy terminologiya'
    assert s['total_sessions']==15
    assert [l['session_number'] for l in s['lessons']]==list(range(1,16))
    assert len(s['lessons'][0]['alphabet'])==25
    assert {x['letter'] for x in s['lessons'][0]['alphabet']}==set('ABCDEFGHIJKLMNOPQRSTUVXYZ')
    assert sum(bool(l['sections']) for l in s['lessons'])==6
    assert all(not l['questions'] for l in s['lessons'] if not l['sections'])
    assert all(not l['teacher_materials'] for l in s['lessons'])
    assert all(not any(x['filename'].lower().endswith(ext) for x in l['teacher_materials'] for ext in ('.jpg', '.doc', '.docx', '.ppt', '.pptx')) for l in s['lessons'])
    assert all(q['id'].startswith('latin_') for l in s['lessons'] for q in l['questions'])


def test_preclinical_uploaded_sources_topic_coverage():
    data=load_catalog()
    course=next(s for s in data['subjects'] if s['id']=='stom_prerest')
    lessons=course['lessons']
    assert len(lessons)==31
    assert [l['session_number'] for l in lessons if not l['sections']]==[23,24,25]
    assert all(len(l['sections'])>=3 for l in lessons if l['sections'])
    assert all(l.get('source_pages') for l in lessons if l['sections'])
    assert any(any(ref['book']=='Trezubov' for ref in l['source_pages']) for l in lessons)
    assert any(any(ref['book']=='Bazikyan' for ref in l['source_pages']) for l in lessons)
    assert any(any(ref['book']=='Kornilov' for ref in l['source_pages']) for l in lessons)
    assert all('Manba va chegaralar' not in [sec['heading'] for sec in l['sections']] for l in lessons)
    assert all(not l['questions'] for l in lessons if not l['sections'])
    assert all('teacher_materials' in l for l in lessons)
