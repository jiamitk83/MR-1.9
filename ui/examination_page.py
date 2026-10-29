from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QLabel
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

        self.exam_input = QLineEdit()
        self.exam_input.setPlaceholderText("Exam Name (e.g. Half Yearly)")
        layout.addWidget(self.exam_input)

        add_btn = QPushButton("Create Examination")
        add_btn.clicked.connect(self.create_exam)
        layout.addWidget(add_btn)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["ID", "Name"])
        layout.addWidget(self.table)

        self.setLayout(layout)
        self.refresh_table()

    def create_exam(self):
        name = self.exam_input.text()
        if name:
            # For now, default to session_id=1 (must improve later)
            self.exam_repo.create_exam(name, 1)
            self.refresh_table()

    def refresh_table(self):
        exams = self.exam_repo.get_exams()
        self.table.setRowCount(len(exams))
        for row, exam in enumerate(exams):
            self.table.setItem(row, 0, QTableWidgetItem(str(exam.id)))
            self.table.setItem(row, 1, QTableWidgetItem(exam.name))
