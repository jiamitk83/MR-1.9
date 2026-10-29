from models.database import SessionLocal, AcademicSession, Class, Section, Subject

class AcademicSetupRepository:
    def __init__(self):
        self.session_factory = SessionLocal

    def add_session(self, name, start_date, end_date, is_active=False):
        with self.session_factory() as session:
            new_session = AcademicSession(name=name, start_date=start_date, end_date=end_date, is_active=is_active)
            session.add(new_session)
            session.commit()
            return new_session

    def get_all_sessions(self):
        with self.session_factory() as session:
            return session.query(AcademicSession).all()

    def add_class(self, name):
        with self.session_factory() as session:
            new_class = Class(name=name)
            session.add(new_class)
            session.commit()
            return new_class

    def get_all_classes(self):
        with self.session_factory() as session:
            return session.query(Class).all()
