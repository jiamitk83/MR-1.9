import pytest
from datetime import date
from decimal import Decimal
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import AcademicSession, Base, Class, Section, Student, Subject
from models.grade_mark import GradeMark
from models.examination import ExamComponent, Examination
from models.marks import Mark
from models.audit import SubjectAlias
from repositories.academic_setup import AcademicSetupRepository
from repositories.examination import ExamRepository
from repositories.mark import MarkRepository
from repositories.report_card import ReportCardRepository
from repositories.student import StudentRepository
from repositories.subject_alias import SubjectAliasRepository
from services.derived_calculations import DerivedCalculationService
from services.half_yearly import HalfYearlyService
from ui.report_card_page import ReportCardPage, ReportDetailsDialog


@pytest.fixture
def report_page(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    test_session_factory = sessionmaker(bind=engine)
    with test_session_factory() as session:
        session.add_all([
            AcademicSession(id=1, name="2026-2027"),
            Class(id=1, name="Grade 10"),
            Subject(id=1, name="Social Study", code="SST"),
        ])
        session.flush()
        session.add(Section(id=1, name="A", class_id=1, session_id=1))
        session.add_all([
            Student(id=1, admission_number="ADM0001", roll_number=1, name="Student One",
                    session_id=1, class_id=1, section_id=1, father_name="Parent One",
                    date_of_birth=date(2015, 2, 9), address="Test address"),
            Student(id=2, admission_number="ADM0002", roll_number=2, name="Student Two",
                    session_id=1, class_id=1, section_id=1),
        ])
        session.add(Examination(id=1, name="PT1", session_id=1))
        session.flush()
        session.add(ExamComponent(id=1, exam_id=1, name="Written", max_marks=25))
        session.add(Mark(
            student_id=1, subject_id=1, component_id=1, marks_obtained=15.5, is_absent=False,
        ))
        session.add(SubjectAlias(
            subject_id=1,
            alias_name="Social Science",
            alias_code="SOCSCI",
            is_primary=True,
        ))
        session.commit()

    def use_test_session(self):
        self.session_factory = test_session_factory

    monkeypatch.setattr(StudentRepository, "__init__", use_test_session)
    monkeypatch.setattr(ExamRepository, "__init__", use_test_session)
    monkeypatch.setattr(MarkRepository, "__init__", use_test_session)
    monkeypatch.setattr(AcademicSetupRepository, "__init__", use_test_session)
    monkeypatch.setattr(SubjectAliasRepository, "__init__", use_test_session)
    monkeypatch.setattr(ReportCardRepository, "__init__", use_test_session)
    monkeypatch.setattr(
        DerivedCalculationService,
        "__init__",
        lambda self: setattr(self, "session_factory", test_session_factory),
    )
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *args: QMessageBox.Ok))
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *args: QMessageBox.Ok))
    monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *args: QMessageBox.Ok))

    app = QApplication.instance() or QApplication([])
    page = ReportCardPage()
    yield page, test_session_factory
    page.close()
    engine.dispose()
    del app


def test_report_card_uses_actual_saved_marks_and_primary_subject_alias(report_page):
    page, _session_factory = report_page
    page.generate_report()

    assert "Social Science" in page.report_text.toHtml()
    assert "Student One" in page.report_text.toHtml()
    assert page.component_table.item(0, 0).text() == "Social Science"
    assert page.component_table.item(0, 2).text() == "25.00"
    assert page.component_table.item(0, 3).text() == "15.50"
    assert page.component_table.item(0, 4).text() == "Entered"
    assert "Scholastic Performance" in page.report_text.toHtml()
    assert "Written" in page.report_text.toHtml()
    assert "15.50" in page.report_text.toHtml()
    assert "Test address" in page.report_text.toHtml()
    assert "Comparative Performance" in page.report_text.toHtml()
    assert "Highest (%)" in page.report_text.toHtml()
    assert len(page._report_pages) == 2
    assert "Test address" in page._report_pages[0]


def test_report_card_blocks_final_result_when_marks_are_pending(report_page):
    page, _session_factory = report_page
    page.student_combo.setCurrentIndex(page.student_combo.findData(2))
    page.generate_report()

    assert "Pending" in page.report_text.toHtml()
    assert page.component_table.item(0, 3).text() == "—"
    assert page.component_table.item(0, 4).text() == "Pending"
    assert not page.export_button.isEnabled()


