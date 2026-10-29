from models.database import SessionLocal
from models.audit import SubjectAlias

class SubjectAliasRepository:
    def __init__(self):
        self.session_factory = SessionLocal

    def add_alias(self, subject_id, alias_name, alias_code=None, is_primary=False):
        """Add a subject alias"""
        with self.session_factory() as session:
            # Check for duplicate
            existing = session.query(SubjectAlias).filter(
                SubjectAlias.subject_id == subject_id,
                SubjectAlias.alias_name == alias_name
            ).first()
            if existing:
                return None

            alias = SubjectAlias(
                subject_id=subject_id,
                alias_name=alias_name,
                alias_code=alias_code,
                is_primary=is_primary
            )
            session.add(alias)
            session.commit()
            return alias

    def get_alias_by_name(self, alias_name):
        """Find subject by alias name"""
        with self.session_factory() as session:
            alias = session.query(SubjectAlias).filter(
                SubjectAlias.alias_name == alias_name
            ).first()
            return alias.subject if alias else None

    def get_alias_by_code(self, alias_code):
        """Find subject by alias code"""
        with self.session_factory() as session:
            alias = session.query(SubjectAlias).filter(
                SubjectAlias.alias_code == alias_code
            ).first()
            return alias.subject if alias else None

    def get_aliases_for_subject(self, subject_id):
        """Get all aliases for a subject"""
        with self.session_factory() as session:
            return session.query(SubjectAlias).filter(
                SubjectAlias.subject_id == subject_id
            ).all()

    def get_primary_alias(self, subject_id):
        """Get the primary display alias for a subject"""
        with self.session_factory() as session:
            alias = session.query(SubjectAlias).filter(
                SubjectAlias.subject_id == subject_id,
                SubjectAlias.is_primary == True
            ).first()
            return alias if alias else None

    def delete_alias(self, alias_id):
        """Delete an alias"""
        with self.session_factory() as session:
            alias = session.query(SubjectAlias).filter(
                SubjectAlias.id == alias_id
            ).first()
            if alias:
                session.delete(alias)
                session.commit()
                return True
            return False
