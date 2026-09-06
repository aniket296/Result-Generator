"""
ui/dialogs/print_one_dialog.py
Dialog for looking up a single student by Unique Field (e.g. Enrollment / Roll No)
and directly printing or saving their individual result paper.
"""
from __future__ import annotations

import os
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from generation.pdf_generator import generate_single_pdf, get_unique_result_filename
from generation.printer import print_single_student_record


class PrintOneDialog(QDialog):
    """Search and print a single student result paper."""

    def __init__(
        self,
        template_state: dict[str, Any],
        headers: list[str],
        rows: list[dict[str, str]],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.template_state = template_state
        self.headers = headers
        self.rows = rows
        self._matched_row: dict[str, str] | None = None

        self.setWindowTitle("Print Individual Student Result")
        self.setFixedSize(560, 520)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Title
        title = QLabel("🔍 Print Individual Student Result")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #1a1a2e;")
        layout.addWidget(title)

        desc = QLabel("Select the unique identifying column and enter the student identifier to locate their record.")
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 12px; color: #4b5563;")
        layout.addWidget(desc)

        # Search Controls Group
        search_box = QGroupBox("Search Student Record")
        search_box.setStyleSheet("""
            QGroupBox {
                font-size: 12px; font-weight: 600; color: #374151;
                border: 1px solid #e5e7eb; border-radius: 6px;
                margin-top: 8px; padding-top: 14px;
            }
        """)
        s_layout = QVBoxLayout(search_box)
        s_layout.setSpacing(10)

        # Row 1: Column selector
        r1 = QHBoxLayout()
        r1_lbl = QLabel("Identifier Column:")
        r1_lbl.setStyleSheet("font-size: 12px; color: #374151;")
        r1.addWidget(r1_lbl)
        self._col_combo = QComboBox()
        self._col_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #d1d5db; border-radius: 4px;
                padding: 4px 8px; font-size: 12px; background: white; color: #000000;
            }
        """)
        for h in self.headers:
            self._col_combo.addItem(h)

        # Preselect Roll/ID if present
        for cand in ["Enrollment", "Enrollment_Number", "Roll No", "Roll", "ID", "Student_ID"]:
            idx = self._col_combo.findText(cand, Qt.MatchFlag.MatchContains)
            if idx >= 0:
                self._col_combo.setCurrentIndex(idx)
                break
        r1.addWidget(self._col_combo, stretch=1)
        s_layout.addLayout(r1)

        # Row 2: Value input + Search Button
        r2 = QHBoxLayout()
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Enter student identifier (e.g. EN2026047)...")
        self._search_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #d1d5db; border-radius: 4px;
                padding: 5px 8px; font-size: 12px; background: white; color: #000000;
            }
            QLineEdit:focus { border-color: #4f7ef8; }
        """)
        self._search_input.returnPressed.connect(self._on_search)

        find_btn = QPushButton("🔍 Find")
        find_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        find_btn.setStyleSheet("""
            QPushButton {
                background: #4f7ef8; color: white; border: none;
                border-radius: 4px; padding: 6px 14px; font-weight: 600;
            }
            QPushButton:hover { background: #3b6ef0; }
        """)
        find_btn.clicked.connect(self._on_search)

        r2.addWidget(self._search_input, stretch=1)
        r2.addWidget(find_btn)
        s_layout.addLayout(r2)

        layout.addWidget(search_box)

        # Result Details Display Area
        self._preview_card = QFrame()
        self._preview_card.setStyleSheet("""
            QFrame {
                background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 6px;
                padding: 10px;
            }
        """)
        p_layout = QVBoxLayout(self._preview_card)
        self._preview_label = QLabel("No student record selected.\nEnter an ID above and click Find.")
        self._preview_label.setStyleSheet("color: #6b7280; font-size: 12px;")
        self._preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p_layout.addWidget(self._preview_label)

        layout.addWidget(self._preview_card, stretch=1)

        # Action Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self._save_btn = QPushButton("💾 Save PDF")
        self._save_btn.setEnabled(False)
        self._save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_btn.setStyleSheet("""
            QPushButton {
                background: #ffffff; color: #374151; border: 1px solid #d1d5db;
                border-radius: 5px; padding: 7px 14px; font-weight: 600;
            }
            QPushButton:hover { background: #f3f4f6; color: #111827; }
            QPushButton:disabled { background: #f3f4f6; color: #9ca3af; border-color: #e5e7eb; }
        """)
        self._save_btn.clicked.connect(self._on_save_pdf)

        self._print_btn = QPushButton("🖨  Print Result")
        self._print_btn.setEnabled(False)
        self._print_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._print_btn.setStyleSheet("""
            QPushButton {
                background: #10b981; color: white; border: none;
                border-radius: 5px; padding: 7px 18px; font-weight: 700;
            }
            QPushButton:hover { background: #059669; color: white; }
            QPushButton:disabled { background: #d1d5db; color: #9ca3af; }
        """)
        self._print_btn.clicked.connect(self._on_print)

        close_btn = QPushButton("Close")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: #ffffff; color: #374151; border: 1px solid #d1d5db;
                border-radius: 5px; padding: 7px 14px; font-weight: 500;
            }
            QPushButton:hover { background: #f3f4f6; color: #111827; }
        """)
        close_btn.clicked.connect(self.reject)

        btn_row.addWidget(self._save_btn)
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        btn_row.addWidget(self._print_btn)
        layout.addLayout(btn_row)

    def _on_search(self) -> None:
        val = self._search_input.text().strip()
        if not val:
            QMessageBox.warning(self, "Input Required", "Please enter a student identifier to search.")
            return

        col = self._col_combo.currentText()
        matched = []
        for r in self.rows:
            if str(r.get(col, "")).strip().lower() == val.lower():
                matched.append(r)

        if not matched:
            self._matched_row = None
            self._save_btn.setEnabled(False)
            self._print_btn.setEnabled(False)
            self._preview_label.setText(f"❌ Student identifier '{val}' was not found in column '{col}'.")
            self._preview_label.setStyleSheet("color: #dc2626; font-size: 12px; font-weight: 600;")
            return

        self._matched_row = matched[0]
        self._save_btn.setEnabled(True)
        self._print_btn.setEnabled(True)

        # Format details
        lines = [f"<b>✓ Student Record Found ({len(matched)} match{'es' if len(matched) > 1 else ''})</b>:<br>"]
        for k, v in self._matched_row.items():
            lines.append(f"• <b>{k}</b>: {v}")

        self._preview_label.setText("<br>".join(lines))
        self._preview_label.setStyleSheet("color: #111827; font-size: 12px;")

    def _on_save_pdf(self) -> None:
        if not self._matched_row:
            return

        col = self._col_combo.currentText()
        u_val = self._matched_row.get(col, "Student")
        name_val = self._matched_row.get("Name", self._matched_row.get("Student_Name", ""))

        default_filename = f"{u_val}_{name_val}.PDF".upper()
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Student Result PDF",
            default_filename,
            "PDF Files (*.pdf)",
        )
        if save_path:
            try:
                generate_single_pdf(self.template_state, self._matched_row, save_path)
                QMessageBox.information(
                    self,
                    "Saved Successfully",
                    f"Student result PDF saved successfully to:\n{save_path}",
                )
            except Exception as exc:
                QMessageBox.critical(self, "Save Error", f"Failed to save PDF:\n{exc}")

    def _on_print(self) -> None:
        if not self._matched_row:
            return

        print_single_student_record(self.template_state, self._matched_row, self)
