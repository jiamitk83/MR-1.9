from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from models.database import init_db
from ui.theme_manager import ThemeHeader, ThemeManager
from ui.dashboard_page import DashboardPage
from ui.academic_setup_page import AcademicSetupPage
from ui.student_master_page import StudentMasterPage
from ui.examination_page import ExaminationPage
from ui.marks_entry_page import MarksEntryPage
from ui.mark_register_page import MarkRegisterPage
from ui.report_card_page import ReportCardPage
from ui.settings_page import SettingsPage
from ui.backup_page import BackupPage

class MainWindow(QMainWindow):
    def __init__(self, theme_manager=None):
        super().__init__()
        self.setWindowTitle("School Mark Register 1.9")
        self.resize(1200, 800)
        self.theme_manager = theme_manager or ThemeManager()
        self.setMenuWidget(ThemeHeader(self.theme_manager, self))

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # Sidebar
        navigation_panel = QWidget()
        navigation_panel.setObjectName("navigationSidebar")
        navigation_panel.setFixedWidth(240)
        navigation_layout = QVBoxLayout(navigation_panel)
        navigation_layout.setContentsMargins(12, 16, 12, 12)
        navigation_layout.setSpacing(10)

        brand_layout = QHBoxLayout()
        brand_layout.setContentsMargins(4, 2, 4, 8)
        brand_layout.setSpacing(10)
        brand_mark = QLabel("MR")
        brand_mark.setObjectName("navigationBrandMark")
        brand_mark.setFixedSize(38, 38)
        brand_mark.setAlignment(Qt.AlignCenter)
        brand_layout.addWidget(brand_mark)
        brand_copy = QVBoxLayout()
        brand_copy.setContentsMargins(0, 0, 0, 0)
        brand_copy.setSpacing(2)
        brand_name = QLabel("MAARK REGISTER")
        brand_name.setObjectName("navigationBrandName")
        brand_subtitle = QLabel("SCHOOL MANAGEMENT")
        brand_subtitle.setObjectName("navigationBrandSubtitle")
        brand_copy.addWidget(brand_name)
        brand_copy.addWidget(brand_subtitle)
        brand_layout.addLayout(brand_copy)
        brand_layout.addStretch()
        navigation_layout.addLayout(brand_layout)

        navigation_divider = QFrame()
        navigation_divider.setObjectName("navigationDivider")
        navigation_divider.setFrameShape(QFrame.HLine)
        navigation_layout.addWidget(navigation_divider)

        navigation_heading = QLabel("WORKSPACE")
        navigation_heading.setObjectName("navigationHeading")
        navigation_layout.addWidget(navigation_heading)

        self.sidebar = QListWidget()
        self.sidebar.setObjectName("navigationList")
        self.sidebar.setSpacing(3)
        for label in (
            "Dashboard",
            "Academic Setup",
            "Student Master",
            "Examination",
            "Marks Entry",
            "Mark Register",
            "Report Card",
            "Settings",
            "Backup & Recovery",
        ):
            item = QListWidgetItem(label)
            item.setSizeHint(QSize(0, 38))
            self.sidebar.addItem(item)
        self.sidebar.setCurrentRow(0)
        self.sidebar.currentRowChanged.connect(self.switch_page)
        navigation_layout.addWidget(self.sidebar)
        main_layout.addWidget(navigation_panel)

        # Main content
        self.content_stack = QStackedWidget()
        main_layout.addWidget(self.content_stack)

        self.pages = {
            "Dashboard": DashboardPage(),
            "Academic Setup": AcademicSetupPage(),
            "Student Master": StudentMasterPage(),
            "Examination": ExaminationPage(),
            "Marks Entry": MarksEntryPage(),
            "Mark Register": MarkRegisterPage(),
            "Report Card": ReportCardPage(),
            "Settings": SettingsPage(),
            "Backup & Recovery": BackupPage(),
        }

        for page in self.pages.values():
            self.content_stack.addWidget(page)

    def switch_page(self, index):
        self.content_stack.setCurrentIndex(index)
        if index == 0:
            self.pages["Dashboard"].refresh_stats()
        elif self.sidebar.item(index).text() == "Report Card":
            self.pages["Report Card"].refresh_data()

def main():
    app = QApplication([])
    app.setOrganizationName("Maark Register")
    app.setApplicationName("School Mark Register")
    app.setStyle("Fusion")
    theme_manager = ThemeManager(app)
    init_db()
    window = MainWindow(theme_manager)
    window.show()
    app.exec()

if __name__ == "__main__":
    main()
