from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, QComboBox)
from repositories.student import StudentRepository
from repositories.academic_setup import AcademicSetupRepository

class StudentMasterPage(QWidget):
    def __init__(self):
        super().__init__()
        self.student_repo = StudentRepository()
        self.setup_repo = AcademicSetupRepository()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Input form
        form_layout = QHBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Student Name")
        self.roll_input = QLineEdit()
        self.roll_input.setPlaceholderText("Roll Number")

        self.father_input = QLineEdit()
        self.father_input.setPlaceholderText("Father's Name (Optional)")

        add_btn = QPushButton("Add Student")
        add_btn.clicked.connect(self.add_student)

        form_layout.addWidget(self.name_input)
        form_layout.addWidget(self.roll_input)
        form_layout.addWidget(self.father_input)
        form_layout.addWidget(add_btn)

        layout.addLayout(form_layout)

        # Student Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Adm No", "Roll No", "Name", "Father's Name"])
        layout.addWidget(self.table)

        self.setLayout(layout)
        self.refresh_table()

    def add_student(self):
        name = self.name_input.text().strip()
        roll = self.roll_input.text().strip()
        father = self.father_input.text().strip()

        if not name or not roll:
            QMessageBox.warning(self, "Validation Error", "Name and Roll Number are required!")
            return

        try:
            roll_no = int(roll)
            self.student_repo.add_student(name=name, roll_number=roll_no, father_name=father)
            self.name_input.clear()
            self.roll_input.clear()
            self.father_input.clear()
            self.refresh_table()
        except ValueError:
            QMessageBox.warning(self, "Validation Error", "Roll Number must be an integer!")

    def refresh_table(self):
        students = self.student_repo.get_students()
        self.table.setRowCount(len(students))
        for row, student in enumerate(students):
            self.table.setItem(row, 0, QTableWidgetItem(student.admission_number))
            self.table.setItem(row, 1, QTableWidgetItem(str(student.roll_number)))
            self.table.setItem(row, 2, QTableWidgetItem(student.name))
            self.table.setItem(row, 3, QTableWidgetItem(student.father_name or ""))
