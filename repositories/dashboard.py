from models.database import SessionLocal
from models.database import Student, AcademicSession
from models.examination import Examination
from models.audit import AuditLog
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
            stats['active_sessions'] = session.query(func.count(AcademicSession.id)).filter(
                AcademicSession.is_active.is_(True)
            ).scalar()

            # Exams configured
            stats['exams_count'] = session.query(func.count(Examination.id)).scalar()

            # Classes count
            from models.database import Class
            stats['classes_count'] = session.query(func.count(Class.id)).scalar()

            return stats

    def get_recent_activity(self, limit=10):
        """Get recent activity from audit log"""
        with self.session_factory() as session:
            return session.query(AuditLog).order_by(
                AuditLog.timestamp.desc(),
                AuditLog.id.desc(),
            ).limit(max(0, limit)).all()
