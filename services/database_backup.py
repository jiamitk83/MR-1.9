import os
import sqlite3
from pathlib import Path


def validate_database(path):
    database_path = Path(path)
    if not database_path.is_file():
        raise FileNotFoundError(f"Database file does not exist: {database_path}")
    connection = sqlite3.connect(str(database_path), timeout=30)
    try:
        result = connection.execute("PRAGMA integrity_check").fetchone()
        if result is None or result[0] != "ok":
            raise sqlite3.DatabaseError(f"Database integrity check failed: {result[0] if result else 'no result'}")
        violations = connection.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise sqlite3.DatabaseError(f"Database has {len(violations)} foreign-key violation(s).")
    finally:
        connection.close()


def create_database_backup(source_path, destination_path):
    source = Path(source_path)
    destination = Path(destination_path)
    if not source.is_file():
        raise FileNotFoundError(f"Database file does not exist: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(f"Backup already exists: {destination}")

    temporary_path = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
    try:
        source_connection = sqlite3.connect(str(source), timeout=30)
        backup_connection = sqlite3.connect(str(temporary_path), timeout=30)
        try:
            source_connection.backup(backup_connection)
            backup_connection.commit()
        finally:
            backup_connection.close()
            source_connection.close()
        validate_database(temporary_path)
        os.replace(temporary_path, destination)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
    return destination


def restore_database_backup(backup_path, database_path, engine):
    backup = Path(backup_path)
    database = Path(database_path)
    if backup.resolve() == database.resolve():
        raise ValueError("The selected backup is the active database.")
    validate_database(backup)
    if not database.is_file():
        raise FileNotFoundError(f"Active database file does not exist: {database}")

    safety_path = database.with_name(f"safety_backup_{database.stem}_{os.getpid()}.db")
    suffix = 1
    while safety_path.exists():
        safety_path = database.with_name(f"safety_backup_{database.stem}_{os.getpid()}_{suffix}.db")
        suffix += 1
    create_database_backup(database, safety_path)

    engine.dispose()
    try:
        copy_database_contents(backup, database)
        validate_database(database)
    except Exception as restore_error:
        try:
            copy_database_contents(safety_path, database)
            validate_database(database)
        except Exception as recovery_error:
            raise RuntimeError(
                f"Restore failed ({restore_error}); automatic recovery also failed "
                f"({recovery_error}). Keep the safety backup at {safety_path}."
            ) from restore_error
        raise RuntimeError(
            f"Restore failed and the original database was recovered. "
            f"Safety backup: {safety_path}. Details: {restore_error}"
        ) from restore_error
    finally:
        engine.dispose()
    return safety_path


def copy_database_contents(source_path, destination_path):
    source = sqlite3.connect(str(source_path), timeout=30)
    destination = sqlite3.connect(str(destination_path), timeout=30)
    try:
        source.backup(destination)
        destination.commit()
    finally:
        destination.close()
        source.close()
