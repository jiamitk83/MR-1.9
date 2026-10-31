from decimal import Decimal, InvalidOperation
import json

from models.database import SessionLocal, Student, Subject
from models.examination import Examination
from models.marks import Mark
from models.examination import ExamComponent
from models.audit import AuditLog, ExamLock
from models.grade_mark import GradeMark
from services.half_yearly import HalfYearlyService
from sqlalchemy import inspect

class MarkRepository:
    def __init__(self):
        self.session_factory = SessionLocal

    def save_marks_batch(self, marks_data):
        """Validate and save marks atomically, recording their audit history."""
        if not marks_data:
            return True

        with self.session_factory() as session:
            try:
                component_columns = {
                    column["name"]
                    for column in inspect(session.get_bind()).get_columns(ExamComponent.__tablename__)
                }
                seen = set()
                for data in marks_data:
                    key = (data['student_id'], data['subject_id'], data['component_id'])
                    if key in seen:
                        raise ValueError("A student has more than one mark in this batch.")
                    seen.add(key)

                    component_fields = [
                        ExamComponent.id,
                        ExamComponent.exam_id,
                        ExamComponent.max_marks,
                    ]
                    if "is_derived" in component_columns:
                        component_fields.append(ExamComponent.is_derived)
                    if "subject_id" in component_columns:
                        component_fields.append(ExamComponent.subject_id)
                    if "entry_max" in component_columns:
                        component_fields.append(ExamComponent.entry_max)
                    component = session.query(*component_fields).filter(
                        ExamComponent.id == data['component_id']
                    ).first()
                    if component is None:
                        raise ValueError("The selected exam component no longer exists.")
                    if getattr(component, "is_derived", False):
                        raise ValueError("Derived marks cannot be entered manually.")
                    student = session.get(Student, data['student_id'])
                    if student is None:
                        raise ValueError("A student in this batch no longer exists.")
                    if session.get(Subject, data['subject_id']) is None:
                        raise ValueError("The selected subject no longer exists.")
                    subject = session.get(Subject, data["subject_id"])
                    if HalfYearlyService.is_grade_only(subject):
                        raise ValueError("Grade-only subjects cannot be saved as numeric marks.")
                    component_subject_id = getattr(component, "subject_id", None)
                    if component_subject_id is not None and component_subject_id != data["subject_id"]:
                        raise ValueError("The selected component belongs to a different subject.")
                    examination = session.get(Examination, component.exam_id)
                    if examination is None or student.session_id != examination.session_id:
                        raise ValueError("The student and examination must belong to the same session.")
                    lock = session.query(ExamLock).filter_by(exam_id=component.exam_id).first()
                    if lock and lock.is_locked:
                        raise ValueError("This exam is locked. Marks cannot be changed.")

                    is_absent = bool(data.get('is_absent', False))
                    marks_obtained = None
                    if not is_absent:
                        try:
                            marks_obtained = Decimal(str(data['marks_obtained']))
                        except (KeyError, InvalidOperation, TypeError, ValueError) as error:
                            raise ValueError("Marks must be a valid number.") from error
                        if not marks_obtained.is_finite() or marks_obtained < 0:
                            raise ValueError("Marks must be a finite, non-negative number.")
                        entry_max = getattr(component, "entry_max", None) or component.max_marks
                        if marks_obtained > Decimal(str(entry_max)):
                            raise ValueError(
                                f"Marks cannot exceed the configured entry maximum of {entry_max}."
                            )

                    existing = session.query(Mark).filter_by(
                        student_id=key[0],
                        subject_id=key[1],
                        component_id=key[2]
                    ).first()

                    if existing:
                        previous_value = {
                            'marks_obtained': str(existing.marks_obtained) if existing.marks_obtained is not None else None,
                            'is_absent': existing.is_absent,
                        }
                        existing.marks_obtained = marks_obtained
                        existing.is_absent = is_absent
                        action = "UPDATE"
                    else:
                        existing = Mark(
                            student_id=key[0],
                            subject_id=key[1],
                            component_id=key[2],
                            marks_obtained=marks_obtained,
                            is_absent=is_absent,
                        )
                        session.add(existing)
                        previous_value = None
                        action = "CREATE"

                    session.flush()
                    session.add(AuditLog(
                        action=action,
                        entity_type="MARK",
                        entity_id=existing.id,
                        previous_value=json.dumps(previous_value) if previous_value is not None else None,
                        new_value=json.dumps({
                            'student_id': key[0],
                            'subject_id': key[1],
                            'component_id': key[2],
                            'marks_obtained': str(marks_obtained) if marks_obtained is not None else None,
                            'is_absent': is_absent,
                        }),
                    ))

                session.commit()
                return True
            except Exception:
                session.rollback()
                raise

    def save_grade_marks_batch(self, exam_id, marks_data):
        if not marks_data:
            return True
        with self.session_factory() as session:
            try:
                seen = set()
                for data in marks_data:
                    key = (data["student_id"], data["subject_id"], exam_id)
                    if key in seen:
                        raise ValueError("A student has more than one grade in this batch.")
                    seen.add(key)
                    student = session.get(Student, data["student_id"])
                    subject = session.get(Subject, data["subject_id"])
                    if student is None or subject is None:
                        raise ValueError("A student or subject in this batch no longer exists.")
                    if not HalfYearlyService.is_grade_only(subject):
                        raise ValueError("Grades can only be saved for configured grade-only subjects.")
                    examination = session.get(Examination, exam_id)
                    if examination is None or student.session_id != examination.session_id:
                        raise ValueError("The student and examination must belong to the same session.")
                    lock = session.query(ExamLock).filter_by(exam_id=exam_id).first()
                    if lock and lock.is_locked:
                        raise ValueError("This exam is locked. Grades cannot be changed.")
                    grade = str(data["grade"]).strip().upper()
                    if not grade or len(grade) > 12:
                        raise ValueError("Enter a grade of 1 to 12 characters.")
                    record = session.query(GradeMark).filter_by(
                        student_id=data["student_id"],
                        subject_id=data["subject_id"],
                        exam_id=exam_id,
                    ).first()
                    if record is None:
                        previous_grade = None
                        record = GradeMark(
                            student_id=data["student_id"],
                            subject_id=data["subject_id"],
                            exam_id=exam_id,
                            grade=grade,
                        )
                        session.add(record)
                        action = "CREATE"
                    else:
                        previous_grade = record.grade
                        record.grade = grade
                        action = "UPDATE"
                    session.flush()
                    session.add(AuditLog(
                        action=action,
                        entity_type="GRADE_MARK",
                        entity_id=record.id,
                        previous_value=(
                            json.dumps({"grade": previous_grade})
                            if previous_grade is not None else None
                        ),
                        new_value=json.dumps({
                            "student_id": data["student_id"],
                            "subject_id": data["subject_id"],
                            "exam_id": exam_id,
                            "grade": grade,
                        }),
                    ))
                session.commit()
                return True
            except Exception:
                session.rollback()
                raise

    def get_grade_marks(self, exam_id, subject_id, student_ids=None):
        with self.session_factory() as session:
            query = session.query(GradeMark).filter_by(
                exam_id=exam_id,
                subject_id=subject_id,
            )
            if student_ids is not None:
                if not student_ids:
                    return []
                query = query.filter(GradeMark.student_id.in_(student_ids))
            return query.all()

    def get_marks(self, subject_id, component_id, student_ids=None):
        with self.session_factory() as session:
            query = session.query(Mark).filter_by(subject_id=subject_id, component_id=component_id)
            if student_ids is not None:
                query = query.filter(Mark.student_id.in_(student_ids))
            return query.all()

    def get_marks_for_student(self, student_id, subject_ids=None, component_ids=None):
        with self.session_factory() as session:
            query = session.query(Mark).filter(Mark.student_id == student_id)
            if subject_ids is not None:
                query = query.filter(Mark.subject_id.in_(subject_ids))
            if component_ids is not None:
                query = query.filter(Mark.component_id.in_(component_ids))
            return query.all()

    def get_marks_for_students(self, student_ids, subject_ids=None, component_ids=None):
        if not student_ids:
            return []
        with self.session_factory() as session:
            query = session.query(Mark).filter(Mark.student_id.in_(student_ids))
            if subject_ids is not None:
                query = query.filter(Mark.subject_id.in_(subject_ids))
            if component_ids is not None:
                query = query.filter(Mark.component_id.in_(component_ids))
            return query.all()
