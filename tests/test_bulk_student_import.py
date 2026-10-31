import time

import pytest
from openpyxl import Workbook, load_workbook
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QMessageBox
from sqlalchemy import create_engine, event
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models.database import AcademicSession, Base, Class, Section, Student
from repositories.academic_setup import AcademicSetupRepository
from repositories.student import StudentRepository
from services.bulk_student_import import BulkStudentImportService
from ui import student_master_page
from ui.bulk_student_entry_dialog import BulkStudentEntryDialog
from ui.student_master_page import StudentMasterPage


@pytest.fixture
def bulk_context(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    with session_factory() as session:
        session.add_all([
            AcademicSession(id=1, name="2026-2027", is_active=True),
            AcademicSession(id=2, name="2025-2026", is_active=False),
            Class(id=1, name="Grade 10"),
            Class(id=2, name="Grade 9"),
        ])
        session.flush()
        session.add_all([
            Section(id=1, name="A", class_id=1, session_id=1),
            Section(id=2, name="B", class_id=1, session_id=1),
            Section(id=3, name="A", class_id=2, session_id=1),
            Section(id=4, name="A", class_id=1, session_id=2),
        ])
        session.add(Student(
            id=10, admission_number="ADM0001", roll_number=1, name="Existing",
            session_id=1, class_id=1, section_id=1,
        ))
        session.commit()

    student_repository = StudentRepository()
    student_repository.session_factory = session_factory
    setup_repository = AcademicSetupRepository()
    setup_repository.session_factory = session_factory
    service = BulkStudentImportService(student_repository, setup_repository)
    monkeypatch.setattr(
        StudentRepository, "__init__",
        lambda self: setattr(self, "session_factory", session_factory),
    )
    monkeypatch.setattr(
        AcademicSetupRepository, "__init__",
        lambda self: setattr(self, "session_factory", session_factory),
    )
    monkeypatch.setattr(
        QMessageBox, "information", staticmethod(lambda *args: QMessageBox.Ok)
    )
    monkeypatch.setattr(
        QMessageBox, "warning", staticmethod(lambda *args: QMessageBox.Ok)
    )
    monkeypatch.setattr(
        QMessageBox, "critical", staticmethod(lambda *args: QMessageBox.Ok)
    )
    app = QApplication.instance() or QApplication([])
    yield service, student_repository, setup_repository, session_factory, engine, app
    engine.dispose()
    del app


def make_workbook(path, rows, headers=("Roll No.", "Student Name")):
    workbook = Workbook()
    worksheet = workbook.active
    if headers is not None:
        worksheet.append(headers)
    for row in rows:
        worksheet.append(row)
    workbook.save(path)
    return path


def test_valid_batch_assigns_context_generates_admission_numbers_and_preserves_existing(
    bulk_context, tmp_path
):
    service, _student_repo, _setup_repo, session_factory, _engine, _app = bulk_context
    file_path = make_workbook(
        tmp_path / "students.xlsx",
        [(2, "  Rahul Sharma  "), (None, None), (3, "张伟")],
    )

    preview = service.preview_file(file_path, 1, 1, 1)
    imported = service.import_preview(preview, 1, 1, 1)

    assert len(imported) == 2
    with session_factory() as session:
        students = session.query(Student).order_by(Student.roll_number).all()
        assert [(s.roll_number, s.name) for s in students] == [
            (1, "Existing"), (2, "Rahul Sharma"), (3, "张伟"),
        ]
        assert [s.admission_number for s in students] == [
            "ADM0001", "ADM0002", "ADM0003",
        ]
        assert all(
            (s.session_id, s.class_id, s.section_id) == (1, 1, 1)
            for s in students
        )
        assert all(s.father_name is None and s.mother_name is None for s in students)
    assert preview.blank_rows_skipped == 1
    assert preview.total_rows == 2


def test_duplicate_roll_numbers_inside_workbook_block_entire_import(
    bulk_context, tmp_path
):
    service, _student_repo, _setup_repo, session_factory, *_ = bulk_context
    path = make_workbook(
        tmp_path / "duplicates.xlsx",
        [(2, "First"), (2, "Second")],
    )

    preview = service.preview_file(path, 1, 1, 1)

    assert preview.duplicate_roll_numbers == 2
    assert len(preview.invalid_rows) == 2
    with pytest.raises(ValueError, match="invalid rows"):
        service.import_preview(preview, 1, 1, 1)
    with session_factory() as session:
        assert session.query(Student).count() == 1


def test_duplicate_roll_number_in_selected_section_blocks_import(
    bulk_context, tmp_path
):
    service, _student_repo, _setup_repo, session_factory, *_ = bulk_context
    path = make_workbook(tmp_path / "existing.xlsx", [(1, "Duplicate")])

    preview = service.preview_file(path, 1, 1, 1)

    assert len(preview.invalid_rows) == 1
    assert "already exists in the selected section" in preview.rows[0].reasons
    assert preview.duplicate_roll_numbers == 1
    with pytest.raises(ValueError, match="invalid rows"):
        service.import_preview(preview, 1, 1, 1)
    with session_factory() as session:
        assert session.query(Student).count() == 1


def test_same_roll_number_in_a_different_section_is_allowed(bulk_context, tmp_path):
    service, _student_repo, _setup_repo, _session_factory, *_ = bulk_context
    path = make_workbook(tmp_path / "other_section.xlsx", [(1, "Other Section")])

    preview = service.preview_file(path, 1, 1, 2)

    assert len(preview.valid_rows) == 1


def test_empty_student_name_is_reported_and_blocks_import(bulk_context, tmp_path):
    service, _student_repo, _setup_repo, session_factory, *_ = bulk_context
    path = make_workbook(tmp_path / "empty_name.xlsx", [(2, "  ")])

    preview = service.preview_file(path, 1, 1, 1)

    assert preview.empty_names == 1
    assert "student name is required" in preview.rows[0].reasons
    with pytest.raises(ValueError, match="invalid rows"):
        service.import_preview(preview, 1, 1, 1)
    with session_factory() as session:
        assert session.query(Student).count() == 1


@pytest.mark.parametrize("roll_number", [0, -2, "abc", 1.5, True, None])
def test_invalid_roll_numbers_are_reported(bulk_context, tmp_path, roll_number):
    service, *_ = bulk_context
    path = make_workbook(
        tmp_path / f"invalid_roll_{str(roll_number)}.xlsx",
        [(roll_number, "Student")],
    )

    preview = service.preview_file(path, 1, 1, 1)

    assert preview.invalid_roll_numbers == 1
    assert not preview.valid_rows


def test_missing_or_misnamed_columns_have_a_meaningful_error(bulk_context, tmp_path):
    service, *_ = bulk_context
    path = make_workbook(
        tmp_path / "wrong_headers.xlsx",
        [(1, "Student")],
        headers=("Roll Number", "Name"),
    )

    with pytest.raises(ValueError, match="exactly these columns"):
        service.preview_file(path, 1, 1, 1)


def test_empty_workbook_has_a_meaningful_validation_error(bulk_context, tmp_path):
    service, *_ = bulk_context
    path = make_workbook(tmp_path / "empty.xlsx", [], headers=None)

    with pytest.raises(ValueError, match="first row must contain"):
        service.preview_file(path, 1, 1, 1)


def test_corrupt_workbook_has_a_meaningful_error(bulk_context, tmp_path):
    service, *_ = bulk_context
    path = tmp_path / "corrupt.xlsx"
    path.write_bytes(b"not an Excel workbook")

    with pytest.raises(ValueError, match="not a readable"):
        service.preview_file(path, 1, 1, 1)


def test_missing_file_and_unsupported_xls_are_reported(bulk_context, tmp_path):
    service, *_ = bulk_context

    with pytest.raises(ValueError, match="\\.xlsx"):
        service.preview_file(tmp_path / "old.xls", 1, 1, 1)
    with pytest.raises(FileNotFoundError, match="missing.xlsx"):
        service.preview_file(tmp_path / "missing.xlsx", 1, 1, 1)


def test_data_outside_the_two_required_columns_is_rejected(bulk_context, tmp_path):
    service, *_ = bulk_context
    path = make_workbook(
        tmp_path / "extra_data.xlsx",
        [(2, "Student", "unexpected field")],
    )

    with pytest.raises(ValueError, match="outside the two required columns"):
        service.preview_file(path, 1, 1, 1)


def test_admission_number_failure_rolls_back_the_entire_batch(
    bulk_context, tmp_path
):
    service, _student_repository, _setup_repo, session_factory, *_ = bulk_context
    path = make_workbook(
        tmp_path / "rollback.xlsx",
        [(2, "First"), (3, "Second")],
    )
    preview = service.preview_file(path, 1, 1, 1)

    def fail_on_second_insert(_mapper, _connection, student):
        if student.name == "Second":
            raise RuntimeError("second student insert failed")

    event.listen(Student, "before_insert", fail_on_second_insert)
    try:
        with pytest.raises(RuntimeError, match="second student insert failed"):
            service.import_preview(preview, 1, 1, 1)
    finally:
        event.remove(Student, "before_insert", fail_on_second_insert)
    with session_factory() as session:
        students = session.query(Student).order_by(Student.id).all()
        assert [(s.id, s.admission_number, s.name) for s in students] == [
            (10, "ADM0001", "Existing")
        ]


def test_import_rejects_context_with_inactive_session(bulk_context, tmp_path):
    service, *_ = bulk_context
    path = make_workbook(tmp_path / "inactive.xlsx", [(2, "Student")])

    with pytest.raises(ValueError, match="active academic session"):
        service.preview_file(path, 2, 1, 4)


def test_template_download_contains_exact_two_columns_and_examples(
    bulk_context, tmp_path, monkeypatch
):
    _service, student_repository, setup_repository, *_ = bulk_context
    output_path = tmp_path / "template.xlsx"
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        staticmethod(lambda *args: (str(output_path), "Excel workbooks (*.xlsx)")),
    )

    dialog = BulkStudentEntryDialog(setup_repository, student_repository)
    dialog._download_template()

    workbook = load_workbook(output_path, read_only=True, data_only=True)
    worksheet = workbook.active
    rows = list(worksheet.iter_rows(values_only=True))
    workbook.close()
    assert rows[0] == ("Roll No.", "Student Name")
    assert rows[1:] == [
        (1, "Rahul Sharma"),
        (2, "Priya Verma"),
        (3, "Amit Singh"),
        (4, "Neha Gupta"),
    ]
    assert dialog.session_combo.count() == 3
    assert dialog.session_combo.itemData(1) == 1
    assert dialog.session_combo.itemText(1) == "2026-2027"
    assert dialog.session_combo.itemData(2) == 2
    assert dialog.session_combo.itemText(2) == "2025-2026 (Inactive)"
    assert not dialog.session_combo.model().item(2).isEnabled()
    assert dialog.session_combo.currentData() is None
    dialog.close()


