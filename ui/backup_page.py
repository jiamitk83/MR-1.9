from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton,
                             QListWidget, QMessageBox, QDialog, QDialogButtonBox,
                             QFormLayout, QLineEdit, QFileDialog)
from PySide6.QtCore import Qt
import os
import shutil
from datetime import datetime

class BackupPage(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)

        # Header
        header = QLabel("Database Backup & Recovery")
        header.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(header)

        # Backup section
        backup_group = QVBoxLayout()
        backup_group.addWidget(QLabel("Create New Backup"))
        self.backup_desc = QLineEdit()
        self.backup_desc.setPlaceholderText("Enter backup description (optional)")
        backup_group.addWidget(self.backup_desc)

        create_btn = QPushButton("Create Backup Now")
        create_btn.clicked.connect(self.create_backup)
        backup_group.addWidget(create_btn)

        layout.addLayout(backup_group)

        # Backup list
        layout.addWidget(QLabel("Available Backups:"))
        self.backup_list = QListWidget()
        self.refresh_backup_list()
        layout.addWidget(self.backup_list)

        # Action buttons
        btn_layout = QVBoxLayout()
        restore_btn = QPushButton("Restore from Selected Backup")
        restore_btn.clicked.connect(self.restore_backup)
        restore_btn.setEnabled(False)
        btn_layout.addWidget(restore_btn)

        delete_btn = QPushButton("Delete Selected Backup")
        delete_btn.clicked.connect(self.delete_backup)
        delete_btn.setEnabled(False)
        btn_layout.addWidget(delete_btn)

        layout.addLayout(btn_layout)
        layout.addStretch()
        self.setLayout(layout)

        # Enable buttons when item selected
        self.backup_list.currentItemChanged.connect(self._on_selection_changed)

    def _on_selection_changed(self, current, previous):
        enabled = current is not None
        for btn in self.findChildren(QPushButton):
            btn.setEnabled(enabled)

    def refresh_backup_list(self):
        """Refresh the backup list from data directory"""
        self.backup_list.clear()
        backup_dir = "data"
        backups = []

        if os.path.exists(backup_dir):
            for file in os.listdir(backup_dir):
                if file.startswith("backup_") and file.endswith(".db"):
                    filepath = os.path.join(backup_dir, file)
                    mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                    backups.append((file, mtime, filepath))

        # Sort by modification time (newest first)
        backups.sort(key=lambda x: x[1], reverse=True)

        for filename, mtime, filepath in backups:
            display_text = f"{filename} ({mtime.strftime('%Y-%m-%d %H:%M:%S')})"
            item = QListWidget()
            item.addItem(display_text)
            item.setData(Qt.UserRole, filepath)
            self.backup_list.addItem(item)

    def create_backup(self):
        """Create a new database backup"""
        try:
            import sqlite3
            db_path = "data/school_register.db"

            if not os.path.exists(db_path):
                QMessageBox.warning(self, "Warning", "Production database not found!")
                return

            description = self.backup_desc.text().strip() or datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"backup_{description}.db"
            backup_path = os.path.join("data", backup_filename)

            # Use SQLite backup API
            source = sqlite3.connect(db_path)
            target = sqlite3.connect(backup_path)
            source.backup(target)
            target.close()
            source.close()

            # Verify backup
            verify_conn = sqlite3.connect(backup_path)
            result = verify_conn.execute("PRAGMA integrity_check").fetchone()
            verify_conn.close()

            if result[0] == "ok":
                QMessageBox.information(self, "Success",
                    f"Backup created successfully!\n\n"
                    f"File: {backup_path}\n"
                    f"Integrity: OK")
                self.refresh_backup_list()
            else:
                QMessageBox.warning(self, "Warning",
                    f"Backup created but integrity check failed: {result[0]}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Backup failed: {str(e)}")

    def restore_backup(self):
        """Restore from selected backup"""
        current_item = self.backup_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a backup to restore!")
            return

        backup_path = current_item.data(Qt.UserRole)

        # Confirmation dialog
        reply = QMessageBox.question(
            self,
            "Confirm Restore",
            f"Are you sure you want to restore from:\n{backup_path}\n\n"
            f"WARNING: This will replace your current database!\n"
            f"This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                import sqlite3
                db_path = "data/school_register.db"

                # Create a safety backup before restore
                safety_backup = f"data/safety_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                if os.path.exists(db_path):
                    shutil.copy2(db_path, safety_backup)

                # Restore
                shutil.copy2(backup_path, db_path)

                # Verify
                verify_conn = sqlite3.connect(db_path)
                result = verify_conn.execute("PRAGMA integrity_check").fetchone()
                verify_conn.close()

                if result[0] == "ok":
                    QMessageBox.information(self, "Success",
                        f"Database restored successfully!\n\n"
                        f"Safety backup saved to: {safety_backup}")
                else:
                    QMessageBox.warning(self, "Warning",
                        f"Restored but integrity check failed: {result[0]}")

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Restore failed: {str(e)}")

    def delete_backup(self):
        """Delete selected backup"""
        current_item = self.backup_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a backup to delete!")
            return

        backup_path = current_item.data(Qt.UserRole)
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete:\n{os.path.basename(backup_path)}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                os.remove(backup_path)
                self.refresh_backup_list()
                QMessageBox.information(self, "Success", "Backup deleted successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Delete failed: {str(e)}")
