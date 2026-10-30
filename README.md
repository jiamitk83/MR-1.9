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

## Appearance

Use the sun/moon control in the application header to switch between Dark Mode and Light Mode. The selection is saved in the desktop application's user settings and restored on the next launch; the default is Light Mode. Changing the appearance does not reload pages or modify academic records. Exported report-card PDFs keep their print styling.
