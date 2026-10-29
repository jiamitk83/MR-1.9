import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.database import Base
from models.examination import Examination, ExamComponent
from repositories.examination import ExamRepository

@pytest.fixture
def repo():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    repo = ExamRepository()
    repo.session_factory = Session
    return repo

def test_create_exam(repo):
    exam_id = repo.create_exam("Half Yearly", session_id=1)
    exams = repo.get_exams()
    assert len(exams) == 1
    assert exams[0].name == "Half Yearly"
    assert exams[0].id == exam_id

def test_add_component(repo):
    exam_id = repo.create_exam("Half Yearly", session_id=1)
    comp_id = repo.add_component(exam_id, "Written", 80.0)

    with repo.session_factory() as session:
        comp = session.query(ExamComponent).get(comp_id)
        assert comp.name == "Written"
        assert comp.max_marks == 80.0
