import csv
import logging
from decimal import Decimal
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from repositories.academic_setup import AcademicSetupRepository
from repositories.examination import ExamRepository
from repositories.mark import MarkRepository
from repositories.student import StudentRepository
from repositories.subject_alias import SubjectAliasRepository
from services.calculation import CalculationService
from services.derived_calculations import DerivedCalculationService
from services.csv_export import spreadsheet_safe
from services.half_yearly import HalfYearlyService


logger = logging.getLogger(__name__)


class MarkRegisterPage(QWidget):
    """Data-backed register for one session, exam, class, section, and subject."""

    def __init__(self):
        super().__init__()
        self.student_repo = StudentRepository()
        self.exam_repo = ExamRepository()
        self.mark_repo = MarkRepository()
        self.setup_repo = AcademicSetupRepository()
        self.alias_repo = SubjectAliasRepository()
        self.derived_service = DerivedCalculationService()
        self.half_yearly_service = HalfYearlyService(self.derived_service)
        self._components = []
        self._headers = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Mark Register"))

        selectors = QFormLayout()
        self.session_combo = QComboBox()
        self.exam_combo = QComboBox()
        self.class_combo = QComboBox()
        self.section_combo = QComboBox()
        self.subject_combo = QComboBox()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by student name, roll, admission, or father...")

        selectors.addRow("Academic Session:", self.session_combo)
        selectors.addRow("Exam:", self.exam_combo)
        selectors.addRow("Class:", self.class_combo)
        selectors.addRow("Section:", self.section_combo)
        selectors.addRow("Subject:", self.subject_combo)
        selectors.addRow("Search:", self.search_input)
        layout.addLayout(selectors)

        actions = QHBoxLayout()
        generate_button = QPushButton("Generate Register")
        generate_button.clicked.connect(self.generate_register)
        export_button = QPushButton("Export CSV")
        export_button.clicked.connect(self.export_csv)
        actions.addWidget(generate_button)
        actions.addWidget(export_button)
        actions.addStretch()
        layout.addLayout(actions)

        self.status_label = QLabel("Select filters, then generate the register.")
        layout.addWidget(self.status_label)

        self.table = QTableWidget()
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table)

        for academic_session in self.setup_repo.get_all_sessions():
            self.session_combo.addItem(academic_session.name, academic_session.id)
        self.session_combo.currentIndexChanged.connect(self._on_session_changed)
        self.class_combo.currentIndexChanged.connect(self._on_class_changed)
        self._on_session_changed(self.session_combo.currentIndex())

    def _on_session_changed(self, _index):
        session_id = self.session_combo.currentData()
        exams = self.exam_repo.get_exams(session_id=session_id) if session_id else []
        classes = self.setup_repo.get_all_classes() if session_id else []
        self.exam_combo.clear()
        for exam in exams:
            self.exam_combo.addItem(exam.name, exam.id)
        self.class_combo.clear()
        for cls in classes:
            self.class_combo.addItem(cls.name, cls.id)
        self.section_combo.clear()
        self.subject_combo.clear()
        self._load_subjects()
        self._clear_register()
        self._on_class_changed(self.class_combo.currentIndex())

    def _on_class_changed(self, _index):
        session_id = self.session_combo.currentData()
        class_id = self.class_combo.currentData()
        self.section_combo.clear()
        if session_id and class_id:
            for section in self.setup_repo.get_sections_by_class_and_session(class_id, session_id):
                self.section_combo.addItem(section.name, section.id)
        self._clear_register()

    def _load_subjects(self):
        for subject in self.setup_repo.get_all_subjects():
            display_name = self.alias_repo.get_display_name(subject.id)
            self.subject_combo.addItem(display_name or subject.name, subject.id)

    def _clear_register(self):
        self._components = []
        self._headers = []
        self.table.clear()
        self.table.setRowCount(0)
        self.table.setColumnCount(0)

    def generate_register(self):
        session_id = self.session_combo.currentData()
        exam_id = self.exam_combo.currentData()
        class_id = self.class_combo.currentData()
        section_id = self.section_combo.currentData()
        subject_id = self.subject_combo.currentData()
        if not all((session_id, exam_id, class_id, section_id, subject_id)):
            QMessageBox.warning(self, "Incomplete Selection", "Select all filters before generating the register.")
            return

        exam = self.exam_repo.get_exam_by_id(exam_id)
        subject = self.setup_repo.get_subject_by_id(subject_id)
        if exam is None or exam.session_id != session_id or subject is None:
            QMessageBox.warning(self, "Invalid Selection", "The selected exam or subject is no longer available.")
            return

        students = self.student_repo.get_students(
            session_id=session_id,
            class_id=class_id,
            section_id=section_id,
            keyword=self.search_input.text().strip() or None,
        )
        all_exam_components = self.exam_repo.get_components_by_exam(exam_id)
        subject_components = [
            component for component in all_exam_components
            if component.subject_id == subject_id
        ]
        if exam.name.strip().casefold() == "half yearly":
            self._generate_half_yearly_register(
                students,
                exam,
                subject,
                subject_components,
                [
                    component for component in all_exam_components
                    if component.subject_id is None
                ],
                session_id,
            )
            return

        self._components = self.exam_repo.get_components_by_exam(exam_id)
        if not self._components:
            QMessageBox.information(self, "No Components", "Configure exam components before generating the register.")
            self._clear_register()
            return

        student_ids = [student.id for student in students]
        marks_by_component = {}
        for component in self._components:
            marks = self.mark_repo.get_marks(
                subject_id=subject_id,
                component_id=component.id,
                student_ids=student_ids,
            )
            marks_by_component[component.id] = {mark.student_id: mark for mark in marks}

        grade_only = CalculationService.is_grade_only_subject(subject)
        self._headers = [
            "S. No.", "Roll No.", "Admission No.", "Student Name",
            *[component.name for component in self._components],
            "Total", "Percentage", "Grade", "Status",
        ]
        self.table.setSortingEnabled(False)
        self.table.clear()
        self.table.setColumnCount(len(self._headers))
        self.table.setHorizontalHeaderLabels(self._headers)
        self.table.setRowCount(len(students))

        for row, student in enumerate(students):
            self._set_cell(row, 0, str(row + 1))
            self._set_cell(row, 1, str(student.roll_number), student.id)
            self._set_cell(row, 2, student.admission_number)
            self._set_cell(row, 3, student.name)

            total_obtained = Decimal("0")
            total_maximum = Decimal("0")
            has_pending = False
            has_absent = False
            for index, component in enumerate(self._components, start=4):
                mark = marks_by_component[component.id].get(student.id)
                total_maximum += Decimal(str(component.max_marks))
                derived = None
                if (
                    component.is_derived
                    and component.name.casefold() == "pt1"
                    and exam.name.casefold() == "half yearly"
                ):
                    derived = self.derived_service.calculate_pt1_derived(
                        student.id, subject_id, session_id, target_exam_name=exam.name
                    )
                elif (
                    component.is_derived
                    and component.name.casefold() == "pt2"
                    and exam.name.casefold() == "annual"
                ):
                    derived = self.derived_service.calculate_pt2_derived(
                        student.id, subject_id, session_id, target_exam_name=exam.name
                    )

                if derived is not None and derived["status"] == "calculated":
                    obtained = Decimal(str(derived["marks"]))
                    self._set_cell(row, index, CalculationService.format_marks(obtained))
                    total_obtained += obtained
                elif derived is not None and derived["status"] == "absent":
                    self._set_cell(row, index, "Absent")
                    has_absent = True
                elif derived is not None or component.is_derived:
                    self._set_cell(row, index, "Pending")
                    has_pending = True
                elif mark is None or (mark.marks_obtained is None and not mark.is_absent):
                    self._set_cell(row, index, "Pending")
                    has_pending = True
                elif mark.is_absent:
                    self._set_cell(row, index, "Absent")
                    has_absent = True
                else:
                    self._set_cell(
                        row,
                        index,
                        CalculationService.format_marks(mark.marks_obtained),
                    )
                    total_obtained += Decimal(str(mark.marks_obtained))

            result_column = 4 + len(self._components)
            if grade_only:
                total, percentage, grade, status = "—", "—", "—", "Grade only"
            elif has_pending:
                total, percentage, grade, status = "—", "—", "—", "Pending"
            elif has_absent:
                total, percentage, grade, status = "—", "—", "—", "Absent"
            else:
                percentage_value = CalculationService.calculate_percentage(total_obtained, total_maximum)
                total = CalculationService.format_marks(total_obtained)
                percentage = f"{percentage_value:.2f}%"
                grade = CalculationService.get_grade(percentage_value)
                status = "Complete"
            self._set_cell(row, result_column, total)
            self._set_cell(row, result_column + 1, percentage)
            self._set_cell(row, result_column + 2, grade)
            self._set_cell(row, result_column + 3, status)
        pending_count = sum(
            1
            for row in range(self.table.rowCount())
            if self.table.item(row, len(self._headers) - 1).text() == "Pending"
        )

        self.table.setSortingEnabled(True)
        self.status_label.setText(
            f"{exam.name} — {subject.name}; {len(students)} student(s); "
            f"{pending_count} pending result(s)."
        )

    def _generate_half_yearly_register(
        self, students, exam, subject, components, legacy_components, session_id
    ):
        grade_only = HalfYearlyService.is_grade_only(subject)
        if not grade_only:
            try:
                HalfYearlyService.validate_components(subject, components)
            except ValueError as error:
                QMessageBox.warning(self, "Scheme Not Configured", str(error))
                self._clear_register()
                return
        student_ids = [student.id for student in students]
        if grade_only:
            grades = self.mark_repo.get_grade_marks(exam.id, subject.id, student_ids)
            grades_by_student = {record.student_id: record.grade for record in grades}
            self._headers = [
                "S. No.", "Roll No.", "Admission No.", "Student Name", "Grade", "Status",
            ]
        else:
            marks = self.mark_repo.get_marks_for_students(
                student_ids,
                subject_ids=[subject.id],
                component_ids=[
                    component.id
                    for component in components + legacy_components
                ],
            )
            marks_by_student = {}
            for mark in marks:
                marks_by_student.setdefault(mark.student_id, {})[
                    mark.component_id
                ] = mark
            self._headers = [
                "S. No.", "Roll No.", "Admission No.", "Student Name",
                *[
                    f"{component.name} ({CalculationService.format_marks(component.max_marks)})"
                    for component in components
                ],
                "Total", "Percentage", "Grade", "Status",
            ]

        self.table.setSortingEnabled(False)
        self.table.clear()
        self.table.setColumnCount(len(self._headers))
        self.table.setHorizontalHeaderLabels(self._headers)
        self.table.setRowCount(len(students))
        pending_count = 0
        for row, student in enumerate(students):
            self._set_cell(row, 0, str(row + 1))
            self._set_cell(row, 1, str(student.roll_number), student.id)
            self._set_cell(row, 2, student.admission_number)
            self._set_cell(row, 3, student.name)
            if grade_only:
                grade = grades_by_student.get(student.id)
                self._set_cell(row, 4, grade or "—")
                status = "Grade only" if grade else "Pending"
                self._set_cell(row, 5, status)
                pending_count += status == "Pending"
                continue
            student_marks = HalfYearlyService.map_legacy_component_marks(
                components,
                legacy_components,
                marks_by_student.get(student.id, {}),
            )
            result = self.half_yearly_service.calculate_subject_result(
                student, subject, session_id, components, student_marks
            )
            for index, result_component in enumerate(result["components"], start=4):
                obtained = result_component["marks"]
                cell_value = (
                    CalculationService.format_marks(obtained)
                    if obtained is not None
                    else result_component["status"].title()
                )
                self._set_cell(row, index, cell_value)
            result_column = 4 + len(components)
            total = (
                CalculationService.format_marks(result["total"])
                if result["total"] is not None else "—"
            )
            percentage = (
                f"{result['percentage']:.2f}%"
                if result["percentage"] is not None else "—"
            )
            self._set_cell(row, result_column, total)
            self._set_cell(row, result_column + 1, percentage)
            self._set_cell(row, result_column + 2, result["grade"] or "—")
            self._set_cell(row, result_column + 3, result["status"])
            pending_count += result["status"] == "Pending"
        self.table.setSortingEnabled(True)
        self.status_label.setText(
            f"{exam.name} — {subject.name}; {len(students)} student(s); "
            f"{pending_count} pending result(s)."
        )

    def _set_cell(self, row, column, value, student_id=None):
        item = QTableWidgetItem(str(value))
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        if student_id is not None:
            item.setData(Qt.UserRole, student_id)
        self.table.setItem(row, column, item)

    def export_csv(self):
        if self.table.rowCount() == 0 or not self._headers:
            QMessageBox.warning(self, "No Register", "Generate a register before exporting.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Mark Register",
            "mark_register.csv",
            "CSV files (*.csv)",
        )
        if not path:
            return
        output_path = Path(path)
        if output_path.exists():
            answer = QMessageBox.question(
                self,
                "Overwrite File",
                f"{output_path.name} already exists. Replace it?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
        try:
            with output_path.open("w", newline="", encoding="utf-8-sig") as output_file:
                writer = csv.writer(output_file)
                writer.writerow(self._headers)
                for row in range(self.table.rowCount()):
                    writer.writerow([
                        spreadsheet_safe(
                            self.table.item(row, column).text() if self.table.item(row, column) else ""
                        )
                        for column in range(self.table.columnCount())
                    ])
        except OSError:
            logger.exception("Could not export mark register")
            QMessageBox.critical(self, "Export Failed", "The CSV file could not be written.")
            return
        QMessageBox.information(self, "Export Complete", f"Mark register exported to {output_path}.")
