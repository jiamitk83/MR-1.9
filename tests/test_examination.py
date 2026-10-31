import pytest
from PySide6.QtWidgets import QApplication
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.database import Base
from models.examination import Examination, ExamComponent
from models.database import AcademicSession, Class, Student, Subject
from repositories.examination import ExamRepository
from repositories.mark import MarkRepository
from ui.examination_page import ComponentDialog
from sqlalchemy import text

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


def test_add_component_requires_positive_maximum(repo):
    exam_id = repo.create_exam("Half Yearly", session_id=1)
    with pytest.raises(ValueError, match="greater than zero"):
        repo.add_component(exam_id, "Written", 0)
    with pytest.raises(ValueError, match="greater than zero"):
        repo.add_component(exam_id, "Written", float("nan"))


def test_component_dialog_exposes_derived_state_and_positive_maximum():
    app = QApplication.instance() or QApplication([])
    dialog = ComponentDialog(current_name="PT1", max_marks=5, is_derived=True)

    assert dialog.get_values() == ("PT1", 5.0, None, True)
    assert dialog.max_marks.minimum() > 0
    dialog.close()
    del app

def test_legacy_component_schema_is_supported_without_migration():
    engine = create_engine("sqlite:///:memory:")
    legacy_tables = [
        table for table in Base.metadata.sorted_tables
        if table.name not in {"exam_components", "marks"}
    ]
    Base.metadata.create_all(engine, tables=legacy_tables)
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE exam_components ("
            "id INTEGER PRIMARY KEY, exam_id INTEGER NOT NULL, "
            "name VARCHAR NOT NULL, max_marks FLOAT NOT NULL)"
        ))
        connection.execute(text(
            "CREATE TABLE marks ("
            "id INTEGER PRIMARY KEY, student_id INTEGER NOT NULL, "
            "subject_id INTEGER NOT NULL, component_id INTEGER NOT NULL, "
            "marks_obtained NUMERIC(5, 2), is_absent BOOLEAN)"
        ))
    Session = sessionmaker(bind=engine)
    with Session() as session:
        session.add_all([
            AcademicSession(id=1, name="2026-2027"),
            Class(id=1, name="Grade 10"),
            Subject(id=1, name="Mathematics", code="MATH"),
        ])
        session.flush()
        session.add(Student(
            id=1, admission_number="ADM0001", roll_number=1, name="Student",
            session_id=1, class_id=1,
        ))
        session.add(Examination(id=1, name="PT1", session_id=1))
        session.commit()

    repo = ExamRepository()
    repo.session_factory = Session
    component_id = repo.add_component(1, "Written", 25)
    component = repo.get_component_by_id(component_id)
    assert component.name == "Written"
    assert component.is_derived is False
    assert component.code is None
    with pytest.raises(ValueError, match="does not support component codes"):
        repo.add_component(1, "Coded", 10, code="CODE")
    with pytest.raises(ValueError, match="does not support derived components"):
        repo.add_component(1, "Derived", 5, is_derived=True)

    mark_repo = MarkRepository()
    mark_repo.session_factory = Session
    mark_repo.save_marks_batch([{
        "student_id": 1,
        "subject_id": 1,
        "component_id": component_id,
        "marks_obtained": 12.5,
        "is_absent": False,
    }])
    assert repo.delete_component(component_id) is False
    engine.dispose()
