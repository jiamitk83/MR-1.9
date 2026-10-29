from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean, Date, DateTime, Text
from sqlalchemy.orm import relationship
from models.database import Base
from datetime import datetime

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    action = Column(String, nullable=False)  # CREATE, UPDATE, DELETE, LOCK, UNLOCK
    entity_type = Column(String, nullable=False)  # STUDENT, EXAM, MARK, SESSION, etc.
    entity_id = Column(Integer)
    previous_value = Column(Text)
    new_value = Column(Text)
    user = Column(String, default="system")  # Will be expanded for auth
    ip_address = Column(String)

class ExamLock(Base):
    __tablename__ = 'exam_locks'
    id = Column(Integer, primary_key=True)
    exam_id = Column(Integer, ForeignKey('examinations.id'), nullable=False, unique=True)
    is_locked = Column(Boolean, default=False)
    locked_by = Column(String, default="system")
    locked_at = Column(DateTime, default=datetime.utcnow)
    lock_reason = Column(String)

class SubjectAlias(Base):
    __tablename__ = 'subject_aliases'
    id = Column(Integer, primary_key=True)
    subject_id = Column(Integer, ForeignKey('subjects.id'), nullable=False)
    alias_name = Column(String, nullable=False)
    alias_code = Column(String)
    is_primary = Column(Boolean, default=False)

    # Relationships
    subject = relationship("Subject", backref="aliases")
