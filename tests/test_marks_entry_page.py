import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import (
    AcademicSession,
    Base,
    Class,
    Section,
    Student,
    Subject,
)
from models.audit import ExamLock
from models.examination import ExamComponent, Examination
from models.marks import Mark
from repositories.academic_setup import AcademicSetupRepository
from repositories.examination import ExamRepository
from repositories.mark import MarkRepository
from repositories.student import StudentRepository
from services.derived_calculations import DerivedCalculationService
from services.half_yearly import HalfYearlyService
from ui.marks_entry_page import MarksEntryPage


@pytest.fixture
def marks_page(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    test_session_factory = sessionmaker(bind=engine)
    with test_session_factory() as session:
        session.add_all([
            AcademicSession(id=1, name="2026-2027"),
            Class(id=1, name="Grade 10"),
            Subject(id=1, name="Mathematics", code="MATH"),
        ])
        session.flush()
        session.add(Section(id=1, name="A", class_id=1, session_id=1))
        session.add_all([
            Student(
                id=1,
                admission_number="ADM0001",
                roll_number=1,
                name="Student One",
                session_id=1,
                class_id=1,
                section_id=1,
            ),
            Student(
                id=2,
                admission_number="ADM0002",
                roll_number=2,
                name="Student Two",
                session_id=1,
                class_id=1,
                section_id=1,
            ),
        ])
        session.add_all([
            Examination(id=1, name="PT1", session_id=1),
            Examination(id=2, name="Half Yearly", session_id=1),
            Examination(id=3, name="Annual", session_id=1),
        ])
        session.flush()
        session.add_all([
            ExamComponent(id=1, exam_id=1, name="Written", max_marks=25),
            ExamComponent(id=2, exam_id=1, name="PT1", max_marks=25),
            ExamComponent(id=3, exam_id=2, name="PT1", max_marks=5, is_derived=True),
        ])
        session.add(Mark(
            student_id=1,
            subject_id=1,
            component_id=2,
            marks_obtained=15,
            is_absent=False,
        ))
        session.commit()

    def use_test_session(self):
        self.session_factory = test_session_factory

    monkeypatch.setattr(StudentRepository, "__init__", use_test_session)
    monkeypatch.setattr(ExamRepository, "__init__", use_test_session)
    monkeypatch.setattr(MarkRepository, "__init__", use_test_session)
    monkeypatch.setattr(AcademicSetupRepository, "__init__", use_test_session)
    monkeypatch.setattr(
        DerivedCalculationService,
        "__init__",
        lambda self: setattr(self, "session_factory", test_session_factory),
    )
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *args: QMessageBox.Ok))
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *args: QMessageBox.Ok))
    monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *args: QMessageBox.Ok))

    app = QApplication.instance() or QApplication([])
    page = MarksEntryPage()
    yield page, test_session_factory
    page.close()
    engine.dispose()
    del app


def test_marks_grid_saves_correct_students_after_sorting(marks_page):
    page, session_factory = marks_page
    page.load_students_grid()
    assert page.table.rowCount() == 2

    page.table.sortItems(MarksEntryPage.ROLL_COLUMN, Qt.DescendingOrder)
    assert page.table.item(0, MarksEntryPage.NAME_COLUMN).text() == "Student Two"
    assert page.table.item(0, MarksEntryPage.ROLL_COLUMN).data(Qt.UserRole) == 2
    assert page.table.item(1, MarksEntryPage.ROLL_COLUMN).data(Qt.UserRole) == 1
    page.table.item(0, MarksEntryPage.MARKS_COLUMN).setText("12.50")
    page.table.item(1, MarksEntryPage.MARKS_COLUMN).setText("20")
    assert page._dirty_student_ids == {1, 2}
    page.save_marks()

    with session_factory() as session:
        marks = {
            mark.student_id: mark.marks_obtained
            for mark in session.query(Mark).filter_by(component_id=1).all()
        }
    assert marks == {1: 20, 2: 12.5}


