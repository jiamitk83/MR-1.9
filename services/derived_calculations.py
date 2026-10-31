from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from sqlalchemy import and_, func, inspect

from models.database import SessionLocal, Student, Subject
from models.examination import Examination, ExamComponent
from models.marks import Mark
from services.calculation import CalculationService


class DerivedCalculationService:
    """Read-only calculations for periodic-test and French marks."""

    SOURCE_EXAMS = {
        "half yearly": "PT1",
        "annual": "PT2",
    }

    def __init__(self, session_factory=SessionLocal):
        self.session_factory = session_factory

    def calculate_pt1_derived(self, student_id, subject_id, session_id, target_exam_name="Half Yearly"):
        return self._calculate_periodic_mark(
            student_id, subject_id, session_id, target_exam_name, expected_source="PT1"
        )

    def calculate_pt2_derived(self, student_id, subject_id, session_id, target_exam_name="Annual"):
        return self._calculate_periodic_mark(
            student_id, subject_id, session_id, target_exam_name, expected_source="PT2"
        )

    def _calculate_periodic_mark(self, student_id, subject_id, session_id, target_exam_name, expected_source):
        target_key = target_exam_name.strip().casefold()
        source_exam_name = self.SOURCE_EXAMS.get(target_key)
        if source_exam_name != expected_source:
            raise ValueError(f"{target_exam_name!r} cannot use {expected_source} as its source exam.")

        with self.session_factory() as session:
            student = session.get(Student, student_id)
            if student is None or student.session_id != session_id:
                return {"status": "pending", "marks": None}

            source_exams = session.query(Examination).filter(
                and_(
                    func.lower(Examination.name) == source_exam_name.casefold(),
                    Examination.session_id == session_id,
                )
            ).all()
            if not source_exams:
                return {"status": "pending", "marks": None}
            if len(source_exams) != 1:
                raise ValueError(f"More than one {source_exam_name} exam exists in this session.")
            source_exam = source_exams[0]

            subject = session.get(Subject, subject_id)
            if subject is None:
                return {"status": "pending", "marks": None}
            component_columns = {
                column["name"]
                for column in inspect(session.get_bind()).get_columns(ExamComponent.__tablename__)
            }
            component_fields = [
                ExamComponent.id,
                ExamComponent.max_marks,
                ExamComponent.name,
            ]
            if "subject_id" in component_columns:
                component_fields.append(ExamComponent.subject_id)
            if "code" in component_columns:
                component_fields.append(ExamComponent.code)
            source_components = session.query(*component_fields).filter(
                ExamComponent.exam_id == source_exam.id
            ).all()
            subject_specific = [
                component for component in source_components
                if getattr(component, "subject_id", None) == subject_id
            ]
            generic = [
                component for component in source_components
                if getattr(component, "subject_id", None) is None
            ]
            candidates = subject_specific or generic
            if len(candidates) > 1:
                coded = [
                    component for component in candidates
                    if (component.code or "").strip().casefold() == source_exam_name.casefold()
                    or component.name.strip().casefold() == source_exam_name.casefold()
                ]
                candidates = coded
            source_components = candidates
            if not source_components:
                return {"status": "pending", "marks": None}
            if len(source_components) != 1:
                raise ValueError(f"More than one {source_exam_name} source component exists for this subject.")
            source_component = source_components[0]

            source_mark = session.query(Mark).filter(
                and_(
                    Mark.student_id == student_id,
                    Mark.subject_id == subject_id,
                    Mark.component_id == source_component.id,
                )
            ).first()
            if source_mark is None or (source_mark.marks_obtained is None and not source_mark.is_absent):
                return {"status": "pending", "marks": None}
            if source_mark.is_absent:
                return {"status": "absent", "marks": None}
            if source_component.max_marks is None or source_component.max_marks <= 0:
                raise ValueError("The periodic-test component maximum must be greater than zero.")

            derived = CalculationService.derive_pt_marks(
                source_mark.marks_obtained,
                source_component.max_marks,
            )
            return {"status": "calculated", "marks": derived}

    @staticmethod
    def calculate_french_conversion(
        student_id=None,
        subject_id=None,
        component_id=None,
        raw_marks=None,
        max_marks=40,
        target_max=80,
        is_converted=False,
    ):
        """Convert explicitly raw marks; never infer conversion from the mark value."""
        try:
            obtained = Decimal(str(raw_marks))
            source_maximum = Decimal(str(max_marks))
            target_maximum = Decimal(str(target_max))
        except (InvalidOperation, TypeError, ValueError) as error:
            raise ValueError("French marks and their maxima must be valid numbers.") from error
        if not all(value.is_finite() for value in (obtained, source_maximum, target_maximum)):
            raise ValueError("French marks and their maxima must be finite numbers.")
        if source_maximum <= 0 or target_maximum <= 0:
            raise ValueError("French mark maxima must be greater than zero.")
        if is_converted:
            if obtained < 0 or obtained > target_maximum:
                raise ValueError("Converted French marks must be between zero and the target maximum.")
            return {"status": "already_converted", "marks": obtained}
        if obtained < 0 or obtained > source_maximum:
            raise ValueError("Raw French marks must be between zero and the source maximum.")

        converted = (obtained / source_maximum * target_maximum).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        return {
            "status": "converted",
            "marks": converted,
            "original_max": source_maximum,
        }

    def get_component_max_marks(self, exam_id, component_name):
        with self.session_factory() as session:
            component = session.query(ExamComponent.max_marks).filter(
                and_(
                    ExamComponent.exam_id == exam_id,
                    ExamComponent.name == component_name,
                )
            ).first()
            return component[0] if component else None
