"""
Dashboard view – Excel file loader and header inspector.

Layout (when file loaded)
-------------------------
QVBoxLayout
 ├── Top bar:  title  +  [Load Excel File] button
 ├── Divider
 ├── [empty-state widget]  -- visible when no file loaded
 └── [loaded-state widget] -- visible once a file is loaded
      ├── File-info bar  (filename · row-count badge · [Clear])
      └── QHBoxLayout
           ├── Headers panel  (QListWidget)
           └── Validation panel (button + result label)
"""
from __future__ import annotations

import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from data_engine.excel_loader import load_excel, validate_all_rows
from data_engine.exceptions import FileLockedError


class DashboardView(QWidget):
    """Dashboard screen: load an Excel file and inspect its structure."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._excel_data: dict | None = None
        self._build_ui()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(18)

        layout.addLayout(self._build_top_bar())
        layout.addWidget(self._make_divider())

        self._empty_state  = self._build_empty_state()
        self._loaded_state = self._build_loaded_state()

        layout.addWidget(self._empty_state,  stretch=1)
        layout.addWidget(self._loaded_state, stretch=1)

        self._loaded_state.hide()

    # ── Top bar ───────────────────────────────────────────────────────────────

    def _build_top_bar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.setSpacing(12)

        title = QLabel("Dashboard")
        title.setStyleSheet(
            "font-size: 22px; font-weight: 700; color: #1a1a2e;"
        )

        self._load_btn = QPushButton("📂   Load Excel File")
        self._load_btn.setFixedHeight(38)
        self._load_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._load_btn.setStyleSheet("""
            QPushButton {
                background-color: #22c55e;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 0 20px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover   { background-color: #16a34a; }
            QPushButton:pressed { background-color: #15803d; }
        """)
        self._load_btn.clicked.connect(self._on_load_excel)

        bar.addWidget(title)
        bar.addStretch()
        bar.addWidget(self._load_btn)
        return bar

    # ── Empty state ───────────────────────────────────────────────────────────

    def _build_empty_state(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)

        icon = QLabel("📋")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("font-size: 56px;")

        heading = QLabel("No Excel File Loaded")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        heading.setStyleSheet(
            "font-size: 20px; font-weight: 700; color: #374151;"
        )

        hint = QLabel(
            'Click \u201cLoad Excel File\u201d to get started.\n'
            "Column headers from your sheet will be listed here."
        )
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)
        hint.setStyleSheet("font-size: 13px; color: #9ca3af;")

        layout.addWidget(icon)
        layout.addWidget(heading)
        layout.addWidget(hint)
        return widget

    # ── Loaded state ──────────────────────────────────────────────────────────

    def _build_loaded_state(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        layout.addWidget(self._build_file_info_bar())

        content = QHBoxLayout()
        content.setSpacing(14)
        content.addWidget(self._build_headers_panel(),    stretch=1)
        content.addWidget(self._build_validation_panel(), stretch=1)
        layout.addLayout(content)

        return widget

    def _build_file_info_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("FileInfoBar")
        bar.setFixedHeight(58)
        bar.setStyleSheet("""
            QFrame#FileInfoBar {
                background: #eff6ff;
                border: 1px solid #bfdbfe;
                border-radius: 8px;
            }
        """)
        row = QHBoxLayout(bar)
        row.setContentsMargins(16, 0, 16, 0)
        row.setSpacing(14)

        icon = QLabel("\U0001f4c4")          # 📄
        icon.setStyleSheet("font-size: 20px;")

        self._filename_label = QLabel("\u2014")
        self._filename_label.setStyleSheet(
            "font-size: 13px; font-weight: 600; color: #1e40af;"
        )

        self._rowcount_badge = QLabel("")
        self._rowcount_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._rowcount_badge.setStyleSheet("""
            background: #3b82f6;
            color: white;
            border-radius: 10px;
            padding: 2px 12px;
            font-size: 12px;
            font-weight: 600;
        """)

        self._colcount_badge = QLabel("")
        self._colcount_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._colcount_badge.setStyleSheet("""
            background: #8b5cf6;
            color: white;
            border-radius: 10px;
            padding: 2px 12px;
            font-size: 12px;
            font-weight: 600;
        """)

        self._clear_btn = QPushButton("\u2715  Clear")
        self._clear_btn.setFixedHeight(28)
        self._clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #6b7280;
                border: 1px solid #d1d5db;
                border-radius: 5px;
                padding: 0 10px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #fee2e2;
                color: #dc2626;
                border-color: #fca5a5;
            }
        """)
        self._clear_btn.clicked.connect(self._on_clear)

        row.addWidget(icon)
        row.addWidget(self._filename_label, stretch=1)
        row.addWidget(self._rowcount_badge)
        row.addWidget(self._colcount_badge)
        row.addWidget(self._clear_btn)
        return bar

    def _build_headers_panel(self) -> QGroupBox:
        group = QGroupBox("Column Headers")
        group.setStyleSheet("""
            QGroupBox {
                font-size: 13px; font-weight: 600; color: #374151;
                border: 1px solid #e5e7eb; border-radius: 8px;
                margin-top: 8px; background: white;
            }
            QGroupBox::title { subcontrol-origin: margin; padding: 0 6px; }
        """)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(10, 12, 10, 10)

        self._headers_list = QListWidget()
        self._headers_list.setAlternatingRowColors(True)
        self._headers_list.setStyleSheet("""
            QListWidget {
                border: none;
                font-size: 13px;
                color: #111827;
                background: white;
                alternate-background-color: #f9fafb;
            }
            QListWidget::item {
                padding: 8px 10px;
            }
            QListWidget::item:selected {
                background-color: #eff6ff;
                color: #1d4ed8;
            }
            QListWidget::item:hover {
                background-color: #f0f9ff;
            }
        """)
        layout.addWidget(self._headers_list)
        return group

    def _build_validation_panel(self) -> QGroupBox:
        group = QGroupBox("Data Validation")
        group.setStyleSheet("""
            QGroupBox {
                font-size: 13px; font-weight: 600; color: #374151;
                border: 1px solid #e5e7eb; border-radius: 8px;
                margin-top: 8px; background: white;
            }
            QGroupBox::title { subcontrol-origin: margin; padding: 0 6px; }
        """)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        self._validate_btn = QPushButton("\U0001f50d   Validate All Rows for Empty Cells")
        self._validate_btn.setFixedHeight(38)
        self._validate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._validate_btn.setStyleSheet("""
            QPushButton {
                background-color: #f59e0b;
                color: white; border: none;
                border-radius: 6px;
                font-size: 13px; font-weight: 600;
            }
            QPushButton:hover   { background-color: #d97706; }
            QPushButton:pressed { background-color: #b45309; }
        """)
        self._validate_btn.clicked.connect(self._on_validate)

        self._validation_result = QLabel(
            "Press the button above to scan all rows\nfor empty or blank cells."
        )
        self._validation_result.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        self._validation_result.setWordWrap(True)
        self._validation_result.setStyleSheet(
            "font-size: 12px; color: #6b7280; line-height: 1.7;"
        )

        layout.addWidget(self._validate_btn)
        layout.addWidget(self._validation_result, stretch=1)
        return group

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_load_excel(self) -> None:
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Open Excel Workbook",
            "",
            "Excel Files (*.xlsx *.xls);;All Files (*)",
        )
        if filepath:
            self._attempt_load(filepath)

    def _attempt_load(self, filepath: str) -> None:
        """Try to load the file; on FileLockedError show Retry/Cancel dialog."""
        try:
            data = load_excel(filepath)
        except FileLockedError as exc:
            self._show_locked_dialog(filepath, str(exc))
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Load Failed",
                f"Could not load the file:\n\n{exc}",
            )
        else:
            self._excel_data = data
            self._populate_ui(data)

    def _show_locked_dialog(self, filepath: str, detail: str) -> None:
        """Show 'File is open in another program' with [Retry] / [Cancel]."""
        msg = QMessageBox(self)
        msg.setWindowTitle("File In Use")
        msg.setText("The file is open in another program.")
        msg.setInformativeText(detail)
        msg.setIcon(QMessageBox.Icon.Warning)

        retry_btn  = msg.addButton("Retry",  QMessageBox.ButtonRole.AcceptRole)
        _cancel    = msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        msg.setDefaultButton(retry_btn)
        msg.exec()

        if msg.clickedButton() is retry_btn:
            self._attempt_load(filepath)   # recursive retry

    def _on_validate(self) -> None:
        if not self._excel_data:
            return

        result = validate_all_rows(self._excel_data["rows"])

        if result["is_valid"]:
            self._validation_result.setStyleSheet(
                "font-size: 12px; color: #16a34a; font-weight: 600;"
            )
            self._validation_result.setText(
                f"\u2705  All {self._excel_data['total_rows']} row(s) are valid.\n"
                f"No empty cells detected."
            )
        else:
            ec = result["error_count"]
            er = len(result["errors_by_row"])

            # Show first 4 errors as a preview
            preview_lines: list[str] = []
            for _row_i, errs in list(result["errors_by_row"].items())[:4]:
                preview_lines.append(f"\u26a0  {errs[0]}")
            if er > 4:
                preview_lines.append(f"... and {er - 4} more row(s) with errors.")

            self._validation_result.setStyleSheet(
                "font-size: 12px; color: #dc2626;"
            )
            self._validation_result.setText(
                f"\u274c  {ec} empty cell(s) across {er} row(s):\n\n"
                + "\n".join(preview_lines)
            )

    def _on_clear(self) -> None:
        self._excel_data = None
        self._headers_list.clear()
        self._validation_result.setStyleSheet("font-size: 12px; color: #6b7280;")
        self._validation_result.setText(
            "Press the button above to scan all rows\nfor empty or blank cells."
        )
        self._loaded_state.hide()
        self._empty_state.show()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _populate_ui(self, data: dict) -> None:
        self._filename_label.setText(os.path.basename(data["filepath"]))
        self._rowcount_badge.setText(f"{data['total_rows']} row(s)")
        self._colcount_badge.setText(f"{len(data['headers'])} column(s)")

        self._headers_list.clear()
        for i, header in enumerate(data["headers"], start=1):
            item = QListWidgetItem(f"  {i}.   {header}")
            self._headers_list.addItem(item)

        # Reset validation panel for new file
        self._validation_result.setStyleSheet("font-size: 12px; color: #6b7280;")
        self._validation_result.setText(
            "Press the button above to scan all rows\nfor empty or blank cells."
        )

        self._empty_state.hide()
        self._loaded_state.show()

    @staticmethod
    def _make_divider() -> QFrame:
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet("color: #e5e7eb;")
        return div
