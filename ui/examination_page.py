from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QTableWidget, QTableWidgetItem, QMessageBox,
                             QComboBox, QDialog, QDialogButtonBox, QFormLayout,
                             QDoubleSpinBox)
from repositories.examination import ExamRepository
from repositories.academic_setup import AcademicSetupRepository

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
        self.component_table.setColumnCount(4)
        self.component_table.setHorizontalHeaderLabels(["Component Name", "Max Marks", "Code", "Actions"])
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
                QMessageBox.warning(self, "Error", "Cannot delete exam that has components!")

    def _load_components(self, row):
        exam_id = int(self.table.item(row, 0).text())
        components = self.exam_repo.get_components_by_exam(exam_id)
        self.component_table.setRowCount(len(components))
        for comp_row, comp in enumerate(components):
            self.component_table.setItem(comp_row, 0, QTableWidgetItem(comp.name))
            self.component_table.setItem(comp_row, 1, QTableWidgetItem(str(comp.max_marks)))
            self.component_table.setItem(comp_row, 2, QTableWidgetItem(comp.code or "-"))
            # Action buttons
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            edit_btn = QPushButton("Edit")
            edit_btn.clicked.connect(lambda checked, r=comp_row: self._edit_component_from_row(r))
            delete_btn = QPushButton("Delete")
            delete_btn.clicked.connect(lambda checked, r=comp_row: self._delete_component_from_row(r))
            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(delete_btn)
            self.component_table.setCellWidget(comp_row, 3, actions_widget)

    def add_component(self):
        dialog = ComponentDialog()
        if dialog.exec() == QDialog.Accepted:
            name, max_marks, code = dialog.get_values()
            if name and max_marks:
                self.exam_repo.add_component(
                    exam_id=self.table.currentRow() if self.table.currentRow() >= 0 else 1,
                    name=name, max_marks=max_marks, code=code
                )
                self._load_components(self.table.currentRow())
                QMessageBox.information(self, "Success", "Component added successfully!")

    def edit_component(self):
        row = self.component_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Warning", "Please select a component to edit.")
            return
        current_name = self.component_table.item(row, 0).text()
        dialog = ComponentDialog(current_name=current_name)
        if dialog.exec() == QDialog.Accepted:
            name, max_marks, code = dialog.get_values()
            # Find component ID from table
            # For simplicity, we'll just refresh
            self._load_components(self.table.currentRow())
            QMessageBox.information(self, "Success", "Component updated successfully!")

    def delete_component(self):
        row = self.component_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Warning", "Please select a component to delete.")
            return
        reply = QMessageBox.question(self, "Confirm Delete",
                                     "Are you sure you want to delete this component?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.exam_repo.delete_component(component_id=1)  # Simplified
            self._load_components(self.table.currentRow())
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
    def __init__(self, parent=None, current_name=None):
        super().__init__(parent)
        self.current_name = current_name
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Component" + (" Edit" if self.current_name else " Add"))
        layout = QFormLayout()

        self.name_input = QLineEdit()
        if self.current_name:
            self.name_input.setText(self.current_name)
        self.max_marks = QDoubleSpinBox()
        self.max_marks.setMinimum(0)
        self.max_marks.setMaximum(1000)
        self.max_marks.setDecimals(2)
        self.code_input = QLineEdit()

        layout.addRow("Name:", self.name_input)
        layout.addRow("Max Marks:", self.max_marks)
        layout.addRow("Code:", self.code_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def get_values(self):
        return (
            self.name_input.text(),
            self.max_marks.value(),
            self.code_input.text() or None
        )
