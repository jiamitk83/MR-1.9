from PySide6.QtCore import QEvent, QObject, QSettings, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QPushButton,
    QTableView,
    QWidget,
)


THEME_SETTING_KEY = "appearance/theme"


THEMES = {
    "light": {
        "window": "#F4F6F8",
        "surface": "#FFFFFF",
        "sidebar": "#E6EBF2",
        "sidebar_text": "#344355",
        "sidebar_secondary": "#64748B",
        "sidebar_hover": "#D9E1EB",
        "sidebar_selected": "#1D5F9E",
        "sidebar_selected_text": "#FFFFFF",
        "sidebar_indicator": "#B7DCFF",
        "card": "#FFFFFF",
        "input": "#FFFFFF",
        "text": "#243447",
        "secondary": "#596779",
        "border": "#D7DEE7",
        "hover": "#E8EDF3",
        "selected": "#D6E8FF",
        "selection_text": "#17324D",
        "alternate": "#F7F9FC",
        "button": "#E9EEF5",
        "button_hover": "#DCE5EF",
        "primary": "#2563A6",
        "primary_hover": "#1D528D",
        "disabled": "#9AA5B1",
        "tooltip": "#243447",
        "tooltip_text": "#FFFFFF",
        "scrollbar": "#C6CFD9",
        "scrollbar_hover": "#AAB6C4",
        "icon": "#315F91",
        "sun": "#C47B00",
    },
    "dark": {
        "window": "#181A1B",
        "surface": "#181A1B",
        "sidebar": "#20262E",
        "sidebar_text": "#DCE4ED",
        "sidebar_secondary": "#AAB4C0",
        "sidebar_hover": "#303A46",
        "sidebar_selected": "#3478B9",
        "sidebar_selected_text": "#FFFFFF",
        "sidebar_indicator": "#B7DCFF",
        "card": "#24292F",
        "input": "#2B3038",
        "text": "#E6EDF3",
        "secondary": "#AAB4C0",
        "border": "#3A414B",
        "hover": "#343B45",
        "selected": "#28496B",
        "selection_text": "#F4F8FC",
        "alternate": "#20252B",
        "button": "#303740",
        "button_hover": "#3B4551",
        "primary": "#3478B9",
        "primary_hover": "#428ACD",
        "disabled": "#77818D",
        "tooltip": "#E6EDF3",
        "tooltip_text": "#181A1B",
        "scrollbar": "#505A66",
        "scrollbar_hover": "#697584",
        "icon": "#B8D7F3",
        "sun": "#F3C969",
    },
}


