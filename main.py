from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget,
                             QStackedWidget, QListWidget, QHBoxLayout, QListWidgetItem)
from models.database import init_db
from ui.academic_setup_page import AcademicSetupPage
from ui.student_master_page import StudentMasterPage
from ui.examination_page import ExaminationPage

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("School Mark Register 1.9")
        self.resize(1000, 700)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # Sidebar
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(200)
        self.sidebar.addItem("Academic Setup")
        self.sidebar.addItem("Student Master")
        self.sidebar.addItem("Examination")
        self.sidebar.currentRowChanged.connect(self.switch_page)
        main_layout.addWidget(self.sidebar)

        # Main content
        self.content_stack = QStackedWidget()
        main_layout.addWidget(self.content_stack)

        self.academic_setup_page = AcademicSetupPage()
        self.student_master_page = StudentMasterPage()
        self.examination_page = ExaminationPage()

        self.content_stack.addWidget(self.academic_setup_page)
        self.content_stack.addWidget(self.student_master_page)
        self.content_stack.addWidget(self.examination_page)

    def switch_page(self, index):
        self.content_stack.setCurrentIndex(index)

if __name__ == "__main__":
    main()
