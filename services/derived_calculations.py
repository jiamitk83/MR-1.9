from decimal import Decimal, ROUND_HALF_UP
from models.database import SessionLocal, Student
from models.marks import Mark
from models.examination import Examination, ExamComponent
from sqlalchemy import and_, func

class DerivedCalculationService:
    """Service for calculating derived marks (PT1→Half Yearly, PT2→Annual)"""

    @staticmethod
    def calculate_pt1_derived(student_id, subject_id, session_id, target_exam_name="Half Yearly"):
        """
        Calculate PT1-derived marks for Half Yearly exam.
        Formula: (PT1_obtained / PT1_max) * 5
        """
        with SessionLocal() as session:
            # Find PT1 exam
            pt1_exam = session.query(Examination).filter(
                and_(
                    Examination.name == "PT1",
                    Examination.session_id == session_id
                )
            ).first()

            if not pt1_exam:
                return None

            # Find PT1 component (max marks = 5)
            pt1_component = session.query(ExamComponent).filter(
                and_(
                    ExamComponent.exam_id == pt1_exam.id,
                    ExamComponent.name == "PT1"
                )
            ).first()

            if not pt1_component:
                return None

            # Get the PT1 mark for this student
            pt1_mark = session.query(Mark).filter(
                and_(
                    Mark.student_id == student_id,
                    Mark.subject_id == subject_id,
                    Mark.component_id == pt1_component.id
                )
            ).first()

            if not pt1_mark or pt1_mark.marks_obtained is None:
                return None

            if pt1_mark.is_absent:
                return {"status": "absent", "marks": None}

            # Calculate derived marks
            obtained = Decimal(str(pt1_mark.marks_obtained))
            max_marks = Decimal(str(pt1_component.max_marks))

            if max_marks == 0:
                return None

            derived = (obtained / max_marks) * 5
            derived = derived.quantize(Decimal("0.00"), rounding=ROUND_HALF_UP)

            return {"status": "calculated", "marks": float(derived)}

    @staticmethod
    def calculate_pt2_derived(student_id, subject_id, session_id, target_exam_name="Annual"):
        """
        Calculate PT2-derived marks for Annual exam.
        Formula: (PT2_obtained / PT2_max) * 5
        """
        with SessionLocal() as session:
            # Find PT2 exam
            pt2_exam = session.query(Examination).filter(
                and_(
                    Examination.name == "PT2",
                    Examination.session_id == session_id
                )
            ).first()

            if not pt2_exam:
                return None

            # Find PT2 component (max marks = 5)
            pt2_component = session.query(ExamComponent).filter(
                and_(
                    ExamComponent.exam_id == pt2_exam.id,
                    ExamComponent.name == "PT2"
                )
            ).first()

            if not pt2_component:
                return None

            # Get the PT2 mark for this student
            pt2_mark = session.query(Mark).filter(
                and_(
                    Mark.student_id == student_id,
                    Mark.subject_id == subject_id,
                    Mark.component_id == pt2_component.id
                )
            ).first()

            if not pt2_mark or pt2_mark.marks_obtained is None:
                return None

            if pt2_mark.is_absent:
                return {"status": "absent", "marks": None}

            # Calculate derived marks
            obtained = Decimal(str(pt2_mark.marks_obtained))
            max_marks = Decimal(str(pt2_component.max_marks))

            if max_marks == 0:
                return None

            derived = (obtained / max_marks) * 5
            derived = derived.quantize(Decimal("0.00"), rounding=ROUND_HALF_UP)

            return {"status": "calculated", "marks": float(derived)}

    @staticmethod
    def calculate_french_conversion(student_id, subject_id, component_id, raw_marks, max_marks=40, target_max=80):
        """
        Convert French written marks from out of 40 to out of 80.
        Only converts if not already converted (track conversion state).
        """
        with SessionLocal() as session:
            # Check if already converted
            existing = session.query(Mark).filter(
                and_(
                    Mark.student_id == student_id,
                    Mark.subject_id == subject_id,
                    Mark.component_id == component_id
                )
            ).first()

            # If marks already saved out of 80, don't convert again
            if existing and existing.marks_obtained and float(existing.marks_obtained) >= target_max:
                return {"status": "already_converted", "marks": float(existing.marks_obtained)}

            # Perform conversion
            obtained = Decimal(str(raw_marks))
            max = Decimal(str(max_marks))
            target = Decimal(str(target_max))

            if max == 0:
                return None

            converted = (obtained / max) * target
            converted = converted.quantize(Decimal("0.00"), rounding=ROUND_HALF_UP)

            return {"status": "converted", "marks": float(converted), "original_max": max_marks}

    @staticmethod
    def get_component_max_marks(exam_id, component_name):
        """Get maximum marks for a component"""
        with SessionLocal() as session:
            comp = session.query(ExamComponent).filter(
                and_(
                    ExamComponent.exam_id == exam_id,
                    ExamComponent.name == component_name
                )
            ).first()
            return comp.max_marks if comp else None
