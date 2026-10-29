import pytest
from models.database import create_engine, Base, sessionmaker
from repositories.academic_setup import AcademicSetupRepository

@pytest.fixture
def repo():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    repo = AcademicSetupRepository()
    repo.session_factory = Session
    return repo

def test_add_session(repo):
    repo.add_session(name="2026-2027", start_date=None, end_date=None)
    sessions = repo.get_all_sessions()
    assert len(sessions) == 1
    assert sessions[0].name == "2026-2027"

def test_add_class(repo):
    repo.add_class(name="Grade 10")
    classes = repo.get_all_classes()
    assert len(classes) == 1
    assert classes[0].name == "Grade 10"
