import re

from models.database import SessionLocal, Student, AcademicSession, Class, Section
from sqlalchemy import and_

class StudentRepository:
    def __init__(self):
        self.session_factory = SessionLocal

    def generate_admission_number(self):
        with self.session_factory() as session:
            return self._generate_admission_numbers(session, 1)[0]

    @staticmethod
    def _generate_admission_numbers(session, count):
        if count <= 0:
            return []
        numbers = {
            admission_number
            for (admission_number,) in session.query(Student.admission_number).all()
            if admission_number
        }
        suffixes = [
            int(match.group(1))
            for admission_number in numbers
            if (match := re.fullmatch(r"ADM(\d+)", admission_number, re.IGNORECASE))
        ]
        next_suffix = max(suffixes, default=0) + 1
        generated = []
        while len(generated) < count:
            candidate = f"ADM{next_suffix:04d}"
            next_suffix += 1
            if candidate in numbers:
                continue
            numbers.add(candidate)
            generated.append(candidate)
        return generated

    def get_existing_roll_numbers(self, session_id, class_id, section_id, roll_numbers=None):
        with self.session_factory() as session:
            query = session.query(Student.roll_number).filter(
                Student.session_id == session_id,
                Student.class_id == class_id,
                Student.section_id == section_id,
            )
            if roll_numbers is not None:
                roll_numbers = set(roll_numbers)
                if not roll_numbers:
                    return set()
                query = query.filter(Student.roll_number.in_(roll_numbers))
            return {roll_number for (roll_number,) in query.all()}

    def add_students_bulk(self, students, session_id, class_id, section_id):
        """Create a validated student batch in one transaction."""
        students = list(students)
        if not students:
            raise ValueError("There are no students to import.")
        if not all((session_id, class_id, section_id)):
            raise ValueError("Select an active session, class, and section.")

        with self.session_factory() as session:
            try:
                academic_session = session.query(AcademicSession).filter(
                    AcademicSession.id == session_id,
                    AcademicSession.is_active.is_(True),
                ).first()
                class_record = session.query(Class).filter(Class.id == class_id).first()
                section_record = session.query(Section).filter(
                    Section.id == section_id,
                    Section.class_id == class_id,
                    Section.session_id == session_id,
                ).first()
                if academic_session is None:
                    raise ValueError("The selected academic session is no longer active.")
                if class_record is None or section_record is None:
                    raise ValueError("The selected class or section is no longer available.")

                roll_numbers = []
                for student_data in students:
                    roll_number = student_data.get("roll_number")
                    name = student_data.get("name")
                    if (
                        isinstance(roll_number, bool)
                        or not isinstance(roll_number, int)
                        or roll_number <= 0
                    ):
                        raise ValueError("Every roll number must be a positive whole number.")
                    if not isinstance(name, str) or not name.strip():
                        raise ValueError("Every student must have a name.")
                    roll_numbers.append(roll_number)
                if len(set(roll_numbers)) != len(roll_numbers):
                    raise ValueError("The import contains duplicate roll numbers.")

                existing_roll_numbers = {
                    existing_roll_number
                    for (existing_roll_number,) in session.query(Student.roll_number).filter(
                        Student.session_id == session_id,
                        Student.class_id == class_id,
                        Student.section_id == section_id,
                        Student.roll_number.in_(roll_numbers),
                    ).all()
                }
                if existing_roll_numbers:
                    duplicates = ", ".join(
                        str(number) for number in sorted(existing_roll_numbers)
                    )
                    raise ValueError(
                        f"Roll number(s) already exist in this section: {duplicates}."
                    )

                admission_numbers = self._generate_admission_numbers(
                    session, len(students)
                )
                created = []
                for student_data, admission_number in zip(
                    students, admission_numbers
                ):
                    student = Student(
                        admission_number=admission_number,
                        roll_number=student_data["roll_number"],
                        name=student_data["name"].strip(),
                        session_id=session_id,
                        class_id=class_id,
                        section_id=section_id,
                    )
                    session.add(student)
                    session.flush()
                    created.append(student)
                session.commit()
                return created
            except Exception:
                session.rollback()
                raise

    def add_student(self, name, roll_number, father_name=None, mother_name=None,
                    dob=None, session_id=None, class_id=None, section_id=None):
        with self.session_factory() as session:
            # Check for duplicate roll number
            existing = session.query(Student).filter(
                and_(Student.roll_number == roll_number)
            ).first()
            if existing:
                return None  # Duplicate roll number

            adm_no = self.generate_admission_number()
            student = Student(
                admission_number=adm_no,
                roll_number=roll_number,
                name=name,
                father_name=father_name,
                mother_name=mother_name,
                dob=dob,
                session_id=session_id,
                class_id=class_id,
                section_id=section_id
            )
            session.add(student)
            session.commit()
            return student

    def get_students(self, session_id=None, class_id=None, section_id=None,
                     keyword=None, active_only=True):
        with self.session_factory() as session:
            query = session.query(Student)
            if session_id:
                query = query.filter(Student.session_id == session_id)
            if class_id:
                query = query.filter(Student.class_id == class_id)
            if section_id:
                query = query.filter(Student.section_id == section_id)
            if keyword:
                query = query.filter(
                    (Student.name.contains(keyword)) |
                    (Student.admission_number.contains(keyword)) |
                    (Student.roll_number.cast(str).contains(keyword)) |
                    (Student.father_name.contains(keyword))
                )
            if active_only:
                query = query.filter(Student.active == True)
            return query.all()

    def get_student_by_id(self, student_id):
        with self.session_factory() as session:
            return session.query(Student).filter(Student.id == student_id).first()

    def update_student(self, student_id, name=None, roll_number=None, father_name=None,
                       mother_name=None, dob=None, session_id=None, class_id=None,
                       section_id=None, active=None):
        with self.session_factory() as session:
            student = session.query(Student).filter(Student.id == student_id).first()
            if not student:
                return None

            # Check duplicate roll number
            if roll_number and roll_number != student.roll_number:
                existing = session.query(Student).filter(
                    and_(Student.roll_number == roll_number, Student.id != student_id)
                ).first()
                if existing:
                    return None  # Duplicate

            if name:
                student.name = name
            if roll_number:
                student.roll_number = roll_number
            if father_name is not None:
                student.father_name = father_name
            if mother_name is not None:
                student.mother_name = mother_name
            if dob is not None:
                student.dob = dob
            if session_id is not None:
                student.session_id = session_id
            if class_id is not None:
                student.class_id = class_id
            if section_id is not None:
                student.section_id = section_id
            if active is not None:
                student.active = active

            session.commit()
            return student

    def delete_student(self, student_id):
        with self.session_factory() as session:
            student = session.query(Student).filter(Student.id == student_id).first()
            if student:
                # Soft delete by deactivating
                student.active = False
                session.commit()
                return True
            return False

    def get_cascading_data(self):
        """Get data for cascading dropdowns"""
        with self.session_factory() as session:
            sessions = session.query(AcademicSession).all()
            classes = session.query(Class).all()
            sections = session.query(Section).all()
            return sessions, classes, sections
