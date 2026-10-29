from models.database import SessionLocal
from models.student import Student
from models.examination import Examination
from models.marks import Mark
from sqlalchemy import func

class DashboardRepository:
    def __init__(self):
        self.session_factory = SessionLocal

    def get_stats(self):
        """Get dashboard statistics"""
        with self.session_factory() as session:
            stats = {}

            # Total active students
            stats['active_students'] = session.query(func.count(Student.id)).filter(Student.active == True).scalar()

            # Total students
            stats['total_students'] = session.query(func.count(Student.id)).scalar()

            # Active sessions
            stats['active_sessions'] = session.query(func.count(Examination.session_id)).\
                filter(Examination.session_id.in_(
                    session.query(Student.session_id).filter(Student.active == True).distinct()
                )).scalar()

            # Exams configured
            stats['exams_count'] = session.query(func.count(Examination.id)).scalar()

            return stats

    def get_recent_activity(self, limit=10):
        """Get recent activity from audit log"""
        with self.session_factory() as session:
            # This would query audit table if implemented
            return []
