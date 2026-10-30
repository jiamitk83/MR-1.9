from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget,
                             QStackedWidget, QListWidget, QHBoxLayout, QListWidgetItem)
from models.database import init_db
from ui.theme_manager import ThemeHeader, ThemeManager
from ui.dashboard_page import DashboardPage
from ui.academic_setup_page import AcademicSetupPage
from ui.student_master_page import StudentMasterPage
from ui.examination_page import ExaminationPage
from ui.marks_entry_page import MarksEntryPage
from ui.mark_register_page import MarkRegisterPage
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
        self.sidebar = QListWidget()
        self.sidebar.setObjectName("navigationSidebar")
        self.sidebar.setFixedWidth(200)
        self.sidebar.addItem("Dashboard")
        self.sidebar.addItem("Academic Setup")
        self.sidebar.addItem("Student Master")
        self.sidebar.addItem("Examination")
        self.sidebar.addItem("Marks Entry")
        self.sidebar.addItem("Mark Register")
        self.sidebar.addItem("Settings")
        self.sidebar.addItem("Backup & Recovery")
        self.sidebar.currentRowChanged.connect(self.switch_page)
        main_layout.addWidget(self.sidebar)

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
            "Settings": SettingsPage(),
            "Backup & Recovery": BackupPage(),
        }

        for page in self.pages.values():
            self.content_stack.addWidget(page)

    def switch_page(self, index):
        self.content_stack.setCurrentIndex(index)

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