def _stylesheet(colors):
    return f"""
        QWidget {{
            color: {colors["text"]};
            selection-background-color: {colors["selected"]};
            selection-color: {colors["selection_text"]};
        }}
        QMainWindow, QStackedWidget, QScrollArea, QAbstractScrollArea {{
            background-color: {colors["surface"]};
        }}
        QWidget#navigationSidebar {{
            background-color: {colors["sidebar"]};
            border: 0;
            border-right: 1px solid {colors["border"]};
        }}
        QLabel#navigationBrandMark {{
            color: #FFFFFF;
            background-color: {colors["primary"]};
            border: 0;
            border-radius: 9px;
            font-size: 13px;
            font-weight: 700;
            qproperty-alignment: AlignCenter;
        }}
        QLabel#navigationBrandName {{
            color: {colors["sidebar_text"]};
            background-color: transparent;
            font-size: 12px;
            font-weight: 700;
        }}
        QLabel#navigationBrandSubtitle {{
            color: {colors["sidebar_secondary"]};
            background-color: transparent;
            font-size: 8px;
            font-weight: 600;
            letter-spacing: 1px;
        }}
        QFrame#navigationDivider {{
            color: {colors["border"]};
            background-color: {colors["border"]};
            border: 0;
            max-height: 1px;
        }}
        QLabel#navigationHeading {{
            color: {colors["sidebar_secondary"]};
            background-color: transparent;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 1px;
            padding: 4px 8px 2px;
        }}
        QListWidget#navigationList {{
            color: {colors["sidebar_text"]};
            background-color: {colors["sidebar"]};
            border: 0;
            outline: 0;
        }}
        QListWidget#navigationList::item {{
            color: {colors["sidebar_text"]};
            padding: 7px 12px;
            margin: 0 3px;
            border: 0;
            border-left: 3px solid transparent;
            border-radius: 6px;
        }}
        QListWidget#navigationList::item:hover {{
            background-color: {colors["sidebar_hover"]};
        }}
        QListWidget#navigationList::item:selected {{
            color: {colors["sidebar_selected_text"]};
            background-color: {colors["sidebar_selected"]};
            border-left: 3px solid {colors["sidebar_indicator"]};
            font-weight: 600;
        }}
        QGroupBox, QFrame#themeCard {{
            background-color: {colors["card"]};
            border: 1px solid {colors["border"]};
            border-radius: 6px;
            margin-top: 8px;
            padding: 8px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 4px;
            color: {colors["text"]};
            background-color: {colors["card"]};
        }}
        QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QDateEdit,
        QTimeEdit, QDateTimeEdit, QSpinBox, QDoubleSpinBox {{
            color: {colors["text"]};
            background-color: {colors["input"]};
            border: 1px solid {colors["border"]};
            border-radius: 4px;
            padding: 5px 7px;
            selection-background-color: {colors["selected"]};
            selection-color: {colors["selection_text"]};
        }}
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
        QComboBox:focus, QDateEdit:focus, QSpinBox:focus,
        QDoubleSpinBox:focus {{
            border: 1px solid {colors["primary"]};
        }}
        QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled,
        QComboBox:disabled, QDateEdit:disabled, QSpinBox:disabled,
        QDoubleSpinBox:disabled {{
            color: {colors["disabled"]};
            background-color: {colors["window"]};
        }}
        QComboBox QAbstractItemView {{
            color: {colors["text"]};
            background-color: {colors["input"]};
            border: 1px solid {colors["border"]};
            selection-background-color: {colors["selected"]};
            selection-color: {colors["selection_text"]};
            outline: 0;
        }}
        QPushButton {{
            color: {colors["text"]};
            background-color: {colors["button"]};
            border: 1px solid {colors["border"]};
            border-radius: 4px;
            padding: 6px 12px;
        }}
        QPushButton:hover {{
            background-color: {colors["button_hover"]};
        }}
        QPushButton:pressed {{
            background-color: {colors["selected"]};
        }}
        QPushButton:disabled {{
            color: {colors["disabled"]};
            background-color: {colors["window"]};
            border-color: {colors["border"]};
        }}
        QPushButton#themeToggle {{
            color: {colors["icon"]};
            background-color: transparent;
            border: 1px solid transparent;
            border-radius: 17px;
            padding: 0;
            font-size: 19px;
        }}
        QPushButton#themeToggle:hover {{
            background-color: {colors["hover"]};
            border-color: {colors["border"]};
        }}
        QWidget#themeHeader {{
            background-color: {colors["surface"]};
            border-bottom: 1px solid {colors["border"]};
        }}
        QTableView, QTableWidget, QTreeView, QTreeWidget {{
            color: {colors["text"]};
            background-color: {colors["surface"]};
            alternate-background-color: {colors["alternate"]};
            gridline-color: {colors["border"]};
            border: 1px solid {colors["border"]};
            selection-background-color: {colors["selected"]};
            selection-color: {colors["selection_text"]};
        }}
        QTableView::item, QTableWidget::item,
        QTreeView::item, QTreeWidget::item {{
            padding: 3px;
        }}
        QHeaderView::section {{
            color: {colors["text"]};
            background-color: {colors["card"]};
            border: 0;
            border-right: 1px solid {colors["border"]};
            border-bottom: 1px solid {colors["border"]};
            padding: 6px;
        }}
        QTabWidget::pane {{
            background-color: {colors["surface"]};
            border: 1px solid {colors["border"]};
        }}
        QTabBar::tab {{
            color: {colors["text"]};
            background-color: {colors["card"]};
            border: 1px solid {colors["border"]};
            padding: 7px 12px;
        }}
        QTabBar::tab:selected {{
            background-color: {colors["surface"]};
            border-bottom-color: {colors["primary"]};
        }}
        QMenu, QMenuBar {{
            color: {colors["text"]};
            background-color: {colors["card"]};
            border: 1px solid {colors["border"]};
        }}
        QMenu::item {{
            padding: 6px 24px 6px 10px;
        }}
        QMenu::item:selected {{
            color: {colors["selection_text"]};
            background-color: {colors["selected"]};
        }}
        QToolTip {{
            color: {colors["tooltip_text"]};
            background-color: {colors["tooltip"]};
            border: 1px solid {colors["border"]};
            padding: 4px;
        }}
        QCheckBox, QRadioButton {{
            color: {colors["text"]};
            spacing: 6px;
        }}
        QCheckBox:disabled, QRadioButton:disabled {{
            color: {colors["disabled"]};
        }}
        QScrollBar:vertical {{
            background-color: {colors["window"]};
            width: 12px;
            margin: 0;
        }}
        QScrollBar:horizontal {{
            background-color: {colors["window"]};
            height: 12px;
            margin: 0;
        }}
        QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
            background-color: {colors["scrollbar"]};
            border-radius: 5px;
            min-height: 24px;
            min-width: 24px;
        }}
        QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {{
            background-color: {colors["scrollbar_hover"]};
        }}
        QScrollBar::add-line, QScrollBar::sub-line {{
            width: 0;
            height: 0;
        }}
    """


