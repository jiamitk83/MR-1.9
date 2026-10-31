import csv
from datetime import datetime
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
                             QMessageBox, QComboBox, QDialog, QDialogButtonBox,
                             QFormLayout, QFileDialog, QCheckBox, QDateEdit, QInputDialog)
from PySide6.QtCore import QDate, Qt
from app.config import DATABASE_PATH
from services.database_backup import create_database_backup
from repositories.student import StudentRepository
from repositories.academic_setup import AcademicSetupRepository
from services.csv_export import spreadsheet_safe
from ui.bulk_student_entry_dialog import BulkStudentEntryDialog

class StudentMasterPage(QWidget):
    def __init__(self):
        super().__init__()
        self.student_repo = StudentRepository()
        self.setup_repo = AcademicSetupRepository()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Search and filters
        filter_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by name, roll no, admission no...")
        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self.refresh_students)
        filter_layout.addWidget(QLabel("Search:"))
        filter_layout.addWidget(self.search_input)
        filter_layout.addWidget(self.search_btn)
        self.show_inactive_check = QCheckBox("Show inactive")
        self.show_inactive_check.toggled.connect(self.refresh_students)
        filter_layout.addWidget(self.show_inactive_check)
        layout.addLayout(filter_layout)

        # Cascading selectors
        cascade_layout = QHBoxLayout()
        self.session_combo = QComboBox()
        self.class_combo = QComboBox()
        self.section_combo = QComboBox()
        self.load_cascade_data()

        self.session_combo.currentIndexChanged.connect(self._on_session_changed)
        self.class_combo.currentIndexChanged.connect(self._on_class_changed)

        cascade_layout.addWidget(QLabel("Session:"))
        cascade_layout.addWidget(self.session_combo)
        cascade_layout.addWidget(QLabel("Class:"))
        cascade_layout.addWidget(self.class_combo)
        cascade_layout.addWidget(QLabel("Section:"))
        cascade_layout.addWidget(self.section_combo)
        layout.addLayout(cascade_layout)

        # Add student actions
        student_actions = QHBoxLayout()
        add_btn = QPushButton("Add New Student")
        add_btn.clicked.connect(self.add_student)
        student_actions.addWidget(add_btn)
        bulk_add_btn = QPushButton("Bulk Student Entry")
        bulk_add_btn.clicked.connect(self.bulk_student_entry)
        student_actions.addWidget(bulk_add_btn)
        student_actions.addStretch()
        layout.addLayout(student_actions)

        # Student Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["Roll No", "Adm No", "Name", "Father's Name", "Class", "Section", "Status", "Actions"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

        # Action buttons
        btn_layout = QHBoxLayout()
        edit_btn = QPushButton("Edit Student")
        edit_btn.clicked.connect(self.edit_student)
        delete_btn = QPushButton("Deactivate Student")
        delete_btn.clicked.connect(self.delete_student)
        purge_btn = QPushButton("Delete Permanently")
        purge_btn.clicked.connect(self.permanently_delete_student)
        export_btn = QPushButton("Export CSV")
        export_btn.clicked.connect(self.export_csv)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(delete_btn)
        btn_layout.addWidget(purge_btn)
        btn_layout.addWidget(export_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.refresh_students()

    def load_cascade_data(self):
        """Load data for cascading dropdowns"""
        sessions, classes, sections = self.student_repo.get_cascading_data()

        self.session_combo.clear()
        self.session_combo.addItem("All Sessions", None)
        for session in sessions:
            self.session_combo.addItem(session.name, session.id)

        self.class_combo.clear()
        self.class_combo.addItem("All Classes", None)
        for cls in classes:
            self.class_combo.addItem(cls.name, cls.id)

        self.section_combo.clear()
        self.section_combo.addItem("All Sections", None)
        for section in sections:
            class_obj = self.setup_repo.get_class_by_id(section.class_id)
            session_obj = self.setup_repo.get_session_by_id(section.session_id)
            self.section_combo.addItem(f"{class_obj.name if class_obj else ''} - {session_obj.name if session_obj else ''}", section.id)

    def _on_session_changed(self, index):
        """Refresh classes when session changes"""
        self.class_combo.clear()
        self.class_combo.addItem("All Classes", None)
        session_id = self.session_combo.currentData()

        classes = self.setup_repo.get_all_classes()
        if session_id:
            # Filter classes that have students in this session (simplified)
            for cls in classes:
                self.class_combo.addItem(cls.name, cls.id)
        else:
            for cls in classes:
                self.class_combo.addItem(cls.name, cls.id)

    def _on_class_changed(self, index):
        """Refresh sections when class changes"""
        self.section_combo.clear()
        self.section_combo.addItem("All Sections", None)
        session_id = self.session_combo.currentData()
        class_id = self.class_combo.currentData()

        if session_id and class_id:
            sections = self.setup_repo.get_sections_by_class_and_session(class_id, session_id)
            for section in sections:
                self.section_combo.addItem(section.name, section.id)

    def refresh_students(self):
        """Refresh the student table"""
        session_id = self.session_combo.currentData()
        class_id = self.class_combo.currentData()
        section_id = self.section_combo.currentData()
        keyword = self.search_input.text().strip()

        students = self.student_repo.get_students(
            session_id=session_id,
            class_id=class_id,
            section_id=section_id,
            keyword=keyword if keyword else None,
            active_only=not self.show_inactive_check.isChecked()
        )
        students.sort(key=lambda student: (student.roll_number, student.id))

        self.table.setRowCount(len(students))
        for row, student in enumerate(students):
            roll_item = QTableWidgetItem(str(student.roll_number))
            roll_item.setData(Qt.UserRole, student.id)
            self.table.setItem(row, 0, roll_item)
            self.table.setItem(row, 1, QTableWidgetItem(student.admission_number))
            self.table.setItem(row, 2, QTableWidgetItem(student.name))
            self.table.setItem(row, 3, QTableWidgetItem(student.father_name or "-"))

            class_obj = self.setup_repo.get_class_by_id(student.class_id)
            self.table.setItem(row, 4, QTableWidgetItem(class_obj.name if class_obj else "-"))

            section_obj = self.setup_repo.get_section_by_id(student.section_id)
            self.table.setItem(row, 5, QTableWidgetItem(section_obj.name if section_obj else "-"))

            self.table.setItem(row, 6, QTableWidgetItem("Active" if student.active else "Inactive"))

            # Action buttons
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            edit_btn = QPushButton("Edit")
            edit_btn.clicked.connect(lambda checked, r=row: self._edit_student_from_row(r))
            delete_btn = QPushButton("Delete Permanently" if not student.active else "Delete")
            if student.active:
                delete_btn.clicked.connect(lambda checked, r=row: self._delete_student_from_row(r))
            else:
                delete_btn.clicked.connect(lambda checked, r=row: self._permanently_delete_from_row(r))
            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(delete_btn)
            self.table.setCellWidget(row, 7, actions_widget)

    def add_student(self):
        dialog = StudentDialog(self)
        if dialog.exec() == QDialog.Accepted:
            values = dialog.get_values()
            result = self.student_repo.add_student(
                name=values['name'],
                roll_number=values['roll_number'],
                father_name=values['father_name'],
                mother_name=values['mother_name'],
                date_of_birth=values.get('date_of_birth'),
                address=values.get('address'),
                session_id=values['session_id'],
                class_id=values['class_id'],
                section_id=values['section_id']
            )
            if result:
                self.refresh_students()
                QMessageBox.information(self, "Success", "Student added successfully!")
            else:
                QMessageBox.warning(self, "Error", "Roll number already exists!")

    def bulk_student_entry(self):
        dialog = BulkStudentEntryDialog(
            self.setup_repo, self.student_repo, parent=self
        )
        if dialog.exec() != QDialog.Accepted:
            return

        for combo, selected_id in (
            (self.session_combo, dialog.session_combo.currentData()),
            (self.class_combo, dialog.class_combo.currentData()),
            (self.section_combo, dialog.section_combo.currentData()),
        ):
            index = combo.findData(selected_id)
            if index >= 0:
                combo.setCurrentIndex(index)
        self.refresh_students()
        QMessageBox.information(
            self,
            "Bulk Import Complete",
            f"Successfully imported {dialog.imported_count} student(s).",
        )

    def edit_student(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Warning", "Please select a student to edit.")
            return
        self._edit_student_from_row(row)

    def _edit_student_from_row(self, row):
        student_id = self.table.item(row, 0).data(Qt.UserRole)
        student = self.student_repo.get_student_by_id(student_id)
        if not student:
            QMessageBox.warning(self, "Error", "Student not found!")
            return

        dialog = StudentDialog(self, student=student)
        if dialog.exec() == QDialog.Accepted:
            values = dialog.get_values()
            result = self.student_repo.update_student(
                student_id=student_id,
                name=values['name'],
                roll_number=values['roll_number'],
                father_name=values['father_name'],
                mother_name=values['mother_name'],
                date_of_birth=values.get('date_of_birth'),
                address=values.get('address'),
                session_id=values['session_id'],
                class_id=values['class_id'],
                section_id=values['section_id']
            )
            if result:
                self.refresh_students()
                QMessageBox.information(self, "Success", "Student updated successfully!")
            elif result is False:
                QMessageBox.warning(self, "Error", "Roll number already exists!")

    def delete_student(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Warning", "Please select a student to delete.")
            return
        self._delete_student_from_row(row)

    def _delete_student_from_row(self, row):
        student_id = self.table.item(row, 0).data(Qt.UserRole)
        student = self.student_repo.get_student_by_id(student_id)
        if not student:
            QMessageBox.warning(self, "Error", "Student not found!")
            return

        reply = QMessageBox.question(self, "Confirm Deactivation",
                                     f"Are you sure you want to deactivate student '{student.name}'?\n\nThis will not delete historical records.",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.student_repo.delete_student(student_id)
            self.refresh_students()
            QMessageBox.information(self, "Success", "Student deactivated successfully!")

    def permanently_delete_student(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Warning", "Please select a student to delete permanently.")
            return
        self._permanently_delete_from_row(row)

    def _permanently_delete_from_row(self, row):
        student_id = self.table.item(row, 0).data(Qt.UserRole)
        student = self.student_repo.get_student_by_id(student_id)
        if not student:
            QMessageBox.warning(self, "Error", "Student not found!")
            return
        if student.active:
            QMessageBox.warning(
                self, "Deactivate First",
                "Only inactive students can be deleted permanently.\n"
                "Deactivate the student first, then tick 'Show inactive'."
            )
            return

        typed, ok = QInputDialog.getText(
            self, "Delete Permanently",
            f"This permanently deletes '{student.name}' and ALL of their marks and report-card data. "
            f"This cannot be undone (a backup is created first).\n\n"
            f"Type the admission number ({student.admission_number}) to confirm:"
        )
        if not ok:
            return
        if typed.strip() != student.admission_number:
            QMessageBox.warning(self, "Cancelled", "Admission number did not match. Nothing was deleted.")
            return

        backup_path = Path(DATABASE_PATH).with_name(
            f"backup_pre_student_delete_{datetime.now():%Y%m%d_%H%M%S_%f}.db"
        )
        try:
            create_database_backup(DATABASE_PATH, backup_path)
            self.student_repo.permanently_delete_student(student_id)
        except Exception as error:
            QMessageBox.critical(self, "Delete Failed", f"Nothing was deleted.\n\n{error}")
            return
        self.refresh_students()
        QMessageBox.information(
            self, "Deleted", f"Student deleted permanently.\n\nSafety backup:\n{backup_path}"
        )

    def export_csv(self):
        """Export student list to CSV"""
        from datetime import datetime
        students = self.student_repo.get_students(
            session_id=self.session_combo.currentData(),
            class_id=self.class_combo.currentData(),
            section_id=self.section_combo.currentData(),
            keyword=self.search_input.text().strip() or None,
        )
        if not students:
            QMessageBox.warning(self, "Warning", "No students to export!")
            return

        filename = f"students_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Students",
            filename,
            "CSV files (*.csv)",
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as output_file:
                writer = csv.writer(output_file)
                writer.writerow([
                    "Roll Number", "Admission Number", "Name", "Father's Name",
                    "Mother's Name", "Date of Birth", "Address", "Session",
                    "Class", "Section", "Status",
                ])
                for s in students:
                    class_obj = self.setup_repo.get_class_by_id(s.class_id)
                    section_obj = self.setup_repo.get_section_by_id(s.section_id)
                    session_obj = self.setup_repo.get_session_by_id(s.session_id)
                    row = (
                        s.roll_number,
                        s.admission_number,
                        s.name,
                        s.father_name,
                        s.mother_name,
                        s.date_of_birth.isoformat() if s.date_of_birth else "",
                        s.address,
                        session_obj.name if session_obj else "",
                        class_obj.name if class_obj else "",
                        section_obj.name if section_obj else "",
                        "Active" if s.active else "Inactive",
                    )
                    writer.writerow([spreadsheet_safe(value) for value in row])
            QMessageBox.information(self, "Success", f"Exported to {path}")
        except OSError as error:
            QMessageBox.critical(self, "Error", f"Export failed: {error}")


class StudentDialog(QDialog):
    def __init__(self, parent=None, student=None):
        super().__init__(parent)
        self.student = student
        self.setup_repo = AcademicSetupRepository()
        self.init_ui()
        if student:
            self.load_student(student)

    def init_ui(self):
        self.setWindowTitle("Student" + (" Edit" if self.student else " Add"))
        layout = QFormLayout()

        self.name_input = QLineEdit()
        self.roll_input = QLineEdit()
        self.father_input = QLineEdit()
        self.mother_input = QLineEdit()
        self.dob_checkbox = QCheckBox("Known")
        self.dob_input = QDateEdit()
        self.dob_input.setCalendarPopup(True)
        self.dob_input.setDisplayFormat("dd-MM-yyyy")
        self.dob_input.setDate(QDate.currentDate())
        self.dob_input.setEnabled(False)
        self.dob_checkbox.toggled.connect(self.dob_input.setEnabled)
        dob_layout = QHBoxLayout()
        dob_layout.addWidget(self.dob_checkbox)
        dob_layout.addWidget(self.dob_input)
        dob_widget = QWidget()
        dob_widget.setLayout(dob_layout)
        self.address_input = QLineEdit()

        self.session_combo = QComboBox()
        self.class_combo = QComboBox()
        self.section_combo = QComboBox()
        self._populate_cascade()

        self.session_combo.currentIndexChanged.connect(self._on_session_changed)
        self.class_combo.currentIndexChanged.connect(self._on_class_changed)
        self._on_session_changed(self.session_combo.currentIndex())

        layout.addRow("Name:", self.name_input)
        layout.addRow("Roll Number:", self.roll_input)
        layout.addRow("Father's Name:", self.father_input)
        layout.addRow("Mother's Name:", self.mother_input)
        layout.addRow("Date of Birth:", dob_widget)
        layout.addRow("Address:", self.address_input)
        layout.addRow("Session:", self.session_combo)
        layout.addRow("Class:", self.class_combo)
        layout.addRow("Section:", self.section_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def _populate_cascade(self):
        """Populate session dropdown"""
        sessions = self.setup_repo.get_all_sessions()
        for session in sessions:
            self.session_combo.addItem(session.name, session.id)

    def _on_session_changed(self, index):
        """Refresh classes when session changes"""
        self.class_combo.clear()
        session_id = self.session_combo.currentData()
        classes = self.setup_repo.get_all_classes()
        for cls in classes:
            self.class_combo.addItem(cls.name, cls.id)

    def _on_class_changed(self, index):
        """Refresh sections when class changes"""
        self.section_combo.clear()
        session_id = self.session_combo.currentData()
        class_id = self.class_combo.currentData()
        if session_id and class_id:
            sections = self.setup_repo.get_sections_by_class_and_session(class_id, session_id)
            for section in sections:
                self.section_combo.addItem(section.name, section.id)

    def load_student(self, student):
        """Load student data into form"""
        self.name_input.setText(student.name)
        self.roll_input.setText(str(student.roll_number))
        self.father_input.setText(student.father_name or "")
        self.mother_input.setText(student.mother_name or "")
        self.address_input.setText(student.address or "")
        if student.date_of_birth:
            self.dob_checkbox.setChecked(True)
            self.dob_input.setDate(QDate(
                student.date_of_birth.year,
                student.date_of_birth.month,
                student.date_of_birth.day,
            ))
        if student.session_id:
            for i in range(self.session_combo.count()):
                if self.session_combo.itemData(i) == student.session_id:
                    self.session_combo.setCurrentIndex(i)
                    break
        if student.class_id:
            for i in range(self.class_combo.count()):
                if self.class_combo.itemData(i) == student.class_id:
                    self.class_combo.setCurrentIndex(i)
                    break
        if student.section_id:
            for i in range(self.section_combo.count()):
                if self.section_combo.itemData(i) == student.section_id:
                    self.section_combo.setCurrentIndex(i)
                    break

    def get_values(self):
        roll_text = self.roll_input.text().strip()
        return {
            'name': self.name_input.text().strip(),
            'roll_number': int(roll_text) if roll_text.isdigit() else None,
            'father_name': self.father_input.text().strip() or None,
            'mother_name': self.mother_input.text().strip() or None,
            'date_of_birth': self.dob_input.date().toPython() if self.dob_checkbox.isChecked() else None,
            'address': self.address_input.text().strip() or None,
            'session_id': self.session_combo.currentData(),
            'class_id': self.class_combo.currentData(),
            'section_id': self.section_combo.currentData()
        }

    def accept(self):
        values = self.get_values()
        if not values['name']:
            QMessageBox.warning(self, "Invalid Student", "Enter the student's name.")
            return
        if values['roll_number'] is None or values['roll_number'] <= 0:
            QMessageBox.warning(self, "Invalid Student", "Enter a positive roll number.")
            return
        if not all((values['session_id'], values['class_id'], values['section_id'])):
            QMessageBox.warning(self, "Invalid Student", "Select a session, class, and section.")
            return
        super().accept()
