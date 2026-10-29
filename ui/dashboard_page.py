from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QFrame, QGraphicsDropShadowEffect, QFont)
from repositories.dashboard import DashboardRepository
from repositories.academic_setup import AcademicSetupRepository

class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()
        self.repo = DashboardRepository()
        self.setup_repo = AcademicSetupRepository()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)

        # Title
        title = QLabel("Dashboard")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        layout.addWidget(title)

        # Stats cards
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(15)

        self.cards = [
            ("Active Students", "0", "text-green-600"),
            ("Total Sessions", "0", "text-blue-600"),
            ("Exams Configured", "0", "text-purple-600"),
            ("Classes", "0", "text-orange-600"),
        ]

        for label, value, color in self.cards:
            card = self._create_stat_card(label, value, color)
            cards_layout.addWidget(card)

        layout.addLayout(cards_layout)

        # Activity section
        activity_label = QLabel("Recent Activity")
        activity_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(activity_label)

        self.activity_text = QLabel("No recent activity")
        self.activity_text.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.activity_text)

        layout.addStretch()
        self.setLayout(layout)
        self.refresh_stats()

    def _create_stat_card(self, title, value, color):
        card = QFrame()
        card.setFixedHeight(100)
        card.setFrameStyle(QFrame.StyledPanel)

        # Add shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(20, 15, 20, 15)

        title_label = QLabel(title)
        title_label.setStyleSheet("color: gray; font-size: 12px;")

        value_label = QLabel(value)
        value_label.setFont(QFont("Segoe UI", 24, QFont.Bold))
        value_label.setStyleSheet(f"color: palette(text);")

        card_layout.addWidget(title_label)
        card_layout.addWidget(value_label)
        card_layout.addStretch()
        card.setLayout(card_layout)

        return card

    def refresh_stats(self):
        """Refresh dashboard statistics"""
        stats = self.repo.get_stats()
        sessions = self.setup_repo.get_all_sessions()

        # Update card values
        self.cards[0][1] = str(stats.get('active_students', 0))
        self.cards[1][1] = str(len(sessions))
        self.cards[2][1] = str(stats.get('exams_count', 0))
        self.cards[3][1] = str(len(self.setup_repo.get_all_classes()))

        # Update UI
        cards = self.findChildren(QFrame)
        for i, card in enumerate(cards[:4]):
            value_label = card.findChild(QLabel, "")
            if value_label and i < len(self.cards):
                value_label.setText(self.cards[i][1])
