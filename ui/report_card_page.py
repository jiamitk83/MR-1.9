import html
import logging
from datetime import date
from decimal import Decimal
from pathlib import Path

from PySide6.QtCore import QDate, QMarginsF, QSignalBlocker, Qt, QRectF
from PySide6.QtGui import QPageLayout, QPageSize, QPdfWriter, QPainter, QTextDocument
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QComboBox,
    QDateEdit,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from repositories.academic_setup import AcademicSetupRepository
from repositories.examination import ExamRepository
from repositories.mark import MarkRepository
from repositories.report_card import ReportCardRepository
from repositories.student import StudentRepository
from repositories.subject_alias import SubjectAliasRepository
from services.calculation import CalculationService
from services.derived_calculations import DerivedCalculationService
from services.half_yearly import HalfYearlyService


logger = logging.getLogger(__name__)

SCHOOL_NAME = "Seth Anandram Jaipuria School, New Jajmau"
SCHOOL_ADDRESS = "1500-1502 Kallupurwa, New Jajmau, Kanpur - Lucknow Road - 209801, Uttar Pradesh"
CO_SCHOLASTIC_AREAS = (
    "Music / Dance",
    "Health and Physical Education",
    "Work Ethics",
    "Value Education",
    "Art",
    "General Knowledge",
)
SUBJECT_SKILLS = {
    "english": ("Speaking and Listening", "Writing", "Reading"),
    "hindi": ("Speaking and Listening", "Writing", "Reading"),
    "mathematics": (
        "Reasoning and Problem Solving",
        "Spatial Visualization and Observation",
        "Numeracy",
    ),
    "math": (
        "Reasoning and Problem Solving",
        "Spatial Visualization and Observation",
        "Numeracy",
    ),
    "science": ("Observational", "Application", "Analytical"),
    "social science": (
        "Analytical",
        "Research Information / Mapping / Diagrams",
        "Problem Solving",
    ),
    "computer": ("Speaking and Listening", "Writing", "Reading"),
}