def test_half_yearly_report_uses_subject_specific_marks_and_derived_pt1(report_page):
    page, session_factory = report_page
    with session_factory() as session:
        session.add(Examination(id=2, name="Half Yearly", session_id=1))
        session.add(Subject(id=2, name="General Knowledge", code="GK"))
        session.commit()
        subject = session.get(Subject, 1)
        template = HalfYearlyService.template_for_subject(subject)
    components = page.exam_repo.configure_subject_components(2, 1, template)
    with session_factory() as session:
        legacy_components = [
            ExamComponent(id=100 + index, exam_id=2, name=name, max_marks=maximum)
            for index, (name, maximum) in enumerate(
                (("MA", 5), ("SE", 5), ("PF", 5), ("WRITTEN 80", 80)),
                start=1,
            )
        ]
        session.add_all(legacy_components)
        session.flush()
        session.add_all([
            Mark(
                student_id=1, subject_id=1, component_id=legacy_components[0].id,
                marks_obtained=4, is_absent=False,
            ),
            Mark(
                student_id=1, subject_id=1, component_id=legacy_components[1].id,
                marks_obtained=5, is_absent=False,
            ),
            Mark(
                student_id=1, subject_id=1, component_id=legacy_components[2].id,
                marks_obtained=5, is_absent=False,
            ),
            Mark(
                student_id=1, subject_id=1, component_id=legacy_components[3].id,
                marks_obtained=70, is_absent=False,
            ),
        ])
        session.add(GradeMark(
            student_id=1, subject_id=2, exam_id=2, grade="A1"
        ))
        session.commit()
    page.exam_combo.addItem("Half Yearly", 2)
    page.exam_combo.setCurrentIndex(page.exam_combo.findData(2))
    assert page.student_combo.currentData() == 1
    assert page.exam_combo.currentData() == 2

    page.generate_report()

    result = page._current_results[0]
    assert result["total"] == "87.10"
    assert result["percentage_value"] == Decimal("87.10")
    assert result["rows"][0]["obtained"] == Decimal("3.10")
    gk_result = page._current_results[1]
    assert gk_result["grade_only"] is True
    assert gk_result["grade"] == "A1"
    assert gk_result["status"] == "Grade only"
    assert "<th>Periodic Test 1" in page._report_pages[0]
    assert "Periodic Test 1" in page._report_pages[0]
    assert "<td>General Knowledge</td>" in page._report_pages[0]


def test_comparative_performance_uses_complete_class_marks(report_page):
    page, session_factory = report_page
    with session_factory() as session:
        session.add(Mark(
            student_id=2,
            subject_id=1,
            component_id=1,
            marks_obtained=20,
            is_absent=False,
        ))
        session.commit()

    page.generate_report()

    result = page._current_results[0]
    assert result["percentage_value"] == 62
    assert result["highest"] == 80
    assert result["average"] == 71


def test_report_card_exports_pdf(report_page, monkeypatch, tmp_path):
    page, _session_factory = report_page
    page.generate_report()
    output_path = tmp_path / "report.pdf"
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        staticmethod(lambda *args: (str(output_path), "PDF files (*.pdf)")),
    )

    page.export_report_pdf()

    assert output_path.read_bytes().startswith(b"%PDF")


def test_report_details_are_saved_and_used_in_report(report_page, monkeypatch):
    page, _session_factory = report_page
    details_dialog = ReportDetailsDialog(
        [(1, "Social Science")],
        {},
    )
    details_dialog.days_present_input.setText("82")
    details_dialog.days_absent_input.setText("18")
    details_dialog.working_days_input.setText("100")
    details_dialog.class_teacher_input.setText("A. Teacher")
    details_dialog.co_scholastic_inputs["Art"].setText("A")
    details_dialog.subject_remark_inputs[(1, "Analytical")].setText("Good progress")

    page.report_repo.save_details(1, 1, details_dialog.get_values())
    page.generate_report()

    report_html = page.report_text.toHtml()
    assert "82%" in report_html
    assert "82" in report_html
    assert "Good progress" in report_html
    assert ">A<" in report_html
    assert "A. Teacher" in report_html


def test_report_details_require_consistent_attendance(report_page):
    _page, _session_factory = report_page
    dialog = ReportDetailsDialog([], {})
    dialog.days_present_input.setText("80")
    dialog.days_absent_input.setText("15")
    dialog.working_days_input.setText("100")

    with pytest.raises(ValueError, match="must equal working days"):
        dialog.get_values()
