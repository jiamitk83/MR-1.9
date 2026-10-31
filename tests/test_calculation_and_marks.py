import pytest
from decimal import Decimal
from services.calculation import CalculationService
from repositories.mark import MarkRepository
from models.database import (
    create_engine, Base, sessionmaker, AcademicSession, Class, Student, Subject,
)
from models.marks import Mark
from models.examination import Examination, ExamComponent
from models.audit import AuditLog

def test_calculation_formatting():
    assert CalculationService.format_marks(15) == "15.00"
    assert CalculationService.format_marks(12.5) == "12.50"
    assert CalculationService.format_marks(4.789) == "4.79" # rounding check

def test_calculation_percentage():
    pct = CalculationService.calculate_percentage(45, 50)
    assert pct == 90.00

def test_calculation_grades():
    assert CalculationService.get_grade(95) == "A1"
    assert CalculationService.get_grade(85) == "A2"
    assert CalculationService.get_grade(32) == "E"

def test_grade_uses_unrounded_decimal_percentage():
    assert CalculationService.get_grade(Decimal("90.999")) == "A2"
    assert CalculationService.get_grade(Decimal("91.000")) == "A1"
    assert CalculationService.get_grade(Decimal("32.999")) == "E"
    assert CalculationService.get_grade(Decimal("33.000")) == "D"

def test_derived_pt_marks():
    derived = CalculationService.derive_pt_marks(15, 25) # 15/25 -> 3.00/5
    assert derived == 3.00

@pytest.fixture
def repo():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as session:
        session.add_all([
            AcademicSession(id=1, name="2026-2027"),
            Class(id=1, name="Grade 10"),
            Subject(id=1, name="Mathematics", code="MATH"),
        ])
        session.flush()
        session.add(Student(
            id=1,
            admission_number="ADM0001",
            roll_number=1,
            name="Test Student",
            session_id=1,
            class_id=1,
        ))
        session.add(Student(
            id=2,
            admission_number="ADM0002",
            roll_number=2,
            name="Second Test Student",
            session_id=1,
            class_id=1,
        ))
        session.add(Examination(id=1, name="PT1", session_id=1))
        session.flush()
        session.add(ExamComponent(id=1, exam_id=1, name="Written", max_marks=25))
        session.commit()

    repo = MarkRepository()
    repo.session_factory = Session
    repo.test_session_factory = Session
    return repo

def test_save_marks_batch(repo):
    success = repo.save_marks_batch([
        {
            'student_id': 1,
            'subject_id': 1,
            'component_id': 1,
            'marks_obtained': 15.5,
            'is_absent': False
        }
    ])
    assert success is True
    marks = repo.get_marks(subject_id=1, component_id=1)
    assert len(marks) == 1
    assert float(marks[0].marks_obtained) == 15.5

def test_save_marks_batch_rejects_marks_above_component_maximum(repo):
    with pytest.raises(ValueError, match="cannot exceed"):
        repo.save_marks_batch([{
            'student_id': 1,
            'subject_id': 1,
            'component_id': 1,
            'marks_obtained': 25.01,
            'is_absent': False,
        }])
    assert repo.get_marks(subject_id=1, component_id=1) == []

def test_save_marks_batch_rolls_back_the_whole_batch(repo):
    with pytest.raises(ValueError, match="cannot exceed"):
        repo.save_marks_batch([
            {
                'student_id': 2,
                'subject_id': 1,
                'component_id': 1,
                'marks_obtained': 12.5,
                'is_absent': False,
            },
            {
                'student_id': 1,
                'subject_id': 1,
                'component_id': 1,
                'marks_obtained': 26,
                'is_absent': False,
            },
        ])
    assert repo.get_marks(subject_id=1, component_id=1) == []

def test_save_absent_mark_and_audit_entry(repo):
    repo.save_marks_batch([{
        'student_id': 1,
        'subject_id': 1,
        'component_id': 1,
        'marks_obtained': None,
        'is_absent': True,
    }])
    mark = repo.get_marks(subject_id=1, component_id=1)[0]
    assert mark.is_absent is True
    assert mark.marks_obtained is None
    with repo.test_session_factory() as session:
        audit = session.query(AuditLog).filter_by(entity_type="MARK", entity_id=mark.id).one()
        assert audit.action == "CREATE"
