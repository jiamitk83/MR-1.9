import sqlite3

import pytest
from PySide6.QtWidgets import QApplication
from sqlalchemy import create_engine

from ui import backup_page
from ui.backup_page import BackupPage
from services.database_backup import (
    create_database_backup,
    restore_database_backup,
    validate_database,
)


def _create_database(path, value):
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE records (value TEXT)")
        connection.execute("INSERT INTO records (value) VALUES (?)", (value,))


def _read_value(path):
    with sqlite3.connect(path) as connection:
        return connection.execute("SELECT value FROM records").fetchone()[0]


def test_create_backup_and_validate(tmp_path):
    source = tmp_path / "school.db"
    backup = tmp_path / "backup_test.db"
    _create_database(source, "source")

    create_database_backup(source, backup)
    validate_database(backup)

    assert _read_value(backup) == "source"


def test_restore_uses_verified_snapshot_and_safety_copy(tmp_path):
    source = tmp_path / "backup.db"
    active = tmp_path / "school.db"
    _create_database(source, "restored")
    _create_database(active, "before")
    engine = create_engine(f"sqlite:///{active}")
    engine.connect().close()

    safety = restore_database_backup(source, active, engine)

    assert _read_value(active) == "restored"
    assert _read_value(safety) == "before"
    engine.dispose()


def test_invalid_backup_is_rejected_without_changing_active_database(tmp_path):
    active = tmp_path / "school.db"
    backup = tmp_path / "invalid.db"
    _create_database(active, "unchanged")
    backup.write_text("not a SQLite database", encoding="utf-8")
    engine = create_engine(f"sqlite:///{active}")

    with pytest.raises(sqlite3.DatabaseError):
        restore_database_backup(backup, active, engine)

    assert _read_value(active) == "unchanged"
    engine.dispose()


def test_backup_list_stores_paths_on_list_items(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    (tmp_path / "backup_existing.db").touch()
    monkeypatch.setattr(backup_page, "BACKUP_DIR", str(tmp_path))
    page = BackupPage()

    item = page.backup_list.item(0)
    assert item is not None
    assert item.data(backup_page.Qt.UserRole) == str((tmp_path / "backup_existing.db").resolve())
    assert page.create_button.isEnabled()

    page.close()
    del app