def test_dialog_loads_sessions_when_opened_and_cascades_class_and_section(
    bulk_context,
):
    _service, student_repository, setup_repository, _session_factory, _engine, app = (
        bulk_context
    )
    dialog = BulkStudentEntryDialog(setup_repository, student_repository)
    dialog.show()
    app.processEvents()

    assert dialog.session_combo.itemText(1) == "2026-2027"
    assert dialog.session_combo.itemData(1) == 1
    assert dialog.session_combo.currentData() is None

    dialog.session_combo.setCurrentIndex(dialog.session_combo.findData(1))
    assert [
        (dialog.class_combo.itemText(index), dialog.class_combo.itemData(index))
        for index in range(1, dialog.class_combo.count())
    ] == [("Grade 10", 1), ("Grade 9", 2)]

    dialog.class_combo.setCurrentIndex(dialog.class_combo.findData(1))
    assert [
        (dialog.section_combo.itemText(index), dialog.section_combo.itemData(index))
        for index in range(1, dialog.section_combo.count())
    ] == [("A", 1), ("B", 2)]
    dialog.close()


def test_no_active_sessions_are_shown_disabled_with_actionable_message(
    bulk_context,
):
    _service, student_repository, setup_repository, session_factory, _engine, _app = (
        bulk_context
    )
    with session_factory() as session:
        for academic_session in session.query(AcademicSession).all():
            academic_session.is_active = False
        session.commit()

    dialog = BulkStudentEntryDialog(setup_repository, student_repository)

    assert dialog.session_combo.currentData() is None
    assert dialog.session_combo.itemText(1) == "2026-2027 (Inactive)"
    assert dialog.session_combo.itemText(2) == "2025-2026 (Inactive)"
    assert not dialog.session_combo.model().item(1).isEnabled()
    assert not dialog.session_combo.model().item(2).isEnabled()
    assert "No active academic session" in dialog.status_label.text()
    assert "Academic Setup" in dialog.status_label.text()
    dialog.close()


