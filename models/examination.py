from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date, Boolean
from sqlalchemy.orm import relationship
from models.database import Base

class Examination(Base):
    __tablename__ = 'examinations'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False) # e.g., PT1, Half Yearly
    session_id = Column(Integer, ForeignKey('academic_sessions.id'), nullable=False)
    is_active = Column(Boolean, default=True)

class ExamComponent(Base):
    __tablename__ = 'exam_components'
    id = Column(Integer, primary_key=True)
    exam_id = Column(Integer, ForeignKey('examinations.id'), nullable=False)
    name = Column(String, nullable=False) # e.g., Written, MA, PT
    max_marks = Column(Float, nullable=False)

    # Relationships
    exam = relationship("Examination", backref="components")
