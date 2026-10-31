from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint

from models.database import Base


class GradeMark(Base):
    __tablename__ = "grade_marks"
    __table_args__ = (
        UniqueConstraint(
            "student_id", "subject_id", "exam_id",
            name="uq_grade_mark_student_subject_exam",
        ),
    )

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    exam_id = Column(Integer, ForeignKey("examinations.id"), nullable=False)
    grade = Column(String, nullable=False)