def test_empty_session_list_shows_configuration_message(bulk_context, monkeypatch):
    _service, student_repository, setup_repository, *_ = bulk_context
    monkeypatch.setattr(setup_repository, "get_all_sessions", lambda: [])

    dialog = BulkStudentEntryDialog(setup_repository, student_repository)

    assert dialog.session_combo.count() == 1
    assert "No academic sessions are configured" in dialog.status_label.text()
    assert "Academic Setup" in dialog.status_label.text()
    dialog.close()


def test_session_database_error_is_logged_and_shown_to_user(
    bulk_context, monkeypatch, caplog
):
    _service, student_repository, setup_repository, *_ = bulk_context

    def fail_to_load_sessions():
        raise SQLAlchemyError("database unavailable")

    monkeypatch.setattr(setup_repository, "get_all_sessions", fail_to_load_sessions)
    dialog = BulkStudentEntryDialog(setup_repository, student_repository)

    assert dialog.session_combo.count() == 1
    assert "could not be loaded" in dialog.status_label.text()
    assert "Academic Setup" not in dialog.status_label.text()
    assert "Could not load academic sessions" in caplog.text
    dialog.close()


def test_bulk_entry_dialog_previews_confirms_and_imports_asynchronously(
    bulk_context, tmp_path, monkeypatch
):
    _service, student_repository, setup_repository, session_factory, _engine, app = bulk_context
    workbook_path = make_workbook(
        tmp_path / "async_students.xlsx",
        [(2, "  Rahul Sharma  "), (3, "Zoë 李")],
    )
    monkeypatch.setattr(
        QMessageBox, "question", staticmethod(lambda *args: QMessageBox.Yes)
    )
    dialog = BulkStudentEntryDialog(setup_repository, student_repository)
    dialog.session_combo.setCurrentIndex(dialog.session_combo.findData(1))
    dialog.class_combo.setCurrentIndex(dialog.class_combo.findData(1))
    dialog.section_combo.setCurrentIndex(dialog.section_combo.findData(1))
    dialog.selected_file = str(workbook_path)
    dialog.file_path.setText(str(workbook_path))
    dialog._preview_selected_file()

    deadline = time.monotonic() + 10
    while dialog._busy_operation and time.monotonic() < deadline:
        app.processEvents()
        QTest.qWait(10)
    app.processEvents()

    assert dialog.preview is not None
    assert len(dialog.preview.valid_rows) == 2
    assert dialog.import_button.isEnabled()
    dialog._confirm_import()

    deadline = time.monotonic() + 10
    while dialog._busy_operation and time.monotonic() < deadline:
        app.processEvents()
        QTest.qWait(10)
    app.processEvents()

    assert dialog.result() == QDialog.Accepted
    assert dialog.imported_count == 2
    with session_factory() as session:
        imported = session.query(Student).filter(
            Student.roll_number.in_((2, 3))
        ).order_by(Student.roll_number).all()
        assert [(student.roll_number, student.name) for student in imported] == [
            (2, "Rahul Sharma"),
            (3, "Zoë 李"),
        ]
    dialog.close()


