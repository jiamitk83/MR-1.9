import logging
from decimal import Decimal, InvalidOperation
from types import SimpleNamespace

from PySide6.QtCore import QRegularExpression, QSignalBlocker, Qt
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStyledItemDelegate,
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
from services.calculation import CalculationService
from services.derived_calculations import DerivedCalculationService
from services.half_yearly import HalfYearlyService


logger = logging.getLogger(__name__)


class HalfYearlyMarksDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        editor.setValidator(QRegularExpressionValidator(
            QRegularExpression(r"^(?:\d{0,4}(?:\.\d{0,2})?|[Aa][Bb])$"),
            editor,
        ))
        return editor


class MarksEntryPage(QWidget):
    """Marks entry grid backed by the selected session, exam, and subject."""

    SERIAL_COLUMN = 0
    ROLL_COLUMN = 1
    NAME_COLUMN = 2
    FATHER_COLUMN = 3
    ADMISSION_COLUMN = 4
    MARKS_COLUMN = 5
    MAX_MARKS_COLUMN = 6
    STATUS_COLUMN = 7

    def __init__(self):
        super().__init__()
        self.student_repo = StudentRepository()
        self.exam_repo = ExamRepository()
        self.mark_repo = MarkRepository()
        self.setup_repo = AcademicSetupRepository()
        self.derived_service = DerivedCalculationService()
        self.student_rows = []
        self._loading_grid = False
        self._dirty = False
        self._dirty_student_ids = set()
        self._dirty_cells = set()
        self._half_yearly_mode = False
        self._grade_only_mode = False
        self._current_components = []
        self._legacy_components = []
        self._dynamic_column_components = {}
        self._last_filter_data = {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Marks Entry"))

        filter_group = QGroupBox("Select Filters")
        filter_layout = QFormLayout(filter_group)
        self.session_combo = QComboBox()
        self.exam_combo = QComboBox()
        self.class_combo = QComboBox()
        self.section_combo = QComboBox()
        self.subject_combo = QComboBox()
        self.component_combo = QComboBox()

        filter_layout.addRow("Academic Session:", self.session_combo)
        filter_layout.addRow("Exam:", self.exam_combo)
        filter_layout.addRow("Class:", self.class_combo)
        filter_layout.addRow("Section:", self.section_combo)
        filter_layout.addRow("Subject:", self.subject_combo)
        self.component_label = QLabel("Component:")
        filter_layout.addRow(self.component_label, self.component_combo)
        layout.addWidget(filter_group)

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by student name, roll, admission, or father...")
        self.search_input.returnPressed.connect(self.load_students_grid)
        load_button = QPushButton("Load Students")
        load_button.clicked.connect(self.load_students_grid)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(load_button)
        layout.addLayout(search_layout)

        self.component_info = QLabel("Select a session, exam, class, section, subject, and component.")
        layout.addWidget(self.component_info)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "S. No.", "Roll No.", "Student Name", "Father's Name",
            "Admission No.", "Marks Obtained", "Maximum", "Status",
        ])
        self.table.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed)
        self.table.setSortingEnabled(True)
        self.table.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.table)

        action_layout = QHBoxLayout()
        self.edit_mode_checkbox = QCheckBox("Edit marks")
        self.edit_mode_checkbox.setChecked(True)
        self.edit_mode_checkbox.stateChanged.connect(self._toggle_edit_mode)
        self.save_button = QPushButton("Save Marks")
        self.save_button.clicked.connect(self.save_marks)
        action_layout.addWidget(self.edit_mode_checkbox)
        action_layout.addStretch()
        action_layout.addWidget(self.save_button)
        layout.addLayout(action_layout)

        self.session_combo.currentIndexChanged.connect(self._on_session_changed)
        self.exam_combo.currentIndexChanged.connect(self._on_exam_changed)
        self.class_combo.currentIndexChanged.connect(self._on_class_changed)
        self.section_combo.currentIndexChanged.connect(self._on_section_changed)
        self.subject_combo.currentIndexChanged.connect(self._on_subject_changed)
        self.component_combo.currentIndexChanged.connect(self._on_component_changed)

        for academic_session in self.setup_repo.get_all_sessions():
            self.session_combo.addItem(academic_session.name, academic_session.id)
        self._on_session_changed(self.session_combo.currentIndex())

    def _confirm_filter_change(self, name, combo):
        current_data = combo.currentData()
        previous_data = self._last_filter_data.get(name)
        if name in self._last_filter_data and current_data != previous_data and self._dirty:
            answer = QMessageBox.question(
                self,
                "Unsaved Marks",
                "Discard unsaved mark changes and change the selected filter?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                with QSignalBlocker(combo):
                    combo.setCurrentIndex(combo.findData(previous_data))
                return False
            self._clear_loaded_grid()
        self._last_filter_data[name] = current_data
        return True

    def _replace_combo_items(self, name, combo, items):
        with QSignalBlocker(combo):
            combo.clear()
            for label, item_data in items:
                combo.addItem(label, item_data)
        self._last_filter_data[name] = combo.currentData()

    def _clear_loaded_grid(self):
        self._loading_grid = True
        self.table.setRowCount(0)
        self.student_rows = []
        self._loading_grid = False
        self._dirty = False
        self._dirty_student_ids.clear()
        self._dirty_cells.clear()

    def _on_session_changed(self, _index):
        if not self._confirm_filter_change("session", self.session_combo):
            return
        self._clear_loaded_grid()
        session_id = self.session_combo.currentData()
        exams = self.exam_repo.get_exams(session_id=session_id) if session_id else []
        classes = self.setup_repo.get_all_classes() if session_id else []
        self._replace_combo_items("exam", self.exam_combo, [(exam.name, exam.id) for exam in exams])
        self._replace_combo_items("class", self.class_combo, [(cls.name, cls.id) for cls in classes])
        self._replace_combo_items("section", self.section_combo, [])
        self._replace_combo_items("subject", self.subject_combo, [])
        self._replace_combo_items("component", self.component_combo, [])
        self._on_exam_changed(self.exam_combo.currentIndex())
        self._on_class_changed(self.class_combo.currentIndex())

    def _on_exam_changed(self, _index):
        if not self._confirm_filter_change("exam", self.exam_combo):
            return
        self._clear_loaded_grid()
        subjects = self.setup_repo.get_all_subjects() if self.exam_combo.currentData() else []
        self._replace_combo_items("subject", self.subject_combo, [(subject.name, subject.id) for subject in subjects])
        self._replace_combo_items("component", self.component_combo, [])
        self._on_subject_changed(self.subject_combo.currentIndex())

    def _on_class_changed(self, _index):
        if not self._confirm_filter_change("class", self.class_combo):
            return
        self._clear_loaded_grid()
        session_id = self.session_combo.currentData()
        class_id = self.class_combo.currentData()
        sections = (
            self.setup_repo.get_sections_by_class_and_session(class_id, session_id)
            if session_id and class_id else []
        )
        self._replace_combo_items("section", self.section_combo, [(section.name, section.id) for section in sections])

    def _on_section_changed(self, _index):
        if self._confirm_filter_change("section", self.section_combo):
            self._clear_loaded_grid()

    def _on_subject_changed(self, _index):
        if not self._confirm_filter_change("subject", self.subject_combo):
            return
        self._clear_loaded_grid()
        exam_id = self.exam_combo.currentData()
        subject_id = self.subject_combo.currentData()
        exam = self.exam_repo.get_exam_by_id(exam_id) if exam_id else None
        subject = self.setup_repo.get_subject_by_id(subject_id) if subject_id else None
        all_components = self.exam_repo.get_components_by_exam(exam_id) if exam_id else []
        subject_components = [
            item for item in all_components if item.subject_id == subject_id
        ]
        self._legacy_components = [
            item for item in all_components if item.subject_id is None
        ]
        self._grade_only_mode = bool(
            exam and exam.name.strip().casefold() == "half yearly"
            and subject and HalfYearlyService.is_grade_only(subject)
        )
        self._half_yearly_mode = bool(
            exam and exam.name.strip().casefold() == "half yearly" and subject
        )
        self._current_components = subject_components if self._half_yearly_mode else []
        self._dynamic_column_components = {}
        self.component_label.setVisible(not self._half_yearly_mode)
        self.component_combo.setVisible(not self._half_yearly_mode)
        if self._half_yearly_mode:
            self._replace_combo_items("component", self.component_combo, [])
            self.component_combo.setEnabled(False)
            self._last_filter_data["component"] = None
            self.edit_mode_checkbox.setEnabled(True)
            self.save_button.setEnabled(self._grade_only_mode or bool(subject_components))
            if self._grade_only_mode:
                self.component_info.setText(
                    f"{subject.name} is grade-only. Enter its grade; no numeric marks or components are used."
                )
            elif subject_components:
                try:
                    HalfYearlyService.validate_components(subject, subject_components)
                    self.component_info.setText(
                        f"{subject.name} — enter all configured Half Yearly components in one grid."
                    )
                except ValueError as error:
                    self.component_info.setText(f"Scheme configuration required: {error}")
                    self.save_button.setEnabled(False)
            else:
                self.component_info.setText(
                    f"{subject.name} has no Half Yearly subject scheme. "
                    "Configure it in Examination before entering marks."
                )
            return

        self._grade_only_mode = False
        self._current_components = []
        components = self.exam_repo.get_components_for_subject(exam_id, subject_id) if exam_id and subject_id else []
        self._replace_combo_items(
            "component",
            self.component_combo,
            [(component.name, component.id) for component in components],
        )
        self.component_combo.setEnabled(bool(components))
        self._on_component_changed(self.component_combo.currentIndex())

    def _on_component_changed(self, _index):
        if not self._confirm_filter_change("component", self.component_combo):
            return
        self._clear_loaded_grid()
        component_id = self.component_combo.currentData()
        component = self.exam_repo.get_component_by_id(component_id) if component_id else None
        if component is None:
            exam = self.exam_repo.get_exam_by_id(self.exam_combo.currentData()) if self.exam_combo.currentData() else None
            if exam is not None:
                self.component_info.setText(
                    f"No components are configured for {exam.name}. "
                    "Go to Examination, select this exam, then choose Add Component."
                )
            else:
                self.component_info.setText(
                    "Select a session, exam, class, section, subject, and component."
                )
            self.edit_mode_checkbox.setEnabled(False)
            self.save_button.setEnabled(False)
            return
        suffix = " (derived; read-only)" if component.is_derived else ""
        self.component_info.setText(
            f"{component.name}{suffix} — maximum {CalculationService.format_marks(component.max_marks)}"
        )
        self.edit_mode_checkbox.setEnabled(not component.is_derived)
        self.save_button.setEnabled(not component.is_derived)
        self._toggle_edit_mode(self.edit_mode_checkbox.checkState())

    def _toggle_edit_mode(self, state):
        editable = state == Qt.Checked
        if self._half_yearly_mode:
            for column, component_key in self._dynamic_column_components.items():
                for row in range(self.table.rowCount()):
                    item = self.table.item(row, column)
                    if item is None:
                        continue
                    is_derived = (
                        isinstance(component_key, int)
                        and any(
                            component.id == component_key and component.is_derived
                            for component in self._current_components
                        )
                    )
                    flags = item.flags()
                    item.setFlags(
                        flags | Qt.ItemIsEditable
                        if editable and not is_derived
                        else flags & ~Qt.ItemIsEditable
                    )
            return
        component_id = self.component_combo.currentData()
        component = self.exam_repo.get_component_by_id(component_id) if component_id else None
        editable = editable and component is not None and not component.is_derived
        for row in range(self.table.rowCount()):
            item = self.table.item(row, self.MARKS_COLUMN)
            if item is not None:
                flags = item.flags() | Qt.ItemIsEditable if editable else item.flags() & ~Qt.ItemIsEditable
                item.setFlags(flags)

    def _on_item_changed(self, item):
        if self._loading_grid:
            return
        if self._half_yearly_mode:
            if item.column() not in self._dynamic_column_components:
                return
            component_key = self._dynamic_column_components[item.column()]
            if isinstance(component_key, int):
                status_column = item.column() + 1
                value = item.text().strip()
                status = (
                    "Absent" if value.upper() == "AB"
                    else "Entered" if value
                    else "Not Entered"
                )
                status_item = self.table.item(item.row(), status_column)
                if status_item is not None:
                    self._loading_grid = True
                    status_item.setText(status)
                    self._loading_grid = False
            else:
                value = item.text().strip()
                status_item = self.table.item(item.row(), item.column() + 1)
                if status_item is not None:
                    self._loading_grid = True
                    status_item.setText("Entered" if value else "Not Entered")
                    self._loading_grid = False
            self._dirty = True
            roll_item = self.table.item(item.row(), self.ROLL_COLUMN)
            student_id = roll_item.data(Qt.UserRole) if roll_item is not None else None
            if student_id is not None:
                self._dirty_student_ids.add(student_id)
                self._dirty_cells.add((student_id, component_key))
            self._refresh_half_yearly_summary(item.row())
            return
        if item.column() != self.MARKS_COLUMN:
            return
        self._dirty = True
        roll_item = self.table.item(item.row(), self.ROLL_COLUMN)
        if roll_item is not None:
            self._dirty_student_ids.add(roll_item.data(Qt.UserRole))
        value = item.text().strip()
        if value.upper() == "AB":
            status = "Absent"
        elif value:
            status = "Entered"
        else:
            status = "Not Entered"
        status_item = self.table.item(item.row(), self.STATUS_COLUMN)
        if status_item is not None:
            self._loading_grid = True
            status_item.setText(status)
            self._loading_grid = False

    def load_students_grid(self):
        if self._dirty:
            answer = QMessageBox.question(
                self,
                "Unsaved Marks",
                "Discard unsaved mark changes and reload students?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
        session_id = self.session_combo.currentData()
        exam_id = self.exam_combo.currentData()
        class_id = self.class_combo.currentData()
        section_id = self.section_combo.currentData()
        subject_id = self.subject_combo.currentData()
        component_id = self.component_combo.currentData()
        if not all((session_id, exam_id, class_id, section_id, subject_id)) or (
            not self._half_yearly_mode and not component_id
        ):
            QMessageBox.warning(self, "Incomplete Selection", "Select all filters before loading students.")
            return

        if self._half_yearly_mode:
            self._load_half_yearly_grid(
                session_id, exam_id, class_id, section_id, subject_id
            )
            return

        component = self.exam_repo.get_component_by_id(component_id)
        if component is None or component.exam_id != exam_id:
            QMessageBox.warning(self, "Invalid Selection", "The selected component does not belong to this exam.")
            return
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "S. No.", "Roll No.", "Student Name", "Father's Name",
            "Admission No.", "Marks Obtained", "Maximum", "Status",
        ])
        exam = self.exam_repo.get_exam_by_id(exam_id)
        if exam is None or exam.session_id != session_id:
            QMessageBox.warning(self, "Invalid Selection", "The selected exam does not belong to this session.")
            return

        students = self.student_repo.get_students(
            session_id=session_id,
            class_id=class_id,
            section_id=section_id,
            keyword=self.search_input.text().strip() or None,
        )
        marks = self.mark_repo.get_marks(
            subject_id=subject_id,
            component_id=component_id,
            student_ids=[student.id for student in students],
        )
        marks_by_student = {mark.student_id: mark for mark in marks}
        maximum = CalculationService.format_marks(component.max_marks)

        self._loading_grid = True
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(students))
        self.student_rows = students
        for row, student in enumerate(students):
            serial_item = QTableWidgetItem(str(row + 1))
            serial_item.setFlags(serial_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, self.SERIAL_COLUMN, serial_item)

            roll_item = QTableWidgetItem(str(student.roll_number))
            roll_item.setData(Qt.UserRole, student.id)
            roll_item.setFlags(roll_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, self.ROLL_COLUMN, roll_item)

            for column, value in (
                (self.NAME_COLUMN, student.name),
                (self.FATHER_COLUMN, student.father_name or ""),
                (self.ADMISSION_COLUMN, student.admission_number),
            ):
                cell = QTableWidgetItem(value)
                cell.setFlags(cell.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, column, cell)

            mark = marks_by_student.get(student.id)
            if (
                component.is_derived
                and component.name.casefold() == "pt1"
                and exam.name.casefold() == "half yearly"
            ):
                derived = self.derived_service.calculate_pt1_derived(
                    student.id, subject_id, session_id, target_exam_name=exam.name
                )
                if derived["status"] == "calculated":
                    mark_text, status = CalculationService.format_marks(derived["marks"]), "Calculated"
                elif derived["status"] == "absent":
                    mark_text, status = "AB", "Absent"
                else:
                    mark_text, status = "", "Pending"
            elif (
                component.is_derived
                and component.name.casefold() == "pt2"
                and exam.name.casefold() == "annual"
            ):
                derived = self.derived_service.calculate_pt2_derived(
                    student.id, subject_id, session_id, target_exam_name=exam.name
                )
                if derived["status"] == "calculated":
                    mark_text, status = CalculationService.format_marks(derived["marks"]), "Calculated"
                elif derived["status"] == "absent":
                    mark_text, status = "AB", "Absent"
                else:
                    mark_text, status = "", "Pending"
            elif component.is_derived:
                mark_text, status = "", "Pending"
            elif mark is None:
                mark_text, status = "", "Not Entered"
            elif mark.is_absent:
                mark_text, status = "AB", "Absent"
            elif mark.marks_obtained is None:
                mark_text, status = "", "Pending"
            else:
                mark_text = CalculationService.format_marks(mark.marks_obtained)
                status = "Entered"
            mark_item = QTableWidgetItem(mark_text)
            if component.is_derived or not self.edit_mode_checkbox.isChecked():
                mark_item.setFlags(mark_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, self.MARKS_COLUMN, mark_item)

            for column, value in ((self.MAX_MARKS_COLUMN, maximum), (self.STATUS_COLUMN, status)):
                cell = QTableWidgetItem(value)
                cell.setFlags(cell.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, column, cell)

        self.table.setSortingEnabled(True)
        self._loading_grid = False
        self._dirty = False
        if not students:
            self.component_info.setText(f"{component.name} — no active students match the selected class, section, and search.")
        else:
            self.component_info.setText(
                f"{component.name} — maximum {maximum}; {len(students)} student(s) loaded."
            )

    def _load_half_yearly_grid(self, session_id, exam_id, class_id, section_id, subject_id):
        exam = self.exam_repo.get_exam_by_id(exam_id)
        if exam is None or exam.session_id != session_id or exam.name.strip().casefold() != "half yearly":
            QMessageBox.warning(self, "Invalid Selection", "Select a valid Half Yearly examination.")
            return
        subject = self.setup_repo.get_subject_by_id(subject_id)
        if subject is None:
            QMessageBox.warning(self, "Invalid Selection", "The selected subject no longer exists.")
            return
        components = self._current_components
        if self._grade_only_mode and not HalfYearlyService.is_grade_only(subject):
            QMessageBox.warning(self, "Invalid Selection", "This subject is not configured for grade-only entry.")
            return
        if not self._grade_only_mode:
            try:
                HalfYearlyService.validate_components(subject, components)
            except ValueError as error:
                QMessageBox.warning(self, "Scheme Not Configured", str(error))
                return

        students = self.student_repo.get_students(
            session_id=session_id,
            class_id=class_id,
            section_id=section_id,
            keyword=self.search_input.text().strip() or None,
        )
        student_ids = [student.id for student in students]
        self._dynamic_column_components = {}
        self._loading_grid = True
        self.table.setSortingEnabled(False)
        self.table.clear()
        identity_headers = [
            "S. No.", "Roll No.", "Student Name", "Father's Name", "Admission No.",
        ]
        if self._grade_only_mode:
            headers = identity_headers + ["Grade", "Status"]
            self._dynamic_column_components = {5: "grade"}
            grade_records = self.mark_repo.get_grade_marks(exam_id, subject_id, student_ids)
            grades_by_student = {record.student_id: record.grade for record in grade_records}
            self.table.setColumnCount(len(headers))
            self.table.setHorizontalHeaderLabels(headers)
        else:
            headers = identity_headers.copy()
            for component in components:
                raw_max = component.entry_max or component.max_marks
                headers.extend([
                    f"{component.name} / {CalculationService.format_marks(raw_max)}"
                    + (" (derived)" if component.is_derived else ""),
                    "Status",
                ])
            headers.extend(["Total / 100", "Result Status"])
            self.table.setColumnCount(len(headers))
            self.table.setHorizontalHeaderLabels(headers)
            self._dynamic_column_components = {
                5 + index * 2: component.id
                for index, component in enumerate(components)
            }
            delegate = HalfYearlyMarksDelegate(self.table)
            for column in self._dynamic_column_components:
                self.table.setItemDelegateForColumn(column, delegate)
            marks = self.mark_repo.get_marks_for_students(
                student_ids,
                subject_ids=[subject_id],
                component_ids=[
                    component.id
                    for component in components + self._legacy_components
                ],
            )
            marks_by_student = {}
            for mark in marks:
                marks_by_student.setdefault(mark.student_id, {})[
                    mark.component_id
                ] = mark

        self.table.setRowCount(len(students))
        self.student_rows = students
        for row, student in enumerate(students):
            self._set_read_only_cell(row, 0, str(row + 1))
            roll = QTableWidgetItem(str(student.roll_number))
            roll.setData(Qt.UserRole, student.id)
            roll.setFlags(roll.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, self.ROLL_COLUMN, roll)
            for column, value in (
                (self.NAME_COLUMN, student.name),
                (self.FATHER_COLUMN, student.father_name or ""),
                (self.ADMISSION_COLUMN, student.admission_number),
            ):
                self._set_read_only_cell(row, column, value)

            if self._grade_only_mode:
                grade = grades_by_student.get(student.id, "")
                item = QTableWidgetItem(grade)
                item.setToolTip("Enter the assigned grade for this grade-only subject.")
                if not self.edit_mode_checkbox.isChecked():
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, 5, item)
                self._set_read_only_cell(row, 6, "Entered" if grade else "Not Entered")
                continue

            student_marks = HalfYearlyService.map_legacy_component_marks(
                components,
                self._legacy_components,
                marks_by_student.get(student.id, {}),
            )
            result = HalfYearlyService(self.derived_service).calculate_subject_result(
                student, subject, session_id, components, student_marks
            )
            for component_index, component in enumerate(components):
                result_component = result["components"][component_index]
                status = result_component["status"].title()
                if result_component["status"] == "entered":
                    status = "Entered"
                mark_text = (
                    "AB" if result_component["status"] == "absent"
                    else CalculationService.format_marks(result_component["marks"])
                    if result_component["marks"] is not None else ""
                )

                mark_column = 5 + component_index * 2
                mark_item = QTableWidgetItem(mark_text)
                mark_item.setToolTip(
                    "Derived from PT1 and read-only."
                    if component.is_derived
                    else f"Enter between 0 and {CalculationService.format_marks(component.entry_max or component.max_marks)}; enter AB for absent."
                )
                if component.is_derived or not self.edit_mode_checkbox.isChecked():
                    mark_item.setFlags(mark_item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, mark_column, mark_item)
                self._set_read_only_cell(row, mark_column + 1, status)
            total_column = 5 + len(components) * 2
            self._set_read_only_cell(
                row,
                total_column,
                CalculationService.format_marks(result["total"])
                if result["total"] is not None else "—",
            )
            self._set_read_only_cell(row, total_column + 1, result["status"])

        self.table.setSortingEnabled(True)
        self._loading_grid = False
        self._dirty = False
        self._dirty_student_ids.clear()
        self._dirty_cells.clear()
        if self._grade_only_mode:
            self.component_info.setText(
                f"{subject.name} — grade-only entry; {len(students)} student(s) loaded."
            )
        else:
            self.component_info.setText(
                f"{subject.name} — Half Yearly components; {len(students)} student(s) loaded."
            )

    def _set_read_only_cell(self, row, column, value):
        item = QTableWidgetItem(value)
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, column, item)

    def _refresh_half_yearly_summary(self, row):
        if self._grade_only_mode or not self._current_components:
            return
        roll_item = self.table.item(row, self.ROLL_COLUMN)
        student_id = roll_item.data(Qt.UserRole) if roll_item else None
        student = next(
            (record for record in self.student_rows if record.id == student_id),
            None,
        )
        subject = self.setup_repo.get_subject_by_id(self.subject_combo.currentData())
        session_id = self.session_combo.currentData()
        if student is None or subject is None or session_id is None:
            return
        marks_by_component = {}
        invalid_component = None
        for component in self._current_components:
            if component.is_derived:
                continue
            column = next(
                key for key, value in self._dynamic_column_components.items()
                if value == component.id
            )
            value = self.table.item(row, column).text().strip()
            if not value:
                continue
            if value.upper() == "AB":
                marks_by_component[component.id] = SimpleNamespace(
                    marks_obtained=None, is_absent=True
                )
                continue
            try:
                obtained = Decimal(value)
                maximum = Decimal(str(component.entry_max or component.max_marks))
                if not obtained.is_finite() or obtained < 0 or obtained > maximum:
                    raise ValueError
            except (InvalidOperation, ValueError):
                invalid_component = component
                break
            marks_by_component[component.id] = SimpleNamespace(
                marks_obtained=obtained, is_absent=False
            )
        total_column = 5 + len(self._current_components) * 2
        if invalid_component is not None:
            column = next(
                key for key, value in self._dynamic_column_components.items()
                if value == invalid_component.id
            )
            self._loading_grid = True
            self.table.item(row, column + 1).setText("Invalid")
            self.table.item(row, total_column).setText("—")
            self.table.item(row, total_column + 1).setText("Invalid")
            self._loading_grid = False
            return
        result = HalfYearlyService(self.derived_service).calculate_subject_result(
            student, subject, session_id, self._current_components, marks_by_component
        )
        self._loading_grid = True
        for component, result_component in zip(
            self._current_components, result["components"]
        ):
            column = next(
                key for key, value in self._dynamic_column_components.items()
                if value == component.id
            )
            status = result_component["status"].title()
            self.table.item(row, column + 1).setText(status)
        self.table.item(row, total_column).setText(
            CalculationService.format_marks(result["total"])
            if result["total"] is not None else "—"
        )
        self.table.item(row, total_column + 1).setText(result["status"])
        self._loading_grid = False

    def save_marks(self):
        if self.table.rowCount() == 0:
            QMessageBox.warning(self, "No Students", "Load students before saving marks.")
            return
        if self._half_yearly_mode:
            self._save_half_yearly_marks()
            return
        session_id = self.session_combo.currentData()
        exam_id = self.exam_combo.currentData()
        subject_id = self.subject_combo.currentData()
        component_id = self.component_combo.currentData()
        component = self.exam_repo.get_component_by_id(component_id) if component_id else None
        if not all((session_id, exam_id, subject_id, component_id)) or component is None:
            QMessageBox.warning(self, "Incomplete Selection", "Select all filters before saving marks.")
            return
        if component.exam_id != exam_id:
            QMessageBox.warning(self, "Invalid Selection", "The selected component does not belong to this exam.")
            return
        if component.is_derived:
            QMessageBox.warning(self, "Read-only Component", "Derived marks cannot be entered manually.")
            return

        maximum = Decimal(str(component.max_marks))
        marks_data = []
        errors = []
        for row in range(self.table.rowCount()):
            roll_item = self.table.item(row, self.ROLL_COLUMN)
            mark_item = self.table.item(row, self.MARKS_COLUMN)
            if roll_item is None or mark_item is None:
                errors.append(f"Row {row + 1}: student or mark cell is missing.")
                continue
            student_id = roll_item.data(Qt.UserRole)
            if student_id not in self._dirty_student_ids:
                continue
            student_name = self.table.item(row, self.NAME_COLUMN).text()
            value = mark_item.text().strip()
            if not value:
                continue
            if value.upper() == "AB":
                marks_data.append({
                    "student_id": student_id,
                    "subject_id": subject_id,
                    "component_id": component_id,
                    "marks_obtained": None,
                    "is_absent": True,
                })
                continue
            try:
                marks = Decimal(value)
                if not marks.is_finite() or marks < 0:
                    raise ValueError("Marks must be a finite, non-negative number.")
                if marks > maximum:
                    raise ValueError(f"Marks exceed the maximum of {CalculationService.format_marks(maximum)}.")
            except (InvalidOperation, ValueError) as error:
                errors.append(f"Row {row + 1} ({student_name}): {error}")
                continue
            marks_data.append({
                "student_id": student_id,
                "subject_id": subject_id,
                "component_id": component_id,
                "marks_obtained": marks,
                "is_absent": False,
            })

        if errors:
            QMessageBox.warning(self, "Validation Errors", "\n".join(errors))
            return
        if not marks_data:
            QMessageBox.information(self, "No Changes", "Edit a student's mark or enter AB before saving.")
            return
        try:
            self.mark_repo.save_marks_batch(marks_data)
        except ValueError as error:
            QMessageBox.warning(self, "Cannot Save Marks", str(error))
            return
        except SQLAlchemyError:
            logger.exception("Could not save marks batch")
            QMessageBox.critical(self, "Save Failed", "Marks could not be saved. No changes were committed.")
            return

        QMessageBox.information(self, "Success", f"Saved marks for {len(marks_data)} student(s).")
        self._dirty = False
        self._dirty_student_ids.clear()
        self.load_students_grid()

    def clear_selection(self):
        self.table.clearSelection()

    def _save_half_yearly_marks(self):
        exam_id = self.exam_combo.currentData()
        subject_id = self.subject_combo.currentData()
        if not exam_id or not subject_id:
            QMessageBox.warning(self, "Incomplete Selection", "Select an exam and subject before saving.")
            return
        if not self._dirty_cells:
            QMessageBox.information(self, "No Changes", "Edit a grade or component mark before saving.")
            return
        errors = []
        if self._grade_only_mode:
            grade_rows = []
            for student_id, component_key in self._dirty_cells:
                if component_key != "grade":
                    continue
                row = next(
                    (row for row in range(self.table.rowCount())
                     if self.table.item(row, self.ROLL_COLUMN).data(Qt.UserRole) == student_id),
                    None,
                )
                if row is None:
                    continue
                grade = self.table.item(row, 5).text().strip()
                if not grade:
                    continue
                if len(grade) > 12:
                    errors.append(f"Row {row + 1}: grade must be at most 12 characters.")
                    continue
                grade_rows.append({
                    "student_id": student_id,
                    "subject_id": subject_id,
                    "grade": grade,
                })
            if errors:
                QMessageBox.warning(self, "Validation Errors", "\n".join(errors))
                return
            try:
                self.mark_repo.save_grade_marks_batch(exam_id, grade_rows)
            except ValueError as error:
                QMessageBox.warning(self, "Cannot Save Grades", str(error))
                return
            except SQLAlchemyError:
                logger.exception("Could not save Half Yearly grades")
                QMessageBox.critical(self, "Save Failed", "Grades could not be saved.")
                return
            QMessageBox.information(self, "Success", f"Saved grades for {len(grade_rows)} student(s).")
            self._dirty = False
            self._dirty_student_ids.clear()
            self._dirty_cells.clear()
            self.load_students_grid()
            return

        marks_data = []
        component_by_id = {component.id: component for component in self._current_components}
        for student_id, component_id in self._dirty_cells:
            component = component_by_id.get(component_id)
            if component is None or component.is_derived:
                continue
            row = next(
                (row for row in range(self.table.rowCount())
                 if self.table.item(row, self.ROLL_COLUMN).data(Qt.UserRole) == student_id),
                None,
            )
            if row is None:
                continue
            mark_column = next(
                (column for column, key in self._dynamic_column_components.items()
                 if key == component_id),
                None,
            )
            value = self.table.item(row, mark_column).text().strip() if mark_column is not None else ""
            if not value:
                continue
            if value.upper() == "AB":
                marks_data.append({
                    "student_id": student_id,
                    "subject_id": subject_id,
                    "component_id": component_id,
                    "marks_obtained": None,
                    "is_absent": True,
                })
                continue
            maximum = Decimal(str(component.entry_max or component.max_marks))
            try:
                obtained = Decimal(value)
                if not obtained.is_finite() or obtained < 0:
                    raise ValueError("Marks must be a finite, non-negative number.")
                if obtained > maximum:
                    raise ValueError(
                        f"Marks exceed the entry maximum of {CalculationService.format_marks(maximum)}."
                    )
            except (InvalidOperation, ValueError) as error:
                errors.append(f"Student {student_id}, {component.name}: {error}")
                continue
            marks_data.append({
                "student_id": student_id,
                "subject_id": subject_id,
                "component_id": component_id,
                "marks_obtained": obtained,
                "is_absent": False,
            })
        if errors:
            QMessageBox.warning(self, "Validation Errors", "\n".join(errors))
            return
        if not marks_data:
            QMessageBox.information(self, "No Changes", "Enter a mark or AB before saving.")
            return
        try:
            self.mark_repo.save_marks_batch(marks_data)
        except ValueError as error:
            QMessageBox.warning(self, "Cannot Save Marks", str(error))
            return
        except SQLAlchemyError:
            logger.exception("Could not save Half Yearly marks")
            QMessageBox.critical(self, "Save Failed", "Marks could not be saved.")
            return
        QMessageBox.information(self, "Success", f"Saved {len(marks_data)} component mark(s).")
        self._dirty = False
        self._dirty_student_ids.clear()
        self._dirty_cells.clear()
        self.load_students_grid()
