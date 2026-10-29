import pytest
from models.database import create_engine, Base, sessionmaker
from repositories.student import StudentRepository

@pytest.fixture
def repo():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    repo = StudentRepository()
    repo.session_factory = Session
    return repo

def test_add_student(repo):
    student = repo.add_student(name="John Doe", roll_number=1, father_name="Richard Doe")
    students = repo.get_students()
    assert len(students) == 1
    assert students[0].name == "John Doe"
    assert students[0].admission_number == "ADM0001"

def test_generate_admission_number(repo):
    repo.add_student(name="Student 1", roll_number=1)
    adm2 = repo.generate_admission_number()
    assert adm2 == "ADM0002"
