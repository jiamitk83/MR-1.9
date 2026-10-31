from sqlalchemy import Column, Date, ForeignKey, Integer, String, Text, UniqueConstraint

from models.database import Base


class ReportCardDetails(Base):
    __tablename__ = "report_card_details"
    __table_args__ = (
        UniqueConstraint("student_id", "exam_id", name="uq_report_card_student_exam"),
    )

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    exam_id = Column(Integer, ForeignKey("examinations.id"), nullable=False)
    days_present = Column(Integer)
    days_absent = Column(Integer)
    working_days = Column(Integer)
    issue_date = Column(Date)
    class_teacher = Column(String)
    co_scholastic = Column(Text)
    subject_remarks = Column(Text)
