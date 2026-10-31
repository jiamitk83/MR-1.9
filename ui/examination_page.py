from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QTableWidget, QTableWidgetItem, QMessageBox,
                             QComboBox, QDialog, QDialogButtonBox, QFormLayout,
                             QDoubleSpinBox, QCheckBox)
from PySide6.QtCore import Qt
from repositories.examination import ExamRepository
from repositories.academic_setup import AcademicSetupRepository
from services.half_yearly import HalfYearlyService
from services.calculation import CalculationService

class ExaminationPage(QWidget):
    def __init__(self):
        super().__init__()
        self.exam_repo = ExamRepository()
        self.setup_repo = AcademicSetupRepository()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Examination Management"))

        # Search and filters
        filter_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search examinations...")
        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self.refresh_exams)
        filter_layout.addWidget(QLabel("Search:"))
        filter_layout.addWidget(self.search_input)
        filter_layout.addWidget(self.search_btn)
        layout.addLayout(filter_layout)

        # Add new exam
        add_layout = QHBoxLayout()
        self.exam_name_input = QLineEdit()
        self.exam_name_input.setPlaceholderText("Exam Name (e.g. Half Yearly)")
        self.session_combo = QComboBox()
        self.load_sessions()
        add_btn = QPushButton("Create Examination")
        add_btn.clicked.connect(self.create_exam)
        add_layout.addWidget(self.exam_name_input)
        add_layout.addWidget(self.session_combo)
        add_layout.addWidget(add_btn)
        layout.addLayout(add_layout)

        # Exam Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Session", "Components", "Actions"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

        # Component management
        comp_layout = QHBoxLayout()
        self.component_table = QTableWidget()
        self.component_table.setColumnCount(7)
        self.component_table.setHorizontalHeaderLabels([
            "Component Name", "Max Marks", "Code", "Derived",
            "Subject", "Entry Max", "Actions",
        ])
        comp_layout.addWidget(QLabel("Selected Exam Components:"))
        layout.addLayout(comp_layout)
        layout.addWidget(self.component_table)

        add_comp_btn = QPushButton("Add Component")
        add_comp_btn.clicked.connect(self.add_component)
        edit_comp_btn = QPushButton("Edit Component")
        edit_comp_btn.clicked.connect(self.edit_component)
        delete_comp_btn = QPushButton("Delete Component")
        delete_comp_btn.clicked.connect(self.delete_component)
        comp_btn_layout = QHBoxLayout()
        comp_btn_layout.addWidget(add_comp_btn)
        comp_btn_layout.addWidget(edit_comp_btn)
        comp_btn_layout.addWidget(delete_comp_btn)
        layout.addLayout(comp_btn_layout)

        scheme_layout = QHBoxLayout()
        self.scheme_subject_combo = QComboBox()
        for subject in self.setup_repo.get_all_subjects():
            self.scheme_subject_combo.addItem(subject.name, subject.id)
        self.french_entry_combo = QComboBox()
        self.french_entry_combo.addItem("French raw entry / 40", 40)
        self.french_entry_combo.addItem("French direct entry / 80", 80)
        self.scheme_preview = QLabel()
        self.scheme_preview.setWordWrap(True)
        configure_scheme_btn = QPushButton("Apply Half Yearly Subject Scheme")
        configure_scheme_btn.clicked.connect(self.configure_half_yearly_scheme)
        self.scheme_subject_combo.currentIndexChanged.connect(
            self.refresh_half_yearly_scheme_preview
        )
        self.french_entry_combo.currentIndexChanged.connect(
            self.refresh_half_yearly_scheme_preview
        )
        scheme_layout.addWidget(QLabel("Half Yearly subject:"))
        scheme_layout.addWidget(self.scheme_subject_combo)
        scheme_layout.addWidget(self.french_entry_combo)
        scheme_layout.addWidget(configure_scheme_btn)
        layout.addLayout(scheme_layout)
        layout.addWidget(self.scheme_preview)
        self.refresh_half_yearly_scheme_preview()

        self.setLayout(layout)
        self.refresh_exams()

    def load_sessions(self):
        sessions = self.setup_repo.get_all_sessions()
        for session in sessions:
            self.session_combo.addItem(session.name, session.id)

    def refresh_exams(self):
        keyword = self.search_input.text().strip()
        exams = self.exam_repo.search_exams(keyword=keyword if keyword else None)
        self.table.setRowCount(len(exams))
        for row, exam in enumerate(exams):
            self.table.setItem(row, 0, QTableWidgetItem(str(exam.id)))
            self.table.setItem(row, 1, QTableWidgetItem(exam.name))
            session = self.setup_repo.get_session_by_id(exam.session_id)
            self.table.setItem(row, 2, QTableWidgetItem(session.name if session else "-"))
            components = self.exam_repo.get_components_by_exam(exam.id)
            self.table.setItem(row, 3, QTableWidgetItem(str(len(components))))
            # Action buttons
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            edit_btn = QPushButton("Edit")
            edit_btn.clicked.connect(lambda checked, r=row: self._edit_exam_from_row(r))
            delete_btn = QPushButton("Delete")
            delete_btn.clicked.connect(lambda checked, r=row: self._delete_exam_from_row(r))
            load_btn = QPushButton("Load")
            load_btn.clicked.connect(lambda checked, r=row: self._load_components(r))
            actions_layout.addWidget(load_btn)
            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(delete_btn)
            self.table.setCellWidget(row, 4, actions_widget)

    def create_exam(self):
        name = self.exam_name_input.text().strip()
        session_id = self.session_combo.currentData()
        if not name or not session_id:
            QMessageBox.warning(self, "Validation Error", "Please enter exam name and select session!")
            return
        result = self.exam_repo.create_exam(name=name, session_id=session_id)
        if result:
            self.exam_name_input.clear()
            self.refresh_exams()
            QMessageBox.information(self, "Success", f"Exam '{name}' created successfully!")
        else:
            QMessageBox.warning(self, "Error", "Exam name already exists for this session!")

    def _edit_exam_from_row(self, row):
        exam_id = self.table.item(row, 0).text()
        current_name = self.table.item(row, 1).text()
        dialog = ExamDialog(self, exam_id=int(exam_id))
        if dialog.exec() == QDialog.Accepted:
            name, session_id = dialog.get_values()
            if name:
                self.exam_repo.update_exam(exam_id=int(exam_id), name=name, session_id=session_id)
                self.refresh_exams()
                QMessageBox.information(self, "Success", "Exam updated successfully!")

    def _delete_exam_from_row(self, row):
        exam_id = self.table.item(row, 0).text()
        reply = QMessageBox.question(self, "Confirm Delete",
                                     f"Are you sure you want to delete exam ID {exam_id}?\n\nNote: Exams with components cannot be deleted.",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            success = self.exam_repo.delete_exam(exam_id=int(exam_id))
            if success:
                self.refresh_exams()
                QMessageBox.information(self, "Success", "Exam deleted successfully!")
            else:
                QMessageBox.warning(
                    self,
                    "Error",
                    "Cannot delete an exam that has components or saved report-card details.",
                )

    def _load_components(self, row):
        exam_id = int(self.table.item(row, 0).text())
        self.table.selectRow(row)
        components = self.exam_repo.get_components_by_exam(exam_id)
        self.component_table.setRowCount(len(components))
        for comp_row, comp in enumerate(components):
            name_item = QTableWidgetItem(comp.name)
            name_item.setData(Qt.UserRole, comp.id)
            self.component_table.setItem(comp_row, 0, name_item)
            self.component_table.setItem(comp_row, 1, QTableWidgetItem(str(comp.max_marks)))
            self.component_table.setItem(comp_row, 2, QTableWidgetItem(comp.code or "-"))
            subject = (
                self.setup_repo.get_subject_by_id(comp.subject_id)
                if comp.subject_id is not None else None
            )
            self.component_table.setItem(
                comp_row, 4, QTableWidgetItem(subject.name if subject else "All subjects")
            )
            self.component_table.setItem(
                comp_row, 5,
                QTableWidgetItem(
                    str(comp.entry_max)
                    if comp.entry_max is not None else str(comp.max_marks)
                ),
            )
            # Action buttons
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            edit_btn = QPushButton("Edit")
            edit_btn.clicked.connect(lambda checked, r=comp_row: self._edit_component_from_row(r))
            delete_btn = QPushButton("Delete")
            delete_btn.clicked.connect(lambda checked, r=comp_row: self._delete_component_from_row(r))
            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(delete_btn)
            self.component_table.setItem(comp_row, 3, QTableWidgetItem("Yes" if comp.is_derived else "No"))
            self.component_table.setCellWidget(comp_row, 6, actions_widget)

    def add_component(self):
        exam_row = self.table.currentRow()
        if exam_row < 0:
            QMessageBox.warning(self, "Select an Exam", "Select an examination before adding a component.")
            return
        dialog = ComponentDialog()
        if dialog.exec() == QDialog.Accepted:
            name, max_marks, code, is_derived = dialog.get_values()
            if name.strip() and max_marks > 0:
                try:
                    self.exam_repo.add_component(
                        exam_id=int(self.table.item(exam_row, 0).text()),
                        name=name.strip(),
                        max_marks=max_marks,
                        code=code,
                        is_derived=is_derived,
                    )
                except ValueError as error:
                    QMessageBox.warning(self, "Cannot Add Component", str(error))
                    return
                self._load_components(exam_row)
                QMessageBox.information(self, "Success", "Component added successfully!")

    def configure_half_yearly_scheme(self):
        exam_row = self.table.currentRow()
        subject_id = self.scheme_subject_combo.currentData()
        if exam_row < 0 or subject_id is None:
            QMessageBox.warning(
                self, "Select an Exam and Subject",
                "Select a Half Yearly examination row and a subject first.",
            )
            return
        exam_id = int(self.table.item(exam_row, 0).text())
        exam = self.exam_repo.get_exam_by_id(exam_id)
        subject = self.setup_repo.get_subject_by_id(subject_id)
        if exam is None or subject is None:
            QMessageBox.warning(self, "Selection Changed", "Refresh the examination and try again.")
            return
        if exam.name.strip().casefold() != "half yearly":
            QMessageBox.warning(
                self, "Wrong Examination",
                "The recommended subject scheme can only be applied to an exam named Half Yearly.",
            )
            return
        if HalfYearlyService.is_grade_only(subject):
            QMessageBox.information(
                self, "Grade-only Subject",
                f"{subject.name} uses a grade-only entry workflow and has no numeric components.",
            )
            return
        template = HalfYearlyService.template_for_subject(
            subject,
            french_entry_maximum=self.french_entry_combo.currentData(),
        )
        if template is None:
            QMessageBox.warning(
                self, "Unsupported Subject",
                "No recommended Half Yearly template exists for this subject.",
            )
            return
        try:
            HalfYearlyService.validate_components(subject, template)
            self.exam_repo.configure_subject_components(exam_id, subject_id, template)
        except ValueError as error:
            QMessageBox.warning(self, "Cannot Configure Scheme", str(error))
            return
        self._load_components(exam_row)
        QMessageBox.information(
            self, "Scheme Configured",
            f"{subject.name} now uses its Half Yearly scheme. Saved component marks were not changed.",
        )
        self.refresh_half_yearly_scheme_preview()

    def refresh_half_yearly_scheme_preview(self, _index=None):
        subject = self.setup_repo.get_subject_by_id(
            self.scheme_subject_combo.currentData()
        )
        if subject is None:
            self.scheme_preview.setText("Select a subject to preview its Half Yearly scheme.")
            return
        try:
            template = HalfYearlyService.template_for_subject(
                subject,
                self.french_entry_combo.currentData() or 40,
            )
        except ValueError as error:
            self.scheme_preview.setText(str(error))
            return
        if HalfYearlyService.is_grade_only(subject):
            self.scheme_preview.setText(
                f"{subject.name}: grade-only; excluded from numeric totals."
            )
            return
        if template is None:
            self.scheme_preview.setText(
                f"{subject.name}: no recommended Half Yearly template."
            )
            return
        details = []
        for component in template:
            entry_maximum = component.entry_maximum
            suffix = " (derived)" if component.is_derived else ""
            if entry_maximum is not None and entry_maximum != component.maximum:
                suffix += f"; enter / {CalculationService.format_marks(entry_maximum)}"
            details.append(
                f"{component.name} / {CalculationService.format_marks(component.maximum)}{suffix}"
            )
        total = sum((component.maximum for component in template), start=0)
        self.scheme_preview.setText(
            f"{subject.name}: {'; '.join(details)}. "
            f"Configured maximum total: {CalculationService.format_marks(total)}"
        )

    def edit_component(self):
        row = self.component_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Warning", "Please select a component to edit.")
            return
        self._edit_component_from_row(row)

    def _edit_component_from_row(self, row):
        name_item = self.component_table.item(row, 0)
        if name_item is None:
            return
        component_id = name_item.data(Qt.UserRole)
        component = self.exam_repo.get_component_by_id(component_id)
        if component is None:
            QMessageBox.warning(self, "Component Not Found", "Refresh the examination and try again.")
            return
        dialog = ComponentDialog(
            current_name=component.name,
            max_marks=component.max_marks,
            code=component.code,
            is_derived=component.is_derived,
        )
        if dialog.exec() == QDialog.Accepted:
            name, max_marks, code, is_derived = dialog.get_values()
            try:
                self.exam_repo.update_component(
                    component_id=component_id,
                    name=name.strip(),
                    max_marks=max_marks,
                    code=code,
                    is_derived=is_derived,
                )
            except ValueError as error:
                QMessageBox.warning(self, "Cannot Update Component", str(error))
                return
            exam_row = self.table.currentRow()
            if exam_row >= 0:
                self._load_components(exam_row)
            QMessageBox.information(self, "Success", "Component updated successfully!")

    def delete_component(self):
        row = self.component_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Warning", "Please select a component to delete.")
            return
        self._delete_component_from_row(row)

    def _delete_component_from_row(self, row):
        name_item = self.component_table.item(row, 0)
        if name_item is None:
            return
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            "Delete this component? Components with saved marks cannot be deleted.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        if not self.exam_repo.delete_component(component_id=name_item.data(Qt.UserRole)):
            QMessageBox.warning(self, "Cannot Delete", "This component has saved marks or no longer exists.")
            return
        exam_row = self.table.currentRow()
        if exam_row >= 0:
            self._load_components(exam_row)
        QMessageBox.information(self, "Success", "Component deleted successfully!")


class ExamDialog(QDialog):
    def __init__(self, parent=None, exam_id=None):
        super().__init__(parent)
        self.exam_id = exam_id
        self.repo = ExamRepository()
        self.setup_repo = AcademicSetupRepository()
        self.init_ui()
        if exam_id:
            self.load_exam(exam_id)

    def init_ui(self):
        self.setWindowTitle("Exam" + (" Edit" if self.exam_id else " Add"))
        layout = QFormLayout()

        self.name_input = QLineEdit()
        self.session_combo = QComboBox()
        sessions = self.setup_repo.get_all_sessions()
        for session in sessions:
            self.session_combo.addItem(session.name, session.id)

        layout.addRow("Name:", self.name_input)
        layout.addRow("Session:", self.session_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def load_exam(self, exam_id):
        exam = self.repo.get_exam_by_id(exam_id)
        if exam:
            self.name_input.setText(exam.name)
            for i in range(self.session_combo.count()):
                if self.session_combo.itemData(i) == exam.session_id:
                    self.session_combo.setCurrentIndex(i)
                    break

    def get_values(self):
        return self.name_input.text(), self.session_combo.currentData()


class ComponentDialog(QDialog):
    def __init__(self, parent=None, current_name=None, max_marks=None, code=None, is_derived=False):
        super().__init__(parent)
        self.current_name = current_name
        self.initial_max_marks = max_marks
        self.initial_code = code
        self.initial_is_derived = is_derived
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Component" + (" Edit" if self.current_name else " Add"))
        layout = QFormLayout()

        self.name_input = QLineEdit()
        if self.current_name:
            self.name_input.setText(self.current_name)
        self.max_marks = QDoubleSpinBox()
        self.max_marks.setMinimum(0.01)
        self.max_marks.setMaximum(1000)
        self.max_marks.setDecimals(2)
        if self.initial_max_marks is not None:
            self.max_marks.setValue(self.initial_max_marks)
        self.code_input = QLineEdit()
        self.code_input.setText(self.initial_code or "")
        self.derived_checkbox = QCheckBox("Calculate from periodic test marks")
        self.derived_checkbox.setChecked(self.initial_is_derived)

        layout.addRow("Name:", self.name_input)
        layout.addRow("Max Marks:", self.max_marks)
        layout.addRow("Code:", self.code_input)
        layout.addRow("Derived:", self.derived_checkbox)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def get_values(self):
        return (
            self.name_input.text(),
            self.max_marks.value(),
            self.code_input.text() or None,
            self.derived_checkbox.isChecked(),
        )
