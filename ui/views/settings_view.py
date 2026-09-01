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
        card = self._make_card(
            icon="📁",
            heading="App Data Folder",
            description=(
                f"All templates, configs, and exports are stored here:\n"
                f"{APP_DATA_DIR}"
            ),
            button_text="Open Folder",
            button_slot=self._open_app_data_folder,
        )
        outer.addWidget(card)

        outer.addStretch()

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
