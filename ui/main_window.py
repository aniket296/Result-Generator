"""
Main application window.

Layout
------
QMainWindow
└── central QWidget
    └── QHBoxLayout (no margins)
        ├── Sidebar  (QWidget, fixed width)
        │   ├── App logo / title
        │   ├── Nav buttons (Dashboard, Template Editor, Settings)
        │   └── Version label (bottom)
        └── QStackedWidget  (content area)
"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QStackedWidget, QMessageBox,
    QSizePolicy, QSpacerItem,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QFont

from ui.views.dashboard_view import DashboardView
from ui.views.template_editor_view import TemplateEditorView
from ui.views.settings_view import SettingsView
from utils.constants import APP_NAME

# ── Palette ────────────────────────────────────────────────────────────────
SIDEBAR_BG      = "#1a1a2e"
SIDEBAR_HOVER   = "#16213e"
SIDEBAR_ACTIVE  = "#4f7ef8"
SIDEBAR_TEXT    = "#c8cde4"
SIDEBAR_TEXT_ACT= "#ffffff"
CONTENT_BG      = "#f3f4f8"


class MainWindow(QMainWindow):
    """Top-level application window."""

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def __init__(self):
        super().__init__()
        self._has_unsaved_changes = True   # mocked True for Step-1 testing

        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(1024, 680)
        self.resize(1200, 750)

        self._nav_buttons: list[QPushButton] = []
        self._build_ui()
        self._navigate(0)   # start on Dashboard

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_sidebar())
        root.addWidget(self._build_content_area())

    # ── Sidebar ───────────────────────────────────────────────────────────────

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet(f"QWidget#Sidebar {{ background-color: {SIDEBAR_BG}; }}")

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Logo / app name ───────────────────────────────────────────────
        logo_area = QWidget()
        logo_area.setFixedHeight(80)
        logo_area.setStyleSheet(f"background-color: {SIDEBAR_BG};")
        logo_layout = QVBoxLayout(logo_area)
        logo_layout.setContentsMargins(20, 0, 20, 0)
        logo_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        app_label = QLabel("📋  Result Manager")
        app_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        app_label.setStyleSheet("""
            color: #ffffff;
            font-size: 14px;
            font-weight: 700;
            letter-spacing: 0.5px;
        """)
        logo_layout.addWidget(app_label)
        layout.addWidget(logo_area)

        # ── Separator line ────────────────────────────────────────────────
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: #2a2d4a;")
        layout.addWidget(sep)

        layout.addSpacing(12)

        # ── Nav buttons ───────────────────────────────────────────────────
        nav_items = [
            ("  Dashboard",       "📊"),
            ("  Template Editor", "🖊️"),
            ("  Settings",        "⚙️"),
        ]
        for index, (label, icon) in enumerate(nav_items):
            btn = self._make_nav_button(f"{icon}{label}", index)
            self._nav_buttons.append(btn)
            layout.addWidget(btn)

        # ── Bottom spacer + version ───────────────────────────────────────
        layout.addStretch()

        ver = QLabel("v1.0.0")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ver.setFixedHeight(36)
        ver.setStyleSheet(f"color: #4a4f72; font-size: 11px;")
        layout.addWidget(ver)

        return sidebar

    def _make_nav_button(self, text: str, index: int) -> QPushButton:
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setFixedHeight(48)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {SIDEBAR_TEXT};
                border: none;
                border-left: 3px solid transparent;
                text-align: left;
                padding-left: 22px;
                font-size: 14px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {SIDEBAR_HOVER};
                color: {SIDEBAR_TEXT_ACT};
            }}
            QPushButton:checked {{
                background-color: {SIDEBAR_HOVER};
                border-left: 3px solid {SIDEBAR_ACTIVE};
                color: {SIDEBAR_TEXT_ACT};
                font-weight: 600;
            }}
        """)
        btn.clicked.connect(lambda _, i=index: self._navigate(i))
        return btn

    # ── Content area ──────────────────────────────────────────────────────────

    def _build_content_area(self) -> QStackedWidget:
        self._stack = QStackedWidget()
        self._stack.setStyleSheet(f"background-color: {CONTENT_BG};")

        self._stack.addWidget(DashboardView())        # index 0
        self._stack.addWidget(TemplateEditorView())   # index 1
        self._stack.addWidget(SettingsView())         # index 2

        return self._stack

    # ── Navigation ────────────────────────────────────────────────────────────

    def _navigate(self, index: int):
        """Switch the active page and update sidebar button states."""
        self._stack.setCurrentIndex(index)
        for i, btn in enumerate(self._nav_buttons):
            btn.setChecked(i == index)

    # ── Close event ───────────────────────────────────────────────────────────

    def closeEvent(self, event):
        if not self._has_unsaved_changes:
            event.accept()
            return

        msg = QMessageBox(self)
        msg.setWindowTitle("Unsaved Changes")
        msg.setText("You have unsaved changes.")
        msg.setInformativeText("Do you want to save before closing?")
        msg.setIcon(QMessageBox.Icon.Warning)

        save_btn     = msg.addButton("Save",       QMessageBox.ButtonRole.AcceptRole)
        no_save_btn  = msg.addButton("Don't Save", QMessageBox.ButtonRole.DestructiveRole)
        cancel_btn   = msg.addButton("Cancel",     QMessageBox.ButtonRole.RejectRole)

        msg.setDefaultButton(save_btn)
        msg.exec()

        clicked = msg.clickedButton()

        if clicked == save_btn:
            # TODO: trigger save logic in future steps
            self._has_unsaved_changes = False
            event.accept()
        elif clicked == no_save_btn:
            event.accept()
        else:                  # Cancel or dialog closed
            event.ignore()
