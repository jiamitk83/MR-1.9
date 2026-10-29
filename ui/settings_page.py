from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QGroupBox,
                             QLineEdit, QPushButton, QFormLayout, QMessageBox, QComboBox)
from PySide6.QtCore import Qt
import os
from datetime import datetime

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
        info_layout.addRow("Database:", QLabel(os.path.abspath("data/school_register.db")))
        info_layout.addRow("Python Version:", QLabel("3.14+"))
        info_layout.addRow("PySide6 Version:", QLabel("6.11.1"))
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Database Settings
        db_group = QGroupBox("Database Settings")
        db_layout = QFormLayout()
        self.db_path_input = QLineEdit()
        self.db_path_input.setText(os.path.abspath("data/school_register.db"))
        self.db_path_input.setReadOnly(True)
        db_layout.addRow("Database Path:", self.db_path_input)
        backup_btn = QPushButton("Create Backup")
        backup_btn.clicked.connect(self.create_backup)
        db_layout.addRow("", backup_btn)
        db_group.setLayout(db_layout)
        layout.addWidget(db_group)

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
        try:
            import sqlite3
            db_path = "data/school_register.db"
            if not os.path.exists(db_path):
                QMessageBox.warning(self, "Warning", "Database file not found!")
                return

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"data/backup_{timestamp}.db"

            # Create backup using SQLite backup API
            conn = sqlite3.connect(db_path)
            backup_conn = sqlite3.connect(backup_path)
            conn.backup(backup_conn)
            backup_conn.close()
            conn.close()

            QMessageBox.information(self, "Success", f"Backup created at:\n{backup_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Backup failed: {str(e)}")
