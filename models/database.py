from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, Boolean, Date
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from app.config import DATABASE_URL

Base = declarative_base()

class AcademicSession(Base):
    __tablename__ = 'academic_sessions'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)  # e.g., 2026-2027
    start_date = Column(Date)
    end_date = Column(Date)
    is_active = Column(Boolean, default=False)

class Class(Base):
    __tablename__ = 'classes'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False) # e.g., Grade 10

class Section(Base):
    __tablename__ = 'sections'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False) # e.g., A
    class_id = Column(Integer, ForeignKey('classes.id'), nullable=False)
    session_id = Column(Integer, ForeignKey('academic_sessions.id'), nullable=False)

class Subject(Base):
    __tablename__ = 'subjects'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    code = Column(String, unique=True)
    is_active = Column(Boolean, default=True)

class Student(Base):
    __tablename__ = 'students'
    id = Column(Integer, primary_key=True)
    admission_number = Column(String, unique=True, nullable=False)
    roll_number = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    father_name = Column(String)
    mother_name = Column(String)
    session_id = Column(Integer, ForeignKey('academic_sessions.id'))
    class_id = Column(Integer, ForeignKey('classes.id'))
    section_id = Column(Integer, ForeignKey('sections.id'))
    active = Column(Boolean, default=True)

# Engine setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    Base.metadata.create_all(engine)
