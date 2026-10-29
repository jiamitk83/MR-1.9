from models.database import SessionLocal
from models.audit import ExamLock
from repositories.audit import AuditRepository
from datetime import datetime

class ExamLockRepository:
    def __init__(self):
        self.session_factory = SessionLocal
        self.audit_repo = AuditRepository()
        self.audit_repo.session_factory = SessionLocal

    def lock_exam(self, exam_id, user="system", reason=None):
        """Lock an examination"""
        with self.session_factory() as session:
            existing = session.query(ExamLock).filter(ExamLock.exam_id == exam_id).first()
            if existing:
                existing.is_locked = True
                existing.locked_by = user
                existing.locked_at = datetime.utcnow()
                existing.lock_reason = reason
            else:
                lock = ExamLock(
                    exam_id=exam_id,
                    is_locked=True,
                    locked_by=user,
                    locked_at=datetime.utcnow(),
                    lock_reason=reason
                )
                session.add(lock)

            session.commit()
            self.audit_repo.log_action(
                action="LOCK",
                entity_type="EXAM",
                entity_id=exam_id,
                new_value=f"Locked by {user}",
                user=user
            )
            return True

    def unlock_exam(self, exam_id, user="system"):
        """Unlock an examination"""
        with self.session_factory() as session:
            lock = session.query(ExamLock).filter(ExamLock.exam_id == exam_id).first()
            if lock:
                lock.is_locked = False
                lock.locked_by = None
                lock.lock_reason = None
            else:
                lock = ExamLock(
                    exam_id=exam_id,
                    is_locked=False,
                    locked_by=None,
                    lock_reason=None
                )
                session.add(lock)

            session.commit()
            self.audit_repo.log_action(
                action="UNLOCK",
                entity_type="EXAM",
                entity_id=exam_id,
                new_value=f"Unlocked by {user}",
                user=user
            )
            return True

    def is_exam_locked(self, exam_id):
        """Check if an exam is locked"""
        with self.session_factory() as session:
            lock = session.query(ExamLock).filter(ExamLock.exam_id == exam_id).first()
            return lock and lock.is_locked

    def get_exam_lock_status(self, exam_id):
        """Get exam lock status details"""
        with self.session_factory() as session:
            lock = session.query(ExamLock).filter(ExamLock.exam_id == exam_id).first()
            return lock