def test_master_refreshes_imported_students_with_context_and_roll_order(
    bulk_context, monkeypatch
):
    _service, _student_repository, _setup_repository, session_factory, _engine, _app = bulk_context

    class AcceptedBulkDialog:
        def __init__(self, _setup, _students, parent=None):
            self.session_combo = type("Combo", (), {"currentData": lambda self: 1})()
            self.class_combo = type("Combo", (), {"currentData": lambda self: 1})()
            self.section_combo = type("Combo", (), {"currentData": lambda self: 1})()
            self.imported_count = 2

        def exec(self):
            with session_factory() as session:
                session.add_all([
                    Student(
                        admission_number="ADM0002", roll_number=7, name="Later",
                        session_id=1, class_id=1, section_id=1,
                    ),
                    Student(
                        admission_number="ADM0003", roll_number=3, name="Earlier",
                        session_id=1, class_id=1, section_id=1,
                    ),
                ])
                session.commit()
            return QDialog.Accepted

    monkeypatch.setattr(student_master_page, "BulkStudentEntryDialog", AcceptedBulkDialog)
    page = StudentMasterPage()

    page.bulk_student_entry()

    assert page.session_combo.currentData() == 1
    assert page.class_combo.currentData() == 1
    assert page.section_combo.currentData() == 1
    assert [
        int(page.table.item(row, 0).text())
        for row in range(page.table.rowCount())
    ] == [1, 3, 7]
    page.close()
