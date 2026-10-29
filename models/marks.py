from sqlalchemy import Column, Integer, Float, ForeignKey, Boolean, Numeric
from models.database import Base

class Mark(Base):
    __tablename__ = 'marks'
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey('students.id'), nullable=False)
    subject_id = Column(Integer, ForeignKey('subjects.id'), nullable=False)
    component_id = Column(Integer, ForeignKey('exam_components.id'), nullable=False)
    marks_obtained = Column(Numeric(precision=5, scale=2)) # Using Numeric for Decimal precision
    is_absent = Column(Boolean, default=False)
