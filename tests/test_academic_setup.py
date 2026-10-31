import pytest
from models.database import create_engine, Base, sessionmaker, AcademicSession, Class, Section, Subject
from models.database import Student
from models.audit import SubjectAlias
from models.examination import ExamComponent, Examination
from models.marks import Mark
from repositories.academic_setup import AcademicSetupRepository
from datetime import date

@pytest.fixture
def repo():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    repo = AcademicSetupRepository()
    repo.session_factory = Session
    return repo

def test_add_session(repo):
    sessions_before = repo.get_all_sessions()
    repo.add_session(name="2026-2027", start_date=date(2026, 1, 1), end_date=date(2027, 6, 30), is_active=True)
    sessions = repo.get_all_sessions()
    assert len(sessions) == len(sessions_before) + 1
    assert sessions[-1].name == "2026-2027"
    assert sessions[-1].is_active == True

def test_add_session_duplicate(repo):
    repo.add_session(name="2026-2027")
    result = repo.add_session(name="2026-2027")
    assert result is None

def test_add_session_invalid_dates(repo):
    with pytest.raises(ValueError):
        repo.add_session(name="2026-2027", start_date=date(2027, 1, 1), end_date=date(2026, 1, 1))

def test_get_session_by_id(repo):
    repo.add_session(name="2026-2027")
    sessions = repo.get_all_sessions()
    session_id = sessions[0].id
    result = repo.get_session_by_id(session_id)
    assert result.name == "2026-2027"

def test_update_session(repo):
    repo.add_session(name="2026-2027")
    sessions = repo.get_all_sessions()
    session_id = sessions[0].id
    repo.update_session(session_id=session_id, name="2026-2028", is_active=True)
    updated = repo.get_session_by_id(session_id)
    assert updated.name == "2026-2028"
    assert updated.is_active == True

def test_update_session_duplicate_name_rejected(repo):
    repo.add_session(name="2026-2027")
    second = repo.add_session(name="2027-2028")
    with pytest.raises(ValueError):
        repo.update_session(session_id=second.id, name=" 2026-2027 ")
    assert repo.get_session_by_id(second.id).name == "2027-2028"

def test_update_session_invalid_dates_rejected(repo):
    created = repo.add_session(name="2026-2027", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))
    with pytest.raises(ValueError):
        repo.update_session(session_id=created.id, start_date=date(2027, 1, 1))
    assert repo.get_session_by_id(created.id).start_date == date(2026, 1, 1)

def test_add_session_strips_name(repo):
    repo.add_session(name="  2026-2027  ")
    assert repo.add_session(name="2026-2027") is None

def test_delete_session(repo):
    repo.add_session(name="2026-2027")
    sessions = repo.get_all_sessions()
    session_id = sessions[0].id
    result = repo.delete_session(session_id)
    assert result == True
    assert repo.get_session_by_id(session_id) is None

def test_search_sessions(repo):
    repo.add_session(name="2025-2026", is_active=True)
    repo.add_session(name="2026-2027", is_active=True)
    repo.add_session(name="2027-2028", is_active=False)
    results = repo.search_sessions(keyword="2026")
    assert len(results) == 2

def test_add_class(repo):
    classes_before = repo.get_all_classes()
    repo.add_class(name="Grade 10")
    classes = repo.get_all_classes()
    assert len(classes) == len(classes_before) + 1
    assert classes[-1].name == "Grade 10"

def test_add_class_duplicate(repo):
    repo.add_class(name="Grade 10")
    with pytest.raises(ValueError):
        repo.add_class(name="Grade 10")

def test_update_class(repo):
    repo.add_class(name="Grade 10")
    classes = repo.get_all_classes()
    class_id = classes[0].id
    repo.update_class(class_id=class_id, name="Grade 11")
    updated = repo.get_class_by_id(class_id)
    assert updated is not None
    assert updated.name == "Grade 11"

def test_delete_class(repo):
    repo.add_class(name="Grade 10")
    classes = repo.get_all_classes()
    class_id = classes[0].id
    result = repo.delete_class(class_id)
    assert result == True
    assert repo.get_class_by_id(class_id) is None

def test_add_subject(repo):
    subjects_before = repo.get_all_subjects()
    result = repo.add_subject(name="Mathematics", code="MATH", is_active=True)
    subjects = repo.get_all_subjects()
    assert len(subjects) == len(subjects_before) + 1
    assert subjects[0].name == "Mathematics"

def test_add_subject_duplicate_name(repo):
    repo.add_subject(name="Mathematics")
    result = repo.add_subject(name="Mathematics")
    assert result is None

def test_add_subject_duplicate_code(repo):
    repo.add_subject(name="Mathematics", code="MATH101")
    result = repo.add_subject(name="Maths", code="MATH101")
    assert result is None

def test_update_subject(repo):
    repo.add_subject(name="Mathematics", code="MATH")
    subjects = repo.get_all_subjects()
    subject_id = subjects[0].id
    repo.update_subject(subject_id=subject_id, name="Maths", code="MATH101", is_active=False)
    updated = repo.get_subject_by_id(subject_id)
    assert updated is not None
    assert updated.name == "Maths"
    assert updated.code == "MATH101"
    assert updated.is_active == False

