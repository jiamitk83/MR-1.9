from models.database import SessionLocal
from models.audit import AuditLog
from datetime import datetime

class AuditRepository:
    def __init__(self):
        self.session_factory = SessionLocal

    def log_action(self, action, entity_type, entity_id=None, previous_value=None,
                   new_value=None, user="system", ip_address=None):
        """Log an action to audit history"""
        with self.session_factory() as session:
            log = AuditLog(
                timestamp=datetime.utcnow(),
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                previous_value=previous_value,
                new_value=new_value,
                user=user,
                ip_address=ip_address
            )
            session.add(log)
            session.commit()
            return log.id

    def get_recent_logs(self, limit=50, entity_type=None):
        """Get recent audit logs"""
        with self.session_factory() as session:
            query = session.query(AuditLog).order_by(AuditLog.timestamp.desc())
            if entity_type:
                query = query.filter(AuditLog.entity_type == entity_type)
            return query.limit(limit).all()

    def get_logs_for_entity(self, entity_type, entity_id):
        """Get all logs for a specific entity"""
        with self.session_factory() as session:
            return session.query(AuditLog).filter(
                AuditLog.entity_type == entity_type,
                AuditLog.entity_id == entity_id
            ).order_by(AuditLog.timestamp.asc()).all()
