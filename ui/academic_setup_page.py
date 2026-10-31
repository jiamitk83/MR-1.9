from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QListWidget, QTableWidget, QTableWidgetItem,
                             QMessageBox, QTabWidget, QDialog, QDialogButtonBox, QFormLayout,
                             QComboBox, QDateEdit, QInputDialog)
from PySide6.QtCore import Qt, QDate
from repositories.academic_setup import AcademicSetupRepository

class AcademicSetupPage(QWidget):
    def __init__(self):
        super().__init__()
        self.repo = AcademicSetupRepository()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Tab widget for different sections
        self.tabs = QTabWidget()

        # Session Tab
        self.session_tab = self._create_session_tab()
        self.tabs.addTab(self.session_tab, "Sessions")

        # Class Tab
        self.class_tab = self._create_class_tab()
        self.tabs.addTab(self.class_tab, "Classes")

        # Section Tab
        self.section_tab = self._create_section_tab()
        self.tabs.addTab(self.section_tab, "Sections")

        # Subject Tab
        self.subject_tab = self._create_subject_tab()
        self.tabs.addTab(self.subject_tab, "Subjects")

        layout.addWidget(self.tabs)
        self.setLayout(layout)

        self.refresh_all()

    def _create_session_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Search
        search_layout = QHBoxLayout()
        self.session_search = QLineEdit()
        self.session_search.setPlaceholderText("Search sessions...")
        self.session_search.textChanged.connect(self.refresh_sessions)
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self.refresh_sessions)
        search_layout.addWidget(QLabel("Search:"))
        search_layout.addWidget(self.session_search)
        search_layout.addWidget(search_btn)
        layout.addLayout(search_layout)

        # Table
        self.session_table = QTableWidget()
        self.session_table.setColumnCount(6)
        self.session_table.setHorizontalHeaderLabels(["ID", "Name", "Start Date", "End Date", "Active", "Actions"])
        self.session_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.session_table)

        # Buttons
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add Session")
        add_btn.clicked.connect(self.add_session)
        edit_btn = QPushButton("Edit Session")
        edit_btn.clicked.connect(self.edit_session)
        delete_btn = QPushButton("Delete Session")
        delete_btn.clicked.connect(self.delete_session)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(delete_btn)
        layout.addLayout(btn_layout)

        widget.setLayout(layout)
        return widget

    def _create_class_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Search
        search_layout = QHBoxLayout()
        self.class_search = QLineEdit()
        self.class_search.setPlaceholderText("Search classes...")
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self.refresh_classes)
        search_layout.addWidget(QLabel("Search:"))
        search_layout.addWidget(self.class_search)
        search_layout.addWidget(search_btn)
        layout.addLayout(search_layout)

        # Table
        self.class_table = QTableWidget()
        self.class_table.setColumnCount(4)
        self.class_table.setHorizontalHeaderLabels(["ID", "Name", "Created", "Actions"])
        self.class_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.class_table)

        # Buttons
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add Class")
        add_btn.clicked.connect(self.add_class)
        edit_btn = QPushButton("Edit Class")
        edit_btn.clicked.connect(self.edit_class)
        delete_btn = QPushButton("Delete Class")
        delete_btn.clicked.connect(self.delete_class)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(delete_btn)
        layout.addLayout(btn_layout)

        widget.setLayout(layout)
        return widget

    def _create_section_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Load selectors
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("Class:"))
        self.section_class_combo = QComboBox()
        self.section_class_combo.currentIndexChanged.connect(self.refresh_sections)
        selector_layout.addWidget(self.section_class_combo)

        selector_layout.addWidget(QLabel("Session:"))
        self.section_session_combo = QComboBox()
        self.section_session_combo.currentIndexChanged.connect(self.refresh_sections)
        selector_layout.addWidget(self.section_session_combo)
        layout.addLayout(selector_layout)

        # Table
        self.section_table = QTableWidget()
        self.section_table.setColumnCount(5)
        self.section_table.setHorizontalHeaderLabels(["ID", "Name", "Class", "Session", "Actions"])
        self.section_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.section_table)

        # Buttons
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add Section")
        add_btn.clicked.connect(self.add_section)
        edit_btn = QPushButton("Edit Section")
        edit_btn.clicked.connect(self.edit_section)
        delete_btn = QPushButton("Delete Section")
        delete_btn.clicked.connect(self.delete_section)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(delete_btn)
        layout.addLayout(btn_layout)

        widget.setLayout(layout)
        return widget

    def _create_subject_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Search
        search_layout = QHBoxLayout()
        self.subject_search = QLineEdit()
        self.subject_search.setPlaceholderText("Search subjects...")
        self.subject_search.textChanged.connect(self.refresh_subjects)
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self.refresh_subjects)
        search_layout.addWidget(QLabel("Search:"))
        search_layout.addWidget(self.subject_search)
        search_layout.addWidget(search_btn)
        layout.addLayout(search_layout)

        # Table
        self.subject_table = QTableWidget()
        self.subject_table.setColumnCount(5)
        self.subject_table.setHorizontalHeaderLabels(["ID", "Name", "Code", "Active", "Actions"])
        self.subject_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.subject_table)

        # Buttons
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add Subject")
        add_btn.clicked.connect(self.add_subject)
        edit_btn = QPushButton("Edit Subject")
        edit_btn.clicked.connect(self.edit_subject)
        delete_btn = QPushButton("Delete Subject")
        delete_btn.clicked.connect(self.delete_subject)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(delete_btn)
        layout.addLayout(btn_layout)

        widget.setLayout(layout)
        return widget

    # ========== Sessions CRUD ==========
    def add_session(self):
        dialog = SessionDialog(self)
        if dialog.exec() == QDialog.Accepted:
            name, start_date, end_date, is_active = dialog.get_values()
            if name.strip():
                try:
                    result = self.repo.add_session(name=name, start_date=start_date, end_date=end_date, is_active=is_active)
                    if result:
                        self.refresh_sessions()
                        QMessageBox.information(self, "Success", "Session added successfully!")
                    else:
                        QMessageBox.warning(self, "Error", "Session with this name already exists.")
                except ValueError as e:
                    QMessageBox.warning(self, "Error", str(e))

    def edit_session(self):
        row = self.session_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Warning", "Please select a session to edit.")
            return
        session_id = self.session_table.item(row, 0).text()
        dialog = SessionDialog(self, session_id=int(session_id))
        if dialog.exec() == QDialog.Accepted:
            name, start_date, end_date, is_active = dialog.get_values()
            if name.strip():
                try:
                    self.repo.update_session(session_id=int(session_id), name=name, start_date=start_date,
                                             end_date=end_date, is_active=is_active)
                except ValueError as e:
                    QMessageBox.warning(self, "Error", str(e))
                    return
                self.refresh_sessions()
                QMessageBox.information(self, "Success", "Session updated successfully!")

    def delete_session(self):
        row = self.session_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Warning", "Please select a session to delete.")
            return
        session_id = self.session_table.item(row, 0).text()
        reply = QMessageBox.question(self, "Confirm Delete",
                                     f"Are you sure you want to delete session ID {session_id}?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.repo.delete_session(session_id=int(session_id)):
                self.refresh_sessions()
                QMessageBox.information(self, "Success", "Session deleted successfully!")
            else:
                QMessageBox.warning(self, "Cannot Delete", "The session is still used by students, sections, or examinations.")

    def refresh_sessions(self):
        keyword = self.session_search.text().strip()
        sessions = self.repo.search_sessions(keyword=keyword if keyword else None)
        self.session_table.setRowCount(len(sessions))
        for row, session in enumerate(sessions):
            self.session_table.setItem(row, 0, QTableWidgetItem(str(session.id)))
            self.session_table.setItem(row, 1, QTableWidgetItem(session.name))
            self.session_table.setItem(row, 2, QTableWidgetItem(session.start_date.strftime("%Y-%m-%d") if session.start_date else "-"))
            self.session_table.setItem(row, 3, QTableWidgetItem(session.end_date.strftime("%Y-%m-%d") if session.end_date else "-"))
            self.session_table.setItem(row, 4, QTableWidgetItem("Yes" if session.is_active else "No"))
            # Action buttons
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            edit_btn = QPushButton("Edit")
            edit_btn.clicked.connect(lambda checked, r=row: self._edit_session_from_row(r))
            delete_btn = QPushButton("Delete")
            delete_btn.clicked.connect(lambda checked, r=row: self._delete_session_from_row(r))
            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(delete_btn)
            self.session_table.setCellWidget(row, 5, actions_widget)

    def _edit_session_from_row(self, row):
        session_id = self.session_table.item(row, 0).text()
        dialog = SessionDialog(self, session_id=int(session_id))
        if dialog.exec() == QDialog.Accepted:
            name, start_date, end_date, is_active = dialog.get_values()
            if name.strip():
                try:
                    self.repo.update_session(session_id=int(session_id), name=name, start_date=start_date,
                                             end_date=end_date, is_active=is_active)
                except ValueError as e:
                    QMessageBox.warning(self, "Error", str(e))
                    return
                self.refresh_sessions()

    def _delete_session_from_row(self, row):
        session_id = self.session_table.item(row, 0).text()
        reply = QMessageBox.question(self, "Confirm Delete",
                                     f"Are you sure you want to delete session ID {session_id}?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.repo.delete_session(session_id=int(session_id)):
                self.refresh_sessions()
            else:
                QMessageBox.warning(self, "Cannot Delete", "The session is still used by students, sections, or examinations.")

    # ========== Classes CRUD ==========
    def add_class(self):
        name, ok = QInputDialog.getText(self, "Add Class", "Enter Class Name")
        if ok and name:
            try:
                self.repo.add_class(name=name)
                self.refresh_classes()
                QMessageBox.information(self, "Success", "Class added successfully!")
            except ValueError as e:
                QMessageBox.warning(self, "Error", str(e))

    def edit_class(self):
        row = self.class_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Warning", "Please select a class to edit.")
            return
        class_id = self.class_table.item(row, 0).text()
        current_name = self.class_table.item(row, 1).text()
        name, ok = QInputDialog.getText(self, "Edit Class", "Enter Class Name", text=current_name)
        if ok and name:
            self.repo.update_class(class_id=int(class_id), name=name)
            self.refresh_classes()
            QMessageBox.information(self, "Success", "Class updated successfully!")

    def delete_class(self):
        row = self.class_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Warning", "Please select a class to delete.")
            return
        class_id = self.class_table.item(row, 0).text()
        reply = QMessageBox.question(self, "Confirm Delete",
                                     f"Are you sure you want to delete class ID {class_id}?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.repo.delete_class(class_id=int(class_id)):
                self.refresh_classes()
                QMessageBox.information(self, "Success", "Class deleted successfully!")
            else:
                QMessageBox.warning(self, "Cannot Delete", "The class is still assigned to students or sections.")

    def refresh_classes(self):
        classes = self.repo.get_all_classes()
        self.class_table.setRowCount(len(classes))
        for row, class_obj in enumerate(classes):
            self.class_table.setItem(row, 0, QTableWidgetItem(str(class_obj.id)))
            self.class_table.setItem(row, 1, QTableWidgetItem(class_obj.name))
            # Action buttons
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            edit_btn = QPushButton("Edit")
            edit_btn.clicked.connect(lambda checked, r=row: self._edit_class_from_row(r))
            delete_btn = QPushButton("Delete")
            delete_btn.clicked.connect(lambda checked, r=row: self._delete_class_from_row(r))
            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(delete_btn)
            self.class_table.setCellWidget(row, 3, actions_widget)

    def _edit_class_from_row(self, row):
        class_id = self.class_table.item(row, 0).text()
        current_name = self.class_table.item(row, 1).text()
        name, ok = QInputDialog.getText(self, "Edit Class", "Enter Class Name", text=current_name)
        if ok and name:
            self.repo.update_class(class_id=int(class_id), name=name)
            self.refresh_classes()

    def _delete_class_from_row(self, row):
        class_id = self.class_table.item(row, 0).text()
        reply = QMessageBox.question(self, "Confirm Delete",
                                     f"Are you sure you want to delete class ID {class_id}?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.repo.delete_class(class_id=int(class_id)):
                self.refresh_classes()
            else:
                QMessageBox.warning(self, "Cannot Delete", "The class is still assigned to students or sections.")

    # ========== Sections CRUD ==========
    def add_section(self):
        dialog = SectionDialog(self)
        if dialog.exec() == QDialog.Accepted:
            name, class_id, session_id = dialog.get_values()
            if name:
                result = self.repo.add_section(name=name, class_id=class_id, session_id=session_id)
                if result:
                    self.refresh_sections()
                    QMessageBox.information(self, "Success", "Section added successfully!")
                else:
                    QMessageBox.warning(self, "Error", "Section already exists for this class and session!")

    def edit_section(self):
        row = self.section_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Warning", "Please select a section to edit.")
            return
        section_id = self.section_table.item(row, 0).text()
        dialog = SectionDialog(self, section_id=int(section_id))
        if dialog.exec() == QDialog.Accepted:
            name, class_id, session_id = dialog.get_values()
            self.repo.update_section(section_id=int(section_id), name=name, class_id=class_id, session_id=session_id)
            self.refresh_sections()
            QMessageBox.information(self, "Success", "Section updated successfully!")

    def delete_section(self):
        row = self.section_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Warning", "Please select a section to delete.")
            return
        section_id = self.section_table.item(row, 0).text()
        reply = QMessageBox.question(self, "Confirm Delete",
                                     f"Are you sure you want to delete section ID {section_id}?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.repo.delete_section(section_id=int(section_id)):
                self.refresh_sections()
                QMessageBox.information(self, "Success", "Section deleted successfully!")
            else:
                QMessageBox.warning(self, "Cannot Delete", "The section is still assigned to students.")

    def refresh_sections(self):
        class_id = self.section_class_combo.currentData()
        session_id = self.section_session_combo.currentData()
        if class_id and session_id:
            sections = self.repo.get_sections_by_class_and_session(class_id, session_id)
        else:
            sections = []
        self.section_table.setRowCount(len(sections))
        for row, section in enumerate(sections):
            self.section_table.setItem(row, 0, QTableWidgetItem(str(section.id)))
            self.section_table.setItem(row, 1, QTableWidgetItem(section.name))
            class_obj = self.repo.get_class_by_id(section.class_id)
            self.section_table.setItem(row, 2, QTableWidgetItem(class_obj.name if class_obj else "-"))
            session_obj = self.repo.get_session_by_id(section.session_id)
            self.section_table.setItem(row, 3, QTableWidgetItem(session_obj.name if session_obj else "-"))
            # Action buttons
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            edit_btn = QPushButton("Edit")
            edit_btn.clicked.connect(lambda checked, r=row: self._edit_section_from_row(r))
            delete_btn = QPushButton("Delete")
            delete_btn.clicked.connect(lambda checked, r=row: self._delete_section_from_row(r))
            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(delete_btn)
            self.section_table.setCellWidget(row, 4, actions_widget)

    def _edit_section_from_row(self, row):
        section_id = self.section_table.item(row, 0).text()
        dialog = SectionDialog(self, section_id=int(section_id))
        if dialog.exec() == QDialog.Accepted:
            name, class_id, session_id = dialog.get_values()
            self.repo.update_section(section_id=int(section_id), name=name, class_id=class_id, session_id=session_id)
            self.refresh_sections()

    def _delete_section_from_row(self, row):
        section_id = self.section_table.item(row, 0).text()
        reply = QMessageBox.question(self, "Confirm Delete",
                                     f"Are you sure you want to delete section ID {section_id}?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.repo.delete_section(section_id=int(section_id)):
                self.refresh_sections()
            else:
                QMessageBox.warning(self, "Cannot Delete", "The section is still assigned to students.")

    # ========== Subjects CRUD ==========
    def add_subject(self):
        dialog = SubjectDialog(self)
        if dialog.exec() == QDialog.Accepted:
            name, code, is_active = dialog.get_values()
            if name:
                result = self.repo.add_subject(name=name, code=code if code else None, is_active=is_active)
                if result:
                    self.refresh_subjects()
                    QMessageBox.information(self, "Success", "Subject added successfully!")
                else:
                    QMessageBox.warning(self, "Error", "Subject name already exists!")

    def edit_subject(self):
        row = self.subject_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Warning", "Please select a subject to edit.")
            return
        subject_id = self.subject_table.item(row, 0).text()
        dialog = SubjectDialog(self, subject_id=int(subject_id))
        if dialog.exec() == QDialog.Accepted:
            name, code, is_active = dialog.get_values()
            self.repo.update_subject(subject_id=int(subject_id), name=name, code=code if code else None, is_active=is_active)
            self.refresh_subjects()
            QMessageBox.information(self, "Success", "Subject updated successfully!")

    def delete_subject(self):
        row = self.subject_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Warning", "Please select a subject to delete.")
            return
        subject_id = self.subject_table.item(row, 0).text()
        reply = QMessageBox.question(self, "Confirm Delete",
                                     f"Are you sure you want to delete subject ID {subject_id}?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.repo.delete_subject(subject_id=int(subject_id)):
                self.refresh_subjects()
                QMessageBox.information(self, "Success", "Subject deleted successfully!")
            else:
                QMessageBox.warning(self, "Cannot Delete", "The subject is still used by marks or aliases.")

    def refresh_subjects(self):
        keyword = self.subject_search.text().strip()
        subjects = self.repo.search_subjects(keyword=keyword if keyword else None)
        self.subject_table.setRowCount(len(subjects))
        for row, subject in enumerate(subjects):
            self.subject_table.setItem(row, 0, QTableWidgetItem(str(subject.id)))
            self.subject_table.setItem(row, 1, QTableWidgetItem(subject.name))
            self.subject_table.setItem(row, 2, QTableWidgetItem(subject.code or "-"))
            self.subject_table.setItem(row, 3, QTableWidgetItem("Yes" if subject.is_active else "No"))
            # Action buttons
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            edit_btn = QPushButton("Edit")
            edit_btn.clicked.connect(lambda checked, r=row: self._edit_subject_from_row(r))
            delete_btn = QPushButton("Delete")
            delete_btn.clicked.connect(lambda checked, r=row: self._delete_subject_from_row(r))
            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(delete_btn)
            self.subject_table.setCellWidget(row, 4, actions_widget)

    def _edit_subject_from_row(self, row):
        subject_id = self.subject_table.item(row, 0).text()
        dialog = SubjectDialog(self, subject_id=int(subject_id))
        if dialog.exec() == QDialog.Accepted:
            name, code, is_active = dialog.get_values()
            self.repo.update_subject(subject_id=int(subject_id), name=name, code=code if code else None, is_active=is_active)
            self.refresh_subjects()

    def _delete_subject_from_row(self, row):
        subject_id = self.subject_table.item(row, 0).text()
        reply = QMessageBox.question(self, "Confirm Delete",
                                     f"Are you sure you want to delete subject ID {subject_id}?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.repo.delete_subject(subject_id=int(subject_id)):
                self.refresh_subjects()
            else:
                QMessageBox.warning(self, "Cannot Delete", "The subject is still used by marks or aliases.")

    def refresh_all(self):
        self.refresh_sessions()
        self.refresh_classes()
        self.refresh_sections()
        self.refresh_subjects()
        self._populate_section_selectors()

    def _populate_section_selectors(self):
        """Populate class and session dropdowns for section tab"""
        self.section_class_combo.clear()
        self.section_session_combo.clear()
        classes = self.repo.get_all_classes()
        sessions = self.repo.get_all_sessions()
        for cls in classes:
            self.section_class_combo.addItem(cls.name, cls.id)
        for session in sessions:
            self.section_session_combo.addItem(session.name, session.id)


class SessionDialog(QDialog):
    def __init__(self, parent=None, session_id=None):
        super().__init__(parent)
        self.session_id = session_id
        self.repo = AcademicSetupRepository()
        self.init_ui()
        if session_id:
            self.load_session(session_id)

    def init_ui(self):
        self.setWindowTitle("Session" + (" Edit" if self.session_id else " Add"))
        layout = QFormLayout()

        self.name_input = QLineEdit()
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.is_active = QComboBox()
        self.is_active.addItems(["No", "Yes"])

        layout.addRow("Name:", self.name_input)
        layout.addRow("Start Date:", self.start_date)
        layout.addRow("End Date:", self.end_date)
        layout.addRow("Active:", self.is_active)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def load_session(self, session_id):
        session = self.repo.get_session_by_id(session_id)
        if session:
            self.name_input.setText(session.name)
            self.start_date.setDate(session.start_date or QDate.currentDate())
            self.end_date.setDate(session.end_date or QDate.currentDate())
            self.is_active.setCurrentText("Yes" if session.is_active else "No")

    def get_values(self):
        return (
            self.name_input.text(),
            self.start_date.date().toPython(),
            self.end_date.date().toPython(),
            self.is_active.currentText() == "Yes"
        )


class SectionDialog(QDialog):
    def __init__(self, parent=None, section_id=None):
        super().__init__(parent)
        self.section_id = section_id
        self.repo = AcademicSetupRepository()
        self.init_ui()
        if section_id:
            self.load_section(section_id)

    def init_ui(self):
        self.setWindowTitle("Section" + (" Edit" if self.section_id else " Add"))
        layout = QFormLayout()

        self.name_input = QLineEdit()
        self.class_combo = QComboBox()
        self.session_combo = QComboBox()

        classes = self.repo.get_all_classes()
        sessions = self.repo.get_all_sessions()
        for cls in classes:
            self.class_combo.addItem(cls.name, cls.id)
        for session in sessions:
            self.session_combo.addItem(session.name, session.id)

        layout.addRow("Name:", self.name_input)
        layout.addRow("Class:", self.class_combo)
        layout.addRow("Session:", self.session_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def load_section(self, section_id):
        section = self.repo.get_section_by_id(section_id)
        if section:
            self.name_input.setText(section.name)
            for i in range(self.class_combo.count()):
                if self.class_combo.itemData(i) == section.class_id:
                    self.class_combo.setCurrentIndex(i)
                    break
            for i in range(self.session_combo.count()):
                if self.session_combo.itemData(i) == section.session_id:
                    self.session_combo.setCurrentIndex(i)
                    break

    def get_values(self):
        return (
            self.name_input.text(),
            self.class_combo.currentData(),
            self.session_combo.currentData()
        )


class SubjectDialog(QDialog):
    def __init__(self, parent=None, subject_id=None):
        super().__init__(parent)
        self.subject_id = subject_id
        self.repo = AcademicSetupRepository()
        self.init_ui()
        if subject_id:
            self.load_subject(subject_id)

    def init_ui(self):
        self.setWindowTitle("Subject" + (" Edit" if self.subject_id else " Add"))
        layout = QFormLayout()

        self.name_input = QLineEdit()
        self.code_input = QLineEdit()
        self.is_active = QComboBox()
        self.is_active.addItems(["No", "Yes"])

        layout.addRow("Name:", self.name_input)
        layout.addRow("Code:", self.code_input)
        layout.addRow("Active:", self.is_active)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def load_subject(self, subject_id):
        subject = self.repo.get_subject_by_id(subject_id)
        if subject:
            self.name_input.setText(subject.name)
            self.code_input.setText(subject.code or "")
            self.is_active.setCurrentText("Yes" if subject.is_active else "No")

    def get_values(self):
        return (
            self.name_input.text(),
            self.code_input.text() or None,
            self.is_active.currentText() == "Yes"
        )