def test_half_yearly_grid_shows_derived_pt1_and_saves_subject_components(marks_page):
    page, session_factory = marks_page
    with session_factory() as session:
        subject = session.get(Subject, 1)
        template = HalfYearlyService.template_for_subject(subject)
    components = page.exam_repo.configure_subject_components(2, 1, template)

    page.exam_combo.setCurrentIndex(page.exam_combo.findData(2))
    page.subject_combo.setCurrentIndex(page.subject_combo.findData(1))
    assert page._half_yearly_mode is True
    assert page.component_combo.isHidden()
    page.load_students_grid()

    assert page.table.columnCount() == 17
    assert page.table.item(0, 5).text() == "3.00"
    assert not (page.table.item(0, 5).flags() & Qt.ItemIsEditable)
    for column, value in ((7, "4"), (9, "5"), (11, "5"), (13, "70")):
        page.table.item(0, column).setText(value)
    assert page.table.item(0, 15).text() == "87.00"
    assert page.table.item(0, 16).text() == "Complete"
    page.save_marks()

    with session_factory() as session:
        saved = session.query(Mark).filter_by(
            student_id=1,
            subject_id=1,
            component_id=components[1].id,
        ).one()
        assert saved.marks_obtained == 4


def test_half_yearly_grade_only_grid_saves_assigned_grade(marks_page):
    page, session_factory = marks_page
    with session_factory() as session:
        session.add(Subject(id=2, name="General Knowledge", code="GK"))
        session.commit()
    page.subject_combo.addItem("General Knowledge", 2)
    page.exam_combo.setCurrentIndex(page.exam_combo.findData(2))
    page.subject_combo.setCurrentIndex(page.subject_combo.findData(2))
    assert page._grade_only_mode is True
    page.load_students_grid()
    assert page.table.columnCount() == 7
    page.table.item(0, 5).setText("A1")
    page.save_marks()

    from models.grade_mark import GradeMark

    with session_factory() as session:
        record = session.query(GradeMark).filter_by(
            student_id=1, subject_id=2, exam_id=2
        ).one()
        assert record.grade == "A1"


def test_marks_grid_rejects_invalid_batch_without_saving(marks_page):
    page, session_factory = marks_page
    page.load_students_grid()
    page.table.item(0, MarksEntryPage.MARKS_COLUMN).setText("10")
    page.table.item(1, MarksEntryPage.MARKS_COLUMN).setText("26")
    page.save_marks()

    with session_factory() as session:
        assert session.query(Mark).filter_by(component_id=1).count() == 0


def test_locked_exam_cannot_save_marks(marks_page):
    page, session_factory = marks_page
    with session_factory() as session:
        session.add(ExamLock(exam_id=1, is_locked=True))
        session.commit()
    page.load_students_grid()
    page.table.item(0, MarksEntryPage.MARKS_COLUMN).setText("10")
    page.save_marks()

    with session_factory() as session:
        assert session.query(Mark).filter_by(component_id=1).count() == 0


def test_derived_half_yearly_component_is_read_only_and_shows_pt1_value(marks_page):
    page, session_factory = marks_page
    with session_factory() as session:
        template = HalfYearlyService.template_for_subject(session.get(Subject, 1))
    page.exam_repo.configure_subject_components(2, 1, template)
    page.exam_combo.setCurrentIndex(page.exam_combo.findData(2))
    page.load_students_grid()

    assert page.table.item(0, 5).text() == "3.00"
    assert page.table.item(0, 6).text() == "Calculated"
    assert page.table.item(1, 6).text() == "Pending"
    assert not (page.table.item(0, 5).flags() & Qt.ItemIsEditable)


def test_exam_without_components_explains_where_to_configure_them(marks_page):
    page, _session_factory = marks_page

    page.exam_combo.setCurrentIndex(page.exam_combo.findData(3))

    assert page.component_combo.count() == 0
    assert not page.component_combo.isEnabled()
    assert "No components are configured for Annual" in page.component_info.text()
    assert "Examination" in page.component_info.text()
    assert not page.save_button.isEnabled()
