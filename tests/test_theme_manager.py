import sqlite3
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ui.theme_manager import THEME_SETTING_KEY, THEMES, ThemeHeader, ThemeManager
from ui.report_card_page import ReportCardPage


@pytest.fixture
def theme_context(tmp_path):
    app = QApplication.instance() or QApplication([])
    settings_path = tmp_path / "theme.ini"
    settings = QSettings(str(settings_path), QSettings.IniFormat)
    settings.clear()
    manager = ThemeManager(app, settings)
    yield app, manager, settings, settings_path
    app.removeEventFilter(manager)
    app.setStyleSheet("")
    app.setPalette(app.style().standardPalette())


def test_first_launch_defaults_to_light_theme(theme_context):
    app, manager, _settings, _path = theme_context

    assert manager.current_theme == "light"
    assert "background-color: #F4F6F8" in app.styleSheet()
    assert app.palette().color(QPalette.Window).name() == "#f4f6f8"


def test_dark_theme_starts_from_saved_preference(theme_context):
    app, _manager, settings, settings_path = theme_context
    settings.setValue(THEME_SETTING_KEY, "dark")
    settings.sync()

    restarted_settings = QSettings(str(settings_path), QSettings.IniFormat)
    restarted_manager = ThemeManager(app, restarted_settings)

    assert restarted_manager.current_theme == "dark"
    assert "background-color: #181A1B" in app.styleSheet()
    app.removeEventFilter(restarted_manager)


def test_theme_preference_persists_after_restart(theme_context):
    app, manager, _settings, settings_path = theme_context
    manager.set_theme("dark")

    restarted_settings = QSettings(str(settings_path), QSettings.IniFormat)
    restarted_manager = ThemeManager(app, restarted_settings)

    assert restarted_settings.value(THEME_SETTING_KEY) == "dark"
    assert restarted_manager.current_theme == "dark"
    assert app.palette().color(QPalette.Window).name() == "#181a1b"
    app.removeEventFilter(restarted_manager)


def test_toggle_button_switches_theme_and_updates_icon_and_tooltip(theme_context):
    _app, manager, _settings, _path = theme_context
    header = ThemeHeader(manager)

    assert header.toggle_button.text() == "☾"
    assert header.toggle_button.toolTip() == "Switch to Dark Mode"
    header.toggle_button.click()
    assert manager.current_theme == "dark"
    assert header.toggle_button.text() == "☀"
    assert header.toggle_button.toolTip() == "Switch to Light Mode"
    header.toggle_button.click()
    assert manager.current_theme == "light"
    header.close()


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_navigation_panel_and_selected_page_have_clear_theme_contrast(
    theme_context, theme
):
    app, manager, _settings, _path = theme_context
    manager.set_theme(theme)

    stylesheet = app.styleSheet()
    colors = THEMES[theme]

    assert "QWidget#navigationSidebar" in stylesheet
    assert "QLabel#navigationBrandMark" in stylesheet
    assert "QLabel#navigationBrandName" in stylesheet
    assert "QFrame#navigationDivider" in stylesheet
    assert "QLabel#navigationHeading" in stylesheet
    assert "QListWidget#navigationList::item:selected" in stylesheet
    assert f'background-color: {colors["sidebar"]};' in stylesheet
    assert f'color: {colors["sidebar_text"]};' in stylesheet
    assert f'background-color: {colors["sidebar_selected"]};' in stylesheet
    assert f'color: {colors["sidebar_selected_text"]};' in stylesheet
    assert f'border-left: 3px solid {colors["sidebar_indicator"]};' in stylesheet


def test_new_dialogs_inherit_theme_and_tables_use_alternating_rows(theme_context):
    app, manager, _settings, _path = theme_context
    manager.set_theme("dark")

    dialog = QDialog()
    layout = QVBoxLayout(dialog)
    table = QTableWidget(2, 1, dialog)
    layout.addWidget(table)
    line_edit = QLineEdit(dialog)
    layout.addWidget(line_edit)
    app.processEvents()

    assert "background-color: #24292F" in app.styleSheet()
    assert table.alternatingRowColors()
    assert line_edit.palette().color(QPalette.Text).name() == "#e6edf3"
    dialog.close()


def test_switching_theme_preserves_open_form_and_table_values(theme_context):
    _app, manager, _settings, _path = theme_context
    line_edit = QLineEdit()
    line_edit.setText("Unsaved form value")
    combo = QComboBox()
    combo.addItems(["Session A", "Session B"])
    combo.setCurrentIndex(1)
    table = QTableWidget(1, 1)
    table.setItem(0, 0, QTableWidgetItem("Unsaved mark"))

    manager.toggle_theme()

    assert line_edit.text() == "Unsaved form value"
    assert combo.currentText() == "Session B"
    assert table.item(0, 0).text() == "Unsaved mark"


def test_switching_theme_does_not_change_academic_database_records(theme_context):
    _app, manager, _settings, _path = theme_context
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE marks (student_id INTEGER, marks REAL)")
    connection.execute("INSERT INTO marks VALUES (7, 86.5)")
    connection.commit()
    before = connection.execute("SELECT student_id, marks FROM marks").fetchall()

    manager.toggle_theme()

    after = connection.execute("SELECT student_id, marks FROM marks").fetchall()
    assert after == before == [(7, 86.5)]
    connection.close()


def test_report_card_print_html_is_identical_in_both_themes(theme_context):
    _app, manager, _settings, _path = theme_context
    fake_page = SimpleNamespace(
        setup_repo=SimpleNamespace(
            get_session_by_id=lambda _session_id: SimpleNamespace(name="2026-2027"),
            get_class_by_id=lambda _class_id: SimpleNamespace(name="Grade 5"),
            get_section_by_id=lambda _section_id: SimpleNamespace(name="A"),
        ),
        exam_repo=SimpleNamespace(
            get_components_by_exam=lambda _exam_id: [
                SimpleNamespace(name="Written", max_marks=Decimal("100"), subject_id=None)
            ]
        ),
        _format_percentage=ReportCardPage._format_percentage,
        _skills_for_subject=ReportCardPage._skills_for_subject,
    )
    student = SimpleNamespace(
        session_id=1,
        class_id=1,
        section_id=1,
        admission_number="ADM-1",
        name="Student",
        roll_number=1,
        father_name="Parent",
        mother_name="Parent",
        date_of_birth=date(2015, 1, 1),
        address="Address",
    )
    exam = SimpleNamespace(id=1, session_id=1, name="PT1")
    results = [{
        "subject_id": 1,
        "subject": "Mathematics",
        "rows": [{"obtained": Decimal("86"), "maximum": Decimal("100")}],
        "total": "86",
        "maximum": Decimal("100"),
        "grade": "A2",
        "status": "Complete",
        "grade_only": False,
        "percentage_value": Decimal("86"),
        "highest": Decimal("90"),
        "average": Decimal("80"),
    }]

    light_html = ReportCardPage._generate_report_pages(
        fake_page, student, exam, results, {}
    )
    manager.set_theme("dark")
    dark_html = ReportCardPage._generate_report_pages(
        fake_page, student, exam, results, {}
    )

    assert dark_html == light_html
    assert "color: #17212b" in light_html[0]
    assert "background: #e8eef4" in light_html[0]
