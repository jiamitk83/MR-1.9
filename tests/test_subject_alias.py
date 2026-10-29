import pytest
from models.database import create_engine, Base, sessionmaker
from repositories.subject_alias import SubjectAliasRepository
from models.database import Subject

@pytest.fixture
def repo():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    repo = SubjectAliasRepository()
    repo.session_factory = Session
    return repo

def test_add_and_find_alias(repo):
    # First add a subject using the test session
    with repo.session_factory() as session:
        subject = Subject(name="Social Study", code="SST_TEST")
        session.add(subject)
        session.commit()
        subject_id = subject.id

    # Add alias
    result = repo.add_alias(subject_id=subject_id, alias_name="Social Science", alias_code="SOC", is_primary=True)
    assert result is not None

    # Find by name
    found_subject = repo.get_alias_by_name("Social Science")
    assert found_subject is not None
    assert found_subject.id == subject_id

    # Find by code
    found_subject = repo.get_alias_by_code("SOC")
    assert found_subject is not None
    assert found_subject.id == subject_id

def test_duplicate_alias_prevention(repo):
    with repo.session_factory() as session:
        subject = Subject(name="Math", code="MATH_TEST")
        session.add(subject)
        session.commit()
        subject_id = subject.id

    repo.add_alias(subject_id=subject_id, alias_name="Mathematics", is_primary=True)
    duplicate = repo.add_alias(subject_id=subject_id, alias_name="Mathematics", is_primary=False)
    assert duplicate is None  # Should prevent duplicate
