import sqlite3

from sqlalchemy import create_engine

from services.schema_migrations import (
    migrate_exam_component_metadata,
    migrate_half_yearly_scheme,
    migrate_report_card_data,
)


def test_component_metadata_migration_preserves_rows_and_is_idempotent(tmp_path):
    database = tmp_path / "legacy.db"
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TABLE exam_components ("
            "id INTEGER PRIMARY KEY, exam_id INTEGER NOT NULL, "
            "name VARCHAR NOT NULL, max_marks FLOAT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO exam_components (id, exam_id, name, max_marks) "
            "VALUES (1, 5, 'PT1', 25)"
        )
    engine = create_engine(f"sqlite:///{database}")

    backup, added = migrate_exam_component_metadata(database, engine)

    assert backup.is_file()
    assert added == ["code", "is_derived", "display_order"]
    with sqlite3.connect(database) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(exam_components)")}
        record = connection.execute(
            "SELECT id, exam_id, name, max_marks, code, is_derived, display_order "
            "FROM exam_components WHERE id=1"
        ).fetchone()
    assert columns >= {"code", "is_derived", "display_order"}
    assert record == (1, 5, "PT1", 25.0, None, 0, 0)

    second_backup, second_added = migrate_exam_component_metadata(database, engine)
    assert second_backup.is_file()
    assert second_added == []
    engine.dispose()


def test_report_card_data_migration_adds_optional_student_fields_and_details_table(tmp_path):
    database = tmp_path / "school.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE students (id INTEGER PRIMARY KEY, name TEXT)")
        connection.execute("CREATE TABLE examinations (id INTEGER PRIMARY KEY, name TEXT)")
        connection.execute("INSERT INTO students (id, name) VALUES (1, 'Student')")
        connection.execute("INSERT INTO examinations (id, name) VALUES (1, 'Term I')")
    engine = create_engine(f"sqlite:///{database}")

    backup, added = migrate_report_card_data(database, engine)

    assert backup.is_file()
    assert added == ["date_of_birth", "address"]
    with sqlite3.connect(database) as connection:
        student_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(students)")
        }
        details_table = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='report_card_details'"
        ).fetchone()
        details_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(report_card_details)")
        }
        student = connection.execute(
            "SELECT id, name, date_of_birth, address FROM students WHERE id=1"
        ).fetchone()
    assert student_columns >= {"date_of_birth", "address"}
    assert details_table == ("report_card_details",)
    assert details_columns >= {
        "days_present", "days_absent", "working_days", "issue_date",
        "class_teacher", "co_scholastic", "subject_remarks",
    }
    assert student == (1, "Student", None, None)

    second_backup, second_added = migrate_report_card_data(database, engine)
    assert second_backup.is_file()
    assert second_added == []
    engine.dispose()


def test_half_yearly_migration_preserves_components_and_is_idempotent(tmp_path):
    database = tmp_path / "half-yearly.db"
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("CREATE TABLE students (id INTEGER PRIMARY KEY)")
        connection.execute("CREATE TABLE subjects (id INTEGER PRIMARY KEY)")
        connection.execute("CREATE TABLE examinations (id INTEGER PRIMARY KEY)")
        connection.execute(
            "CREATE TABLE exam_components ("
            "id INTEGER PRIMARY KEY, exam_id INTEGER NOT NULL, "
            "name VARCHAR NOT NULL, max_marks FLOAT NOT NULL, "
            "code VARCHAR, is_derived BOOLEAN DEFAULT 0, display_order INTEGER DEFAULT 0)"
        )
        connection.execute(
            "INSERT INTO exam_components (id, exam_id, name, max_marks, code) "
            "VALUES (1, 1, 'Written Examination', 80, 'WE')"
        )
    engine = create_engine(f"sqlite:///{database}")

    backup, added = migrate_half_yearly_scheme(database, engine)

    assert backup.is_file()
    assert added == ["subject_id", "entry_max"]
    with sqlite3.connect(database) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(exam_components)")
        }
        component = connection.execute(
            "SELECT id, exam_id, name, max_marks, code, subject_id, entry_max "
            "FROM exam_components WHERE id=1"
        ).fetchone()
        grade_table = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='grade_marks'"
        ).fetchone()
    assert columns >= {"subject_id", "entry_max"}
    assert component == (1, 1, "Written Examination", 80.0, "WE", None, None)
    assert grade_table == ("grade_marks",)

    second_backup, second_added = migrate_half_yearly_scheme(database, engine)
    assert second_backup.is_file()
    assert second_added == []
    engine.dispose()
