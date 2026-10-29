from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QStackedWidget
from models.database import init_db
from ui.academic_setup_page import AcademicSetupPage

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("School Mark Register 1.9")
        self.resize(800, 600)

        self.central_widget = QStackedWidget()
        self.setCentralWidget(self.central_widget)

        self.academic_setup_page = AcademicSetupPage()
        self.central_widget.addWidget(self.academic_setup_page)

def main():
    init_db()
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()

if __name__ == "__main__":
    main()
