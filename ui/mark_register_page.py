from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QComboBox, QPushButton, QTableWidget, QTableWidgetItem)
from repositories.student import StudentRepository
from repositories.examination import ExamRepository
from repositories.mark import MarkRepository
from services.calculation import CalculationService

class MarkRegisterPage(QWidget):
    def __init__(self):
        super().__init__()
        self.student_repo = StudentRepository()
        self.exam_repo = ExamRepository()
        self.mark_repo = MarkRepository()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Mark Register & Results Summary"))

        # Filter controls
        filter_layout = QHBoxLayout()
        self.exam_combo = QComboBox()
        self.load_exams()
        filter_layout.addWidget(QLabel("Exam:"))
        filter_layout.addWidget(self.exam_combo)

        load_btn = QPushButton("Generate Register")
        load_btn.clicked.connect(self.generate_register)
        filter_layout.addWidget(load_btn)

        layout.addLayout(filter_layout)

        # Register Grid
        self.table = QTableWidget()
        layout.addWidget(self.table)

        self.setLayout(layout)

    def load_exams(self):
        self.exam_combo.clear()
        exams = self.exam_repo.get_exams()
        for exam in exams:
            self.exam_combo.addItem(exam.name, exam.id)

    def generate_register(self):
        students = self.student_repo.get_students()
        exam_id = self.exam_combo.currentData()
        if not exam_id:
            return

        self.table.setRowCount(len(students))
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Roll No", "Student Name", "Marks Obtained", "Percentage", "Grade", "Status"])

        for row, student in enumerate(students):
            # Fetch marks for this student
            marks = self.mark_repo.get_marks(subject_id=1, component_id=1, student_ids=[student.id])
            obtained = float(marks[0].marks_obtained) if marks else 0.0
            max_marks = 100.0 # Standard assumed max for demo

            percentage = CalculationService.calculate_percentage(obtained, max_marks)
            grade = CalculationService.get_grade(percentage)

            self.table.setItem(row, 0, QTableWidgetItem(str(student.roll_number)))
            self.table.setItem(row, 1, QTableWidgetItem(student.name))
            self.table.setItem(row, 2, QTableWidgetItem(CalculationService.format_marks(obtained)))
            self.table.setItem(row, 3, QTableWidgetItem(f"{percentage:.2f}%"))
            self.table.setItem(row, 4, QTableWidgetItem(grade))
            self.table.setItem(row, 5, QTableWidgetItem("Complete" if marks else "Pending"))
