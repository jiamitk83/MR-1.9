import logging
from pathlib import Path

from openpyxl import Workbook
from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QObject,
    QRunnable,
    QThreadPool,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
)
from sqlalchemy.exc import SQLAlchemyError

from services.bulk_student_import import (
    EXPECTED_HEADERS,
    BulkStudentImportService,
    BulkStudentPreview,
)


logger = logging.getLogger(__name__)


class _TaskSignals(QObject):
    finished = Signal(int, object, object)


class _ImportTask(QRunnable):
    def __init__(self, request_id, operation):
        super().__init__()
        self.request_id = request_id
        self.operation = operation
        self.signals = _TaskSignals()

    def run(self):
        try:
            self.signals.finished.emit(self.request_id, self.operation(), None)
        except Exception as error:
            self.signals.finished.emit(self.request_id, None, error)


class _PreviewTableModel(QAbstractTableModel):
    HEADERS = ("S.No.", "Roll No.", "Student Name", "Status")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.preview = BulkStudentPreview(())

    def set_preview(self, preview):
        self.beginResetModel()
        self.preview = preview
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else self.preview.total_rows

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.HEADERS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self.preview.rows[index.row()]
        if role == Qt.DisplayRole:
            values = (
                str(index.row() + 1),
                str(row.roll_number) if row.roll_number is not None else "—",
                row.name or "—",
                "Valid" if row.is_valid else "Invalid: " + "; ".join(row.reasons),
            )
            return values[index.column()]
        if role == Qt.BackgroundRole and not row.is_valid:
            return QColor("#FCE8E6")
        if role == Qt.ForegroundRole and not row.is_valid:
            return QColor("#8B1E16")
        if role == Qt.ToolTipRole:
            return f"Excel row {row.excel_row}"
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.HEADERS[section]
        return None