def test_delete_subject(repo):
    repo.add_subject(name="Mathematics", code="MATH")
    subjects = repo.get_all_subjects()
    subject_id = subjects[0].id
    result = repo.delete_subject(subject_id)
    assert result == True
    assert repo.get_subject_by_id(subject_id) is None

def test_search_subjects(repo):
    repo.add_subject(name="Mathematics", code="MATH")
    repo.add_subject(name="Physics", code="PHYS")
    results = repo.search_subjects(keyword="MATH")
    assert len(results) == 1
    assert results[0].name == "Mathematics"

def test_add_section(repo):
    repo.add_session(name="2026-2027")
    repo.add_class(name="Grade 10")
    sessions = repo.get_all_sessions()
    session_id = sessions[0].id
    classes = repo.get_all_classes()
    class_id = classes[0].id
    section = repo.add_section(name="A", class_id=class_id, session_id=session_id)
    assert section is not None
    sections = repo.get_sections_by_class_and_session(class_id, session_id)
    assert len(sections) == 1
    assert sections[0].name == "A"

def test_add_section_duplicate(repo):
    repo.add_session(name="2026-2027")
    repo.add_class(name="Grade 10")
    sessions = repo.get_all_sessions()
    session_id = sessions[0].id
    classes = repo.get_all_classes()
    class_id = classes[0].id
    repo.add_section(name="A", class_id=class_id, session_id=session_id)
    result = repo.add_section(name="A", class_id=class_id, session_id=session_id)
    assert result is None

def test_get_sections_by_class_and_session(repo):
    repo.add_session(name="2025-2026")
    repo.add_session(name="2026-2027")
    repo.add_class(name="Grade 10")
    sessions = repo.get_all_sessions()
    session1_id = sessions[0].id
    session2_id = sessions[1].id
    classes = repo.get_all_classes()
    class_id = classes[0].id
    repo.add_section(name="A", class_id=class_id, session_id=session1_id)
    repo.add_section(name="B", class_id=class_id, session_id=session1_id)
    repo.add_section(name="A", class_id=class_id, session_id=session2_id)
    
    sections = repo.get_sections_by_class_and_session(class_id, session1_id)
    assert len(sections) == 2

def test_update_section(repo):
    repo.add_session(name="2026-2027")
    repo.add_class(name="Grade 10")
    sessions = repo.get_all_sessions()
    session_id = sessions[0].id
    classes = repo.get_all_classes()
    class_id = classes[0].id
    repo.add_section(name="A", class_id=class_id, session_id=session_id)
    sections = repo.get_sections_by_class_and_session(class_id, session_id)
    section_id = sections[0].id
    repo.add_class(name="Grade 11")
    repo.add_session(name="2027-2028")
    classes2 = repo.get_all_classes()
    class2_id = classes2[1].id
    sessions2 = repo.get_all_sessions()
    session2_id = sessions2[1].id
    
    repo.update_section(section_id=section_id, name="B", class_id=class2_id, session_id=session2_id)
    updated = repo.get_section_by_id(section_id)
    assert updated is not None
    assert updated.name == "B"
    assert updated.class_id == class2_id
    assert updated.session_id == session2_id

def test_delete_section(repo):
    repo.add_session(name="2026-2027")
    repo.add_class(name="Grade 10")
    sessions = repo.get_all_sessions()
    session_id = sessions[0].id
    classes = repo.get_all_classes()
    class_id = classes[0].id
    repo.add_section(name="A", class_id=class_id, session_id=session_id)
    sections = repo.get_sections_by_class_and_session(class_id, session_id)
    section_id = sections[0].id
    
    result = repo.delete_section(section_id)
    assert result == True
    # Verify section is deleted by checking it's not in results
    all_sections = repo.get_sections_by_class_and_session(class_id, session_id)
    assert len(all_sections) == 0


def test_delete_referenced_academic_records_is_blocked(repo):
    with repo.session_factory() as session:
        session.add_all([
            AcademicSession(id=10, name="2027-2028"),
            Class(id=10, name="Grade 8"),
            Subject(id=10, name="Science", code="SCI"),
        ])
        session.flush()
        session.add(Section(id=10, name="A", class_id=10, session_id=10))
        session.add(Student(
            id=10, admission_number="ADM0010", roll_number=10, name="Student",
            session_id=10, class_id=10, section_id=10,
        ))
        session.add(Examination(id=10, name="Final", session_id=10))
        session.flush()
        session.add(ExamComponent(id=10, exam_id=10, name="Written", max_marks=100))
        session.add(Mark(
            student_id=10, subject_id=10, component_id=10,
            marks_obtained=80, is_absent=False,
        ))
        session.add(SubjectAlias(
            id=10, subject_id=10, alias_name="Natural Science", is_primary=False,
        ))
        session.commit()

    assert repo.delete_session(10) is False
    assert repo.delete_class(10) is False
    assert repo.delete_section(10) is False
    assert repo.delete_subject(10) is False