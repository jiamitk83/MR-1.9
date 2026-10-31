from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QGroupBox,
                             QLineEdit, QPushButton, QFormLayout, QMessageBox, QComboBox)
import sqlite3
from datetime import datetime
from pathlib import Path

from app.config import BACKUP_DIR, DATABASE_PATH
from services.database_backup import create_database_backup
from services.schema_migrations import migrate_half_yearly_scheme
from models.database import engine

class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)

        # Application Info
        info_group = QGroupBox("Application Information")
        info_layout = QFormLayout()
        info_layout.addRow("Application Name:", QLabel("School Mark Register"))
        info_layout.addRow("Version:", QLabel("1.9.0"))
        info_layout.addRow("Database:", QLabel(str(Path(DATABASE_PATH).resolve())))
        info_layout.addRow("Python Version:", QLabel("3.14+"))
        info_layout.addRow("PySide6 Version:", QLabel("6.11.1"))
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Database Settings
        db_group = QGroupBox("Database Settings")
        db_layout = QFormLayout()
        self.db_path_input = QLineEdit()
        self.db_path_input.setText(str(Path(DATABASE_PATH).resolve()))
        self.db_path_input.setReadOnly(True)
        db_layout.addRow("Database Path:", self.db_path_input)
        backup_btn = QPushButton("Create Backup")
        backup_btn.clicked.connect(self.create_backup)
        db_layout.addRow("", backup_btn)
        self.scheme_migration_status = QLabel()
        self.scheme_migration_button = QPushButton("Enable Half Yearly Scheme")
        self.scheme_migration_button.clicked.connect(self.migrate_half_yearly_data)
        db_layout.addRow("Half Yearly schema:", self.scheme_migration_status)
        db_layout.addRow("", self.scheme_migration_button)
        db_group.setLayout(db_layout)
        layout.addWidget(db_group)
        self.refresh_scheme_migration_status()

        # Grading Scale
        grade_group = QGroupBox("Grading Scale Configuration")
        grade_layout = QFormLayout()
        grades = [
            ("A1", "91-100", "Excellent"),
            ("A2", "81-90", "Very Good"),
            ("B1", "71-80", "Good"),
            ("B2", "61-70", "Above Average"),
            ("C1", "51-60", "Average"),
            ("C2", "41-50", "Below Average"),
            ("D", "33-40", "Pass"),
            ("E", "Below 33", "Fail"),
        ]
        for grade, range_val, desc in grades:
            grade_layout.addRow(f"{grade}:", QLabel(f"{range_val}% - {desc}"))
        grade_group.setLayout(grade_layout)
        layout.addWidget(grade_group)

        # System Info
        system_group = QGroupBox("System Information")
        system_layout = QFormLayout()
        system_layout.addRow("Last Backup:", QLabel("N/A"))
        system_layout.addRow("Total Tables:", QLabel("9"))
        system_group.setLayout(system_layout)
        layout.addWidget(system_group)

        layout.addStretch()
        self.setLayout(layout)

    def create_backup(self):
        """Create a timestamped database backup"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup_path = Path(BACKUP_DIR) / f"backup_{timestamp}_settings.db"
        try:
            create_database_backup(DATABASE_PATH, backup_path)
        except (OSError, sqlite3.Error) as error:
            QMessageBox.critical(self, "Backup Failed", f"Could not create a verified backup: {error}")
            return
        QMessageBox.information(self, "Backup Complete", f"Verified backup created at:\n{backup_path}")

    def refresh_scheme_migration_status(self):
        try:
            with sqlite3.connect(DATABASE_PATH) as connection:
                tables = {
                    row[0] for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                }
                component_columns = (
                    {
                        row[1] for row in connection.execute(
                            "PRAGMA table_info(exam_components)"
                        )
                    }
                    if "exam_components" in tables else set()
                )
            ready = (
                {"subject_id", "entry_max"} <= component_columns
                and "grade_marks" in tables
            )
        except sqlite3.Error as error:
            self.scheme_migration_status.setText(f"Could not inspect schema: {error}")
            self.scheme_migration_button.setEnabled(False)
            return
        self.scheme_migration_status.setText("Ready" if ready else "Migration required")
        self.scheme_migration_button.setEnabled(not ready)
        if ready:
            self.scheme_migration_button.setText("Half Yearly Scheme Enabled")

    def migrate_half_yearly_data(self):
        answer = QMessageBox.question(
            self,
            "Enable Half Yearly Scheme",
            "This adds subject-specific component fields and the grade-only marks table. "
            "A verified database backup is created before migration. Existing marks and "
            "components are preserved. Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        try:
            backup_path, added_columns = migrate_half_yearly_scheme(DATABASE_PATH, engine)
        except (OSError, sqlite3.Error, RuntimeError) as error:
            QMessageBox.critical(
                self, "Migration Failed",
                f"The Half Yearly schema was not enabled:\n{error}",
            )
            self.refresh_scheme_migration_status()
            return
        self.refresh_scheme_migration_status()
        QMessageBox.information(
            self,
            "Migration Complete",
            "Half Yearly schema is ready. Existing records were preserved.\n"
            f"Added columns: {', '.join(added_columns) if added_columns else 'none'}\n"
            f"Verified backup: {backup_path}",
        )
