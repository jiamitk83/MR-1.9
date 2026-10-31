from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import AcademicSession, Base, Class, Student, Subject
from models.examination import ExamComponent, Examination
from models.marks import Mark
from services.calculation import CalculationService
from services.derived_calculations import DerivedCalculationService


@pytest.fixture
def derived_service():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    test_session_factory = sessionmaker(bind=engine)
    with test_session_factory() as session:
        session.add_all([
            AcademicSession(id=1, name="2026-2027"),
            Class(id=1, name="Grade 10"),
            Subject(id=1, name="Mathematics", code="MATH"),
        ])
        session.flush()
        session.add_all([
            Student(id=1, admission_number="ADM0001", roll_number=1, name="Student One", session_id=1, class_id=1),
            Student(id=2, admission_number="ADM0002", roll_number=2, name="Student Two", session_id=1, class_id=1),
        ])
        session.add_all([
            Examination(id=1, name="PT1", session_id=1),
            Examination(id=2, name="PT2", session_id=1),
            Examination(id=3, name="Half Yearly", session_id=1),
            Examination(id=4, name="Annual", session_id=1),
        ])
        session.flush()
        session.add_all([
            ExamComponent(id=1, exam_id=1, name="PT1", max_marks=25),
            ExamComponent(id=2, exam_id=2, name="PT2", max_marks=25),
            ExamComponent(id=3, exam_id=3, name="PT1", max_marks=5, is_derived=True),
            ExamComponent(id=4, exam_id=4, name="PT2", max_marks=5, is_derived=True),
        ])
        session.add_all([
            Mark(student_id=1, subject_id=1, component_id=1, marks_obtained=15, is_absent=False),
            Mark(student_id=1, subject_id=1, component_id=2, marks_obtained=12.5, is_absent=False),
            Mark(student_id=2, subject_id=1, component_id=1, marks_obtained=None, is_absent=True),
        ])
        session.commit()

    yield DerivedCalculationService(test_session_factory)
    engine.dispose()


def test_derive_pt1_marks(derived_service):
    result = derived_service.calculate_pt1_derived(1, 1, 1)
    assert result == {"status": "calculated", "marks": Decimal("3.00")}


def test_derive_pt2_marks_for_annual(derived_service):
    result = derived_service.calculate_pt2_derived(1, 1, 1)
    assert result == {"status": "calculated", "marks": Decimal("2.50")}


def test_missing_source_marks_are_pending(derived_service):
    result = derived_service.calculate_pt2_derived(2, 1, 1)
    assert result == {"status": "pending", "marks": None}


def test_absent_source_marks_remain_absent(derived_service):
    result = derived_service.calculate_pt1_derived(2, 1, 1)
    assert result == {"status": "absent", "marks": None}


def test_derived_calculation_cannot_use_wrong_periodic_exam(derived_service):
    with pytest.raises(ValueError, match="cannot use PT1"):
        derived_service.calculate_pt1_derived(1, 1, 1, target_exam_name="Annual")


def test_calculate_pt_marks_without_persisting_derived_rows(derived_service):
    result = derived_service.calculate_pt1_derived(1, 1, 1)
    with derived_service.session_factory() as session:
        assert session.query(Mark).count() == 3
    assert result["marks"] == Decimal("3.00")


def test_french_conversion_uses_explicit_conversion_state():
    converted = DerivedCalculationService.calculate_french_conversion(raw_marks=35)
    assert converted["status"] == "converted"
    assert converted["marks"] == Decimal("70.00")

    already_converted = DerivedCalculationService.calculate_french_conversion(
        raw_marks=70, is_converted=True
    )
    assert already_converted == {"status": "already_converted", "marks": Decimal("70")}


def test_french_conversion_rejects_out_of_range_raw_marks():
    with pytest.raises(ValueError, match="source maximum"):
        DerivedCalculationService.calculate_french_conversion(raw_marks=41)


def test_grade_boundaries_are_evaluated_without_rounding():
    assert CalculationService.get_grade(Decimal("90.999")) == "A2"
    assert CalculationService.get_grade(Decimal("91")) == "A1"
    assert CalculationService.get_grade(Decimal("32.999")) == "E"
    assert CalculationService.get_grade(Decimal("33")) == "D"
