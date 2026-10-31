from models.database import SessionLocal, AcademicSession, Class, Section, Subject
from models.database import Student
from models.examination import Examination
from models.marks import Mark
from models.audit import SubjectAlias
from sqlalchemy import and_

class AcademicSetupRepository:
    def __init__(self):
        self.session_factory = SessionLocal

    # ========== Sessions ==========
    def add_session(self, name, start_date=None, end_date=None, is_active=False):
        name = name.strip() if name else name
        with self.session_factory() as session:
            # Check for duplicate session name
            existing_session = session.query(AcademicSession).filter(AcademicSession.name == name).first()
            if existing_session:
                return None

            # Validate date consistency
            if start_date and end_date and start_date > end_date:
                raise ValueError("Start date must be before or equal to end date.")

            new_session = AcademicSession(name=name, start_date=start_date, end_date=end_date, is_active=is_active)
            session.add(new_session)
            session.commit()
            session.refresh(new_session)
            return new_session

    def get_all_sessions(self):
        with self.session_factory() as session:
            return session.query(AcademicSession).all()

    def get_session_by_id(self, session_id):
        with self.session_factory() as session:
            return session.query(AcademicSession).filter(AcademicSession.id == session_id).first()

    def update_session(self, session_id, name=None, start_date=None, end_date=None, is_active=None):
        with self.session_factory() as session:
            session_record = session.query(AcademicSession).filter(AcademicSession.id == session_id).first()
            if not session_record:
                return None
            if name is not None:
                name = name.strip()
            if name:
                duplicate = session.query(AcademicSession).filter(
                    AcademicSession.name == name, AcademicSession.id != session_id
                ).first()
                if duplicate:
                    raise ValueError("Session with this name already exists.")
            new_start = start_date or session_record.start_date
            new_end = end_date or session_record.end_date
            if new_start and new_end and new_start > new_end:
                raise ValueError("Start date must be before or equal to end date.")
            if name:
                session_record.name = name
            if start_date:
                session_record.start_date = start_date
            if end_date:
                session_record.end_date = end_date
            if is_active is not None:
                session_record.is_active = is_active
            session.commit()
            session.refresh(session_record)
            return session_record

    def delete_session(self, session_id):
        with self.session_factory() as session:
            session_record = session.query(AcademicSession).filter(AcademicSession.id == session_id).first()
            if session_record:
                if (
                    session.query(Section.id).filter(Section.session_id == session_id).first()
                    or session.query(Student.id).filter(Student.session_id == session_id).first()
                    or session.query(Examination.id).filter(Examination.session_id == session_id).first()
                ):
                    return False
                session.delete(session_record)
                session.commit()
                return True
            return False

    def search_sessions(self, keyword=None, is_active=None):
        with self.session_factory() as session:
            query = session.query(AcademicSession)
            if keyword:
                query = query.filter(AcademicSession.name.contains(keyword))
            if is_active is not None:
                query = query.filter(AcademicSession.is_active == is_active)
            return query.all()

    # ========== Classes ==========
    def add_class(self, name):
        with self.session_factory() as session:
            # Check for duplicate class name
            existing_class = session.query(Class).filter(Class.name == name).first()
            if existing_class:
                raise ValueError("Class name already exists.")

            new_class = Class(name=name)
            session.add(new_class)
            session.commit()
            return new_class

    def get_all_classes(self):
        with self.session_factory() as session:
            return session.query(Class).all()

    def get_class_by_id(self, class_id):
        with self.session_factory() as session:
            return session.query(Class).filter(Class.id == class_id).first()

    def update_class(self, class_id, name):
        with self.session_factory() as session:
            class_record = session.query(Class).filter(Class.id == class_id).first()
            if not class_record:
                return None
            class_record.name = name
            session.commit()
            return class_record

    def delete_class(self, class_id):
        with self.session_factory() as session:
            class_record = session.query(Class).filter(Class.id == class_id).first()
            if class_record:
                if (
                    session.query(Section.id).filter(Section.class_id == class_id).first()
                    or session.query(Student.id).filter(Student.class_id == class_id).first()
                ):
                    return False
                session.delete(class_record)
                session.commit()
                return True
            return False

    # ========== Sections ==========
    def add_section(self, name, class_id, session_id):
        with self.session_factory() as session:
            existing = session.query(Section).filter(
                and_(Section.name == name, Section.class_id == class_id, Section.session_id == session_id)
            ).first()
            if existing:
                return None
            new_section = Section(name=name, class_id=class_id, session_id=session_id)
            session.add(new_section)
            session.commit()
            return new_section

    def get_sections_by_class_and_session(self, class_id, session_id):
        with self.session_factory() as session:
            return session.query(Section).filter(
                and_(Section.class_id == class_id, Section.session_id == session_id)
            ).all()

    def get_section_by_id(self, section_id):
        with self.session_factory() as session:
            return session.query(Section).filter(Section.id == section_id).first()

    def update_section(self, section_id, name=None, class_id=None, session_id=None):
        with self.session_factory() as session:
            section_record = session.query(Section).filter(Section.id == section_id).first()
            if not section_record:
                return None
            if name:
                section_record.name = name
            if class_id is not None:
                section_record.class_id = class_id
            if session_id is not None:
                section_record.session_id = session_id
            session.commit()
            return section_record

    def delete_section(self, section_id):
        with self.session_factory() as session:
            section_record = session.query(Section).filter(Section.id == section_id).first()
            if section_record:
                if session.query(Student.id).filter(Student.section_id == section_id).first():
                    return False
                session.delete(section_record)
                session.commit()
                return True
            return False

    # ========== Subjects ==========
    def add_subject(self, name, code=None, is_active=True):
        with self.session_factory() as session:
            existing = session.query(Subject).filter(Subject.name == name).first()
            if existing:
                return None
            if code:
                existing_code = session.query(Subject).filter(Subject.code == code).first()
                if existing_code:
                    return None
            new_subject = Subject(name=name, code=code, is_active=is_active)
            session.add(new_subject)
            session.commit()
            return new_subject

    def get_all_subjects(self):
        with self.session_factory() as session:
            return session.query(Subject).all()

    def get_subject_by_id(self, subject_id):
        with self.session_factory() as session:
            return session.query(Subject).filter(Subject.id == subject_id).first()

    def update_subject(self, subject_id, name=None, code=None, is_active=None):
        with self.session_factory() as session:
            subject = session.query(Subject).filter(Subject.id == subject_id).first()
            if not subject:
                return None
            if name:
                subject.name = name
            if code is not None:
                if code != subject.code:
                    existing = session.query(Subject).filter(Subject.code == code, Subject.id != subject_id).first()
                    if existing:
                        return None
                subject.code = code if code else None
            if is_active is not None:
                subject.is_active = is_active
            session.commit()
            return subject

    def delete_subject(self, subject_id):
        with self.session_factory() as session:
            subject = session.query(Subject).filter(Subject.id == subject_id).first()
            if subject:
                if (
                    session.query(Mark.id).filter(Mark.subject_id == subject_id).first()
                    or session.query(SubjectAlias.id).filter(SubjectAlias.subject_id == subject_id).first()
                ):
                    return False
                session.delete(subject)
                session.commit()
                return True
            return False

    def search_subjects(self, keyword=None):
        with self.session_factory() as session:
            query = session.query(Subject)
            if keyword:
                query = query.filter(Subject.name.contains(keyword) | Subject.code.contains(keyword))
            return query.all()
