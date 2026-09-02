"""
Dashboard view – Dataset management, header inspection, validation, printing & batch generation.
"""
from __future__ import annotations

import os
from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
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

from data_engine.excel_loader import (
    export_dataset_backup,
    import_dataset_backup,
    load_excel,
    validate_all_rows,
    validate_unique_column,
)
from data_engine.exceptions import DuplicateUniqueValueError, FileLockedError


class DashboardView(QWidget):
    """Dashboard screen: load dataset, inspect fields, validate, print & generate."""

    excel_loaded = pyqtSignal(list)
    dataset_cleared = pyqtSignal()
    print_one_requested = pyqtSignal()
    print_all_requested = pyqtSignal()
    generate_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._headers: list[str] = []
        self._rows: list[dict[str, str]] = []
        self._source_file_path: str = ""

        self._build_ui()

    # ── UI Construction ───────────────────────────────────────────────────────

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

    def _build_top_bar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.setSpacing(10)

        title = QLabel("Dashboard")
        title.setStyleSheet("font-size: 22px; font-weight: 700; color: #1a1a2e;")

        self._load_btn = QPushButton("📂  Load Excel File")
        self._load_btn.setFixedHeight(38)
        self._load_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._load_btn.setStyleSheet("""
            QPushButton {
                background-color: #22c55e; color: white; border: none;
                border-radius: 6px; padding: 0 16px; font-size: 13px; font-weight: 600;
            }
            QPushButton:hover { background-color: #16a34a; }
        """)
        self._load_btn.clicked.connect(self._on_load_excel)

        self._import_backup_btn = QPushButton("📦  Import .dataset.backup")
        self._import_backup_btn.setFixedHeight(38)
        self._import_backup_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._import_backup_btn.setStyleSheet("""
            QPushButton {
                background-color: #6366f1; color: white; border: none;
                border-radius: 6px; padding: 0 16px; font-size: 13px; font-weight: 600;
            }
            QPushButton:hover { background-color: #4f46e5; }
        """)
        self._import_backup_btn.clicked.connect(self._on_import_backup)

        self._export_backup_btn = QPushButton("💾  Export .dataset.backup")
        self._export_backup_btn.setFixedHeight(38)
        self._export_backup_btn.setEnabled(False)
        self._export_backup_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._export_backup_btn.setStyleSheet("""
            QPushButton {
                background-color: #f3f4f6; color: #374151; border: 1px solid #d1d5db;
                border-radius: 6px; padding: 0 16px; font-size: 13px; font-weight: 600;
            }
            QPushButton:hover { background-color: #e5e7eb; }
        """)
        self._export_backup_btn.clicked.connect(self._on_export_backup)

        bar.addWidget(title)
        bar.addStretch()
        bar.addWidget(self._import_backup_btn)
        bar.addWidget(self._export_backup_btn)
        bar.addWidget(self._load_btn)
        return bar

    def _build_empty_state(self) -> QWidget:
        box = QFrame()
        box.setObjectName("EmptyStateCard")
        box.setStyleSheet("""
            QFrame#EmptyStateCard {
                background-color: #ffffff; border: 2px dashed #d1d5db;
                border-radius: 12px;
            }
        """)
        v = QVBoxLayout(box)
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.setSpacing(12)

        icon = QLabel("📊")
        icon.setStyleSheet("font-size: 48px;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        head = QLabel("No Student Dataset Loaded")
        head.setStyleSheet("font-size: 18px; font-weight: 600; color: #111827;")
        head.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sub = QLabel(
            "Click 'Load Excel File' above to ingest student records (.xlsx / .xls)\n"
            "or import an external '.dataset.backup' file."
        )
        sub.setStyleSheet("font-size: 13px; color: #6b7280;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)

        v.addWidget(icon)
        v.addWidget(head)
        v.addWidget(sub)
        return box

    def _build_loaded_state(self) -> QWidget:
        root = QWidget()
        v = QVBoxLayout(root)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(14)

        v.addWidget(self._build_file_info_bar())

        # Main operations bar (Print One, Print All, Save All)
        ops_group = QGroupBox("Operations")
        ops_group.setStyleSheet("""
            QGroupBox {
                font-size: 13px; font-weight: 700; color: #1a1a2e;
                border: 1px solid #e5e7eb; border-radius: 8px;
                padding-top: 14px; background: white;
            }
        """)
        ops_row = QHBoxLayout(ops_group)
        ops_row.setSpacing(10)

        p1_btn = QPushButton("🔍  Print Single Result")
        p1_btn.setFixedHeight(36)
        p1_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        p1_btn.setStyleSheet("""
            QPushButton {
                background: #f3f4f6; color: #1f2937; border: 1px solid #d1d5db;
                border-radius: 5px; padding: 0 14px; font-weight: 600; font-size: 12px;
            }
            QPushButton:hover { background: #e5e7eb; }
        """)
        p1_btn.clicked.connect(self.print_one_requested.emit)

        pall_btn = QPushButton("🖨  Print All Results")
        pall_btn.setFixedHeight(36)
        pall_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        pall_btn.setStyleSheet("""
            QPushButton {
                background: #f3f4f6; color: #1f2937; border: 1px solid #d1d5db;
                border-radius: 5px; padding: 0 14px; font-weight: 600; font-size: 12px;
            }
            QPushButton:hover { background: #e5e7eb; }
        """)
        pall_btn.clicked.connect(self.print_all_requested.emit)

        gen_all_btn = QPushButton("🚀  Save All (Generate PDFs)")
        gen_all_btn.setFixedHeight(36)
        gen_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        gen_all_btn.setStyleSheet("""
            QPushButton {
                background: #4f7ef8; color: white; border: none;
                border-radius: 5px; padding: 0 18px; font-weight: 700; font-size: 12px;
            }
            QPushButton:hover { background: #3b6ef0; }
        """)
        gen_all_btn.clicked.connect(self.generate_requested.emit)

        ops_row.addWidget(p1_btn)
        ops_row.addWidget(pall_btn)
        ops_row.addStretch()
        ops_row.addWidget(gen_all_btn)
        v.addWidget(ops_group)

        # Columns + Validation
        cols_row = QHBoxLayout()
        cols_row.setSpacing(14)
        cols_row.addWidget(self._build_headers_panel(), stretch=2)
        cols_row.addWidget(self._build_validation_panel(), stretch=3)
        v.addLayout(cols_row, stretch=1)

        return root

    def _build_file_info_bar(self) -> QWidget:
        bar = QFrame()
        bar.setStyleSheet("""
            QFrame {
                background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px;
                padding: 4px;
            }
        """)
        row = QHBoxLayout(bar)
        row.setContentsMargins(14, 8, 14, 8)
        row.setSpacing(12)

        icon = QLabel("📄")
        icon.setStyleSheet("font-size: 20px;")
        self._filename_label = QLabel()
        self._filename_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #15803d;")

        self._rowcount_badge = QLabel()
        self._rowcount_badge.setStyleSheet("""
            background: #dcfce7; color: #166534; font-size: 12px; font-weight: 600;
            padding: 3px 10px; border-radius: 12px;
        """)

        clear_btn = QPushButton("✕ Clear Dataset")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #dc2626; border: none;
                font-size: 12px; font-weight: 600; padding: 4px 8px;
            }
            QPushButton:hover { text-decoration: underline; }
        """)
        clear_btn.clicked.connect(self._on_clear)

        row.addWidget(icon)
        row.addWidget(self._filename_label, stretch=1)
        row.addWidget(self._rowcount_badge)
        row.addWidget(clear_btn)
        return bar

    def _build_headers_panel(self) -> QGroupBox:
        group = QGroupBox("Dataset Columns")
        group.setStyleSheet("""
            QGroupBox {
                font-size: 13px; font-weight: 600; color: #374151;
                border: 1px solid #e5e7eb; border-radius: 8px;
                padding-top: 14px; background: white;
            }
        """)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(10, 12, 10, 10)

        self._headers_list = QListWidget()
        self._headers_list.setStyleSheet("""
            QListWidget {
                border: none; font-size: 12px; color: #111827; background: white;
            }
            QListWidget::item { padding: 6px 8px; }
            QListWidget::item:hover { background-color: #f0f9ff; }
        """)
        layout.addWidget(self._headers_list)
        return group

    def _build_validation_panel(self) -> QGroupBox:
        group = QGroupBox("Data Integrity & Validation")
        group.setStyleSheet("""
            QGroupBox {
                font-size: 13px; font-weight: 600; color: #374151;
                border: 1px solid #e5e7eb; border-radius: 8px;
                padding-top: 14px; background: white;
            }
        """)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        desc = QLabel("Scan all rows for empty cells, whitespace-only entries, or duplicate records.")
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 12px; color: #6b7280;")
        layout.addWidget(desc)

        val_btn = QPushButton("🔍  Validate All Records")
        val_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        val_btn.setStyleSheet("""
            QPushButton {
                background: #f3f4f6; color: #374151; border: 1px solid #d1d5db;
                border-radius: 5px; padding: 8px 14px; font-weight: 600; font-size: 12px;
            }
            QPushButton:hover { background: #e5e7eb; }
        """)
        val_btn.clicked.connect(self._on_validate_data)
        layout.addWidget(val_btn)

        self._val_result_lbl = QLabel("Ready to validate.")
        self._val_result_lbl.setStyleSheet("font-size: 12px; color: #6b7280;")
        self._val_result_lbl.setWordWrap(True)
        layout.addWidget(self._val_result_lbl)

        layout.addStretch()
        return group

    # ── Actions & Slots ───────────────────────────────────────────────────────

    def _on_load_excel(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Student Excel File",
            "",
            "Excel Files (*.xlsx *.xls)",
        )
        if not path:
            return

        while True:
            try:
                headers, rows = load_excel(path)
                self._source_file_path = path
                self._headers = headers
                self._rows = rows
                self._apply_dataset(os.path.basename(path), headers, rows)
                break
            except FileLockedError as exc:
                reply = QMessageBox.warning(
                    self,
                    "File Open in Excel",
                    str(exc),
                    QMessageBox.StandardButton.Retry | QMessageBox.StandardButton.Cancel,
                    QMessageBox.StandardButton.Retry,
                )
                if reply != QMessageBox.StandardButton.Retry:
                    break
            except Exception as exc:
                QMessageBox.critical(self, "Load Error", f"Failed to load Excel file:\n{exc}")
                break

    def _on_import_backup(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Dataset Backup",
            "",
            "Dataset Backup Files (*.dataset.backup *.json)",
        )
        if path:
            try:
                headers, rows, meta = import_dataset_backup(path)
                self._headers = headers
                self._rows = rows
                self._source_file_path = path
                self._apply_dataset(os.path.basename(path), headers, rows)
                QMessageBox.information(self, "Backup Restored", f"Restored {len(rows)} records successfully.")
            except Exception as exc:
                QMessageBox.critical(self, "Import Error", f"Failed to restore backup:\n{exc}")

    def _on_export_backup(self) -> None:
        if not self._rows:
            return
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Dataset Backup",
            "StudentRecords.dataset.backup",
            "Dataset Backup Files (*.dataset.backup)",
        )
        if save_path:
            try:
                export_dataset_backup(save_path, self._rows, self._headers)
                QMessageBox.information(self, "Backup Saved", f"Dataset backup saved successfully to:\n{save_path}")
            except Exception as exc:
                QMessageBox.critical(self, "Backup Error", f"Failed to save backup:\n{exc}")

    def _apply_dataset(self, filename: str, headers: list[str], rows: list[dict[str, str]]) -> None:
        self._filename_label.setText(filename)
        self._rowcount_badge.setText(f"{len(rows)} rows  •  {len(headers)} columns")

        self._headers_list.clear()
        for h in headers:
            self._headers_list.addItem(QListWidgetItem(f"•  {h}"))

        self._export_backup_btn.setEnabled(True)
        self._empty_state.hide()
        self._loaded_state.show()

        self.excel_loaded.emit(headers)

    def _on_clear(self) -> None:
        self._headers = []
        self._rows = []
        self._source_file_path = ""
        self._export_backup_btn.setEnabled(False)
        self._loaded_state.hide()
        self._empty_state.show()
        self.dataset_cleared.emit()

    def _on_validate_data(self) -> None:
        errors = validate_all_rows(self._rows)
        if not errors:
            self._val_result_lbl.setText("✅  All records are valid! Zero empty cells found.")
            self._val_result_lbl.setStyleSheet("color: #16a34a; font-weight: 600; font-size: 12px;")
        else:
            lines = [f"❌  Found {len(errors)} empty cell(s):"]
            for row_num, col in errors[:8]:
                lines.append(f"• Row {row_num}: Column '{col}' is empty")
            if len(errors) > 8:
                lines.append(f"... and {len(errors) - 8} more.")
            self._val_result_lbl.setText("\n".join(lines))
            self._val_result_lbl.setStyleSheet("color: #dc2626; font-size: 12px;")

    def get_dataset(self) -> tuple[list[str], list[dict[str, str]]]:
        return self._headers, self._rows

    @staticmethod
    def _make_divider() -> QFrame:
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet("color: #e5e7eb;")
        return div
