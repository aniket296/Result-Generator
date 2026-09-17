"""
ui/dialogs/sheet_selection_dialog.py
Dialog for selecting a specific worksheet from a multi-sheet Excel workbook.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class SheetSelectionDialog(QDialog):
    """Clean popup dialog when an uploaded Excel file contains multiple sheets."""

    def __init__(
        self,
        sheet_names: list[str],
        filename: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.sheet_names = list(sheet_names)
        self.filename = filename

        self.setWindowTitle("Select Excel Worksheet")
        self.setFixedWidth(440)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        # Header
        title = QLabel("📊 Multiple Sheets Detected")
        title.setStyleSheet("font-size: 15px; font-weight: 700; color: #1a1a2e;")
        layout.addWidget(title)

        desc_text = (
            f"The workbook <b>{self.filename}</b> contains {len(self.sheet_names)} worksheets.<br>"
            "Please choose which sheet contains the student result records to import:"
            if self.filename
            else f"This workbook contains {len(self.sheet_names)} worksheets. Choose the sheet to import:"
        )
        desc = QLabel(desc_text)
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 12px; color: #4b5563; line-height: 1.4;")
        layout.addWidget(desc)

        # Card container for selection
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: #f9fafb;
                border: 1px solid #e5e7eb;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(6)

        sheet_lbl = QLabel("Worksheet:")
        sheet_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #374151;")
        card_layout.addWidget(sheet_lbl)

        self._combo = QComboBox()
        self._combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #d1d5db;
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 13px;
                background: white;
                color: #111827;
                font-weight: 500;
            }
            QComboBox:focus {
                border-color: #4f7ef8;
            }
            QComboBox QAbstractItemView {
                background: white;
                color: #111827;
                selection-background-color: #eff6ff;
                selection-color: #1d4ed8;
                padding: 4px;
            }
        """)
        for name in self.sheet_names:
            self._combo.addItem(name)

        card_layout.addWidget(self._combo)
        layout.addWidget(card)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #ffffff; color: #374151; border: 1px solid #d1d5db;
                border-radius: 5px; padding: 7px 16px; font-size: 12px; font-weight: 600;
            }
            QPushButton:hover { background: #f3f4f6; color: #111827; }
        """)
        cancel_btn.clicked.connect(self.reject)

        load_btn = QPushButton("✓  Load Sheet")
        load_btn.setDefault(True)
        load_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        load_btn.setStyleSheet("""
            QPushButton {
                background: #4f7ef8; color: white; border: 1px solid #3b82f6;
                border-radius: 5px; padding: 7px 18px; font-size: 12px; font-weight: 600;
            }
            QPushButton:hover { background: #3b6fd8; }
            QPushButton:pressed { background: #2b5fc8; }
        """)
        load_btn.clicked.connect(self.accept)

        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(load_btn)
        layout.addLayout(btn_row)

    def get_selected_sheet(self) -> str:
        """Return the user-selected sheet name."""
        return self._combo.currentText()

