"""
Generation Dialogs.
Includes:
- GenerationSetupDialog: Select output folder & naming column, run pre-checks.
- GenerationProgressDialog: Live progress dashboard with pause/resume error resolution.
"""
from __future__ import annotations

import os
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from generation.pdf_generator import GeneratorWorker, check_pre_generation


class GenerationSetupDialog(QDialog):
    """Dialog to choose destination folder and filename identifier before starting batch."""

    def __init__(self, headers: list[str], total_records: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Batch Generation Setup")
        self.setFixedSize(480, 260)
        self.headers = headers
        self.total_records = total_records

        self.selected_output_dir = os.path.join(os.path.expanduser("~"), "Documents", "ResultGenerator_Outputs")
        self.selected_name_col = ""

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Title / Info
        title = QLabel(f"Generate PDFs for {self.total_records} Records")
        title.setStyleSheet("font-size: 15px; font-weight: 700; color: #1a1a2e;")
        layout.addWidget(title)

        # Output Folder Selection
        f_lbl = QLabel("Output Destination Folder:")
        f_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #374151;")
        layout.addWidget(f_lbl)

        f_row = QHBoxLayout()
        f_row.setSpacing(8)
        self._dir_label = QLabel(self.selected_output_dir)
        self._dir_label.setStyleSheet("""
            background: #f3f4f6; border: 1px solid #d1d5db; border-radius: 4px;
            padding: 6px 10px; font-size: 11px; color: #1f2937;
        """)
        browse_btn = QPushButton("Browse...")
        browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_btn.setStyleSheet("""
            QPushButton {
                background: white; border: 1px solid #d1d5db; border-radius: 4px;
                padding: 6px 12px; font-size: 12px; font-weight: 600;
            }
            QPushButton:hover { background: #f9fafb; }
        """)
        browse_btn.clicked.connect(self._on_browse)
        f_row.addWidget(self._dir_label, stretch=1)
        f_row.addWidget(browse_btn)
        layout.addLayout(f_row)

        # Filename Column Selection
        c_lbl = QLabel("File Naming Column (e.g. Student Name / Roll No):")
        c_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #374151;")
        layout.addWidget(c_lbl)

        self._col_combo = QComboBox()
        self._col_combo.addItem("(Auto: Result_Row_X)")
        for h in self.headers:
            self._col_combo.addItem(h)
        # Try to preselect common student name/id fields if present
        for candidate in ["Name", "Student Name", "Student_Name", "Roll No", "Roll", "ID"]:
            idx = self._col_combo.findText(candidate, Qt.MatchFlag.MatchFixedString)
            if idx > 0:
                self._col_combo.setCurrentIndex(idx)
                break
        self._col_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #d1d5db; border-radius: 4px;
                padding: 5px 8px; font-size: 12px; background: white;
            }
        """)
        layout.addWidget(self._col_combo)

        layout.addStretch()

        # Action Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: white; border: 1px solid #d1d5db; border-radius: 4px;
                padding: 6px 16px; font-size: 12px; font-weight: 600; color: #374151;
            }
            QPushButton:hover { background: #f3f4f6; }
        """)
        cancel_btn.clicked.connect(self.reject)

        start_btn = QPushButton("🚀 Start Generation")
        start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        start_btn.setStyleSheet("""
            QPushButton {
                background: #22c55e; border: none; border-radius: 4px;
                padding: 6px 18px; font-size: 12px; font-weight: 600; color: white;
            }
            QPushButton:hover { background: #16a34a; }
        """)
        start_btn.clicked.connect(self._on_start)

        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(start_btn)
        layout.addLayout(btn_row)

    def _on_browse(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder", self.selected_output_dir)
        if folder:
            self.selected_output_dir = folder
            self._dir_label.setText(folder)

    def _on_start(self):
        # Pre-generation checks: Permissions + 10% disk space buffer
        est_size = max(5 * 1024 * 1024, self.total_records * 500 * 1024)
        ok, msg = check_pre_generation(self.selected_output_dir, est_size)
        if not ok:
            QMessageBox.critical(self, "Pre-Generation Check Failed", msg)
            return

        choice = self._col_combo.currentText()
        self.selected_name_col = "" if choice.startswith("(Auto:") else choice
        self.accept()


class GenerationProgressDialog(QDialog):
    """Active Generation Progress Dashboard with pause/error prompt handling."""

    def __init__(
        self,
        template_state: dict,
        rows: list[dict[str, str]],
        output_dir: str,
        name_column: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Generating PDFs...")
        self.setFixedSize(500, 240)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint)

        self.template_state = template_state
        self.rows = rows
        self.output_dir = output_dir
        self.name_column = name_column

        self.worker = GeneratorWorker(template_state, rows, output_dir, name_column, self)
        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        self._status_title = QLabel("Batch PDF Generation in Progress...")
        self._status_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #1a1a2e;")
        layout.addWidget(self._status_title)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, len(self.rows))
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #d1d5db; border-radius: 6px;
                text-align: center; font-size: 12px; font-weight: 600;
                height: 22px; background: #f3f4f6;
            }
            QProgressBar::chunk {
                background-color: #4f7ef8; border-radius: 5px;
            }
        """)
        layout.addWidget(self._progress_bar)

        self._current_file_lbl = QLabel("Initializing...")
        self._current_file_lbl.setStyleSheet("font-size: 12px; color: #4b5563;")
        layout.addWidget(self._current_file_lbl)

        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel_btn.setStyleSheet("""
            QPushButton {
                background: #fee2e2; border: 1px solid #fca5a5; border-radius: 4px;
                padding: 6px 16px; font-size: 12px; font-weight: 600; color: #dc2626;
            }
            QPushButton:hover { background: #fecaca; }
        """)
        self._cancel_btn.clicked.connect(self._on_cancel)
        btn_row.addWidget(self._cancel_btn)
        layout.addLayout(btn_row)

    def _connect_signals(self):
        self.worker.progress_updated.connect(self._on_progress)
        self.worker.error_occurred.connect(self._on_missing_data_error)
        self.worker.generation_finished.connect(self._on_finished)
        self.worker.generation_aborted.connect(self._on_aborted)

    def start(self):
        self.worker.start()
        self.exec()

    def _on_progress(self, current: int, total: int, filename: str):
        self._progress_bar.setValue(current)
        self._current_file_lbl.setText(f"Processing ({current}/{total}): {filename}")

    def _on_missing_data_error(self, row_num: int, col_name: str, row_dict: dict):
        """Display Missing Data Error Dashboard: [Retry] [Skip Record] [Cancel]."""
        msg = QMessageBox(self)
        msg.setWindowTitle("Missing Data Error")
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setText(f"Critical Error: Missing data in Row {row_num}!")
        msg.setInformativeText(
            f"The mapped Excel column '{col_name}' is empty for this student record.\n"
            f"Empty cells are not allowed during generation.\n\n"
            f"How would you like to proceed?"
        )

        retry_btn = msg.addButton("Retry", QMessageBox.ButtonRole.ActionRole)
        skip_btn = msg.addButton("Skip Record", QMessageBox.ButtonRole.ActionRole)
        cancel_btn = msg.addButton("Cancel Generation", QMessageBox.ButtonRole.RejectRole)
        msg.setDefaultButton(retry_btn)

        msg.exec()
        clicked = msg.clickedButton()

        if clicked == retry_btn:
            self.worker.resolve_error(GeneratorWorker.ACTION_RETRY)
        elif clicked == skip_btn:
            self.worker.resolve_error(GeneratorWorker.ACTION_SKIP)
        else:
            self.worker.resolve_error(GeneratorWorker.ACTION_CANCEL)

    def _on_finished(self, success_count: int, skipped_count: int):
        self._progress_bar.setValue(len(self.rows))
        self._status_title.setText("Generation Complete! 🎉")
        self._current_file_lbl.setText(f"Successfully created {success_count} PDFs. (Skipped: {skipped_count})")
        self._cancel_btn.setText("Close")
        self._cancel_btn.setStyleSheet("""
            QPushButton {
                background: #22c55e; border: none; border-radius: 4px;
                padding: 6px 18px; font-size: 12px; font-weight: 600; color: white;
            }
            QPushButton:hover { background: #16a34a; }
        """)
        self._cancel_btn.clicked.disconnect()
        self._cancel_btn.clicked.connect(self.accept)

        QMessageBox.information(
            self,
            "Success",
            f"Batch generation completed!\n\n"
            f"Generated: {success_count} PDF(s)\n"
            f"Skipped: {skipped_count} record(s)\n"
            f"Saved in: {self.output_dir}"
        )

    def _on_aborted(self, reason: str):
        self._status_title.setText("Generation Stopped")
        self._current_file_lbl.setText(reason)
        self._cancel_btn.setText("Close")
        self._cancel_btn.clicked.disconnect()
        self._cancel_btn.clicked.connect(self.reject)
        QMessageBox.warning(self, "Batch Stopped", reason)

    def _on_cancel(self):
        self._cancel_btn.setEnabled(False)
        self._current_file_lbl.setText("Cancelling...")
        self.worker.cancel()
