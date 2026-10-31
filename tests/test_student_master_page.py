import csv

import pytest
from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QMessageBox
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import AcademicSession, Base, Class, Section, Student
from repositories.academic_setup import AcademicSetupRepository
from repositories.student import StudentRepository
from ui import student_master_page
from ui.student_master_page import StudentDialog, StudentMasterPage


@pytest.fixture
def student_page(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    with session_factory() as session:
        session.add_all([
            AcademicSession(id=1, name="2026-2027"),
            Class(id=1, name="Grade 10"),
        ])
        session.flush()
        session.add(Section(id=1, name="A", class_id=1, session_id=1))
        session.add_all([
            Student(
                id=10, admission_number="ADM0010", roll_number=1, name="First",
                session_id=1, class_id=1, section_id=1,
            ),
            Student(
                id=20, admission_number="ADM0020", roll_number=2, name="Second",
                session_id=1, class_id=1, section_id=1,
            ),
        ])
        session.commit()

    def use_test_session(self):
        self.session_factory = session_factory

    monkeypatch.setattr(StudentRepository, "__init__", use_test_session)
    monkeypatch.setattr(AcademicSetupRepository, "__init__", use_test_session)
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *args: QMessageBox.Ok))
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *args: QMessageBox.Ok))
    app = QApplication.instance() or QApplication([])
    page = StudentMasterPage()
    yield page, session_factory
    page.close()
    engine.dispose()
    del app


def test_add_student_ui_uses_only_persisted_student_fields(student_page, monkeypatch):
    page, session_factory = student_page

    class AcceptedStudentDialog:
        def __init__(self, _parent):
            pass

        def exec(self):
            return QDialog.Accepted

        def get_values(self):
            return {
                "name": "Third",
                "roll_number": 3,
                "father_name": None,
                "mother_name": None,
                "date_of_birth": None,
                "address": "Third Street",
                "session_id": 1,
                "class_id": 1,
                "section_id": 1,
            }

    monkeypatch.setattr(student_master_page, "StudentDialog", AcceptedStudentDialog)
    page.add_student()

    with session_factory() as session:
        student = session.query(Student).filter_by(name="Third").one()
        assert student.address == "Third Street"


def test_student_dialog_captures_birth_date_and_address(student_page):
    _page, _session_factory = student_page

    dialog = StudentDialog(None)
    dialog.name_input.setText("Fourth")
    dialog.roll_input.setText("4")
    dialog.address_input.setText("24 Test Road")
    dialog.dob_checkbox.setChecked(True)
    dialog.dob_input.setDate(dialog.dob_input.date().fromString("09-02-2015", "dd-MM-yyyy"))

    values = dialog.get_values()

    assert values["date_of_birth"].isoformat() == "2015-02-09"
    assert values["address"] == "24 Test Road"
    dialog.close()


def test_student_dialog_populates_class_and_section_for_initial_session(student_page):
    _page, _session_factory = student_page

    dialog = StudentDialog(None)

    assert dialog.session_combo.currentText() == "2026-2027"
    assert dialog.class_combo.count() == 1
    assert dialog.class_combo.currentText() == "Grade 10"
    assert dialog.section_combo.count() == 1
    assert dialog.section_combo.currentText() == "A"
    dialog.close()


def test_edit_row_uses_student_primary_key_not_roll_number(student_page, monkeypatch):
    page, _session_factory = student_page
    fetched_ids = []
    get_student = page.student_repo.get_student_by_id

    def track_student_id(student_id):
        fetched_ids.append(student_id)
        return get_student(student_id)

    page.student_repo.get_student_by_id = track_student_id

    class CancelledStudentDialog:
        def __init__(self, _parent, student=None):
            assert student.id == 10

        def exec(self):
            return QDialog.Rejected

    monkeypatch.setattr(student_master_page, "StudentDialog", CancelledStudentDialog)
    page._edit_student_from_row(0)

    assert fetched_ids == [10]


def test_student_export_escapes_spreadsheet_formulas_and_quotes_fields(
    student_page, monkeypatch, tmp_path
):
    page, session_factory = student_page
    with session_factory() as session:
        student = session.query(Student).filter_by(id=10).one()
        student.name = '=HYPERLINK("https://example.invalid")'
        student.father_name = "Father, Sr"
        session.commit()

    output_path = tmp_path / "students.csv"
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        staticmethod(lambda *args: (str(output_path), "CSV files (*.csv)")),
    )

    page.export_csv()

    with output_path.open(encoding="utf-8-sig", newline="") as exported:
        rows = list(csv.reader(exported))
    assert rows[1][2] == '\'=HYPERLINK("https://example.invalid")'
    assert rows[1][3] == "Father, Sr"
