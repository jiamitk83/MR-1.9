from models.database import SessionLocal
from models.examination import Examination, ExamComponent
from sqlalchemy import and_

class ExamRepository:
    def __init__(self):
        self.session_factory = SessionLocal

    # ========== Examinations CRUD ==========
    def create_exam(self, name, session_id):
        with self.session_factory() as session:
            existing = session.query(Examination).filter(
                and_(Examination.name == name, Examination.session_id == session_id)
            ).first()
            if existing:
                return None  # Duplicate
            exam = Examination(name=name, session_id=session_id)
            session.add(exam)
            session.commit()
            return exam.id

    def get_exam_by_id(self, exam_id):
        with self.session_factory() as session:
            return session.query(Examination).filter(Examination.id == exam_id).first()

    def get_exams(self, session_id=None):
        with self.session_factory() as session:
            query = session.query(Examination)
            if session_id:
                query = query.filter(Examination.session_id == session_id)
            return query.all()

    def search_exams(self, keyword=None, session_id=None):
        with self.session_factory() as session:
            query = session.query(Examination)
            if keyword:
                query = query.filter(Examination.name.contains(keyword))
            if session_id:
                query = query.filter(Examination.session_id == session_id)
            return query.all()

    def update_exam(self, exam_id, name=None, session_id=None, is_active=None):
        with self.session_factory() as session:
            exam = session.query(Examination).filter(Examination.id == exam_id).first()
            if not exam:
                return None
            if name:
                exam.name = name
            if session_id:
                exam.session_id = session_id
            if is_active is not None:
                exam.is_active = is_active
            session.commit()
            return exam

    def delete_exam(self, exam_id):
        with self.session_factory() as session:
            exam = session.query(Examination).filter(Examination.id == exam_id).first()
            if exam:
                # Check if exam has marks before deleting
                mark_count = session.query(ExamComponent).filter(
                    ExamComponent.exam_id == exam_id
                ).count()
                if mark_count > 0:
                    return False  # Cannot delete exam with components
                session.delete(exam)
                session.commit()
                return True
            return False

    # ========== Components CRUD ==========
    def add_component(self, exam_id, name, max_marks, code=None, is_derived=False):
        with self.session_factory() as session:
            comp = ExamComponent(
                exam_id=exam_id,
                name=name,
                max_marks=max_marks,
                code=code,
                is_derived=is_derived
            )
            session.add(comp)
            session.commit()
            return comp.id

    def get_components_by_exam(self, exam_id):
        with self.session_factory() as session:
            return session.query(ExamComponent).filter(
                ExamComponent.exam_id == exam_id
            ).all()

    def update_component(self, component_id, name=None, max_marks=None, code=None):
        with self.session_factory() as session:
            comp = session.query(ExamComponent).filter(
                ExamComponent.id == component_id
            ).first()
            if not comp:
                return None
            if name:
                comp.name = name
            if max_marks is not None:
                comp.max_marks = max_marks
            if code:
                comp.code = code
            session.commit()
            return comp

    def delete_component(self, component_id):
        with self.session_factory() as session:
            comp = session.query(ExamComponent).filter(
                ExamComponent.id == component_id
            ).first()
            if comp:
                session.delete(comp)
                session.commit()
                return True
            return False
