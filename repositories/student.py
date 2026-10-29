from models.database import SessionLocal, Student, AcademicSession, Class, Section

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

    def add_student(self, name, roll_number, father_name=None, mother_name=None, session_id=None, class_id=None, section_id=None):
        with self.session_factory() as session:
            adm_no = self.generate_admission_number()
            student = Student(
                admission_number=adm_no,
                roll_number=roll_number,
                name=name,
                father_name=father_name,
                mother_name=mother_name,
                session_id=session_id,
                class_id=class_id,
                section_id=section_id
            )
            session.add(student)
            session.commit()
            return student

    def get_students(self, session_id=None, class_id=None, section_id=None):
        with self.session_factory() as session:
            query = session.query(Student)
            if session_id:
                query = query.filter(Student.session_id == session_id)
            if class_id:
                query = query.filter(Student.class_id == class_id)
            if section_id:
                query = query.filter(Student.section_id == section_id)
            return query.filter(Student.active == True).all()
