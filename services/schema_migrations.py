import sqlite3
from datetime import datetime
from pathlib import Path

from services.database_backup import (
    copy_database_contents,
    create_database_backup,
    validate_database,
)


def migrate_exam_component_metadata(database_path, engine):
    database = Path(database_path)
    validate_database(database)

    backup_path = database.with_name(
        f"backup_pre_component_metadata_{datetime.now():%Y%m%d_%H%M%S_%f}.db"
    )
    create_database_backup(database, backup_path)
    engine.dispose()

    connection = None
    added_columns = []
    try:
        connection = sqlite3.connect(str(database), timeout=30)
        connection.execute("BEGIN IMMEDIATE")
        table_exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='exam_components'"
        ).fetchone()
        if table_exists is None:
            raise sqlite3.DatabaseError("The exam_components table does not exist.")

        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(exam_components)")
        }
        additions = (
            ("code", "VARCHAR"),
            ("is_derived", "BOOLEAN DEFAULT 0"),
            ("display_order", "INTEGER DEFAULT 0"),
        )
        for name, definition in additions:
            if name not in columns:
                connection.execute(f"ALTER TABLE exam_components ADD COLUMN {name} {definition}")
                added_columns.append(name)
        connection.commit()
        validate_database(database)
    except Exception as migration_error:
        if connection is not None and connection.in_transaction:
            connection.rollback()
        if connection is not None:
            connection.close()
            connection = None
        try:
            copy_database_contents(backup_path, database)
            validate_database(database)
        except Exception as recovery_error:
            raise RuntimeError(
                f"Schema migration failed ({migration_error}) and automatic recovery failed "
                f"({recovery_error}). Keep the safety backup at {backup_path}."
            ) from migration_error
        raise RuntimeError(
            f"Schema migration failed and the original database was recovered. "
            f"Safety backup: {backup_path}. Details: {migration_error}"
        ) from migration_error
    finally:
        if connection is not None:
            connection.close()
        engine.dispose()

    return backup_path, added_columns


def migrate_report_card_data(database_path, engine):
    database = Path(database_path)
    validate_database(database)

    backup_path = database.with_name(
        f"backup_pre_report_card_data_{datetime.now():%Y%m%d_%H%M%S_%f}.db"
    )
    create_database_backup(database, backup_path)
    engine.dispose()

    connection = None
    added_columns = []
    try:
        connection = sqlite3.connect(str(database), timeout=30)
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("BEGIN IMMEDIATE")
        student_table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='students'"
        ).fetchone()
        if student_table is None:
            raise sqlite3.DatabaseError("The students table does not exist.")

        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(students)")
        }
        additions = (
            ("date_of_birth", "DATE"),
            ("address", "VARCHAR"),
        )
        for name, definition in additions:
            if name not in columns:
                connection.execute(f"ALTER TABLE students ADD COLUMN {name} {definition}")
                added_columns.append(name)

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS report_card_details (
                id INTEGER PRIMARY KEY,
                student_id INTEGER NOT NULL REFERENCES students(id),
                exam_id INTEGER NOT NULL REFERENCES examinations(id),
                days_present INTEGER,
                days_absent INTEGER,
                working_days INTEGER,
                issue_date DATE,
                class_teacher VARCHAR,
                co_scholastic TEXT,
                subject_remarks TEXT,
                CONSTRAINT uq_report_card_student_exam UNIQUE (student_id, exam_id)
            )
            """
        )
        connection.commit()
        validate_database(database)
    except Exception as migration_error:
        if connection is not None and connection.in_transaction:
            connection.rollback()
        if connection is not None:
            connection.close()
            connection = None
        try:
            copy_database_contents(backup_path, database)
            validate_database(database)
        except Exception as recovery_error:
            raise RuntimeError(
                f"Schema migration failed ({migration_error}) and automatic recovery failed "
                f"({recovery_error}). Keep the safety backup at {backup_path}."
            ) from migration_error
        raise RuntimeError(
            f"Schema migration failed and the original database was recovered. "
            f"Safety backup: {backup_path}. Details: {migration_error}"
        ) from migration_error
    finally:
        if connection is not None:
            connection.close()
        engine.dispose()

    return backup_path, added_columns


def migrate_half_yearly_scheme(database_path, engine):
    database = Path(database_path)
    validate_database(database)

    backup_path = database.with_name(
        f"backup_pre_half_yearly_scheme_{datetime.now():%Y%m%d_%H%M%S_%f}.db"
    )
    create_database_backup(database, backup_path)
    engine.dispose()

    connection = None
    added_columns = []
    try:
        connection = sqlite3.connect(str(database), timeout=30)
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("BEGIN IMMEDIATE")
        component_table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='exam_components'"
        ).fetchone()
        if component_table is None:
            raise sqlite3.DatabaseError("The exam_components table does not exist.")
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(exam_components)")
        }
        additions = (
            ("code", "VARCHAR"),
            ("is_derived", "BOOLEAN DEFAULT 0"),
            ("display_order", "INTEGER DEFAULT 0"),
            ("subject_id", "INTEGER REFERENCES subjects(id)"),
            ("entry_max", "NUMERIC(7, 2)"),
        )
        for name, definition in additions:
            if name not in columns:
                connection.execute(f"ALTER TABLE exam_components ADD COLUMN {name} {definition}")
                added_columns.append(name)
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS grade_marks (
                id INTEGER PRIMARY KEY,
                student_id INTEGER NOT NULL REFERENCES students(id),
                subject_id INTEGER NOT NULL REFERENCES subjects(id),
                exam_id INTEGER NOT NULL REFERENCES examinations(id),
                grade VARCHAR NOT NULL,
                CONSTRAINT uq_grade_mark_student_subject_exam
                    UNIQUE (student_id, subject_id, exam_id)
            )
            """
        )
        connection.commit()
        validate_database(database)
    except Exception as migration_error:
        if connection is not None and connection.in_transaction:
            connection.rollback()
        if connection is not None:
            connection.close()
            connection = None
        try:
            copy_database_contents(backup_path, database)
            validate_database(database)
        except Exception as recovery_error:
            raise RuntimeError(
                f"Schema migration failed ({migration_error}) and automatic recovery failed "
                f"({recovery_error}). Keep the safety backup at {backup_path}."
            ) from migration_error
        raise RuntimeError(
            f"Schema migration failed and the original database was recovered. "
            f"Safety backup: {backup_path}. Details: {migration_error}"
        ) from migration_error
    finally:
        if connection is not None:
            connection.close()
        engine.dispose()

    return backup_path, added_columns