class ReportCardPage(QWidget):
    """Generate a printable report from saved student and examination records."""

    def __init__(self):
        super().__init__()
        self.student_repo = StudentRepository()
        self.exam_repo = ExamRepository()
        self.mark_repo = MarkRepository()
        self.setup_repo = AcademicSetupRepository()
        self.alias_repo = SubjectAliasRepository()
        self.report_repo = ReportCardRepository()
        self.derived_service = DerivedCalculationService()
        self.half_yearly_service = HalfYearlyService(self.derived_service)
        self._report_ready = False
        self._can_publish = False
        self._report_pages = []
        self._current_student = None
        self._current_exam = None
        self._current_results = []
        self._current_details = {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Report Card"))

        filter_group = QGroupBox("Select Parameters")
        filter_layout = QFormLayout(filter_group)
        self.session_combo = QComboBox()
        self.exam_combo = QComboBox()
        self.class_combo = QComboBox()
        self.section_combo = QComboBox()
        self.student_combo = QComboBox()
        filter_layout.addRow("Academic Session:", self.session_combo)
        filter_layout.addRow("Exam:", self.exam_combo)
        filter_layout.addRow("Class:", self.class_combo)
        filter_layout.addRow("Section:", self.section_combo)
        filter_layout.addRow("Student:", self.student_combo)
        layout.addWidget(filter_group)

        action_layout = QHBoxLayout()
        self.details_button = QPushButton("Edit Attendance and Remarks")
        self.details_button.setEnabled(False)
        self.details_button.clicked.connect(self.edit_report_details)
        generate_button = QPushButton("Generate Report Card")
        generate_button.clicked.connect(self.generate_report)
        self.export_button = QPushButton("Export PDF")
        self.export_button.setEnabled(False)
        self._can_publish = False
        self.export_button.clicked.connect(self.export_report_pdf)
        action_layout.addWidget(self.details_button)
        action_layout.addWidget(generate_button)
        action_layout.addWidget(self.export_button)
        action_layout.addStretch()
        layout.addLayout(action_layout)

        self.report_text = QTextBrowser()
        self.report_text.setMinimumHeight(300)
        layout.addWidget(self.report_text)

        self.component_table = QTableWidget()
        self.component_table.setColumnCount(5)
        self.component_table.setHorizontalHeaderLabels([
            "Subject", "Component", "Maximum", "Obtained", "Status",
        ])
        layout.addWidget(self.component_table)

        self.session_combo.currentIndexChanged.connect(self._on_session_changed)
        self.exam_combo.currentIndexChanged.connect(lambda _index: self._clear_report())
        self.class_combo.currentIndexChanged.connect(self._on_class_changed)
        self.section_combo.currentIndexChanged.connect(self._on_section_changed)
        self.student_combo.currentIndexChanged.connect(lambda _index: self._clear_report())
        self.refresh_data()

    def refresh_data(self):
        """Reload selectors from the database, keeping the current selection where possible."""
        previous = {
            "session": self.session_combo.currentData(),
            "exam": self.exam_combo.currentData(),
            "class": self.class_combo.currentData(),
            "section": self.section_combo.currentData(),
            "student": self.student_combo.currentData(),
        }
        with QSignalBlocker(self.session_combo):
            self.session_combo.clear()
            for academic_session in self.setup_repo.get_all_sessions():
                self.session_combo.addItem(academic_session.name, academic_session.id)
            index = self.session_combo.findData(previous["session"])
            if index >= 0:
                self.session_combo.setCurrentIndex(index)
        self._on_session_changed(self.session_combo.currentIndex())
        for key, combo in (
            ("exam", self.exam_combo),
            ("class", self.class_combo),
            ("section", self.section_combo),
        ):
            index = combo.findData(previous[key])
            if index >= 0 and index != combo.currentIndex():
                combo.setCurrentIndex(index)
        index = self.student_combo.findData(previous["student"])
        if index >= 0:
            self.student_combo.setCurrentIndex(index)

    def _on_session_changed(self, _index):
        session_id = self.session_combo.currentData()
        classes = self.setup_repo.get_all_classes() if session_id else []
        exams = self.exam_repo.get_exams(session_id=session_id) if session_id else []
        with QSignalBlocker(self.class_combo):
            self.class_combo.clear()
            for class_record in classes:
                self.class_combo.addItem(class_record.name, class_record.id)
        with QSignalBlocker(self.exam_combo):
            self.exam_combo.clear()
            for exam in exams:
                self.exam_combo.addItem(exam.name, exam.id)
        self._on_class_changed(self.class_combo.currentIndex())

    def _on_class_changed(self, _index):
        session_id = self.session_combo.currentData()
        class_id = self.class_combo.currentData()
        sections = (
            self.setup_repo.get_sections_by_class_and_session(class_id, session_id)
            if session_id and class_id else []
        )
        with QSignalBlocker(self.section_combo):
            self.section_combo.clear()
            for section in sections:
                self.section_combo.addItem(section.name, section.id)
        self._on_section_changed(self.section_combo.currentIndex())

    def _on_section_changed(self, _index):
        self.student_combo.clear()
        session_id = self.session_combo.currentData()
        class_id = self.class_combo.currentData()
        section_id = self.section_combo.currentData()
        if not all((session_id, class_id, section_id)):
            self._clear_report()
            return
        students = self.student_repo.get_students(
            session_id=session_id,
            class_id=class_id,
            section_id=section_id,
        )
        for student in students:
            self.student_combo.addItem(f"{student.name} (Roll: {student.roll_number})", student.id)
        self._clear_report()

    def _clear_report(self):
        self.report_text.clear()
        self.component_table.setRowCount(0)
        self._report_ready = False
        self._report_pages = []
        self._current_student = None
        self._current_exam = None
        self._current_results = []
        self._current_details = {}
        self.export_button.setEnabled(False)
        self.details_button.setEnabled(
            bool(self.student_combo.currentData() and self.exam_combo.currentData())
        )

    def generate_report(self):
        student_id = self.student_combo.currentData()
        exam_id = self.exam_combo.currentData()
        if not student_id or not exam_id:
            QMessageBox.warning(self, "Incomplete Selection", "Select an exam and student first.")
            return

        student = self.student_repo.get_student_by_id(student_id)
        exam = self.exam_repo.get_exam_by_id(exam_id)
        if (
            student is None
            or exam is None
            or exam.session_id != self.session_combo.currentData()
            or student.session_id != exam.session_id
        ):
            QMessageBox.warning(self, "Invalid Selection", "The selected student and exam do not match.")
            return

        try:
            results = self._get_report_results(student, exam)
            try:
                details = self.report_repo.get_details(student.id, exam.id)
            except SQLAlchemyError:
                logger.exception("Could not load report-card detail fields")
                QMessageBox.critical(self, "Report Error", "Attendance and remarks could not be loaded.")
                return
        except ValueError as error:
            QMessageBox.warning(self, "Subject Mapping Error", str(error))
            return
        except SQLAlchemyError:
            logger.exception("Could not load report card data")
            QMessageBox.critical(self, "Report Error", "Report data could not be loaded.")
            return

        self._current_student = student
        self._current_exam = exam
        self._current_results = results
        self._current_details = details
        self._report_pages = self._generate_report_pages(student, exam, results, details)
        self.report_text.setHtml("<hr>".join(self._report_pages))
        self._populate_component_table(results)
        self._report_ready = True
        self._can_publish = bool(results) and all(
            result["status"] in {"Complete", "Grade only"}
            for result in results
        )
        self.export_button.setEnabled(self._can_publish)
        self.details_button.setEnabled(True)

    def _get_report_results(self, student, exam):
        components = self.exam_repo.get_components_by_exam(exam.id)
        subjects = [
            subject for subject in self.setup_repo.get_all_subjects()
            if subject.is_active
        ]
        class_students = self.student_repo.get_students(
            session_id=student.session_id,
            class_id=student.class_id,
            section_id=student.section_id,
        )
        student_ids = [record.id for record in class_students]
        marks = self.mark_repo.get_marks_for_students(
            student_ids,
            subject_ids=[subject.id for subject in subjects],
            component_ids=[component.id for component in components],
        ) if components and subjects else []
        marks_by_key = {
            (mark.student_id, mark.subject_id, mark.component_id): mark
            for mark in marks
        }
        grade_marks_by_key = {}
        if exam.name.strip().casefold() == "half yearly":
            for subject in subjects:
                if HalfYearlyService.is_grade_only(subject):
                    grade_records = self.mark_repo.get_grade_marks(
                        exam.id, subject.id, student_ids
                    )
                    grade_marks_by_key.update({
                        (record.student_id, subject.id): record.grade
                        for record in grade_records
                    })
        results_by_student = {
            record.id: self._get_student_subject_results(
                record, exam, subjects, components, marks_by_key, grade_marks_by_key
            )
            for record in class_students
        }
        results = results_by_student.get(student.id)
        if results is None:
            results = self._get_student_subject_results(
                student, exam, subjects, components, marks_by_key, grade_marks_by_key
            )

        comparison_results = list(results_by_student.values())
        for result in results:
            peer_percentages = [
                peer_result["percentage_value"]
                for peer_results in comparison_results
                for peer_result in peer_results
                if peer_result["subject_id"] == result["subject_id"]
                and peer_result["status"] == "Complete"
                and peer_result["percentage_value"] is not None
            ]
            result["highest"] = max(peer_percentages) if peer_percentages else None
            result["average"] = (
                sum(peer_percentages, Decimal("0")) / len(peer_percentages)
                if peer_percentages else None
            )
        return results

    def _get_student_subject_results(
        self, student, exam, subjects, components, marks_by_key, grade_marks_by_key=None
    ):
        grade_marks_by_key = grade_marks_by_key or {}
        results = []
        for subject in subjects:
            display_name = self.alias_repo.get_display_name(subject.id) or subject.name
            subject_specific = [
                component for component in components
                if component.subject_id == subject.id
            ]
            generic_components = [
                component for component in components if component.subject_id is None
            ]
            subject_components = subject_specific or generic_components
            if exam.name.strip().casefold() == "half yearly":
                subject_components = subject_specific
                student_marks = {
                    component.id: marks_by_key.get(
                        (student.id, subject.id, component.id)
                    )
                    for component in components
                }
                student_marks = HalfYearlyService.map_legacy_component_marks(
                    subject_components,
                    generic_components,
                    student_marks,
                )
                student_marks["grade"] = grade_marks_by_key.get(
                    (student.id, subject.id)
                )
                result = self.half_yearly_service.calculate_subject_result(
                    student,
                    subject,
                    exam.session_id,
                    subject_components,
                    student_marks,
                )
                rows = [
                    {
                        "subject": display_name,
                        "component": row["name"],
                        "code": row["code"],
                        "maximum": row["maximum"],
                        "obtained": row["marks"],
                        "status": row["status"].title(),
                    }
                    for row in result["components"]
                ]
                results.append({
                    "subject_id": subject.id,
                    "subject": display_name,
                    "rows": rows,
                    "total": (
                        CalculationService.format_marks(result["total"])
                        if result["total"] is not None else "—"
                    ),
                    "maximum": result["maximum"],
                    "percentage": (
                        f"{result['percentage']:.2f}%"
                        if result["percentage"] is not None else "—"
                    ),
                    "percentage_value": result["percentage"],
                    "grade": result["grade"] or "—",
                    "status": result["status"],
                    "grade_only": result["grade_only"],
                })
                continue

            grade_only = CalculationService.is_grade_only_subject(subject)
            rows = []
            total_obtained = Decimal("0")
            total_maximum = Decimal("0")
            has_pending = False
            has_absent = False
            for component in subject_components:
                status = "Pending"
                obtained = None
                mark = marks_by_key.get((student.id, subject.id, component.id))
                if (
                    component.is_derived
                    and component.name.casefold() == "pt1"
                    and exam.name.casefold() == "half yearly"
                ):
                    derived = self.derived_service.calculate_pt1_derived(
                        student.id, subject.id, exam.session_id, exam.name
                    )
                    if derived["status"] == "calculated":
                        obtained, status = derived["marks"], "Calculated"
                    elif derived["status"] == "absent":
                        status = "Absent"
                elif (
                    component.is_derived
                    and component.name.casefold() == "pt2"
                    and exam.name.casefold() == "annual"
                ):
                    derived = self.derived_service.calculate_pt2_derived(
                        student.id, subject.id, exam.session_id, exam.name
                    )
                    if derived["status"] == "calculated":
                        obtained, status = derived["marks"], "Calculated"
                    elif derived["status"] == "absent":
                        status = "Absent"
                elif component.is_derived:
                    status = "Pending"
                elif mark is not None and mark.is_absent:
                    status = "Absent"
                elif mark is not None and mark.marks_obtained is not None:
                    obtained, status = mark.marks_obtained, "Entered"

                if status == "Pending":
                    has_pending = True
                elif status == "Absent":
                    has_absent = True
                elif obtained is not None:
                    total_obtained += Decimal(str(obtained))
                    total_maximum += Decimal(str(component.max_marks))

                rows.append({
                    "subject": display_name,
                    "component": component.name,
                    "maximum": component.max_marks,
                    "obtained": obtained,
                    "status": status,
                })

            if grade_only:
                total, percentage, grade, result_status = "—", "—", "—", "Grade only"
                percentage_value = None
            elif has_pending:
                total, percentage, grade, result_status = "—", "—", "—", "Pending"
                percentage_value = None
            elif has_absent:
                total, percentage, grade, result_status = "—", "—", "—", "Absent"
                percentage_value = None
            elif rows:
                percentage_value = CalculationService.calculate_percentage(total_obtained, total_maximum)
                total = CalculationService.format_marks(total_obtained)
                percentage = f"{percentage_value:.2f}%"
                grade = CalculationService.get_grade(percentage_value)
                result_status = "Complete"
            else:
                total, percentage, grade, result_status = "—", "—", "—", "Pending"
                percentage_value = None

            results.append({
                "subject_id": subject.id,
                "subject": display_name,
                "rows": rows,
                "total": total,
                "maximum": total_maximum if result_status == "Complete" else None,
                "percentage": percentage,
                "percentage_value": percentage_value,
                "grade": grade,
                "status": result_status,
                "grade_only": grade_only,
            })
        return results

    def _generate_report_pages(self, student, exam, results, details):
        academic_session = self.setup_repo.get_session_by_id(exam.session_id)
        session_name = academic_session.name if academic_session else "N/A"
        class_record = self.setup_repo.get_class_by_id(student.class_id)
        section_record = self.setup_repo.get_section_by_id(student.section_id)
        class_section = (
            f"{class_record.name if class_record else '—'} - "
            f"{section_record.name if section_record else '—'}"
        )
        components = self.exam_repo.get_components_by_exam(exam.id)
        half_yearly_subject_schemes = exam.name.strip().casefold() == "half yearly"
        subject_specific_scheme_exists = any(
            component.subject_id is not None for component in components
        )
        if half_yearly_subject_schemes and subject_specific_scheme_exists:
            component_by_code = {}
            for component in components:
                if component.subject_id is None:
                    continue
                code = (component.code or "").strip().upper()
                if code:
                    component_by_code.setdefault(code, component)
            code_order = ("PT1", "MA", "ENR", "PF", "WE", "PRAC", "THEORY")
            report_component_codes = [
                code for code in code_order if code in component_by_code
            ]
            headers = "".join(
                f"<th>{html.escape(component_by_code[code].name)}<br>"
                f"<small>({CalculationService.format_marks(component_by_code[code].max_marks)})</small></th>"
                for code in report_component_codes
            )
        elif half_yearly_subject_schemes:
            report_component_codes = []
            headers = "<th>Components / Grade</th>"
        else:
            report_component_codes = []
            headers = "".join(
                f"<th>{html.escape(component.name)}<br><small>({CalculationService.format_marks(component.max_marks)})</small></th>"
                for component in components
            )
        subject_rows = []
        numeric_results = [
            result for result in results
            if not result.get("grade_only", result["status"] != "Grade only")
        ]
        all_complete = bool(numeric_results) and all(
            result["status"] == "Complete" for result in numeric_results
        )
        total_obtained = sum(
            (Decimal(result["total"]) for result in numeric_results if result["status"] == "Complete"),
            Decimal("0"),
        )
        total_maximum = sum(
            (result["maximum"] for result in numeric_results if result["status"] == "Complete"),
            Decimal("0"),
        )
        for result in results:
            if half_yearly_subject_schemes:
                if subject_specific_scheme_exists:
                    result_rows_by_code = {
                        (row.get("code") or "").strip().upper(): row
                        for row in result["rows"]
                    }
                    mark_cells = "".join(
                        "<td>"
                        + html.escape(
                            (
                                CalculationService.format_marks(
                                    result_rows_by_code[code]["obtained"]
                                )
                                if result_rows_by_code[code]["obtained"] is not None
                                else result_rows_by_code[code]["status"]
                            )
                            if code in result_rows_by_code else "—"
                        )
                        + "</td>"
                        for code in report_component_codes
                    )
                else:
                    grade_cell = (
                        f"Grade: {html.escape(result['grade'])}"
                        if result.get("grade_only") and result["grade"] != "—"
                        else "Not Configured"
                    )
                    mark_cells = f"<td>{grade_cell}</td>"
            else:
                mark_cells = "".join(
                    f"<td>{html.escape(CalculationService.format_marks(row['obtained']) if row['obtained'] is not None else '—')}</td>"
                    for row in result["rows"]
                )
            subject_rows.append(
                f"<tr><td>{html.escape(result['subject'])}</td>{mark_cells}"
                f"<td>{html.escape(result['total'])}</td>"
                f"<td>{html.escape(result['grade'] if result['grade'] != '—' else result['status'])}</td></tr>"
            )
        overall_percentage = (
            CalculationService.calculate_percentage(total_obtained, total_maximum)
            if all_complete and total_maximum else None
        )
        overall_grade = (
            CalculationService.get_grade(overall_percentage)
            if overall_percentage is not None else "Pending"
        )
        overall_total = (
            f"{CalculationService.format_marks(total_obtained)} / "
            f"{CalculationService.format_marks(total_maximum)}"
            if all_complete else "Pending"
        )
        overall_percent_text = f"{overall_percentage:.2f}%" if overall_percentage is not None else "—"
        dob = student.date_of_birth.strftime("%Y-%m-%d") if student.date_of_birth else "—"
        grades = (
            ("91 - 100", "A1"), ("81 - 90", "A2"), ("71 - 80", "B1"),
            ("61 - 70", "B2"), ("51 - 60", "C1"), ("41 - 50", "C2"),
            ("33 - 40", "D"), ("32 and below", "E"),
        )
        grade_rows = "".join(
            f"<tr><td>{lower}</td><td>{grade}</td></tr>" for lower, grade in grades
        )
        comparison_rows = []
        for result in results:
            my_marks = self._format_percentage(result["percentage_value"])
            highest = self._format_percentage(result["highest"])
            average = self._format_percentage(result["average"])
            comparison_rows.append(
                "<tr>"
                f"<td>{html.escape(result['subject'])}</td>"
                f"<td>{html.escape(my_marks)}</td>"
                f"<td>{html.escape(highest)}</td>"
                f"<td>{html.escape(average)}</td>"
                "</tr>"
            )
        co_scholastic = details.get("co_scholastic", {})
        co_scholastic_rows = "".join(
            f"<tr><td>{html.escape(area)}</td><td>{html.escape(co_scholastic.get(area, '') or '—')}</td></tr>"
            for area in CO_SCHOLASTIC_AREAS
        )
        subject_remarks = details.get("subject_remarks", {})
        remark_rows = []
        for result in results:
            remarks = subject_remarks.get(str(result["subject_id"]), {})
            skills = self._skills_for_subject(result["subject"])
            for skill in skills:
                remark_rows.append(
                    f"<tr><td>{html.escape(result['subject'])}</td>"
                    f"<td>{html.escape(skill)}</td>"
                    f"<td>{html.escape(remarks.get(skill, '') or '—')}</td></tr>"
                )
        present = details.get("days_present")
        absent = details.get("days_absent")
        working = details.get("working_days")
        attendance_percentage = (
            Decimal(present) / Decimal(working) * 100
            if present is not None and working else None
        )
        attendance_text = f"{attendance_percentage:.0f}%" if attendance_percentage is not None else "—"
        attendance_present = present if present is not None else "—"
        attendance_absent = absent if absent is not None else "—"
        attendance_working = working if working is not None else "—"
        issue_date = details.get("issue_date") or date.today()
        issue_text = issue_date.strftime("%d-%m-%Y")
        class_teacher = html.escape(details.get("class_teacher") or "—")
        style = """
        <style>
        body { font-family: Arial, sans-serif; color: #17212b; font-size: 9pt; }
        h1 { font-size: 13pt; text-align: center; margin: 2px 0; }
        h2 { font-size: 12pt; margin: 10px 0 5px; }
        .school-address, .term { text-align: center; margin: 2px 0 6px; }
        .term { font-weight: bold; font-size: 12pt; }
        table { width: 100%; border-collapse: collapse; margin: 5px 0 9px; }
        th, td { border: 1px solid #455a64; padding: 3px; text-align: left; }
        th { background: #e8eef4; }
        .marks th, .marks td { text-align: center; }
        .student td { border: 0; padding: 3px 4px; }
        .totals th, .totals td { text-align: center; }
        .small { font-size: 8pt; }
        .signatures { margin-top: 24px; }
        .signatures td { border: 0; padding-top: 22px; }
        </style>
        """
        page_one = f"""
        <html><head>{style}</head><body>
        <h1>{html.escape(SCHOOL_NAME)}</h1>
        <p class="school-address">{html.escape(SCHOOL_ADDRESS)}</p>
        <p class="term">{html.escape(exam.name)} — {html.escape(session_name)}</p>
        <table class="student" width="100%">
          <tr><td><b>ADMISSION NO.</b> {html.escape(student.admission_number)}</td>
              <td><b>STUDENT'S NAME</b> {html.escape(student.name)}</td>
              <td><b>CLASS &amp; SECTION</b> {html.escape(class_section)}</td></tr>
          <tr><td><b>DATE OF BIRTH</b> {html.escape(dob)}</td>
              <td><b>ROLL NO.</b> {student.roll_number}</td>
              <td><b>FATHER'S NAME</b> {html.escape(student.father_name or '—')}</td></tr>
          <tr><td><b>MOTHER'S NAME</b> {html.escape(student.mother_name or '—')}</td>
              <td colspan="2"><b>ADDRESS</b> {html.escape(student.address or '—')}</td></tr>
        </table>
        <h2>Scholastic Performance — {html.escape(exam.name)}</h2>
        <table class="marks" width="100%"><thead><tr><th>Subject</th>{headers}<th>Total</th><th>Grade</th></tr></thead>
        <tbody>{"".join(subject_rows)}</tbody></table>
        <table class="totals" width="100%">
          <tr><th>MARKS OBTAINED</th><th>PERCENTAGE</th><th>OVERALL GRADE</th></tr>
          <tr><td>{html.escape(overall_total)}</td><td>{html.escape(overall_percent_text)}</td><td>{html.escape(overall_grade)}</td></tr>
        </table>
        <h2>Key to Grades — Scholastic Areas</h2>
        <table class="small"><thead><tr><th>MARKS RANGE</th><th>GRADE</th></tr></thead>
        <tbody>{grade_rows}</tbody></table>
        </body></html>
        """
        page_two = f"""
        <html><head>{style}</head><body>
        <h1>{html.escape(SCHOOL_NAME)}</h1>
        <p class="term">{html.escape(student.name)} — {html.escape(class_section)} — {html.escape(student.admission_number)}</p>
        <p class="school-address">{html.escape(exam.name)} — {html.escape(session_name)}</p>
        <h2>Comparative Performance</h2>
        <table width="100%"><thead><tr><th>Subject</th><th>My Marks (%)</th><th>Highest (%)</th><th>Average (%)</th></tr></thead>
        <tbody>{"".join(comparison_rows)}</tbody></table>
        <h2>Co-Scholastic &amp; Attendance</h2>
        <table width="100%"><thead><tr><th>Area</th><th>Assessment</th></tr></thead>
        <tbody>{co_scholastic_rows}</tbody></table>
        <p><b>ATTENDANCE</b> {attendance_text}
        &nbsp; Present: {attendance_present} &nbsp; Absent: {attendance_absent}
        &nbsp; Working Days: {attendance_working}</p>
        <h2>Skills &amp; Subject Remarks</h2>
        <table width="100%"><thead><tr><th>Subject</th><th>Skill</th><th>Remark</th></tr></thead>
        <tbody>{"".join(remark_rows)}</tbody></table>
        <p>Date of Issue: {html.escape(issue_text)}</p>
        <table class="signatures" width="100%"><tr><td>Class Teacher<br>{class_teacher}</td><td>Class Teacher's Signature</td><td>Principal's Signature</td></tr></table>
        </body></html>
        """
        return [page_one, page_two]

    @staticmethod
    def _skills_for_subject(subject_name):
        normalized = subject_name.strip().casefold()
        return SUBJECT_SKILLS.get(normalized, ("Remarks",))

    @staticmethod
    def _format_percentage(value):
        return f"{value:.2f}" if value is not None else "—"

    def edit_report_details(self):
        student_id = self.student_combo.currentData()
        exam_id = self.exam_combo.currentData()
        if not student_id or not exam_id:
            QMessageBox.warning(
                self,
                "Incomplete Selection",
                "Select a session, exam, class, section, and student first.",
            )
            return
        student = self.student_repo.get_student_by_id(student_id)
        exam = self.exam_repo.get_exam_by_id(exam_id)
        if student is None or exam is None or student.session_id != exam.session_id:
            QMessageBox.warning(self, "Invalid Selection", "The selected student and exam do not match.")
            return

        subjects = [
            (
                subject.id,
                self.alias_repo.get_display_name(subject.id) or subject.name,
            )
            for subject in self.setup_repo.get_all_subjects()
            if subject.is_active
        ]
        details = self.report_repo.get_details(student.id, exam.id)
        dialog = ReportDetailsDialog(subjects, details, self)
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            self.report_repo.save_details(student.id, exam.id, dialog.get_values())
        except SQLAlchemyError:
            logger.exception("Could not save report card details")
            QMessageBox.critical(self, "Save Failed", "Attendance and remarks could not be saved.")
            return
        QMessageBox.information(self, "Saved", "Attendance and remarks saved for this student and exam.")
        self.generate_report()

    def _populate_component_table(self, results):
        component_rows = []
        for result in results:
            component_rows.extend(result["rows"])
            if result.get("grade_only"):
                component_rows.append({
                    "subject": result["subject"],
                    "component": "Assigned Grade",
                    "maximum": None,
                    "obtained": result["grade"] if result["grade"] != "—" else None,
                    "status": result["status"],
                })
        self.component_table.setRowCount(len(component_rows))
        for row_index, result_row in enumerate(component_rows):
            values = (
                result_row["subject"],
                result_row["component"],
                CalculationService.format_marks(result_row["maximum"])
                if result_row["maximum"] is not None else "—",
                (
                    str(result_row["obtained"])
                    if result_row["component"] == "Assigned Grade"
                    and result_row["obtained"] is not None
                    else CalculationService.format_marks(result_row["obtained"])
                    if result_row["obtained"] is not None else "—"
                ),
                result_row["status"],
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.component_table.setItem(row_index, column, item)

    def export_report_pdf(self):
        if not self._report_ready:
            QMessageBox.warning(self, "No Report", "Generate a report card before exporting.")
            return
        if not self._can_publish:
            QMessageBox.warning(
                self,
                "Incomplete Results",
                "PDF publication is blocked while required subjects are Pending, Absent, "
                "or not configured.",
            )
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Report Card",
            "report_card.pdf",
            "PDF files (*.pdf)",
        )
        if not path:
            return
        output_path = Path(path)
        if output_path.exists():
            answer = QMessageBox.question(
                self,
                "Overwrite File",
                f"{output_path.name} already exists. Replace it?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
        writer = QPdfWriter(str(output_path))
        writer.setPageLayout(QPageLayout(
            QPageSize(QPageSize.A4),
            QPageLayout.Orientation.Portrait,
            QMarginsF(9, 9, 9, 9),
        ))
        writer.setResolution(96)
        painter = QPainter()
        if not painter.begin(writer):
            QMessageBox.critical(self, "Export Failed", "The PDF could not be opened for writing.")
            return
        try:
            page_rect = writer.pageLayout().paintRectPixels(writer.resolution())
            for index, page_html in enumerate(self._report_pages):
                document = QTextDocument()
                document.setDocumentMargin(0)
                document.setDefaultFont(self.report_text.font())
                document.setHtml(page_html)
                document.setTextWidth(page_rect.width())
                content_height = max(document.size().height(), 1)
                scale = min(1.0, page_rect.height() / content_height)
                painter.save()
                horizontal_offset = page_rect.width() * (1 - scale) / 2
                painter.translate(page_rect.left() + horizontal_offset, page_rect.top())
                painter.scale(scale, scale)
                document.drawContents(
                    painter,
                    QRectF(0, 0, page_rect.width(), page_rect.height() / scale),
                )
                painter.restore()
                if index + 1 < len(self._report_pages) and not writer.newPage():
                    raise OSError("Could not create the second report-card page.")
        except OSError as error:
            logger.exception("Could not render report card PDF")
            QMessageBox.critical(self, "Export Failed", f"The PDF could not be written: {error}")
            return
        finally:
            painter.end()
        if not output_path.is_file() or output_path.stat().st_size == 0:
            QMessageBox.critical(self, "Export Failed", "The PDF could not be written.")
            return
        QMessageBox.information(self, "Export Complete", f"Report card exported to {output_path}.")


class ReportDetailsDialog(QDialog):
    def __init__(self, subjects, details, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Report Card Attendance and Remarks")
        self.subjects = subjects
        self.details = details
        self.co_scholastic_inputs = {}
        self.subject_remark_inputs = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        layout.addWidget(tabs)

        attendance_page = QWidget()
        attendance_form = QFormLayout(attendance_page)
        self.days_present_input = QLineEdit(self._initial_count("days_present"))
        self.days_absent_input = QLineEdit(self._initial_count("days_absent"))
        self.working_days_input = QLineEdit(self._initial_count("working_days"))
        self.issue_date_input = QDateEdit()
        self.issue_date_input.setCalendarPopup(True)
        self.issue_date_input.setDisplayFormat("dd-MM-yyyy")
        issue_date = self.details.get("issue_date") or date.today()
        self.issue_date_input.setDate(QDate(issue_date.year, issue_date.month, issue_date.day))
        self.class_teacher_input = QLineEdit(self.details.get("class_teacher", ""))
        attendance_form.addRow("Days Present:", self.days_present_input)
        attendance_form.addRow("Days Absent:", self.days_absent_input)
        attendance_form.addRow("Working Days:", self.working_days_input)
        attendance_form.addRow("Date of Issue:", self.issue_date_input)
        attendance_form.addRow("Class Teacher:", self.class_teacher_input)
        tabs.addTab(attendance_page, "Attendance")

        co_scholastic_page = QWidget()
        co_scholastic_form = QFormLayout(co_scholastic_page)
        for area in CO_SCHOLASTIC_AREAS:
            field = QLineEdit(self.details.get("co_scholastic", {}).get(area, ""))
            self.co_scholastic_inputs[area] = field
            co_scholastic_form.addRow(f"{area}:", field)
        tabs.addTab(co_scholastic_page, "Co-Scholastic")

        skills_page = QWidget()
        skills_layout = QVBoxLayout(skills_page)
        skills_layout.addWidget(QLabel("Enter a rating or remark for each skill."))
        skill_rows = [
            (subject_id, subject_name, skill)
            for subject_id, subject_name in self.subjects
            for skill in ReportCardPage._skills_for_subject(subject_name)
        ]
        self.skills_table = QTableWidget(len(skill_rows), 3)
        self.skills_table.setHorizontalHeaderLabels(["Subject", "Skill", "Remark"])
        self.skills_table.verticalHeader().setVisible(False)
        self.skills_table.setWordWrap(True)
        saved_remarks = self.details.get("subject_remarks", {})
        for row, (subject_id, subject_name, skill) in enumerate(skill_rows):
            subject_item = QTableWidgetItem(subject_name)
            skill_item = QTableWidgetItem(skill)
            subject_item.setFlags(subject_item.flags() & ~Qt.ItemIsEditable)
            skill_item.setFlags(skill_item.flags() & ~Qt.ItemIsEditable)
            self.skills_table.setItem(row, 0, subject_item)
            self.skills_table.setItem(row, 1, skill_item)
            field = QLineEdit(saved_remarks.get(str(subject_id), {}).get(skill, ""))
            self.skills_table.setCellWidget(row, 2, field)
            self.subject_remark_inputs[(subject_id, skill)] = field
        self.skills_table.resizeColumnsToContents()
        skills_layout.addWidget(self.skills_table)
        tabs.addTab(skills_page, "Subject Skills")

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.resize(760, 650)

    def _initial_count(self, key):
        value = self.details.get(key)
        return "" if value is None else str(value)

    def _parse_count(self, field, label):
        text = field.text().strip()
        if not text:
            return None
        try:
            value = int(text)
        except ValueError:
            raise ValueError(f"{label} must be a whole number.") from None
        if value < 0:
            raise ValueError(f"{label} cannot be negative.")
        return value

    def get_values(self):
        attendance = {
            "days_present": self._parse_count(self.days_present_input, "Days present"),
            "days_absent": self._parse_count(self.days_absent_input, "Days absent"),
            "working_days": self._parse_count(self.working_days_input, "Working days"),
        }
        entered_counts = [value is not None for value in attendance.values()]
        if any(entered_counts) and not all(entered_counts):
            raise ValueError("Enter days present, days absent, and working days together.")
        if all(entered_counts) and (
            attendance["days_present"] + attendance["days_absent"] != attendance["working_days"]
        ):
            raise ValueError("Days present plus days absent must equal working days.")

        co_scholastic = {
            area: field.text().strip()
            for area, field in self.co_scholastic_inputs.items()
            if field.text().strip()
        }
        subject_remarks = {}
        for (subject_id, skill), field in self.subject_remark_inputs.items():
            remark = field.text().strip()
            if remark:
                subject_remarks.setdefault(str(subject_id), {})[skill] = remark
        return {
            **attendance,
            "issue_date": self.issue_date_input.date().toPython(),
            "class_teacher": self.class_teacher_input.text().strip(),
            "co_scholastic": co_scholastic,
            "subject_remarks": subject_remarks,
        }

    def accept(self):
        try:
            self.get_values()
        except ValueError as error:
            QMessageBox.warning(self, "Invalid Report Details", str(error))
            return
        super().accept()
