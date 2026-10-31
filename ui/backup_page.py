import sqlite3
import re
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QLabel,
)
from app.config import BACKUP_DIR, DATABASE_PATH
from models.database import engine
from services.database_backup import create_database_backup, restore_database_backup


class BackupPage(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        header = QLabel("Database Backup & Recovery")
        header.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(header)
        layout.addWidget(QLabel("Create New Backup"))

        self.backup_desc = QLineEdit()
        self.backup_desc.setPlaceholderText("Enter backup description (optional)")
        layout.addWidget(self.backup_desc)

        self.create_button = QPushButton("Create Backup Now")
        self.create_button.clicked.connect(self.create_backup)
        layout.addWidget(self.create_button)

        layout.addWidget(QLabel("Available Backups:"))
        self.backup_list = QListWidget()
        layout.addWidget(self.backup_list)

        self.restore_button = QPushButton("Restore from Selected Backup")
        self.restore_button.clicked.connect(self.restore_backup)
        self.restore_button.setEnabled(False)
        layout.addWidget(self.restore_button)

        self.delete_button = QPushButton("Delete Selected Backup")
        self.delete_button.clicked.connect(self.delete_backup)
        self.delete_button.setEnabled(False)
        layout.addWidget(self.delete_button)
        layout.addStretch()

        self.backup_list.currentItemChanged.connect(self._on_selection_changed)
        self.refresh_backup_list()

    def _on_selection_changed(self, current, _previous):
        enabled = current is not None
        self.restore_button.setEnabled(enabled)
        self.delete_button.setEnabled(enabled)

    def refresh_backup_list(self):
        self.backup_list.clear()
        backup_dir = Path(BACKUP_DIR)
        if not backup_dir.is_dir():
            return

        backups = sorted(
            (
                path for path in backup_dir.iterdir()
                if path.is_file() and path.name.startswith("backup_") and path.suffix == ".db"
            ),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for path in backups:
            mtime = datetime.fromtimestamp(path.stat().st_mtime)
            item = QListWidgetItem(f"{path.name} ({mtime:%Y-%m-%d %H:%M:%S})")
            item.setData(Qt.UserRole, str(path.resolve()))
            self.backup_list.addItem(item)

    def create_backup(self):
        description = re.sub(r"[^A-Za-z0-9._-]+", "_", self.backup_desc.text().strip())[:60]
        description = description.strip("._-") or "manual"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup_path = Path(BACKUP_DIR) / f"backup_{timestamp}_{description}.db"
        try:
            create_database_backup(DATABASE_PATH, backup_path)
        except (OSError, sqlite3.Error) as error:
            QMessageBox.critical(self, "Backup Failed", f"Could not create a verified backup: {error}")
            return

        self.refresh_backup_list()
        QMessageBox.information(
            self,
            "Backup Complete",
            f"Verified backup created at:\n{backup_path}",
        )

    def _selected_backup_path(self):
        item = self.backup_list.currentItem()
        if item is None:
            return None
        backup_path = Path(item.data(Qt.UserRole)).resolve()
        if (
            backup_path.parent != Path(BACKUP_DIR).resolve()
            or not backup_path.name.startswith("backup_")
            or backup_path.suffix != ".db"
        ):
            raise ValueError("The selected file is not a managed backup.")
        return backup_path

    def restore_backup(self):
        try:
            backup_path = self._selected_backup_path()
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Invalid Backup", str(error))
            return
        if backup_path is None:
            QMessageBox.warning(self, "No Backup Selected", "Select a backup to restore.")
            return

        reply = QMessageBox.question(
            self,
            "Confirm Restore",
            f"Restore the active database from:\n{backup_path}\n\n"
            "A verified safety backup will be created before replacement.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            safety_path = restore_database_backup(backup_path, DATABASE_PATH, engine)
        except (OSError, RuntimeError, ValueError, sqlite3.Error) as error:
            QMessageBox.critical(self, "Restore Failed", str(error))
            return
        self.refresh_backup_list()
        QMessageBox.information(
            self,
            "Restore Complete",
            f"Database restored and verified.\nSafety backup: {safety_path}",
        )

    def delete_backup(self):
        try:
            backup_path = self._selected_backup_path()
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Invalid Backup", str(error))
            return
        if backup_path is None:
            QMessageBox.warning(self, "No Backup Selected", "Select a backup to delete.")
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete backup {backup_path.name}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            backup_path.unlink()
        except OSError as error:
            QMessageBox.critical(self, "Delete Failed", f"Could not delete the backup: {error}")
            return
        self.refresh_backup_list()
        QMessageBox.information(self, "Backup Deleted", "The selected backup was deleted.")
