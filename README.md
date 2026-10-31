# School Mark Register (MR 1.9)

A professional, production-ready examination management system built with PySide6, SQLAlchemy, and SQLite.

## Project Structure

- `app/`: Main application entry point and configuration
- `models/`: SQLAlchemy database models
- `repositories/`: Data access layer
- `services/`: Business logic and calculations
- `ui/`: PySide6 UI components and pages
- `tests/`: Automated test suite
- `data/`: SQLite database storage
- `memory/`: Persistent project memory

## Database safety

The application database and managed backups live in the project's `data/` directory, independent of the current working directory. Backups are integrity-checked; restoring a backup first creates a verified safety copy and validates the selected snapshot.

Startup creates missing tables but does not migrate existing tables. Older databases can be upgraded explicitly with `services.schema_migrations.migrate_exam_component_metadata`; it creates and verifies a safety backup before adding the optional component metadata columns. Report-card capture fields also require the explicit `services.schema_migrations.migrate_report_card_data` migration. The Half Yearly feature requires `services.schema_migrations.migrate_half_yearly_scheme`; use **Settings → Enable Half Yearly Scheme** to create its verified pre-migration backup and upgrade the schema. No production schema migration is performed automatically.

## Appearance

Use the sun/moon control in the application header to switch between Dark Mode and Light Mode. The selection is saved in the desktop application's user settings and restored on the next launch; the default is Light Mode. Changing the appearance does not reload pages or modify academic records. Exported report-card PDFs keep their print styling.

## Half Yearly workflow

1. In **Settings**, enable the Half Yearly schema. The migration is additive and idempotent; review the backup path reported on completion.
2. In **Examination**, select the exam named **Half Yearly**, choose a subject, and apply its recommended subject scheme. Core subjects, Computer, and French get their corresponding component templates; French can use raw written marks out of 40 (converted to 80 for results) or direct entry out of 80. The configured components total 100, with PT1/5 read-only and derived from the PT1 exam.
3. Use **Marks Entry** to enter the subject's components in one grid. Enter `AB` for absent students. GK / General Knowledge is grade-only and is entered separately without numeric totals.
4. Review **Mark Register** and **Report Card** for calculated totals, percentages, grades, pending/absent status, and grade-only GK. Subject schemes cannot be changed after marks have been saved. Existing generic components and marks are retained; recognized legacy MA, SE, PF, and Written marks are projected read-only into a subject scheme only when the mapping is unambiguous. PDF export is blocked until required results are complete.

Report cards calculate class comparison scores only from complete, non-absent subject marks; use **Edit Attendance and Remarks** to enter attendance, issue date, class teacher, co-scholastic ratings, and subject-skill remarks.

## Tests

Run the test suite with `python -m pytest`.
