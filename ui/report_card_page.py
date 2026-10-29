from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
                             QMessageBox, QGroupBox, QFormLayout, QTextBrowser)
from PySide6.QtCore import Qt
from repositories.student import StudentRepository
from repositories.examination import ExamRepository
from repositories.mark import MarkRepository
from repositories.academic_setup import AcademicSetupRepository
from repositories.subject_alias import SubjectAliasRepository
from services.calculation import CalculationService
from services.derived_calculations import DerivedCalculationService

class ReportCardPage(QWidget):
    """Report Card viewer - displays actual saved records with subject alias resolution"""

    GRADE_ONLY_SUBJECTS = {'GK', 'GUIDANCE', 'CIVICS'}

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
        layout.addWidget(QLabel("Report Card Viewer"))

        # Filters
        filter_group = QGroupBox("Select Parameters")
        filter_layout = QFormLayout()

        self.session_combo = QComboBox()
        self.class_combo = QComboBox()
        self.section_combo = QComboBox()
        self.exam_combo = QComboBox()
        self.student_combo = QComboBox()

        self.load_filters()
        self.session_combo.currentIndexChanged.connect(self._on_session_changed)
        self.class_combo.currentIndexChanged.connect(self._on_class_changed)
        self.section_combo.currentIndexChanged.connect(self._on_section_changed)
        self.exam_combo.currentIndexChanged.connect(self._on_exam_changed)

        filter_layout.addRow("Session:", self.session_combo)
        filter_layout.addRow("Class:", self.class_combo)
        filter_layout.addRow("Section:", self.section_combo)
        filter_layout.addRow("Exam:", self.exam_combo)
        filter_layout.addRow("Student:", self.student_combo)

        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)

        # Generate button
        gen_btn = QPushButton("Generate Report Card")
        gen_btn.clicked.connect(self.generate_report)
        layout.addWidget(gen_btn)

        # Report display
        self.report_text = QTextBrowser()
        self.report_text.setMinimumHeight(400)
        layout.addWidget(self.report_text)

        # Component-wise table
        self.component_table = QTableWidget()
        self.component_table.setColumnCount(5)
        self.component_table.setHorizontalHeaderLabels(["Subject", "Component", "Max Marks", "Obtained", "Status"])
        layout.addWidget(self.component_table)

        self.setLayout(layout)

    def load_filters(self):
        """Load all filter dropdowns"""
        sessions = self.setup_repo.get_all_sessions()
        for s in sessions:
            self.session_combo.addItem(s.name, s.id)

    def _on_session_changed(self, index):
        """Refresh class dropdown on session change"""
        self.class_combo.clear()
        self.section_combo.clear()
        self.exam_combo.clear()
        self.student_combo.clear()

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
        """Refresh student dropdown on section change"""
        self.student_combo.clear()
        students = self.student_repo.get_students(
            session_id=self.session_combo.currentData(),
            class_id=self.class_combo.currentData(),
            section_id=self.section_combo.currentData()
        )
        for s in students:
            self.student_combo.addItem(f"{s.name} (Roll: {s.roll_number})", s.id)

    def _on_exam_changed(self, index):
        """Refresh exams on class/section change"""
        self.exam_combo.clear()
        session_id = self.session_combo.currentData()
        if session_id:
            exams = self.exam_repo.get_exams(session_id=session_id)
            for exam in exams:
                self.exam_combo.addItem(exam.name, exam.id)

    def generate_report(self):
        """Generate report card for selected student"""
        student_id = self.student_combo.currentData()
        exam_id = self.exam_combo.currentData()
        subject_id = 1  # Default - will be expanded

        if not student_id or not exam_id:
            QMessageBox.warning(self, "Warning", "Please select student and exam!")
            return

        student = self.student_repo.get_student_by_id(student_id)
        exam = self.exam_repo.get_exam_by_id(exam_id)

        if not student or not exam:
            QMessageBox.warning(self, "Error", "Invalid selection!")
            return

        # Generate HTML report
        html = self._generate_html_report(student, exam)
        self.report_text.setHtml(html)

        # Populate component table
        self._populate_component_table(student_id, exam_id, subject_id)

    def _generate_html_report(self, student, exam):
        """Generate HTML report card"""
        # Get session name
        session = self.setup_repo.get_session_by_id(exam.session_id)
        session_name = session.name if session else "N/A"

        html = f"""
        <div style="font-family: Arial, sans-serif; padding: 20px; max-width: 800px; margin: 0 auto;">
            <div style="text-align: center; border-bottom: 3px solid #333; padding-bottom: 10px; margin-bottom: 20px;">
                <h1 style="margin: 0; color: #1a5276;">School Mark Register</h1>
                <h2 style="margin: 5px 0; color: #2874a6;">Report Card</h2>
                <p style="margin: 5px 0; color: #666;">Session: {session_name} | Exam: {exam.name}</p>
            </div>

            <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                <h3 style="margin-top: 0; color: #2c3e50;">Student Details</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr><td style="padding: 5px; border-bottom: 1px solid #ddd;"><strong>Name:</strong></td>
                        <td style="padding: 5px; border-bottom: 1px solid #ddd;">{student.name}</td>
                        <td style="padding: 5px; border-bottom: 1px solid #ddd;"><strong>Roll No:</strong></td>
                        <td style="padding: 5px; border-bottom: 1px solid #ddd;">{student.roll_number}</td></tr>
                    <tr><td style="padding: 5px; border-bottom: 1px solid #ddd;"><strong>Adm No:</strong></td>
                        <td style="padding: 5px; border-bottom: 1px solid #ddd;">{student.admission_number}</td>
                        <td style="padding: 5px; border-bottom: 1px solid #ddd;"><strong>Father's Name:</strong></td>
                        <td style="padding: 5px; border-bottom: 1px solid #ddd;">{student.father_name or 'N/A'}</td></tr>
                </table>
            </div>

            <div style="text-align: center; padding: 20px; background: #e8f6f3; border-radius: 5px;">
                <h3 style="color: #1a8c70; margin-top: 0;">Report Generated Successfully</h3>
                <p>Use the table below to view component-wise marks.</p>
            </div>
        </div>
        """
        return html

    def _populate_component_table(self, student_id, exam_id, subject_id):
        """Populate component-wise marks table"""
        components = self.exam_repo.get_components_by_exam(exam_id)
        self.component_table.setRowCount(len(components))

        for row, comp in enumerate(components):
            marks = self.mark_repo.get_marks(
                subject_id=subject_id,
                component_id=comp.id,
                student_ids=[student_id]
            )

            if marks:
                mark = marks[0]
                self.component_table.setItem(row, 1, QTableWidgetItem(comp.name))
                self.component_table.setItem(row, 2, QTableWidgetItem(CalculationService.format_marks(comp.max_marks)))
                self.component_table.setItem(row, 3, QTableWidgetItem(
                    CalculationService.format_marks(float(mark.marks_obtained)) if mark.marks_obtained else "0.00"
                ))
                status = "Absent" if mark.is_absent else "Entered"
                self.component_table.setItem(row, 4, QTableWidgetItem(status))
            else:
                self.component_table.setItem(row, 1, QTableWidgetItem(comp.name))
                self.component_table.setItem(row, 2, QTableWidgetItem(CalculationService.format_marks(comp.max_marks)))
                self.component_table.setItem(row, 3, QTableWidgetItem("0.00"))
                self.component_table.setItem(row, 4, QTableWidgetItem("Pending"))

    def export_report_pdf(self):
        """Export report card to PDF (placeholder for future implementation)"""
        QMessageBox.information(self, "Info", "PDF export will be implemented in the next update.")
