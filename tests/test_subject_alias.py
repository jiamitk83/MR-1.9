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

def test_sst_alias_resolves_to_existing_subject_identity(repo):
    with repo.session_factory() as session:
        subject = Subject(name="Social Study", code="SST")
        session.add(subject)
        session.commit()
        subject_id = subject.id

    repo.add_alias(
        subject_id=subject_id,
        alias_name="Social Science",
        alias_code="SOCSCI",
        is_primary=True,
    )

    by_code = repo.resolve_subject(code="sst")
    by_display_name = repo.resolve_subject(name="social science")
    by_both = repo.resolve_subject(name="Social Science", code="SST")

    assert by_code.id == subject_id
    assert by_display_name.id == subject_id
    assert by_both.id == subject_id
    assert repo.get_display_name(subject_id) == "Social Science"

def test_ambiguous_subject_alias_is_not_resolved(repo):
    with repo.session_factory() as session:
        first = Subject(name="Social Study", code="SST")
        second = Subject(name="Social Studies", code="SS")
        session.add_all([first, second])
        session.commit()
        first_id, second_id = first.id, second.id

    repo.add_alias(subject_id=first_id, alias_name="Social Science")
    repo.add_alias(subject_id=second_id, alias_name="Social Science")

    with pytest.raises(ValueError, match="multiple subjects"):
        repo.resolve_subject(name="Social Science")
