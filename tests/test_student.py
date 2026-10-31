from datetime import date

import pytest
from models.database import create_engine, Base, sessionmaker, Student
from repositories.student import StudentRepository

@pytest.fixture
def repo():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    repo = StudentRepository()
    repo.session_factory = Session
    return repo

def test_add_student(repo):
    student = repo.add_student(name="John Doe", roll_number=1, father_name="Richard Doe")
    students = repo.get_students()
    assert len(students) == 1
    assert students[0].name == "John Doe"
    assert students[0].admission_number == "ADM0001"

def test_generate_admission_number(repo):
    repo.add_student(name="Student 1", roll_number=1)
    adm2 = repo.generate_admission_number()
    assert adm2 == "ADM0002"


def test_student_profile_date_of_birth_and_address_can_be_saved_and_cleared(repo):
    repo.add_student(
        name="Student",
        roll_number=1,
        date_of_birth=date(2015, 2, 9),
        address="24 Test Road",
    )

    repo.update_student(
        1,
        date_of_birth=None,
        address=None,
    )

    with repo.session_factory() as session:
        student = session.query(Student).filter_by(id=1).one()
        assert student.date_of_birth is None
        assert student.address is None


def test_generate_admission_number_ignores_malformed_latest_record(repo):
    repo.add_student(name="Student 1", roll_number=1)
    with repo.session_factory() as session:
        session.add(Student(
            admission_number="legacy-code", roll_number=2, name="Legacy",
        ))
        session.commit()

    assert repo.generate_admission_number() == "ADM0002"


def test_roll_numbers_are_unique_within_class_section_and_session(repo):
    repo.add_student(name="Grade 9 Student", roll_number=1, session_id=1, class_id=1, section_id=1)
    other_class = repo.add_student(
        name="Grade 10 Student", roll_number=1, session_id=1, class_id=2, section_id=2
    )

    assert other_class is not None
    assert repo.add_student(
        name="Duplicate", roll_number=1, session_id=1, class_id=1, section_id=1
    ) is None


def test_permanently_delete_requires_inactive_and_removes_marks(repo):
    from models.database import AcademicSession, Subject
    from models.examination import Examination, ExamComponent
    from models.marks import Mark

    repo.add_student(name="Gone", roll_number=1)
    with repo.session_factory() as session:
        session.add_all([AcademicSession(id=1, name="2026"), Subject(id=1, name="Maths")])
        session.flush()
        session.add(Examination(id=1, name="Final", session_id=1))
        session.flush()
        session.add(ExamComponent(id=1, exam_id=1, name="Written", max_marks=100))
        session.flush()
        session.add(Mark(student_id=1, subject_id=1, component_id=1, marks_obtained=50))
        session.commit()

    with pytest.raises(ValueError):
        repo.permanently_delete_student(1)

    repo.delete_student(1)
    assert repo.permanently_delete_student(1) is True
    assert repo.get_student_by_id(1) is None
    with repo.session_factory() as session:
        assert session.query(Mark).count() == 0
    assert repo.permanently_delete_student(1) is False