class BulkStudentEntryDialog(QDialog):
    def __init__(self, setup_repository, student_repository, parent=None):
        super().__init__(parent)
        self.setup_repository = setup_repository
        self.student_repository = student_repository
        self.import_service = BulkStudentImportService(
            student_repository, setup_repository
        )
        self.thread_pool = QThreadPool.globalInstance()
        self._request_id = 0
        self._busy_operation = None
        self.preview = None
        self.selected_file = None
        self.imported_count = 0
        self._build_ui()
        self._load_active_sessions()
        self._update_controls()

    def _build_ui(self):
        self.setWindowTitle("Bulk Student Entry")
        self.resize(820, 620)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Import students from an Excel workbook containing only Roll No. and Student Name."
        ))

        selection_form = QFormLayout()
        self.session_combo = QComboBox()
        self.class_combo = QComboBox()
        self.section_combo = QComboBox()
        self.session_combo.addItem("Select academic session", None)
        self.class_combo.addItem("Select class", None)
        self.section_combo.addItem("Select section", None)
        selection_form.addRow("Academic Session:", self.session_combo)
        selection_form.addRow("Class:", self.class_combo)
        selection_form.addRow("Section:", self.section_combo)
        layout.addLayout(selection_form)

        file_row = QHBoxLayout()
        self.file_path = QLineEdit()
        self.file_path.setReadOnly(True)
        self.file_path.setPlaceholderText("No Excel workbook selected")
        self.browse_button = QPushButton("Browse Excel File")
        self.browse_button.clicked.connect(self._browse_file)
        self.template_button = QPushButton("Download Excel Template")
        self.template_button.clicked.connect(self._download_template)
        file_row.addWidget(self.file_path, 1)
        file_row.addWidget(self.browse_button)
        file_row.addWidget(self.template_button)
        layout.addLayout(file_row)

        self.summary_label = QLabel("Select a session, class, section, and workbook.")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        self.preview_model = _PreviewTableModel(self)
        self.preview_table = QTableView()
        self.preview_table.setModel(self.preview_model)
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.setSortingEnabled(False)
        self.preview_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.preview_table, 1)

        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.import_button = QPushButton("Import Students")
        self.import_button.clicked.connect(self._confirm_import)
        self.button_box = QDialogButtonBox(QDialogButtonBox.Cancel)
        self.button_box.rejected.connect(self.reject)
        footer = QHBoxLayout()
        footer.addWidget(self.import_button)
        footer.addStretch()
        footer.addWidget(self.button_box)
        layout.addLayout(footer)

        self.session_combo.currentIndexChanged.connect(self._on_session_changed)
        self.class_combo.currentIndexChanged.connect(self._on_class_changed)
        self.section_combo.currentIndexChanged.connect(self._on_context_changed)

    def _load_active_sessions(self):
        active_sessions = 0
        for academic_session in self.setup_repository.get_all_sessions():
            if academic_session.is_active:
                self.session_combo.addItem(academic_session.name, academic_session.id)
                active_sessions += 1
        if not active_sessions:
            self.status_label.setText(
                "No active academic session is configured. Mark the intended session active "
                "in Academic Setup before importing students."
            )

    def _on_session_changed(self, _index):
        self.class_combo.blockSignals(True)
        self.class_combo.clear()
        self.class_combo.addItem("Select class", None)
        self.section_combo.blockSignals(True)
        self.section_combo.clear()
        self.section_combo.addItem("Select section", None)
        session_id = self.session_combo.currentData()
        if session_id:
            for class_record in self.setup_repository.get_all_classes():
                sections = self.setup_repository.get_sections_by_class_and_session(
                    class_record.id, session_id
                )
                if sections:
                    self.class_combo.addItem(class_record.name, class_record.id)
        self.class_combo.blockSignals(False)
        self.section_combo.blockSignals(False)
        self._on_context_changed()

    def _on_class_changed(self, _index):
        self.section_combo.blockSignals(True)
        self.section_combo.clear()
        self.section_combo.addItem("Select section", None)
        session_id = self.session_combo.currentData()
        class_id = self.class_combo.currentData()
        if session_id and class_id:
            sections = self.setup_repository.get_sections_by_class_and_session(
                class_id, session_id
            )
            for section in sections:
                self.section_combo.addItem(section.name, section.id)
        self.section_combo.blockSignals(False)
        self._on_context_changed()

    def _context(self):
        return (
            self.session_combo.currentData(),
            self.class_combo.currentData(),
            self.section_combo.currentData(),
        )

    def _has_context(self):
        return all(self._context())

    def _on_context_changed(self, _index=None):
        if self._busy_operation == "import":
            return
        self._request_id += 1
        if self._busy_operation == "preview":
            self._busy_operation = None
        self.preview = None
        self.preview_model.set_preview(BulkStudentPreview(()))
        self.status_label.clear()
        self._update_controls()
        if self.selected_file and self._has_context() and self._busy_operation != "import":
            self._preview_selected_file()

    def _update_controls(self):
        context_ready = self._has_context()
        importing = self._busy_operation == "import"
        self.session_combo.setEnabled(not importing)
        self.class_combo.setEnabled(not importing)
        self.section_combo.setEnabled(not importing)
        self.browse_button.setEnabled(context_ready and self._busy_operation is None)
        self.template_button.setEnabled(self._busy_operation is None)
        valid_preview = bool(
            self.preview
            and self.preview.total_rows
            and not self.preview.invalid_rows
            and self._busy_operation is None
        )
        self.import_button.setEnabled(valid_preview)
        cancel_button = self.button_box.button(QDialogButtonBox.Cancel)
        if cancel_button:
            cancel_button.setEnabled(self._busy_operation != "import")

    def _browse_file(self):
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Select Student Excel Workbook",
            "",
            "Excel workbooks (*.xlsx);;All files (*)",
        )
        if not path:
            return
        self.selected_file = path
        self.file_path.setText(path)
        self._preview_selected_file()

    def _preview_selected_file(self):
        if not self._has_context() or not self.selected_file:
            self._update_controls()
            return
        self.preview = None
        self.preview_model.set_preview(BulkStudentPreview(()))
        self._busy_operation = "preview"
        self.status_label.setText("Reading and validating the workbook…")
        self._update_controls()
        context = self._context()
        file_path = self.selected_file
        self._start_task(
            lambda: self.import_service.preview_file(file_path, *context),
            "preview",
        )

    def _start_task(self, operation, kind):
        self._request_id += 1
        request_id = self._request_id
        self._busy_operation = kind
        worker = _ImportTask(request_id, operation)
        worker.signals.finished.connect(self._task_finished)
        self.thread_pool.start(worker)
        self._update_controls()

    def _task_finished(self, request_id, result, error):
        if request_id != self._request_id:
            return
        operation = self._busy_operation
        self._busy_operation = None
        if error is not None:
            if isinstance(error, (ValueError, FileNotFoundError)):
                self.status_label.setText(str(error))
                QMessageBox.warning(self, "Bulk Student Entry", str(error))
            else:
                logger.error(
                    "Bulk student %s failed",
                    operation,
                    exc_info=(type(error), error, error.__traceback__),
                )
                message = (
                    "The student batch could not be saved. No records were imported."
                    if operation == "import"
                    else "The workbook could not be read. Check the file and try again."
                )
                self.status_label.setText(message)
                QMessageBox.critical(self, "Bulk Student Entry", message)
            self._update_controls()
            return

        if operation == "preview":
            self.preview = result
            self.preview_model.set_preview(result)
            self._show_preview_summary(result)
        elif operation == "import":
            self.imported_count = len(result)
            self.accept()
            return
        self._update_controls()

    def _show_preview_summary(self, preview):
        self.summary_label.setText(
            f"Total rows: {preview.total_rows}  |  Valid: {len(preview.valid_rows)}"
            f"  |  Invalid: {len(preview.invalid_rows)}"
        )
        details = [
            f"Duplicate roll numbers: {preview.duplicate_roll_numbers}",
            f"Empty names: {preview.empty_names}",
            f"Invalid roll numbers: {preview.invalid_roll_numbers}",
        ]
        if preview.blank_rows_skipped:
            details.append(f"Blank rows skipped: {preview.blank_rows_skipped}")
        if preview.invalid_rows:
            details.append("Correct every invalid row; the batch cannot be imported yet.")
        else:
            details.append("All student rows are valid and ready to import.")
        self.status_label.setText("  |  ".join(details))

    def _confirm_import(self):
        if not self.preview or self.preview.invalid_rows or not self.preview.valid_rows:
            return
        session_id, class_id, section_id = self._context()
        session = self.setup_repository.get_session_by_id(session_id)
        class_record = self.setup_repository.get_class_by_id(class_id)
        section = self.setup_repository.get_section_by_id(section_id)
        roll_numbers = sorted(row.roll_number for row in self.preview.valid_rows)
        confirmation = (
            f"Academic Session: {session.name}\n"
            f"Class: {class_record.name}\n"
            f"Section: {section.name}\n"
            f"Total students to import: {len(roll_numbers)}\n"
            f"Starting roll number: {roll_numbers[0]}\n"
            f"Ending roll number: {roll_numbers[-1]}\n\n"
            "Import all students in one transaction?"
        )
        answer = QMessageBox.question(
            self,
            "Confirm Bulk Student Import",
            confirmation,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        preview = self.preview
        context = self._context()
        self.status_label.setText("Importing students…")
        self._start_task(
            lambda: self.import_service.import_preview(preview, *context),
            "import",
        )

    def _download_template(self):
        path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Download Student Excel Template",
            "student_import_template.xlsx",
            "Excel workbooks (*.xlsx)",
        )
        if not path:
            return
        output_path = Path(path)
        if output_path.suffix.casefold() != ".xlsx":
            output_path = output_path.with_suffix(".xlsx")
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Students"
        worksheet.append(EXPECTED_HEADERS)
        worksheet.append((1, "Rahul Sharma"))
        worksheet.append((2, "Priya Verma"))
        worksheet.append((3, "Amit Singh"))
        worksheet.append((4, "Neha Gupta"))
        worksheet.column_dimensions["A"].width = 14
        worksheet.column_dimensions["B"].width = 28
        try:
            workbook.save(output_path)
        except (OSError, PermissionError) as error:
            logger.exception("Could not save bulk student template")
            QMessageBox.critical(
                self, "Template Download Failed",
                f"The Excel template could not be saved to that location: {error}",
            )
            return
        QMessageBox.information(
            self, "Template Downloaded", f"Excel template saved to:\n{output_path}"
        )

    def reject(self):
        if self._busy_operation == "import":
            return
        self._request_id += 1
        super().reject()
