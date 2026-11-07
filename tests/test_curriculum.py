"""User-provided lesson calendar and strictly separated content sources."""
from app.core import load_catalog


def test_all_subjects_and_teacher_source_separation():
    data=load_catalog()
    assert len(data['subjects'])==5
    expected={'stom_prerest':31,'stom_kirish':12,'odam_anatomiyasi_1':14,'medical_english':5,'biofizika':4}
    for subject in data['subjects']:
        assert len(subject['lessons'])==expected[subject['id']]
        assert all(isinstance(l.get('teacher_materials'),list) for l in subject['lessons'])
        assert all(isinstance(l.get('supplementary'),list) for l in subject['lessons'])
        for lesson in subject['lessons']:
            assert all(item.get('url','').startswith(('https://e-library.sammu.uz/', 'https://openstax.org/')) for item in lesson['supplementary'])
            assert all(not item.get('url') for item in lesson['teacher_materials'])
            assert lesson.get('sammu_books'), 'SamMU catalog books must remain on every topic'
            assert all(x['url'].startswith('https://e-library.sammu.uz/uz/book/') for x in lesson['sammu_books'])
            assert all(not x.get('url','').startswith('https://e-library.sammu.uz/') for x in lesson['supplementary'])
            assert all(x.get('access') for x in lesson['sammu_books'])

            for question in lesson['questions']:
                assert len(question['options'])==4
    assert sum(len(s['lessons']) for s in data['subjects'])==66


def test_preclinical_calendar_and_no_invented_content():
    data=load_catalog()
    course=data['subjects'][0]
    assert course['id']=='stom_prerest'
    assert [l['session_number'] for l in course['lessons']]==list(range(1,32))
    assert course['lessons'][0]['id']=='ergonomika'
    assert all(l['sections'] for l in course['lessons'])
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
    assert all(len(l.get('supplement_sections', [])) >= 1 for l in b['lessons'])
    assert all(len(l.get('supplement_questions', [])) >= 1 for l in b['lessons'])

def test_free_notes_and_sammu_books_are_separate_on_anatomy_and_preclinical_topics():
    data=load_catalog()
    a=data['subjects'][2]['lessons'][2]
    assert a['supplement_sections']
    assert a['supplement_questions']
    assert a['supplementary'][0]['url'].startswith('https://openstax.org/')
    assert a['sammu_books'][0]['url'].startswith('https://e-library.sammu.uz/')
    p=data['subjects'][0]['lessons'][0]
    assert p['questions']
    assert not p.get('supplement_questions')
    assert not p.get('supplement_sections')
    assert p['sammu_books']
    assert not p['supplementary']
