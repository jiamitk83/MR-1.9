from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget,
                             QStackedWidget, QListWidget, QHBoxLayout, QListWidgetItem)
from models.database import init_db
from ui.academic_setup_page import AcademicSetupPage
from ui.student_master_page import StudentMasterPage
from ui.examination_page import ExaminationPage
from ui.marks_entry_page import MarksEntryPage
from ui.mark_register_page import MarkRegisterPage

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("School Mark Register 1.9")
        self.resize(1100, 750)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # Sidebar
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(200)
        self.sidebar.addItem("Academic Setup")
        self.sidebar.addItem("Student Master")
        self.sidebar.addItem("Examination")
        self.sidebar.addItem("Marks Entry")
        self.sidebar.addItem("Mark Register")
        self.sidebar.currentRowChanged.connect(self.switch_page)
        main_layout.addWidget(self.sidebar)

        # Main content
        self.content_stack = QStackedWidget()
        main_layout.addWidget(self.content_stack)

        self.academic_setup_page = AcademicSetupPage()
        self.student_master_page = StudentMasterPage()
        self.examination_page = ExaminationPage()
        self.marks_entry_page = MarksEntryPage()
        self.mark_register_page = MarkRegisterPage()

        self.content_stack.addWidget(self.academic_setup_page)
        self.content_stack.addWidget(self.student_master_page)
        self.content_stack.addWidget(self.examination_page)
        self.content_stack.addWidget(self.marks_entry_page)
        self.content_stack.addWidget(self.mark_register_page)

    def switch_page(self, index):
        self.content_stack.setCurrentIndex(index)

def main():
    init_db()
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()

if __name__ == "__main__":
    main()
