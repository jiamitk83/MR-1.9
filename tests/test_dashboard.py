import pytest
from PySide6.QtWidgets import QApplication
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import AcademicSession, Base, Class, Student
from models.audit import AuditLog
from models.examination import Examination
from repositories.academic_setup import AcademicSetupRepository
from repositories.dashboard import DashboardRepository
from ui.dashboard_page import DashboardPage


@pytest.fixture
def dashboard(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    test_session_factory = sessionmaker(bind=engine)
    with test_session_factory() as session:
        session.add_all([
            AcademicSession(id=1, name="2026-2027", is_active=True),
            Class(id=1, name="Grade 10"),
        ])
        session.flush()
        session.add(Student(
            id=1,
            admission_number="ADM0001",
            roll_number=1,
            name="Test Student",
            session_id=1,
            class_id=1,
            active=True,
        ))
        session.add(Examination(id=1, name="PT1", session_id=1))
        session.commit()

    def use_test_session(self):
        self.session_factory = test_session_factory

    monkeypatch.setattr(DashboardRepository, "__init__", use_test_session)
    monkeypatch.setattr(AcademicSetupRepository, "__init__", use_test_session)
    app = QApplication.instance() or QApplication([])
    page = DashboardPage()
    yield page
    page.close()
    engine.dispose()
    del app


def test_dashboard_renders_database_counts_without_replacing_card_titles(dashboard):
    assert [label.text() for label in dashboard.stat_value_labels] == ["1", "1", "1", "1", "1"]
    assert [card[0] for card in dashboard.cards] == [
        "Active Students", "Total Students", "Active Sessions", "Exams Configured", "Classes",
    ]


def test_dashboard_shows_recent_audit_activity(dashboard):
    with dashboard.repo.session_factory() as session:
        session.add(AuditLog(
            action="UPDATE", entity_type="MARK", entity_id=5, user="teacher",
        ))
        session.commit()

    dashboard.refresh_stats()

    assert "UPDATE MARK" in dashboard.activity_text.text()
