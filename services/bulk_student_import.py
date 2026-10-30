import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from zipfile import BadZipFile

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from repositories.academic_setup import AcademicSetupRepository
from repositories.student import StudentRepository


EXPECTED_HEADERS = ("Roll No.", "Student Name")


@dataclass(frozen=True)
class BulkStudentRow:
    excel_row: int
    roll_number: int | None
    name: str
    reasons: tuple[str, ...] = ()

    @property
    def is_valid(self):
        return not self.reasons


@dataclass(frozen=True)
class BulkStudentPreview:
    rows: tuple[BulkStudentRow, ...]
    blank_rows_skipped: int = 0

    @property
    def total_rows(self):
        return len(self.rows)

    @property
    def valid_rows(self):
        return tuple(row for row in self.rows if row.is_valid)

    @property
    def invalid_rows(self):
        return tuple(row for row in self.rows if not row.is_valid)

    @property
    def duplicate_roll_numbers(self):
        return sum(
            "duplicate in Excel file" in row.reasons
            or "already exists in the selected section" in row.reasons
            for row in self.rows
        )

    @property
    def empty_names(self):
        return sum("student name is required" in row.reasons for row in self.rows)

    @property
    def invalid_roll_numbers(self):
        return sum(
            any("positive whole number" in reason for reason in row.reasons)
            for row in self.rows
        )


class BulkStudentImportService:
    """Parse, validate, and transactionally import a two-column student workbook."""

    def __init__(self, student_repository=None, setup_repository=None):
        self.student_repository = student_repository or StudentRepository()
        self.setup_repository = setup_repository or AcademicSetupRepository()

    @staticmethod
    def _validate_context(session_id, class_id, section_id, setup_repository):
        if not all((session_id, class_id, section_id)):
            raise ValueError("Select an academic session, class, and section first.")
        academic_session = setup_repository.get_session_by_id(session_id)
        if academic_session is None or not academic_session.is_active:
            raise ValueError("Select an active academic session.")
        if setup_repository.get_class_by_id(class_id) is None:
            raise ValueError("Select a valid class.")
        section = setup_repository.get_section_by_id(section_id)
        if (
            section is None
            or section.class_id != class_id
            or section.session_id != session_id
        ):
            raise ValueError("Select a section belonging to the chosen class and session.")

    @staticmethod
    def _parse_roll_number(value):
        if isinstance(value, bool) or value is None:
            return None
        if isinstance(value, int):
            return value if value > 0 else None
        if isinstance(value, float):
            if not math.isfinite(value) or not value.is_integer() or value <= 0:
                return None
            return int(value)
        text = str(value).strip()
        if not re.fullmatch(r"[0-9]+", text):
            return None
        number = int(text)
        return number if number > 0 else None

    @staticmethod
    def _validate_headers(values):
        headers = list(values or ())
        while headers and headers[-1] is None:
            headers.pop()
        normalized = tuple(
            value.strip().casefold() if isinstance(value, str) else ""
            for value in headers
        )
        expected = tuple(header.casefold() for header in EXPECTED_HEADERS)
        if normalized != expected:
            raise ValueError(
                "The first row must contain exactly these columns in order: "
                "'Roll No.' and 'Student Name'."
            )

    def preview_file(self, file_path, session_id, class_id, section_id):
        self._validate_context(
            session_id, class_id, section_id, self.setup_repository
        )
        path = Path(file_path)
        if path.suffix.casefold() != ".xlsx":
            raise ValueError("Choose an Excel .xlsx workbook. Legacy .xls files are not supported.")
        if not path.is_file():
            raise FileNotFoundError(f"Excel file not found: {path}")

        try:
            workbook = load_workbook(path, read_only=True, data_only=True)
        except (BadZipFile, InvalidFileException, OSError, ValueError) as error:
            raise ValueError(
                "The selected file is not a readable .xlsx workbook."
            ) from error

        try:
            worksheet = workbook.active
            rows = worksheet.iter_rows(values_only=True)
            self._validate_headers(next(rows, None))

            parsed = []
            blank_rows_skipped = 0
            candidate_roll_numbers = []
            for excel_row, values in enumerate(rows, start=2):
                if any(
                    value is not None and not (
                        isinstance(value, str) and not value.strip()
                    )
                    for value in values[2:]
                ):
                    raise ValueError(
                        f"Excel row {excel_row} contains data outside the two required columns."
                    )
                cells = list(values[:2])
                cells.extend([None] * (2 - len(cells)))
                roll_value, name_value = cells
                if all(value is None or (isinstance(value, str) and not value.strip()) for value in cells):
                    blank_rows_skipped += 1
                    continue

                roll_number = self._parse_roll_number(roll_value)
                name = name_value.strip() if isinstance(name_value, str) else (
                    "" if name_value is None else str(name_value).strip()
                )
                reasons = []
                if roll_number is None:
                    reasons.append("roll number must be a positive whole number")
                if not name:
                    reasons.append("student name is required")
                parsed.append((excel_row, roll_number, name, reasons))
                if roll_number is not None:
                    candidate_roll_numbers.append(roll_number)
        finally:
            workbook.close()

        duplicate_counts = Counter(candidate_roll_numbers)
        duplicate_in_file = {
            roll_number for roll_number, count in duplicate_counts.items() if count > 1
        }
        existing_roll_numbers = self.student_repository.get_existing_roll_numbers(
            session_id, class_id, section_id, candidate_roll_numbers
        )
        preview_rows = []
        for excel_row, roll_number, name, reasons in parsed:
            if roll_number in duplicate_in_file:
                reasons.append("duplicate in Excel file")
            if roll_number in existing_roll_numbers:
                reasons.append("already exists in the selected section")
            preview_rows.append(
                BulkStudentRow(excel_row, roll_number, name, tuple(reasons))
            )
        if not preview_rows:
            raise ValueError("The Excel workbook contains no student rows.")
        return BulkStudentPreview(tuple(preview_rows), blank_rows_skipped)

    def import_preview(self, preview, session_id, class_id, section_id):
        self._validate_context(
            session_id, class_id, section_id, self.setup_repository
        )
        if preview.invalid_rows:
            raise ValueError(
                "Correct all invalid rows in the Excel file before importing."
            )
        if not preview.valid_rows:
            raise ValueError("There are no valid student rows to import.")
        try:
            return self.student_repository.add_students_bulk(
                [
                    {"roll_number": row.roll_number, "name": row.name}
                    for row in preview.valid_rows
                ],
                session_id,
                class_id,
                section_id,
            )
        except ValueError:
            raise
        except IntegrityError as error:
            raise RuntimeError(
                "The student batch conflicts with existing database records. "
                "No students were imported; refresh the preview and try again."
            ) from error
        except SQLAlchemyError as error:
            raise RuntimeError(
                "The student batch could not be saved. No students were imported."
            ) from error
