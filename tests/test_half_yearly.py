from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import AcademicSession, Base, Class, Student, Subject
from models.examination import ExamComponent, Examination
from models.marks import Mark
from repositories.examination import ExamRepository
from services.derived_calculations import DerivedCalculationService
from services.half_yearly import HalfYearlyService


class DerivedService:
    def calculate_pt1_derived(self, *_args, **_kwargs):
        return {"status": "calculated", "marks": Decimal("4")}

    @staticmethod
    def calculate_french_conversion(**kwargs):
        return DerivedCalculationService.calculate_french_conversion(**kwargs)


def test_templates_and_french_conversion_are_explicit():
    math = SimpleNamespace(name="Mathematics", code="MATH")
    french = SimpleNamespace(name="French", code="FRENCH")
    gk = SimpleNamespace(name="General Knowledge", code="GK")

    assert sum(item.maximum for item in HalfYearlyService.template_for_subject(math)) == 100
    assert sum(item.maximum for item in HalfYearlyService.template_for_subject(
        SimpleNamespace(name="Computer", code="COMPUTER")
    )) == 100
    assert HalfYearlyService.template_for_subject(gk) == ()
    assert HalfYearlyService.template_for_subject(french)[1].entry_maximum == 40
    assert HalfYearlyService.template_for_subject(french, 80)[1].entry_maximum == 80
    with pytest.raises(ValueError, match="either 40 or 80"):
        HalfYearlyService.template_for_subject(french, 60)


def test_half_yearly_french_result_converts_raw_written_mark_once():
    subject = SimpleNamespace(id=1, name="French", code="FRENCH")
    template = HalfYearlyService.template_for_subject(subject, 40)
    components = [
        SimpleNamespace(
            id=index,
            name=item.name,
            code=item.code,
            max_marks=item.maximum,
            entry_max=item.entry_maximum,
            is_derived=item.is_derived,
        )
        for index, item in enumerate(template, start=1)
    ]
    marks = {
        components[1].id: SimpleNamespace(marks_obtained=Decimal("20"), is_absent=False),
        components[2].id: SimpleNamespace(marks_obtained=Decimal("4"), is_absent=False),
        components[3].id: SimpleNamespace(marks_obtained=Decimal("5"), is_absent=False),
        components[4].id: SimpleNamespace(marks_obtained=Decimal("5"), is_absent=False),
    }

    result = HalfYearlyService(DerivedService()).calculate_subject_result(
        SimpleNamespace(id=1), subject, 1, components, marks
    )

    assert result["status"] == "Complete"
    assert result["components"][1]["marks"] == Decimal("40.00")
    assert result["total"] == Decimal("58.00")
    assert result["maximum"] == Decimal("100")
    assert result["percentage"] == Decimal("58.00")


def test_french_conversion_examples_and_direct_entry_are_not_reconverted():
    for raw, expected in (("30", "60.00"), ("35", "70.00")):
        converted = DerivedCalculationService.calculate_french_conversion(
            raw_marks=raw, max_marks=40, target_max=80
        )
        assert converted["marks"] == Decimal(expected)
    already_converted = DerivedCalculationService.calculate_french_conversion(
        raw_marks=70, max_marks=40, target_max=80, is_converted=True
    )
    assert already_converted["marks"] == Decimal("70")

    subject = SimpleNamespace(id=1, name="French", code="FRENCH")
    template = HalfYearlyService.template_for_subject(subject, 80)
    components = [
        SimpleNamespace(
            id=index,
            name=item.name,
            code=item.code,
            max_marks=item.maximum,
            entry_max=item.entry_maximum,
            is_derived=item.is_derived,
        )
        for index, item in enumerate(template, start=1)
    ]
    marks = {
        components[1].id: SimpleNamespace(marks_obtained=Decimal("70"), is_absent=False),
        components[2].id: SimpleNamespace(marks_obtained=Decimal("5"), is_absent=False),
        components[3].id: SimpleNamespace(marks_obtained=Decimal("5"), is_absent=False),
        components[4].id: SimpleNamespace(marks_obtained=Decimal("5"), is_absent=False),
    }

    result = HalfYearlyService(DerivedService()).calculate_subject_result(
        SimpleNamespace(id=1), subject, 1, components, marks
    )

    assert result["status"] == "Complete"
    assert result["components"][1]["marks"] == Decimal("70")
    assert result["total"] == Decimal("89.00")


