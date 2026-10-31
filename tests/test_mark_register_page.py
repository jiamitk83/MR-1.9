import csv

import pytest
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import AcademicSession, Base, Class, Section, Student, Subject
from models.examination import ExamComponent, Examination
from models.marks import Mark
from repositories.academic_setup import AcademicSetupRepository
from repositories.examination import ExamRepository
from repositories.mark import MarkRepository
from repositories.student import StudentRepository
from repositories.subject_alias import SubjectAliasRepository
from services.derived_calculations import DerivedCalculationService
from services.half_yearly import HalfYearlyService
from ui.mark_register_page import MarkRegisterPage


@pytest.fixture
def register_page(monkeypatch):
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
            Student(id=1, admission_number="ADM0001", roll_number=1, name="Student One",
                    session_id=1, class_id=1, section_id=1),
            Student(id=2, admission_number="ADM0002", roll_number=2, name="Student Two",
                    session_id=1, class_id=1, section_id=1),
            Student(id=3, admission_number="ADM0003", roll_number=3, name="Student Three",
                    session_id=1, class_id=1, section_id=1),
        ])
        session.add(Examination(id=1, name="PT1", session_id=1))
        session.flush()
        session.add(ExamComponent(id=1, exam_id=1, name="Written", max_marks=25))
        session.add_all([
            Mark(student_id=1, subject_id=1, component_id=1, marks_obtained=15.5, is_absent=False),
            Mark(student_id=2, subject_id=1, component_id=1, marks_obtained=None, is_absent=True),
        ])
        session.commit()

    def use_test_session(self):
        self.session_factory = test_session_factory

    monkeypatch.setattr(StudentRepository, "__init__", use_test_session)
    monkeypatch.setattr(ExamRepository, "__init__", use_test_session)
    monkeypatch.setattr(MarkRepository, "__init__", use_test_session)
    monkeypatch.setattr(AcademicSetupRepository, "__init__", use_test_session)
    monkeypatch.setattr(SubjectAliasRepository, "__init__", use_test_session)
    monkeypatch.setattr(
        DerivedCalculationService,
        "__init__",
        lambda self: setattr(self, "session_factory", test_session_factory),
    )
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *args: QMessageBox.Ok))
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *args: QMessageBox.Ok))
    monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *args: QMessageBox.Ok))

    app = QApplication.instance() or QApplication([])
    page = MarkRegisterPage()
    yield page, test_session_factory
    page.close()
    engine.dispose()
    del app


def test_register_uses_real_marks_and_distinguishes_pending_and_absent(register_page):
    page, _session_factory = register_page
    page.generate_register()

    assert page.table.rowCount() == 3
    total_column = 4 + len(page._components)
    assert page.table.item(0, 4).text() == "15.50"
    assert page.table.item(0, total_column).text() == "15.50"
    assert page.table.item(0, total_column + 1).text() == "62.00%"
    assert page.table.item(0, total_column + 2).text() == "B2"
    assert page.table.item(0, total_column + 3).text() == "Complete"
    assert page.table.item(1, total_column + 3).text() == "Absent"
    assert page.table.item(2, 4).text() == "Pending"
    assert page.table.item(2, total_column + 3).text() == "Pending"


def test_register_exports_utf8_csv(register_page, monkeypatch, tmp_path):
    page, _session_factory = register_page
    page.generate_register()
    page.table.item(0, 3).setText("=1+1, Student")
    output_path = tmp_path / "register.csv"
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        staticmethod(lambda *args: (str(output_path), "CSV files (*.csv)")),
    )

    page.export_csv()

    with output_path.open(encoding="utf-8-sig", newline="") as exported:
        rows = list(csv.reader(exported))
    assert rows[0] == page._headers
    assert rows[1][3] == "'=1+1, Student"
    assert rows[1][4] == "15.50"
    assert rows[1][-4] == "15.50"


def test_register_calculates_derived_periodic_marks(register_page):
    page, session_factory = register_page
    with session_factory() as session:
        session.add(ExamComponent(id=2, exam_id=1, name="PT1", max_marks=25))
        session.add(Mark(
            student_id=1, subject_id=1, component_id=2,
            marks_obtained=15.5, is_absent=False,
        ))
        session.add(Examination(id=2, name="Half Yearly", session_id=1))
        session.commit()
        subject = session.get(Subject, 1)
        template = HalfYearlyService.template_for_subject(subject)
    page.exam_repo.configure_subject_components(2, 1, template)

    page.exam_combo.addItem("Half Yearly", 2)
    page.exam_combo.setCurrentIndex(page.exam_combo.findData(2))
    page.generate_register()

    assert page.table.item(0, 4).text() == "3.10"
    status_column = len(page._headers) - 1
    assert page.table.item(0, status_column).text() == "Pending"
    assert page.table.item(1, status_column).text() == "Pending"


def test_half_yearly_register_uses_subject_specific_components(register_page):
    page, session_factory = register_page
    with session_factory() as session:
        exam = Examination(id=2, name="Half Yearly", session_id=1)
        session.add(exam)
        session.commit()
        subject = session.get(Subject, 1)
        template = HalfYearlyService.template_for_subject(subject)
    components = page.exam_repo.configure_subject_components(2, 1, template)
    with session_factory() as session:
        session.add_all([
            Mark(
                student_id=1, subject_id=1, component_id=components[1].id,
                marks_obtained=4, is_absent=False,
            ),
            Mark(
                student_id=1, subject_id=1, component_id=components[2].id,
                marks_obtained=5, is_absent=False,
            ),
            Mark(
                student_id=1, subject_id=1, component_id=components[3].id,
                marks_obtained=5, is_absent=False,
            ),
            Mark(
                student_id=1, subject_id=1, component_id=components[4].id,
                marks_obtained=70, is_absent=False,
            ),
        ])
        session.commit()

    page.exam_combo.addItem("Half Yearly", 2)
    page.exam_combo.setCurrentIndex(page.exam_combo.findData(2))
    page.generate_register()

    assert page.table.item(0, 4).text() == "3.10"
    result_column = 4 + len(components)
    assert page.table.item(0, result_column).text() == "87.10"
    assert page.table.item(0, result_column + 1).text() == "87.10%"
    assert page.table.item(0, result_column + 3).text() == "Complete"
