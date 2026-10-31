from models.database import SessionLocal, Subject
from models.examination import Examination, ExamComponent
from models.marks import Mark
from models.report_card import ReportCardDetails
from models.grade_mark import GradeMark
from sqlalchemy import and_, delete, inspect, text, update
from decimal import Decimal, InvalidOperation
from typing import NamedTuple


class ExamComponentRecord(NamedTuple):
    id: int
    exam_id: int
    name: str
    max_marks: float
    code: str | None = None
    is_derived: bool = False
    display_order: int = 0
    subject_id: int | None = None
    entry_max: float | None = None

class ExamRepository:
    def __init__(self):
        self.session_factory = SessionLocal

    # ========== Examinations CRUD ==========
    def create_exam(self, name, session_id):
        with self.session_factory() as session:
            existing = session.query(Examination).filter(
                and_(Examination.name == name, Examination.session_id == session_id)
            ).first()
            if existing:
                return None  # Duplicate
            exam = Examination(name=name, session_id=session_id)
            session.add(exam)
            session.commit()
            return exam.id

    def get_exam_by_id(self, exam_id):
        with self.session_factory() as session:
            return session.query(Examination).filter(Examination.id == exam_id).first()

    def get_exams(self, session_id=None):
        with self.session_factory() as session:
            query = session.query(Examination)
            if session_id:
                query = query.filter(Examination.session_id == session_id)
            return query.all()

    def search_exams(self, keyword=None, session_id=None):
        with self.session_factory() as session:
            query = session.query(Examination)
            if keyword:
                query = query.filter(Examination.name.contains(keyword))
            if session_id:
                query = query.filter(Examination.session_id == session_id)
            return query.all()

    def update_exam(self, exam_id, name=None, session_id=None, is_active=None):
        with self.session_factory() as session:
            exam = session.query(Examination).filter(Examination.id == exam_id).first()
            if not exam:
                return None
            if name:
                exam.name = name
            if session_id:
                exam.session_id = session_id
            if is_active is not None:
                exam.is_active = is_active
            session.commit()
            return exam

    def delete_exam(self, exam_id):
        with self.session_factory() as session:
            exam = session.query(Examination).filter(Examination.id == exam_id).first()
            if exam:
                # Check if exam has marks before deleting
                mark_count = session.query(ExamComponent).filter(
                    ExamComponent.exam_id == exam_id
                ).count()
                report_details = session.query(ReportCardDetails.id).filter(
                    ReportCardDetails.exam_id == exam_id
                ).first()
                grade_marks = (
                    session.query(GradeMark.id).filter(GradeMark.exam_id == exam_id).first()
                    if inspect(session.get_bind()).has_table(GradeMark.__tablename__)
                    else None
                )
                if mark_count > 0 or report_details or grade_marks:
                    return False
                session.delete(exam)
                session.commit()
                return True
            return False

    # ========== Components CRUD ==========
    def add_component(
        self, exam_id, name, max_marks, code=None, is_derived=False,
        subject_id=None, entry_max=None, display_order=0,
    ):
        self._validate_max_marks(max_marks)
        if entry_max is not None:
            self._validate_max_marks(entry_max)
            if Decimal(str(entry_max)) > Decimal(str(max_marks)):
                raise ValueError("The entry maximum cannot exceed the component maximum.")
        with self.session_factory() as session:
            table = ExamComponent.__table__
            columns = {column["name"] for column in inspect(session.get_bind()).get_columns(table.name)}
            if code and "code" not in columns:
                raise ValueError("This database schema does not support component codes.")
            if is_derived and "is_derived" not in columns:
                raise ValueError("This database schema does not support derived components.")
            if subject_id is not None and "subject_id" not in columns:
                raise ValueError("This database schema does not support subject-specific components.")
            if entry_max is not None and "entry_max" not in columns:
                raise ValueError("This database schema does not support entry maxima.")
            if subject_id is not None:
                existing = self._get_component_records(session, exam_id=exam_id)
                for component in existing:
                    if component.subject_id != subject_id:
                        continue
                    if code and component.code and component.code.casefold() == code.casefold():
                        raise ValueError("Component codes must be unique for this subject and examination.")
            values = {"exam_id": exam_id, "name": name, "max_marks": max_marks}
            insert_columns = ["exam_id", "name", "max_marks"]
            if code is not None:
                insert_columns.append("code")
                values["code"] = code
            if "is_derived" in columns:
                insert_columns.append("is_derived")
                values["is_derived"] = is_derived
            if "display_order" in columns:
                insert_columns.append("display_order")
                values["display_order"] = display_order
            if subject_id is not None:
                insert_columns.append("subject_id")
                values["subject_id"] = subject_id
            if entry_max is not None:
                insert_columns.append("entry_max")
                values["entry_max"] = entry_max
            column_sql = ", ".join(insert_columns)
            parameter_sql = ", ".join(f":{column}" for column in insert_columns)
            result = session.execute(
                text(f"INSERT INTO {table.name} ({column_sql}) VALUES ({parameter_sql})"),
                values,
            )
            session.commit()
            return result.lastrowid

    def get_components_by_exam(self, exam_id):
        with self.session_factory() as session:
            return self._get_component_records(session, exam_id=exam_id)

    def get_components_for_subject(self, exam_id, subject_id):
        components = self.get_components_by_exam(exam_id)
        specific = [component for component in components if component.subject_id == subject_id]
        if specific:
            return specific
        return [component for component in components if component.subject_id is None]

    def configure_subject_components(self, exam_id, subject_id, definitions):
        definitions = tuple(definitions)
        if not definitions:
            raise ValueError("Numeric subjects require configured examination components.")
        with self.session_factory() as session:
            table = ExamComponent.__table__
            columns = {
                column["name"]
                for column in inspect(session.get_bind()).get_columns(table.name)
            }
            required_columns = {"subject_id", "entry_max"}
            if not required_columns <= columns:
                raise ValueError("Migrate the database before configuring subject-specific components.")
            existing = [
                component
                for component in self._get_component_records(session, exam_id=exam_id)
                if component.subject_id == subject_id
            ]
            if session.get(Examination, exam_id) is None:
                raise ValueError("The selected examination no longer exists.")
            if session.get(Subject, subject_id) is None:
                raise ValueError("The selected subject no longer exists.")
            requested_codes = [item.code.strip().upper() for item in definitions]
            if len(set(requested_codes)) != len(requested_codes):
                raise ValueError("Component codes must be unique within this subject and examination.")
            for item in definitions:
                self._validate_max_marks(item.maximum)
                if item.entry_maximum is not None:
                    self._validate_max_marks(item.entry_maximum)
                    if Decimal(str(item.entry_maximum)) > Decimal(str(item.maximum)):
                        raise ValueError("A component entry maximum cannot exceed its final maximum.")
            if sum(
                (Decimal(str(item.maximum)) for item in definitions),
                Decimal("0"),
            ) != Decimal("100"):
                raise ValueError("Numeric Half Yearly component maxima must total exactly 100.")
            pt1 = [
                item for item in definitions
                if item.code.strip().upper() == "PT1"
            ]
            if len(pt1) != 1 or not pt1[0].is_derived or Decimal(str(pt1[0].maximum)) != Decimal("5"):
                raise ValueError("PT1 / 5 must be configured exactly once as a derived component.")
            existing_by_code = {
                (component.code or "").strip().upper(): component
                for component in existing
            }
            is_same = len(existing) == len(definitions) and all(
                (item.code.strip().upper() in existing_by_code)
                and Decimal(str(existing_by_code[item.code.strip().upper()].max_marks))
                    == Decimal(str(item.maximum))
                and existing_by_code[item.code.strip().upper()].is_derived == item.is_derived
                and (
                    existing_by_code[item.code.strip().upper()].entry_max is None
                    and item.entry_maximum is None
                    or existing_by_code[item.code.strip().upper()].entry_max is not None
                    and item.entry_maximum is not None
                    and Decimal(str(existing_by_code[item.code.strip().upper()].entry_max))
                        == Decimal(str(item.entry_maximum))
                )
                for item in definitions
            )
            if is_same:
                return existing
            for component in existing:
                if session.query(Mark.id).filter(Mark.component_id == component.id).first():
                    raise ValueError(
                        f"Cannot change {component.name}; marks have already been saved. "
                        "Existing historical component records were preserved."
                    )
            for component in existing:
                session.execute(delete(table).where(ExamComponent.id == component.id))
            for order, item in enumerate(definitions):
                values = {
                    "exam_id": exam_id,
                    "name": item.name,
                    "max_marks": float(item.maximum),
                    "code": item.code,
                    "is_derived": item.is_derived,
                    "display_order": order,
                    "subject_id": subject_id,
                    "entry_max": (
                        float(item.entry_maximum)
                        if item.entry_maximum is not None else None
                    ),
                }
                fields = [
                    "exam_id", "name", "max_marks", "code", "is_derived",
                    "display_order", "subject_id", "entry_max",
                ]
                session.execute(
                    text(
                        f"INSERT INTO {table.name} ({', '.join(fields)}) "
                        f"VALUES ({', '.join(f':{field}' for field in fields)})"
                    ),
                    values,
                )
            session.commit()
        return self.get_components_for_subject(exam_id, subject_id)

    def get_component_by_id(self, component_id):
        with self.session_factory() as session:
            records = self._get_component_records(session, component_id=component_id)
            return records[0] if records else None

    @staticmethod
    def _get_component_records(session, exam_id=None, component_id=None):
        table = ExamComponent.__table__
        columns = {column["name"] for column in inspect(session.get_bind()).get_columns(table.name)}
        selected = [
            ExamComponent.id,
            ExamComponent.exam_id,
            ExamComponent.name,
            ExamComponent.max_marks,
        ]
        if "code" in columns:
            selected.append(ExamComponent.code)
        if "is_derived" in columns:
            selected.append(ExamComponent.is_derived)
        if "display_order" in columns:
            selected.append(ExamComponent.display_order)
        if "subject_id" in columns:
            selected.append(ExamComponent.subject_id)
        if "entry_max" in columns:
            selected.append(ExamComponent.entry_max)
        query = session.query(*selected)
        if exam_id is not None:
            query = query.filter(ExamComponent.exam_id == exam_id)
        if component_id is not None:
            query = query.filter(ExamComponent.id == component_id)
        if "display_order" in columns:
            query = query.order_by(ExamComponent.display_order, ExamComponent.id)
        else:
            query = query.order_by(ExamComponent.id)
        records = []
        for row in query.all():
            records.append(ExamComponentRecord(
                id=row.id,
                exam_id=row.exam_id,
                name=row.name,
                max_marks=row.max_marks,
                code=getattr(row, "code", None),
                is_derived=getattr(row, "is_derived", False) or False,
                display_order=getattr(row, "display_order", 0) or 0,
                subject_id=getattr(row, "subject_id", None),
                entry_max=getattr(row, "entry_max", None),
            ))
        return records

    def update_component(self, component_id, name=None, max_marks=None, code=None, is_derived=None):
        with self.session_factory() as session:
            component = self.get_component_by_id(component_id)
            if component is None:
                return None
            if max_marks is not None:
                self._validate_max_marks(max_marks)
                if max_marks != component.max_marks:
                    mark_count = session.query(Mark.id).filter(Mark.component_id == component_id).count()
                    if mark_count:
                        raise ValueError("Cannot change maximum marks after marks have been recorded.")
            columns = {
                column["name"]
                for column in inspect(session.get_bind()).get_columns(ExamComponent.__tablename__)
            }
            if is_derived is not None and is_derived != component.is_derived:
                mark_count = session.query(Mark.id).filter(Mark.component_id == component_id).count()
                if mark_count:
                    raise ValueError("Cannot change a component's derived state after marks have been recorded.")
            values = {}
            if name:
                values["name"] = name
            if max_marks is not None:
                values["max_marks"] = max_marks
            if code is not None:
                if code and "code" not in columns:
                    raise ValueError("This database schema does not support component codes.")
                if "code" in columns:
                    values["code"] = code or None
            if is_derived:
                if "is_derived" not in columns:
                    raise ValueError("This database schema does not support derived components.")
                values["is_derived"] = True
            elif is_derived is not None and "is_derived" in columns:
                values["is_derived"] = False
            if values:
                session.execute(
                    update(ExamComponent.__table__)
                    .where(ExamComponent.id == component_id)
                    .values(**values)
                )
            session.commit()
            return self.get_component_by_id(component_id)

    @staticmethod
    def _validate_max_marks(max_marks):
        try:
            maximum = Decimal(str(max_marks))
        except (InvalidOperation, TypeError, ValueError) as error:
            raise ValueError("Maximum marks must be a valid number greater than zero.") from error
        if not maximum.is_finite() or maximum <= 0:
            raise ValueError("Maximum marks must be a finite number greater than zero.")

    def delete_component(self, component_id):
        with self.session_factory() as session:
            component = self.get_component_by_id(component_id)
            if component is None:
                return False
            mark_count = session.query(Mark.id).filter(Mark.component_id == component_id).count()
            if mark_count:
                return False
            session.execute(delete(ExamComponent.__table__).where(ExamComponent.id == component_id))
            session.commit()
            return True
