from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
                             QMessageBox, QGroupBox, QDoubleSpinBox, QCheckBox)
from PySide6.QtCore import Qt
from repositories.student import StudentRepository
from repositories.examination import ExamRepository
from repositories.mark import MarkRepository
from repositories.academic_setup import AcademicSetupRepository
from repositories.subject_alias import SubjectAliasRepository
from services.calculation import CalculationService
from services.derived_calculations import DerivedCalculationService

class MarksEntryPage(QWidget):
    """Enhanced Marks Entry with full cascading selectors and proper component handling"""

    def __init__(self):
        super().__init__()
        self.student_repo = StudentRepository()
        self.exam_repo = ExamRepository()
        self.mark_repo = MarkRepository()
        self.setup_repo = AcademicSetupRepository()
        self.alias_repo = SubjectAliasRepository()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Marks Entry Module"))

        # Filter controls
        filter_group = QGroupBox("Select Filters")
        filter_layout = QFormLayout()

        self.session_combo = QComboBox()
        self.class_combo = QComboBox()
        self.section_combo = QComboBox()
        self.exam_combo = QComboBox()
        self.subject_combo = QComboBox()
        self.component_combo = QComboBox()

        # Load sessions
        sessions = self.setup_repo.get_all_sessions()
        for s in sessions:
            self.session_combo.addItem(s.name, s.id)

        self.session_combo.currentIndexChanged.connect(self._on_session_changed)
        self.class_combo.currentIndexChanged.connect(self._on_class_changed)
        self.section_combo.currentIndexChanged.connect(self._on_section_changed)
        self.exam_combo.currentIndexChanged.connect(self._on_exam_changed)
        self.component_combo.currentIndexChanged.connect(self._on_component_changed)

        filter_layout.addRow("Session:", self.session_combo)
        filter_layout.addRow("Class:", self.class_combo)
        filter_layout.addRow("Section:", self.section_combo)
        filter_layout.addRow("Exam:", self.exam_combo)
        filter_layout.addRow("Subject:", self.subject_combo)
        filter_layout.addRow("Component:", self.component_combo)

        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)

        # Search and load
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search students...")
        load_btn = QPushButton("Load Students")
        load_btn.clicked.connect(self.load_students_grid)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(load_btn)
        layout.addLayout(search_layout)

        # Student Marks Grid
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Roll No", "Student Name", "Father's Name", "Marks Obtained", "Max Marks", "Status"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

        # Edit mode toggle
        edit_layout = QHBoxLayout()
        self.edit_mode_checkbox = QCheckBox("Edit Mode")
        self.edit_mode_checkbox.stateChanged.connect(self._toggle_edit_mode)
        save_btn = QPushButton("Save Marks")
        save_btn.clicked.connect(self.save_marks)
        clear_btn = QPushButton("Clear Selection")
        clear_btn.clicked.connect(self.clear_selection)

        edit_layout.addWidget(self.edit_mode_checkbox)
        edit_layout.addWidget(save_btn)
        edit_layout.addWidget(clear_btn)
        layout.addLayout(edit_layout)

        self.setLayout(layout)

    def _on_session_changed(self, index):
        """Refresh class dropdown on session change"""
        self.class_combo.clear()
        self.section_combo.clear()
        self.exam_combo.clear()
        self.subject_combo.clear()
        self.component_combo.clear()

        session_id = self.session_combo.currentData()
        classes = self.setup_repo.get_all_classes()
        for cls in classes:
            self.class_combo.addItem(cls.name, cls.id)

    def _on_class_changed(self, index):
        """Refresh section dropdown on class change"""
        self.section_combo.clear()
        session_id = self.session_combo.currentData()
        class_id = self.class_combo.currentData()

        if session_id and class_id:
            sections = self.setup_repo.get_sections_by_class_and_session(class_id, session_id)
            for sec in sections:
                self.section_combo.addItem(sec.name, sec.id)

    def _on_section_changed(self, index):
        """Refresh exams on section change"""
        self.exam_combo.clear()
        session_id = self.session_combo.currentData()
        if session_id:
            exams = self.exam_repo.get_exams(session_id=session_id)
            for exam in exams:
                self.exam_combo.addItem(exam.name, exam.id)

    def _on_exam_changed(self, index):
        """Refresh components on exam change"""
        self.component_combo.clear()
        exam_id = self.exam_combo.currentData()
        if exam_id:
            components = self.exam_repo.get_components_by_exam(exam_id)
            for comp in components:
                self.component_combo.addItem(comp.name, comp.id)

    def _on_component_changed(self, index):
        """Handle component change"""
        pass

    def _toggle_edit_mode(self, state):
        """Toggle edit mode for marks cells"""
        is_edit = state == Qt.Checked
        for col in range(2, self.table.columnCount()):
            for row in range(self.table.rowCount()):
                item = self.table.item(row, col)
                if item:
                    flags = item.flags()
                    if is_edit:
                        flags |= Qt.ItemIsEditable
                    else:
                        flags &= ~Qt.ItemIsEditable
                    item.setFlags(flags)

    def load_students_grid(self):
        """Load students into grid"""
        session_id = self.session_combo.currentData()
        class_id = self.class_combo.currentData()
        section_id = self.section_combo.currentData()
        keyword = self.search_input.text().strip()

        students = self.student_repo.get_students(
            session_id=session_id,
            class_id=class_id,
            section_id=section_id,
            keyword=keyword if keyword else None
        )

        self.table.setRowCount(len(students))
        self.student_rows = students

        exam_id = self.exam_combo.currentData()
        component_id = self.component_combo.currentData()

        for row, student in enumerate(students):
            self.table.setItem(row, 0, QTableWidgetItem(str(student.roll_number)))
            self.table.setItem(row, 1, QTableWidgetItem(student.name))
            self.table.setItem(row, 2, QTableWidgetItem(student.father_name or "-"))

            # Get existing marks if any
            if exam_id and component_id:
                marks = self.mark_repo.get_marks(
                    subject_id=1,  # Will be expanded
                    component_id=component_id,
                    student_ids=[student.id]
                )
                if marks:
                    mark_val = float(marks[0].marks_obtained) if marks[0].marks_obtained else 0
                    self.table.setItem(row, 3, QTableWidgetItem(CalculationService.format_marks(mark_val)))
                    self.table.setItem(row, 4, QTableWidgetItem("Saved"))
                else:
                    self.table.setItem(row, 3, QTableWidgetItem("0.00"))
                    self.table.setItem(row, 4, QTableWidgetItem("Not Entered"))
            else:
                self.table.setItem(row, 3, QTableWidgetItem("0.00"))
                self.table.setItem(row, 4, QTableWidgetItem("N/A"))

            # Get max marks for component
            if exam_id and component_id:
                comp = next((c for c in self.exam_repo.get_components_by_exam(exam_id)
                           if c.id == component_id), None)
                if comp:
                    self.table.setItem(row, 5, QTableWidgetItem(str(comp.max_marks)))
                else:
                    self.table.setItem(row, 5, QTableWidgetItem("-"))
            else:
                self.table.setItem(row, 5, QTableWidgetItem("-"))

    def save_marks(self):
        """Save marks transactionally"""
        if not hasattr(self, 'student_rows') or not self.student_rows:
            QMessageBox.warning(self, "Warning", "No students loaded!")
            return

        exam_id = self.exam_combo.currentData()
        component_id = self.component_combo.currentData()

        if not exam_id or not component_id:
            QMessageBox.warning(self, "Warning", "Please select exam and component!")
            return

        marks_data = []
        errors = []

        for row, student in enumerate(self.student_rows):
            val_str = self.table.item(row, 3).text().strip()
            try:
                marks_val = float(val_str)
                formatted_marks = CalculationService.format_marks(marks_val)

                marks_data.append({
                    'student_id': student.id,
                    'subject_id': 1,
                    'component_id': component_id,
                    'marks_obtained': float(formatted_marks),
                    'is_absent': False
                })
            except ValueError:
                errors.append(f"Row {row + 1} ({student.name}): Invalid value '{val_str}'")

        if errors:
            QMessageBox.warning(self, "Validation Errors", "\n".join(errors))
            return

        success = self.mark_repo.save_marks_batch(marks_data)
        if success:
            QMessageBox.information(self, "Success", f"Successfully saved marks for {len(marks_data)} students!")
            self.load_students_grid()
        else:
            QMessageBox.critical(self, "Error", "Failed to save marks. Transaction rolled back.")

    def clear_selection(self):
        """Clear selected rows"""
        self.table.clearSelection()
