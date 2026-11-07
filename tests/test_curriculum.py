"""User-provided lesson calendar and strictly separated content sources."""
from app.core import load_catalog


def test_all_subjects_and_teacher_source_separation():
    data=load_catalog()
    assert len(data['subjects'])==5
    expected={'stom_prerest':31,'stom_kirish':12,'odam_anatomiyasi_1':14,'medical_english':5,'biofizika':4}
    for subject in data['subjects']:
        assert len(subject['lessons'])==expected[subject['id']]
        assert all(isinstance(l.get('teacher_materials'),list) for l in subject['lessons'])
        for lesson in subject['lessons']:
            assert not any(key in lesson for key in ('supplementary','supplement_sections','supplement_questions','sammu_books'))
            assert all(not item.get('url') for item in lesson['teacher_materials'])
            for question in lesson['questions']:
                assert len(question['options'])==4
    assert sum(len(s['lessons']) for s in data['subjects'])==66


def test_preclinical_calendar_and_no_invented_content():
    data=load_catalog()
    course=data['subjects'][0]
    assert course['id']=='stom_prerest'
    assert [l['session_number'] for l in course['lessons']]==list(range(1,32))
    assert course['lessons'][0]['id']=='ergonomika'
    assert sum(bool(l['sections']) for l in course['lessons']) == 24
    assert sum(not l['sections'] for l in course['lessons']) == 7
    assert len(set(sec['body'] for l in course['lessons'] for sec in l['sections'])) == 24
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
    assert sum(len(l['questions']) for l in e['lessons']+b['lessons'])==58

def test_only_required_information_is_present():
    data=load_catalog()
    assert all('supplementary' not in l and 'sammu_books' not in l
               for s in data['subjects'] for l in s['lessons'])
