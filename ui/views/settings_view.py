"""
Settings view.
"""
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PyQt6.QtCore import Qt
from utils.constants import APP_DATA_DIR


class SettingsView(QWidget):
    """Settings screen with app-data folder shortcut."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignmentFlag.AlignTop)
        outer.setContentsMargins(40, 40, 40, 40)
        outer.setSpacing(24)

        # ── Page title ──────────────────────────────────────────────────────
        title = QLabel("Settings")
        title.setStyleSheet("""
            font-size: 24px;
            font-weight: 700;
            color: #1a1a2e;
        """)
        outer.addWidget(title)

        # ── Divider ──────────────────────────────────────────────────────────
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("color: #e5e7eb;")
        outer.addWidget(divider)

        # ── Storage card ─────────────────────────────────────────────────────
        storage_card = self._make_card(
            icon="📁",
            heading="App Data Folder",
            description=(
                f"All templates, configs, and exports are stored here:\n"
                f"{APP_DATA_DIR}"
            ),
            button_text="Open Folder",
            button_slot=self._open_app_data_folder,
        )
        outer.addWidget(storage_card)

        # ── File Naming Pattern card ─────────────────────────────────────────
        naming_card = self._build_naming_pattern_card()
        outer.addWidget(naming_card)

        outer.addStretch()

    def _build_naming_pattern_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("SettingsCard")
        card.setStyleSheet("""
            QFrame#SettingsCard {
                background: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 10px;
                padding: 0px;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.setSpacing(16)

        icon_label = QLabel("🏷️")
        icon_label.setStyleSheet("font-size: 28px;")
        icon_label.setFixedWidth(40)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        text_col = QVBoxLayout()
        text_col.setSpacing(4)

        heading_lbl = QLabel("Default File Naming Pattern")
        heading_lbl.setStyleSheet("font-size: 15px; font-weight: 600; color: #111827;")

        desc_lbl = QLabel(
            "Configure how generated individual PDF results are named using bracketed column tokens."
        )
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("font-size: 12px; color: #6b7280;")

        text_col.addWidget(heading_lbl)
        text_col.addWidget(desc_lbl)

        top_row.addWidget(icon_label)
        top_row.addLayout(text_col, stretch=1)
        layout.addLayout(top_row)

        input_row = QHBoxLayout()
        input_row.setSpacing(10)

        from PyQt6.QtCore import QSettings
        from PyQt6.QtWidgets import QLineEdit
        from utils.constants import DEFAULT_NAMING_PATTERN

        settings = QSettings("TeacherResultSoftware", "ResultGenerator")
        saved_pattern = settings.value("naming_pattern", DEFAULT_NAMING_PATTERN)

        self._pattern_input = QLineEdit(saved_pattern)
        self._pattern_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #d1d5db; border-radius: 6px;
                padding: 8px 12px; font-size: 13px; font-family: Consolas, monospace;
                background: #f9fafb; color: #111827;
            }
            QLineEdit:focus { border-color: #3b82f6; background: #ffffff; }
        """)
        self._pattern_input.textChanged.connect(self._on_pattern_changed)
        input_row.addWidget(self._pattern_input, stretch=1)

        reset_btn = QPushButton("Reset Default")
        reset_btn.setFixedWidth(130)
        reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #f3f4f6; color: #374151; border: 1px solid #d1d5db;
                border-radius: 6px; padding: 8px 16px; font-size: 13px; font-weight: 600;
            }
            QPushButton:hover { background-color: #e5e7eb; color: #111827; }
        """)
        reset_btn.clicked.connect(self._reset_default_pattern)
        input_row.addWidget(reset_btn)

        layout.addLayout(input_row)

        help_lbl = QLabel("💡 Available tokens: [Enrollment number], [Name], [Roll No], [Class], etc.")
        help_lbl.setStyleSheet("font-size: 11px; color: #6b7280; font-style: italic;")
        layout.addWidget(help_lbl)

        return card

    def get_naming_pattern(self) -> str:
        from PyQt6.QtCore import QSettings
        from utils.constants import DEFAULT_NAMING_PATTERN
        settings = QSettings("TeacherResultSoftware", "ResultGenerator")
        return str(settings.value("naming_pattern", DEFAULT_NAMING_PATTERN))

    def _on_pattern_changed(self, text: str) -> None:
        from PyQt6.QtCore import QSettings
        settings = QSettings("TeacherResultSoftware", "ResultGenerator")
        settings.setValue("naming_pattern", text.strip() or "[Enrollment number]_[Name].pdf")

    def _reset_default_pattern(self) -> None:
        from utils.constants import DEFAULT_NAMING_PATTERN
        self._pattern_input.setText(DEFAULT_NAMING_PATTERN)

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _make_card(self, icon, heading, description, button_text, button_slot):
        """Return a styled settings card widget."""
        card = QFrame()
        card.setObjectName("SettingsCard")
        card.setStyleSheet("""
            QFrame#SettingsCard {
                background: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 10px;
                padding: 0px;
            }
        """)

        row = QHBoxLayout(card)
        row.setContentsMargins(20, 18, 20, 18)
        row.setSpacing(16)

        # Left: icon + text
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 28px;")
        icon_label.setFixedWidth(40)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        text_col = QVBoxLayout()
        text_col.setSpacing(4)

        heading_lbl = QLabel(heading)
        heading_lbl.setStyleSheet("font-size: 15px; font-weight: 600; color: #111827;")

        desc_lbl = QLabel(description)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("font-size: 12px; color: #6b7280;")

        text_col.addWidget(heading_lbl)
        text_col.addWidget(desc_lbl)

        # Right: action button
        btn = QPushButton(button_text)
        btn.setFixedWidth(130)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #4f7ef8;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover  { background-color: #3b6ef0; }
            QPushButton:pressed { background-color: #2c5ee8; }
        """)
        btn.clicked.connect(button_slot)

        row.addWidget(icon_label)
        row.addLayout(text_col, stretch=1)
        row.addWidget(btn, alignment=Qt.AlignmentFlag.AlignVCenter)

        return card

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _open_app_data_folder(self):
        """Open the app data directory in Windows Explorer."""
        os.makedirs(APP_DATA_DIR, exist_ok=True)
        os.startfile(APP_DATA_DIR)  # noqa: S606  (Windows-only, offline app)
