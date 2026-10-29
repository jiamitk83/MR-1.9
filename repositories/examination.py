from models.database import SessionLocal
from models.examination import Examination, ExamComponent

class ExamRepository:
    def __init__(self):
        self.session_factory = SessionLocal

    def create_exam(self, name, session_id):
        with self.session_factory() as session:
            exam = Examination(name=name, session_id=session_id)
            session.add(exam)
            session.commit()
            session.refresh(exam)
            return exam.id

    def add_component(self, exam_id, name, max_marks):
        with self.session_factory() as session:
            comp = ExamComponent(exam_id=exam_id, name=name, max_marks=max_marks)
            session.add(comp)
            session.commit()
            return comp.id

    def get_exams(self, session_id=None):
        with self.session_factory() as session:
            query = session.query(Examination)
            if session_id:
                query = query.filter(Examination.session_id == session_id)
            return query.all()
