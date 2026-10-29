from models.database import SessionLocal, Student, AcademicSession, Class, Section
from sqlalchemy import and_

class StudentRepository:
    def __init__(self):
        self.session_factory = SessionLocal

    def generate_admission_number(self):
        with self.session_factory() as session:
            last_student = session.query(Student).order_by(Student.id.desc()).first()
            if last_student and last_student.admission_number:
                try:
                    num = int(last_student.admission_number.replace("ADM", ""))
                    return f"ADM{num + 1:04d}"
                except ValueError:
                    pass
            return "ADM0001"

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
