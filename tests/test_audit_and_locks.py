import pytest
from models.database import create_engine, Base, sessionmaker
from repositories.audit import AuditRepository
from repositories.exam_lock import ExamLockRepository

@pytest.fixture
def audit_repo():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    repo = AuditRepository()
    repo.session_factory = Session
    return repo

@pytest.fixture
def lock_repo(audit_repo):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    repo = ExamLockRepository()
    repo.session_factory = Session
    repo.audit_repo.session_factory = Session
    return repo

def test_audit_log_creation(audit_repo):
    log_id = audit_repo.log_action(
        action="CREATE",
        entity_type="STUDENT",
        entity_id=1,
        new_value="Student added",
        user="admin"
    )
    assert log_id is not None
    logs = audit_repo.get_recent_logs()
    assert len(logs) >= 1

def test_audit_filter_by_entity(audit_repo):
    audit_repo.log_action(action="CREATE", entity_type="STUDENT", entity_id=1)
    audit_repo.log_action(action="CREATE", entity_type="EXAM", entity_id=1)

    student_logs = audit_repo.get_recent_logs(entity_type="STUDENT")
    assert len(student_logs) >= 1
    assert student_logs[0].entity_type == "STUDENT"

def test_exam_lock_lock_exam(lock_repo):
    result = lock_repo.lock_exam(exam_id=1, user="admin", reason="Marks locked")
    assert result is True
    assert lock_repo.is_exam_locked(1) is True

def test_exam_lock_unlock_exam(lock_repo):
    lock_repo.lock_exam(exam_id=1, user="admin")
    result = lock_repo.unlock_exam(exam_id=1, user="admin")
    assert result is True
    assert lock_repo.is_exam_locked(1) is False

def test_exam_lock_status(lock_repo):
    status = lock_repo.get_exam_lock_status(1)
    assert status is None  # Not locked yet

    lock_repo.lock_exam(exam_id=1, user="admin")
    status = lock_repo.get_exam_lock_status(1)
    assert status is not None
    assert status.is_locked is True
    assert status.locked_by == "admin"
