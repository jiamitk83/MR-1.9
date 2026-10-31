import json

from models.database import SessionLocal
from models.report_card import ReportCardDetails


class ReportCardRepository:
    def __init__(self):
        self.session_factory = SessionLocal

    def get_details(self, student_id, exam_id):
        with self.session_factory() as session:
            record = session.query(ReportCardDetails).filter_by(
                student_id=student_id,
                exam_id=exam_id,
            ).first()
            if record is None:
                return {}
            return {
                "days_present": record.days_present,
                "days_absent": record.days_absent,
                "working_days": record.working_days,
                "issue_date": record.issue_date,
                "class_teacher": record.class_teacher or "",
                "co_scholastic": json.loads(record.co_scholastic or "{}"),
                "subject_remarks": json.loads(record.subject_remarks or "{}"),
            }

    def save_details(self, student_id, exam_id, details):
        with self.session_factory() as session:
            record = session.query(ReportCardDetails).filter_by(
                student_id=student_id,
                exam_id=exam_id,
            ).first()
            if record is None:
                record = ReportCardDetails(student_id=student_id, exam_id=exam_id)
                session.add(record)
            record.days_present = details["days_present"]
            record.days_absent = details["days_absent"]
            record.working_days = details["working_days"]
            record.issue_date = details["issue_date"]
            record.class_teacher = details["class_teacher"]
            record.co_scholastic = json.dumps(
                details["co_scholastic"], ensure_ascii=False, sort_keys=True,
            )
            record.subject_remarks = json.dumps(
                details["subject_remarks"], ensure_ascii=False, sort_keys=True,
            )
            session.commit()
