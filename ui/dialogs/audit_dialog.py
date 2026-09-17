"""
ui/dialogs/audit_dialog.py
Pre-Flight Data Audit dialog displayed when flaws (empty cells, duplicates) are detected before PDF generation.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from data_engine.preflight_sanitizer import AuditReport


class AuditPreCheckDialog(QDialog):
    """Audit Dialog showing detected dataset flaws with Auto-Sanitize & Continue or Cancel options."""

    def __init__(
        self,
        report: AuditReport,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.report = report

        self.setWindowTitle("Pre-Flight Data Audit")
        self.resize(680, 480)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Title
        title = QLabel("⚠️  Pre-Flight Data Audit Found Issues")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #92400e;")
        layout.addWidget(title)

        # Summary Banner Card
        banner = QFrame()
        banner.setStyleSheet("""
            QFrame {
                background: #fffbeb;
                border: 1px solid #fde68a;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        b_layout = QVBoxLayout(banner)
        b_layout.setContentsMargins(12, 10, 12, 10)
        b_layout.setSpacing(4)

        summary_text = (
            f"<b>{len(self.report.issues)} total issue(s)</b> detected across <b>{self.report.affected_rows_count} record(s)</b>.<br>"
            f"• Empty/Missing Mapped Values: <b>{self.report.empty_count}</b><br>"
            f"• Duplicate Identifier(s): <b>{self.report.duplicate_count}</b>"
        )
        summary_lbl = QLabel(summary_text)
        summary_lbl.setStyleSheet("font-size: 12px; color: #78350f; line-height: 1.4;")
        b_layout.addWidget(summary_lbl)
        layout.addWidget(banner)

        desc = QLabel(
            "Review the detected issues below. You can either <b>Cancel</b> to fix your spreadsheet, "
            "or choose <b>Auto-Sanitize & Continue</b> to automatically fill empty mapped cells and resolve duplicate identifiers."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 12px; color: #4b5563;")
        layout.addWidget(desc)

        # Issues Table
        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["Row #", "Column", "Issue Type", "Details"])
        self._table.setRowCount(len(self.report.issues))
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        self._table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #e5e7eb;
                border-radius: 4px;
                background-color: white;
                color: #111827;
                font-size: 12px;
                gridline-color: #f3f4f6;
            }
            QTableWidget::item {
                padding: 4px 8px;
            }
            QHeaderView::section {
                background-color: #f9fafb;
                color: #374151;
                font-weight: 600;
                border: none;
                border-bottom: 1px solid #e5e7eb;
                padding: 6px 8px;
            }
        """)

        for row_idx, issue in enumerate(self.report.issues):
            item_row = QTableWidgetItem(f"Row {issue.row_num}")
            item_row.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row_idx, 0, item_row)

            item_col = QTableWidgetItem(issue.column_name)
            self._table.setItem(row_idx, 1, item_col)

            item_type = QTableWidgetItem(issue.issue_type)
            item_type.setForeground(Qt.GlobalColor.darkRed if issue.issue_type == "Empty Cell" else Qt.GlobalColor.darkYellow)
            self._table.setItem(row_idx, 2, item_type)

            item_desc = QTableWidgetItem(issue.description)
            self._table.setItem(row_idx, 3, item_desc)

        layout.addWidget(self._table)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        cancel_btn = QPushButton("✕  Cancel Generation")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #ffffff; color: #374151; border: 1px solid #d1d5db;
                border-radius: 5px; padding: 7px 16px; font-size: 12px; font-weight: 600;
            }
            QPushButton:hover { background: #fee2e2; color: #991b1b; border-color: #fca5a5; }
        """)
        cancel_btn.clicked.connect(self.reject)

        sanitize_btn = QPushButton("⚡  Auto-Sanitize & Continue")
        sanitize_btn.setDefault(True)
        sanitize_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        sanitize_btn.setStyleSheet("""
            QPushButton {
                background: #4f7ef8; color: white; border: 1px solid #3b82f6;
                border-radius: 5px; padding: 7px 18px; font-size: 12px; font-weight: 600;
            }
            QPushButton:hover { background: #3b6fd8; }
            QPushButton:pressed { background: #2b5fc8; }
        """)
        sanitize_btn.clicked.connect(self.accept)

        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(sanitize_btn)
        layout.addLayout(btn_row)

