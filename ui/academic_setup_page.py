from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QListWidget, QLineEdit, QHBoxLayout
from repositories.academic_setup import AcademicSetupRepository

class AcademicSetupPage(QWidget):
    def __init__(self):
        super().__init__()
        self.repo = AcademicSetupRepository()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Session controls
        layout.addWidget(QLabel("Academic Sessions"))
        self.session_list = QListWidget()
        layout.addWidget(self.session_list)

        input_layout = QHBoxLayout()
        self.session_input = QLineEdit()
        self.session_input.setPlaceholderText("Enter Session Name (e.g. 2026-2027)")
        add_btn = QPushButton("Add Session")
        add_btn.clicked.connect(self.add_session)
        input_layout.addWidget(self.session_input)
        input_layout.addWidget(add_btn)
        layout.addLayout(input_layout)

        self.setLayout(layout)
        self.refresh_list()

    def add_session(self):
        name = self.session_input.text()
        if name:
            self.repo.add_session(name=name, start_date=None, end_date=None)
            self.session_input.clear()
            self.refresh_list()

    def refresh_list(self):
        self.session_list.clear()
        for session in self.repo.get_all_sessions():
            self.session_list.addItem(session.name)
