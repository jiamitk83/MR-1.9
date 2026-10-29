from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QComboBox, QPushButton, QTableWidget, QTableWidgetItem, QMessageBox)
from repositories.student import StudentRepository
from repositories.examination import ExamRepository
from repositories.mark import MarkRepository
from services.calculation import CalculationService

class MarksEntryPage(QWidget):
    def __init__(self):
        super().__init__()
        self.student_repo = StudentRepository()
        self.exam_repo = ExamRepository()
        self.mark_repo = MarkRepository()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Marks Entry Module"))

        # Filter controls
        filter_layout = QHBoxLayout()

        self.exam_combo = QComboBox()
        self.load_exams()
        filter_layout.addWidget(QLabel("Exam:"))
        filter_layout.addWidget(self.exam_combo)

        load_btn = QPushButton("Load Students")
        load_btn.clicked.connect(self.load_students_grid)
        filter_layout.addWidget(load_btn)

        layout.addLayout(filter_layout)

        # Student Marks Grid
        self.table = QTableWidget()
        layout.addWidget(self.table)

        # Save Button
        save_btn = QPushButton("Save Marks")
        save_btn.clicked.connect(self.save_marks)
        layout.addWidget(save_btn)

        self.setLayout(layout)

    def load_exams(self):
        self.exam_combo.clear()
        exams = self.exam_repo.get_exams()
        for exam in exams:
            self.exam_combo.addItem(exam.name, exam.id)

    def load_students_grid(self):
        students = self.student_repo.get_students()
        self.table.setRowCount(len(students))
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Roll No", "Student Name", "Marks Obtained", "Status"])

        self.student_rows = students
        for row, student in enumerate(students):
            self.table.setItem(row, 0, QTableWidgetItem(str(student.roll_number)))
            self.table.setItem(row, 1, QTableWidgetItem(student.name))

            # Default input
            marks_item = QTableWidgetItem(CalculationService.format_marks(0))
            self.table.setItem(row, 2, marks_item)

            status_item = QTableWidgetItem("Entered")
            self.table.setItem(row, 3, status_item)

    def save_marks(self):
        if not hasattr(self, 'student_rows') or not self.student_rows:
            QMessageBox.warning(self, "Warning", "No students loaded!")
            return

        exam_id = self.exam_combo.currentData()
        if not exam_id:
            QMessageBox.warning(self, "Warning", "Please select an examination!")
            return

        marks_data = []
        try:
            for row, student in enumerate(self.student_rows):
                val_str = self.table.item(row, 2).text().strip()
                marks_val = float(val_str)
                formatted_marks = CalculationService.format_marks(marks_val)

                marks_data.append({
                    'student_id': student.id,
                    'subject_id': 1, # Default subject for now
                    'component_id': 1, # Default component for now
                    'marks_obtained': float(formatted_marks),
                    'is_absent': False
                })

            success = self.mark_repo.save_marks_batch(marks_data)
            if success:
                QMessageBox.information(self, "Success", "Marks saved successfully with strict 2-decimal precision!")
            else:
                QMessageBox.critical(self, "Error", "Failed to save marks.")
        except ValueError:
            QMessageBox.warning(self, "Validation Error", "Please enter valid numeric marks for all students!")
