import pytest
from services.calculation import CalculationService
from repositories.mark import MarkRepository
from models.database import create_engine, Base, sessionmaker
from models.marks import Mark

def test_calculation_formatting():
    assert CalculationService.format_marks(15) == "15.00"
    assert CalculationService.format_marks(12.5) == "12.50"
    assert CalculationService.format_marks(4.789) == "4.79" # rounding check

def test_calculation_percentage():
    pct = CalculationService.calculate_percentage(45, 50)
    assert pct == 90.00

def test_calculation_grades():
    assert CalculationService.get_grade(95) == "A1"
    assert CalculationService.get_grade(85) == "A2"
    assert CalculationService.get_grade(32) == "E"

def test_derived_pt_marks():
    derived = CalculationService.derive_pt_marks(15, 25) # 15/25 -> 3.00/5
    assert derived == 3.00

@pytest.fixture
def repo():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    repo = MarkRepository()
    repo.session_factory = Session
    return repo

def test_save_marks_batch(repo):
    success = repo.save_marks_batch([
        {
            'student_id': 1,
            'subject_id': 1,
            'component_id': 1,
            'marks_obtained': 15.5,
            'is_absent': False
        }
    ])
    assert success is True
    marks = repo.get_marks(subject_id=1, component_id=1)
    assert len(marks) == 1
    assert float(marks[0].marks_obtained) == 15.5
