from models.database import SessionLocal
from models.marks import Mark

class MarkRepository:
    def __init__(self):
        self.session_factory = SessionLocal

    def save_marks_batch(self, marks_data):
        """
        Saves or updates a batch of marks.
        marks_data: list of dicts {student_id, subject_id, component_id, marks_obtained, is_absent}
        """
        with self.session_factory() as session:
            try:
                for data in marks_data:
                    # Check if mark already exists
                    existing = session.query(Mark).filter_by(
                        student_id=data['student_id'],
                        subject_id=data['subject_id'],
                        component_id=data['component_id']
                    ).first()

                    if existing:
                        existing.marks_obtained = data['marks_obtained']
                        existing.is_absent = data['is_absent']
                    else:
                        new_mark = Mark(**data)
                        session.add(new_mark)

                session.commit()
                return True
            except Exception as e:
                session.rollback()
                print(f"Error saving batch: {e}")
                return False

    def get_marks(self, subject_id, component_id, student_ids=None):
        with self.session_factory() as session:
            query = session.query(Mark).filter_by(subject_id=subject_id, component_id=component_id)
            if student_ids:
                query = query.filter(Mark.student_id.in_(student_ids))
            return query.all()