def test_grade_only_result_never_contributes_numeric_total():
    service = HalfYearlyService(DerivedService())
    subject = SimpleNamespace(name="General Knowledge", code="GK")
    student = SimpleNamespace(id=1)

    pending = service.calculate_subject_result(student, subject, 1, (), {"grade": None})
    graded = service.calculate_subject_result(student, subject, 1, (), {"grade": "A"})

    assert pending["status"] == "Pending"
    assert pending["total"] is None
    assert graded["status"] == "Grade only"
    assert graded["grade"] == "A"
    assert graded["grade_only"] is True
    assert graded["total"] is None


def test_legacy_generic_marks_are_projected_by_subject_without_rewriting():
    subject = SimpleNamespace(name="Social Study", code="SST")
    template = HalfYearlyService.template_for_subject(subject)
    configured = [
        SimpleNamespace(
            id=index,
            name=item.name,
            code=item.code,
            max_marks=item.maximum,
            entry_max=item.entry_maximum,
            is_derived=item.is_derived,
            subject_id=1,
        )
        for index, item in enumerate(template, start=10)
    ]
    legacy = [
        SimpleNamespace(
            id=index, name=name, code=None, is_derived=False, subject_id=None
        )
        for index, name in enumerate(("MA", "SE", "PF", "WRITTEN 80"), start=1)
    ]
    saved_marks = {
        1: SimpleNamespace(marks_obtained=Decimal("4"), is_absent=False),
        2: SimpleNamespace(marks_obtained=Decimal("4"), is_absent=False),
        3: SimpleNamespace(marks_obtained=Decimal("5"), is_absent=False),
        4: SimpleNamespace(marks_obtained=Decimal("68"), is_absent=False),
    }

    projected = HalfYearlyService.map_legacy_component_marks(
        configured, legacy, saved_marks
    )

    assert projected[configured[1].id] is saved_marks[1]
    assert projected[configured[2].id] is saved_marks[2]
    assert projected[configured[3].id] is saved_marks[3]
    assert projected[configured[4].id] is saved_marks[4]
    assert set(saved_marks) == {1, 2, 3, 4}


def test_subject_configuration_is_idempotent_and_preserves_saved_marks():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    with session_factory() as session:
        session.add_all([
            AcademicSession(id=1, name="2026-2027"),
            Class(id=1, name="Grade 6"),
            Subject(id=1, name="Mathematics", code="MATH"),
        ])
        session.flush()
        session.add(Student(
            id=1, admission_number="A1", roll_number=1, name="Student",
            session_id=1, class_id=1,
        ))
        session.add_all([
            Examination(id=1, name="Half Yearly", session_id=1),
            Examination(id=2, name="PT1", session_id=1),
        ])
        session.commit()

    repository = ExamRepository()
    repository.session_factory = session_factory
    template = HalfYearlyService.template_for_subject(
        SimpleNamespace(name="Mathematics", code="MATH")
    )
    configured = repository.configure_subject_components(1, 1, template)
    again = repository.configure_subject_components(1, 1, template)
    assert [item.code for item in configured] == [item.code for item in again]
    assert configured[0].subject_id == 1

    with session_factory() as session:
        session.add(Mark(
            student_id=1, subject_id=1, component_id=configured[1].id,
            marks_obtained=Decimal("4"), is_absent=False,
        ))
        session.commit()
    changed = list(template)
    changed[1] = replace(changed[1], maximum=Decimal("6"))
    changed[2] = replace(changed[2], maximum=Decimal("4"))
    with pytest.raises(ValueError, match="marks have already been saved"):
        repository.configure_subject_components(1, 1, changed)

    with session_factory() as session:
        assert session.query(ExamComponent).filter_by(
            exam_id=1, subject_id=1
        ).count() == 5
        assert session.query(Mark).filter_by(component_id=configured[1].id).count() == 1
    engine.dispose()