def _palette(colors):
    palette = QPalette()
    roles = {
        QPalette.Window: colors["window"],
        QPalette.WindowText: colors["text"],
        QPalette.Base: colors["input"],
        QPalette.AlternateBase: colors["alternate"],
        QPalette.ToolTipBase: colors["tooltip"],
        QPalette.ToolTipText: colors["tooltip_text"],
        QPalette.Text: colors["text"],
        QPalette.Button: colors["button"],
        QPalette.ButtonText: colors["text"],
        QPalette.BrightText: "#FF5555",
        QPalette.Highlight: colors["selected"],
        QPalette.HighlightedText: colors["selection_text"],
        QPalette.PlaceholderText: colors["secondary"],
        QPalette.Link: colors["primary"],
    }
    for role, color in roles.items():
        palette.setColor(role, QColor(color))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor(colors["disabled"]))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(colors["disabled"]))
    palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor(colors["disabled"]))
    return palette


class ThemeManager(QObject):
    """Apply and persist the application-wide light or dark appearance."""

    themeChanged = Signal(str)

    def __init__(self, app=None, settings=None):
        super().__init__(app or QApplication.instance())
        self.app = app or QApplication.instance()
        if self.app is None:
            raise RuntimeError("Create QApplication before initializing ThemeManager.")
        self.settings = settings or QSettings()
        saved_theme = str(self.settings.value(THEME_SETTING_KEY, "light")).lower()
        self.current_theme = saved_theme if saved_theme in THEMES else "light"
        self._row_refresh_pending = False
        self.apply_theme()
        self.app.installEventFilter(self)
        self._enable_alternating_rows()

    def set_theme(self, theme):
        if theme not in THEMES:
            raise ValueError(f"Unknown theme: {theme!r}")
        if theme == self.current_theme:
            return
        self.current_theme = theme
        self.settings.setValue(THEME_SETTING_KEY, theme)
        self.settings.sync()
        self.apply_theme()
        self.themeChanged.emit(theme)

    def toggle_theme(self):
        self.set_theme("dark" if self.current_theme == "light" else "light")

    def apply_theme(self):
        colors = THEMES[self.current_theme]
        self.app.setPalette(_palette(colors))
        self.app.setStyleSheet(_stylesheet(colors))

    def _enable_alternating_rows(self):
        for widget in self.app.allWidgets():
            if isinstance(widget, QTableView):
                widget.setAlternatingRowColors(True)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.ChildAdded and not self._row_refresh_pending:
            self._row_refresh_pending = True
            QTimer.singleShot(0, self._refresh_alternating_rows)
        return False

    def _refresh_alternating_rows(self):
        self._row_refresh_pending = False
        self._enable_alternating_rows()


class ThemeHeader(QWidget):
    """Compact application header containing the global theme control."""

    def __init__(self, theme_manager, parent=None):
        super().__init__(parent)
        self.theme_manager = theme_manager
        self.setObjectName("themeHeader")
        self.setFixedHeight(42)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 3, 10, 3)
        layout.addStretch()
        self.toggle_button = QPushButton()
        self.toggle_button.setObjectName("themeToggle")
        self.toggle_button.setFixedSize(34, 34)
        self.toggle_button.setCursor(Qt.PointingHandCursor)
        self.toggle_button.clicked.connect(self.theme_manager.toggle_theme)
        self.theme_manager.themeChanged.connect(self._update_button)
        self._update_button()
        layout.addWidget(self.toggle_button)

    def _update_button(self):
        if self.theme_manager.current_theme == "dark":
            self.toggle_button.setText("☀")
            self.toggle_button.setToolTip("Switch to Light Mode")
            self.toggle_button.setAccessibleName("Switch to Light Mode")
        else:
            self.toggle_button.setText("☾")
            self.toggle_button.setToolTip("Switch to Dark Mode")
            self.toggle_button.setAccessibleName("Switch to Dark Mode")
