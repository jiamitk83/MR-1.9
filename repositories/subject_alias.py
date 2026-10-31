from models.database import SessionLocal
from models.audit import SubjectAlias
from models.database import Subject
from sqlalchemy import func

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

    def resolve_subject(self, name=None, code=None):
        """Resolve exact canonical names/codes and aliases without ambiguous matches."""
        normalized_name = name.strip().casefold() if name else None
        normalized_code = code.strip().casefold() if code else None
        if not normalized_name and not normalized_code:
            raise ValueError("Provide a subject name or code to resolve.")

        with self.session_factory() as session:
            candidate_sets = []
            if normalized_name:
                canonical_ids = session.query(Subject.id).filter(
                    func.lower(func.trim(Subject.name)) == normalized_name
                )
                alias_ids = session.query(SubjectAlias.subject_id).filter(
                    func.lower(func.trim(SubjectAlias.alias_name)) == normalized_name
                )
                candidate_sets.append({row[0] for row in canonical_ids.union(alias_ids).all()})
            if normalized_code:
                canonical_ids = session.query(Subject.id).filter(
                    func.lower(func.trim(Subject.code)) == normalized_code
                )
                alias_ids = session.query(SubjectAlias.subject_id).filter(
                    func.lower(func.trim(SubjectAlias.alias_code)) == normalized_code
                )
                candidate_sets.append({row[0] for row in canonical_ids.union(alias_ids).all()})

            subject_ids = set.intersection(*candidate_sets)
            if len(subject_ids) > 1:
                raise ValueError("The subject name or code matches multiple subjects.")
            if not subject_ids:
                return None
            return session.get(Subject, subject_ids.pop())

    def get_display_name(self, subject_id):
        """Return the explicitly primary alias or the canonical subject name."""
        with self.session_factory() as session:
            subject = session.get(Subject, subject_id)
            if subject is None:
                return None
            aliases = session.query(SubjectAlias).filter(
                SubjectAlias.subject_id == subject_id,
                SubjectAlias.is_primary.is_(True),
            ).all()
            if len(aliases) > 1:
                raise ValueError(f"Subject {subject_id} has multiple primary display aliases.")
            return aliases[0].alias_name if aliases else subject.name

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
