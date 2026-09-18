"""
ui/dialogs/generation_dialog.py
Complete Generation Setup, Live Dashboard, Error Handling,
Failed Records Management & Skipped Records Regeneration.
"""
from __future__ import annotations

import datetime
import os
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from utils.constants import DEFAULT_NAMING_PATTERN

from generation.pdf_generator import (
    GeneratorWorker,
    check_pre_generation,
    generate_single_pdf,
    get_unique_result_filename,
    preview_filenames,
)



def _make_lbl(text: str, style: str = "") -> QLabel:
    """Create a QLabel with explicit text colour so it is always visible."""
    lbl = QLabel(text)
    lbl.setStyleSheet(style)
    return lbl


# ═════════════════════════════════════════════════════════════════════════════
# 1. GENERATION SETUP DIALOG
# ═════════════════════════════════════════════════════════════════════════════

class GenerationSetupDialog(QDialog):
    """Configuration dialog with live filename preview, validation, and print bundling."""

    def __init__(
        self,
        template_name: str,
        headers: list[str],
        rows: list[dict[str, str]],
        parent=None,
        init_bundle_enabled: bool = False,
        init_bundle_col: str = "",
        init_naming_pattern: str = DEFAULT_NAMING_PATTERN,
        init_zip_package: bool = False,
    ) -> None:
        super().__init__(parent)
        self.template_name = template_name or "Result"
        self.headers = headers
        self.rows = rows
        self.init_bundle_enabled = init_bundle_enabled
        self.init_bundle_col = init_bundle_col
        self.init_naming_pattern = init_naming_pattern or DEFAULT_NAMING_PATTERN
        self.init_zip_package = init_zip_package

        self.selected_dir: str = os.path.join(os.path.expanduser("~"), "Desktop")
        self.unique_column: str = ""
        self.name_column: str = ""

        self.setWindowTitle("Result Generation Setup")
        self.resize(620, 680)
        self.setMinimumSize(520, 560)
        self.setModal(True)
        self._build_ui()
        self._update_preview()

    @property
    def bundle_enabled(self) -> bool:
        return self._bundle_cb.isChecked()

    @property
    def bundle_column(self) -> str:
        return self._bundle_combo.currentText()

    @property
    def naming_pattern(self) -> str:
        return self._pattern_edit.text().strip() if hasattr(self, "_pattern_edit") else self.init_naming_pattern

    @property
    def zip_package(self) -> bool:
        return self._zip_cb.isChecked() if hasattr(self, "_zip_cb") else False

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)

        # Title
        title = QLabel("⚙️ Result Generation Setup")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #1a1a2e;")
        layout.addWidget(title)

        # Output Folder Selection
        f_lbl = QLabel("Output Destination Folder:")
        f_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #374151;")
        layout.addWidget(f_lbl)

        folder_row = QHBoxLayout()
        folder_row.setSpacing(8)

        self._dir_label = QLabel(self.selected_dir)
        self._dir_label.setStyleSheet("""
            QLabel {
                border: 1px solid #d1d5db; border-radius: 4px;
                padding: 6px 10px; font-size: 11px; background: #f9fafb; color: #111827;
            }
        """)
        folder_row.addWidget(self._dir_label, stretch=1)

        browse_btn = QPushButton("📁 Browse...")
        browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_btn.setStyleSheet("""
            QPushButton {
                background: #ffffff; color: #374151; border: 1px solid #d1d5db;
                border-radius: 4px; padding: 6px 12px; font-size: 12px; font-weight: 600;
            }
            QPushButton:hover { background: #f3f4f6; color: #111827; }
        """)
        browse_btn.clicked.connect(self._on_browse)
        folder_row.addWidget(browse_btn)
        layout.addLayout(folder_row)

        # Auto subfolder option
        self._subfolder_cb = QCheckBox("Create timestamped subfolder (e.g. Template_2026-08-31_2215)")
        self._subfolder_cb.setChecked(True)
        self._subfolder_cb.setStyleSheet("font-size: 11px; color: #4b5563; margin-bottom: 2px;")
        self._subfolder_cb.toggled.connect(self._update_preview)
        layout.addWidget(self._subfolder_cb)

        # Mapping Columns & Pattern
        cols_box = QGroupBox("Filename Formatting & Dynamic Pattern")
        cols_box.setStyleSheet("""
            QGroupBox {
                font-size: 12px; font-weight: 600; color: #374151;
                border: 1px solid #e5e7eb; border-radius: 6px;
                margin-top: 4px; padding: 8px 10px;
            }
        """)
        c_layout = QVBoxLayout(cols_box)
        c_layout.setSpacing(6)

        # File Naming Pattern Row
        pat_row = QHBoxLayout()
        pat_lbl = QLabel("File Naming Pattern:")
        pat_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #374151;")
        pat_row.addWidget(pat_lbl)

        self._pattern_edit = QLineEdit(self.init_naming_pattern)
        self._pattern_edit.setStyleSheet("""
            QLineEdit {
                border: 1px solid #d1d5db; border-radius: 4px;
                padding: 4px 8px; font-size: 12px; font-family: Consolas, monospace;
                background: white; color: #111827;
            }
            QLineEdit:focus { border-color: #3b82f6; }
        """)
        self._pattern_edit.textChanged.connect(self._update_preview)
        pat_row.addWidget(self._pattern_edit, stretch=1)
        c_layout.addLayout(pat_row)

        # Unique Col
        u_row = QHBoxLayout()
        u_lbl = QLabel("Unique Identifier Column:")
        u_lbl.setStyleSheet("font-size: 12px; color: #374151;")
        u_row.addWidget(u_lbl)
        self._unique_combo = QComboBox()
        self._unique_combo.setStyleSheet("color: #000000; background: white; padding: 4px;")
        for h in self.headers:
            self._unique_combo.addItem(h)
        for cand in ["Enrollment", "Roll", "ID", "Roll No", "Student_ID"]:
            idx = self._unique_combo.findText(cand, Qt.MatchFlag.MatchContains)
            if idx >= 0:
                self._unique_combo.setCurrentIndex(idx)
                break
        self._unique_combo.currentTextChanged.connect(self._update_preview)
        u_row.addWidget(self._unique_combo, stretch=1)
        c_layout.addLayout(u_row)

        # Name Col
        n_row = QHBoxLayout()
        n_lbl = QLabel("Student Name Column:")
        n_lbl.setStyleSheet("font-size: 12px; color: #374151;")
        n_row.addWidget(n_lbl)
        self._name_combo = QComboBox()
        self._name_combo.setStyleSheet("color: #000000; background: white; padding: 4px;")
        for h in self.headers:
            self._name_combo.addItem(h)
        for cand in ["Name", "Student Name", "Student_Name"]:
            idx = self._name_combo.findText(cand, Qt.MatchFlag.MatchContains)
            if idx >= 0:
                self._name_combo.setCurrentIndex(idx)
                break
        self._name_combo.currentTextChanged.connect(self._update_preview)
        n_row.addWidget(self._name_combo, stretch=1)
        c_layout.addLayout(n_row)

        layout.addWidget(cols_box)

        # Packaging & Print Bundling Options Box
        bundle_box = QGroupBox("Packaging & Print Bundling Options")
        bundle_box.setStyleSheet("""
            QGroupBox {
                font-size: 12px; font-weight: 600; color: #374151;
                border: 1px solid #e5e7eb; border-radius: 6px;
                margin-top: 4px; padding: 8px 10px;
            }
        """)
        b_layout = QVBoxLayout(bundle_box)
        b_layout.setSpacing(8)

        # Print Bundling Row
        b_row = QHBoxLayout()
        b_row.setSpacing(8)

        self._bundle_cb = QCheckBox("Generate Class-Wise Print Bundles")
        self._bundle_cb.setChecked(self.init_bundle_enabled)
        self._bundle_cb.setStyleSheet("font-size: 11px; color: #1d4ed8; font-weight: 600;")
        self._bundle_cb.toggled.connect(self._on_bundle_toggled)

        self._bundle_col_lbl = QLabel("Grouping Column:")
        self._bundle_col_lbl.setStyleSheet("font-size: 11px; color: #374151;")

        self._bundle_combo = QComboBox()
        self._bundle_combo.setStyleSheet("color: #000000; background: white; padding: 4px;")
        for h in self.headers:
            self._bundle_combo.addItem(h)

        if self.init_bundle_col:
            idx = self._bundle_combo.findText(self.init_bundle_col)
            if idx >= 0:
                self._bundle_combo.setCurrentIndex(idx)
        else:
            for cand in ["Class", "Standard", "Sec", "Section", "Grade", "Group", "Branch"]:
                idx = self._bundle_combo.findText(cand, Qt.MatchFlag.MatchContains)
                if idx >= 0:
                    self._bundle_combo.setCurrentIndex(idx)
                    break

        b_row.addWidget(self._bundle_cb)
        b_row.addSpacing(10)
        b_row.addWidget(self._bundle_col_lbl)
        b_row.addWidget(self._bundle_combo, stretch=1)

        self._bundle_col_lbl.setVisible(self.init_bundle_enabled)
        self._bundle_combo.setVisible(self.init_bundle_enabled)

        b_layout.addLayout(b_row)

        # ZIP Package Row
        self._zip_cb = QCheckBox("Package all output results into a single ZIP archive (.zip)")
        self._zip_cb.setChecked(self.init_zip_package)
        self._zip_cb.setStyleSheet("font-size: 11px; color: #4f46e5; font-weight: 600;")
        b_layout.addWidget(self._zip_cb)

        layout.addWidget(bundle_box)

        # Filename Preview Group
        prev_box = QGroupBox("Generated Filename Preview")
        prev_box.setStyleSheet("""
            QGroupBox {
                font-size: 12px; font-weight: 600; color: #374151;
                border: 1px solid #e5e7eb; border-radius: 6px;
                margin-top: 6px; padding: 10px;
            }
        """)
        p_layout = QVBoxLayout(prev_box)
        self._preview_label = QLabel()
        self._preview_label.setStyleSheet("font-family: Consolas, monospace; font-size: 11px; color: #1f2937;")
        p_layout.addWidget(self._preview_label)
        layout.addWidget(prev_box, stretch=1)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #ffffff; color: #374151; border: 1px solid #d1d5db;
                border-radius: 5px; padding: 7px 16px; font-size: 12px; font-weight: 500;
            }
            QPushButton:hover { background: #f3f4f6; color: #111827; }
        """)
        cancel_btn.clicked.connect(self.reject)

        start_btn = QPushButton("🚀  Start Generation")
        start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        start_btn.setStyleSheet("""
            QPushButton {
                background: #10b981; color: #ffffff; border: none;
                border-radius: 5px; padding: 7px 20px; font-size: 13px; font-weight: 700;
            }
            QPushButton:hover { background: #059669; color: #ffffff; }
        """)
        start_btn.clicked.connect(self._on_start)

        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(start_btn)
        layout.addLayout(btn_row)

    def _on_bundle_toggled(self, checked: bool) -> None:
        self._bundle_col_lbl.setVisible(checked)
        self._bundle_combo.setVisible(checked)

    def _on_browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Output Directory", self.selected_dir)
        if folder:
            self.selected_dir = folder
            self._dir_label.setText(folder)
            self._update_preview()

    def get_effective_output_dir(self) -> str:
        base = self.selected_dir
        if self._subfolder_cb.isChecked():
            ts = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
            safe_tmpl = "".join(c for c in self.template_name if c.isalnum() or c in ("_", "-")).strip() or "Result"
            return os.path.join(base, f"{safe_tmpl}_{ts}")
        return base

    def _update_preview(self) -> None:
        u_col = self._unique_combo.currentText()
        n_col = self._name_combo.currentText()
        pattern = self._pattern_edit.text().strip() if hasattr(self, "_pattern_edit") else ""
        eff_dir = self.get_effective_output_dir()

        previews = preview_filenames(eff_dir, self.rows, u_col, n_col, ".PDF", pattern=pattern)
        if not previews:
            self._preview_label.setText("No records available in dataset.")
            return

        lines = [f"Output Folder: {eff_dir}\n"]
        for row_num, fname in previews:
            lines.append(f"Row {row_num:>3}:  {fname}")
        if len(self.rows) > 5 and len(previews) == 5:
            lines.insert(4, "       ... [remaining records] ...")

        self._preview_label.setText("\n".join(lines))

    def _on_start(self) -> None:
        eff_dir = self.get_effective_output_dir()
        est_bytes = len(self.rows) * 500 * 1024  # 500 KB per record estimate
        ok, err = check_pre_generation(eff_dir, est_bytes)
        if not ok:
            QMessageBox.critical(self, "Pre-Generation Check Failed", err)
            return

        self.unique_column = self._unique_combo.currentText()
        self.name_column = self._name_combo.currentText()
        self.selected_dir = eff_dir
        self.accept()


# ═════════════════════════════════════════════════════════════════════════════
# 2. ACTIVE GENERATION PROGRESS DASHBOARD
# ═════════════════════════════════════════════════════════════════════════════

class GenerationProgressDialog(QDialog):
    """Active generation dashboard with progress percentage, pause/retry handling, and cancellation."""

    def __init__(self, worker: GeneratorWorker, total_records: int, parent=None) -> None:
        super().__init__(parent)
        self.worker = worker
        self.total_records = total_records

        self.generated_count = 0
        self.skipped_count = 0
        self.failed_count = 0
        self.output_directory = ""
        self.created_bundles: list[str] = []
        self.created_zip_path: str = ""
        self.report_path: str = ""
        self.elapsed_seconds: float = 0.0
        self.failed_records: list[dict[str, Any]] = []

        self.setWindowTitle("Generating Results...")
        self.resize(540, 320)
        self.setMinimumSize(460, 280)
        self.setModal(True)
        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        self._status_title = QLabel("Generating Result Papers...")
        self._status_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #1a1a2e;")
        layout.addWidget(self._status_title)

        # Progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #d1d5db; border-radius: 6px;
                text-align: center; font-weight: 600; font-size: 12px;
                height: 24px; background: #f3f4f6; color: #111827;
            }
            QProgressBar::chunk {
                background-color: #10b981; border-radius: 5px;
            }
        """)
        layout.addWidget(self._progress_bar)

        # Statistics row
        self._stats_lbl = QLabel(f"Record: 0 / {self.total_records}  |  Completed: 0  |  Remaining: {self.total_records}")
        self._stats_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #374151;")
        layout.addWidget(self._stats_lbl)

        # Current file label
        self._current_file_lbl = QLabel("Current File: Preparing...")
        self._current_file_lbl.setStyleSheet("font-size: 11px; color: #6b7280; font-family: Consolas, monospace;")
        layout.addWidget(self._current_file_lbl)

        layout.addStretch()

        # Action button
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._cancel_btn = QPushButton("Cancel Generation")
        self._cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel_btn.setStyleSheet("""
            QPushButton {
                background: #fee2e2; color: #b91c1c; border: 1px solid #fca5a5;
                border-radius: 5px; padding: 7px 18px; font-weight: 600; font-size: 12px;
            }
            QPushButton:hover { background: #fecaca; }
        """)
        self._cancel_btn.clicked.connect(self._on_cancel_clicked)
        btn_row.addWidget(self._cancel_btn)
        layout.addLayout(btn_row)

    def _connect_signals(self) -> None:
        self.worker.progress.connect(self._on_progress)
        self.worker.log_message.connect(self._on_log_message)
        self.worker.error_occurred.connect(self._on_error)
        self.worker.generation_finished.connect(self._on_finished)
        self.worker.generation_cancelled.connect(self._on_cancelled)

    def _on_progress(self, current: int, total: int, pct: int, filename: str, status: str) -> None:
        self._progress_bar.setValue(pct)
        completed = int((pct / 100) * total) if total > 0 else current
        remaining = max(0, total - current)
        self._stats_lbl.setText(f"Record: {current} / {total}  |  Completed: {completed}  |  Remaining: {remaining}")
        self._current_file_lbl.setText(f"Current File: {filename}")
        self._status_title.setText(status)

    def _on_log_message(self, message: str) -> None:
        """Display worker diagnostics received through a queued Qt signal."""
        self._current_file_lbl.setText(f"Status: {message}")

    def _on_error(self, row_num: int, col_name: str, row_dict: dict, retries_left: int) -> None:
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setWindowTitle("Record Error - Action Required")
        msg_box.setText(
            f"<b>Missing or Invalid Data in Row {row_num}</b><br><br>"
            f"Field: <b>{col_name}</b> is empty or failed to render.<br>"
            f"Retries remaining for this record: <b>{retries_left}</b>"
        )
        retry_btn = msg_box.addButton("🔄 Retry", QMessageBox.ButtonRole.ActionRole)
        skip_btn = msg_box.addButton("⏭ Skip Record", QMessageBox.ButtonRole.ActionRole)
        cancel_btn = msg_box.addButton("⛔ Cancel Generation", QMessageBox.ButtonRole.RejectRole)

        if retries_left <= 0:
            retry_btn.setEnabled(False)

        msg_box.exec()
        clicked = msg_box.clickedButton()
        if clicked == retry_btn:
            self.worker.resolve_error(GeneratorWorker.ACTION_RETRY)
        elif clicked == cancel_btn:
            self.worker.resolve_error(GeneratorWorker.ACTION_CANCEL)
        else:
            self.worker.resolve_error(GeneratorWorker.ACTION_SKIP)

    def _on_cancel_clicked(self) -> None:
        reply = QMessageBox.question(
            self,
            "Confirm Cancellation",
            "Are you sure you want to cancel generation?\n"
            "Any result files generated during this session will be removed.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._cancel_btn.setEnabled(False)
            self._status_title.setText("Cancelling & Cleaning Up...")
            self.worker.cancel()

    def _on_cancelled(self) -> None:
        QMessageBox.information(
            self,
            "Generation Cancelled",
            "Generation cancelled.",
        )
        self.reject()

    def _on_finished(self, gen: int, skip: int, fail: int, out_dir: str, failed_records: list) -> None:
        self.generated_count = gen
        self.skipped_count = skip
        self.failed_count = fail
        self.output_directory = out_dir
        self.failed_records = failed_records
        self.created_bundles = list(getattr(self.worker, "created_bundles", []))
        self.created_zip_path = str(getattr(self.worker, "created_zip_path", ""))
        self.report_path = str(getattr(self.worker, "report_path", ""))
        self.elapsed_seconds = float(getattr(self.worker, "elapsed_seconds", 0.0))
        self.accept()


# ═════════════════════════════════════════════════════════════════════════════
# 3. COMPLETION SUMMARY DIALOG
# ═════════════════════════════════════════════════════════════════════════════

class GenerationCompletedDialog(QDialog):
    """Post-generation summary screen with Open Folder, View Errors, Audit Report, and Skip Regeneration."""

    def __init__(
        self,
        generated: int,
        skipped: int,
        failed: int,
        output_dir: str,
        failed_records: list[dict[str, Any]],
        template_state: dict[str, Any],
        parent=None,
        created_bundles: list[str] | None = None,
        created_zip: str = "",
        report_path: str = "",
        elapsed_seconds: float = 0.0,
    ) -> None:
        super().__init__(parent)
        self.generated = generated
        self.skipped = skipped
        self.failed = failed
        self.output_dir = output_dir
        self.failed_records = failed_records
        self.template_state = template_state
        self.created_bundles = created_bundles or []
        self.created_zip = created_zip
        self.report_path = report_path or os.path.join(output_dir, "generation_report.txt")
        self.elapsed_seconds = elapsed_seconds

        self.setWindowTitle("Generation Summary")
        self.resize(560, 480)
        self.setMinimumSize(480, 400)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        if self.failed == 0:
            title = QLabel("✅  Generation Completed Successfully")
            title.setStyleSheet("font-size: 16px; font-weight: 700; color: #065f46;")
        else:
            title = QLabel("⚠️  Generation Completed with Errors")
            title.setStyleSheet("font-size: 16px; font-weight: 700; color: #b45309;")
        layout.addWidget(title)

        # Stats Card
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 6px;
                padding: 12px;
            }
        """)
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(6)
        _lbl_style = "font-size: 13px; color: #111827;"
        c_layout.addWidget(_make_lbl(f"• <b>Successfully Generated:</b> {self.generated} results", _lbl_style))
        if self.elapsed_seconds > 0:
            c_layout.addWidget(_make_lbl(
                f"• <b>Execution Time:</b> {self.elapsed_seconds:.2f} seconds",
                _lbl_style,
            ))
        if self.created_bundles:
            c_layout.addWidget(_make_lbl(
                f"• <b>Class Print Bundles:</b> {len(self.created_bundles)} master print bundles created in <i>Print_Bundles</i> folder.",
                _lbl_style,
            ))
            c_layout.addWidget(_make_lbl(
                f"✨ <i>Individual PDFs generated, plus {len(self.created_bundles)} class print bundles created.</i>",
                "font-size: 12px; color: #059669; font-weight: 600; padding: 2px 0;",
            ))
        if self.created_zip:
            c_layout.addWidget(_make_lbl(
                f"• <b>ZIP Package:</b> <span style='color: #4f46e5; font-weight: 600;'>{os.path.basename(self.created_zip)}</span>",
                _lbl_style,
            ))
            c_layout.addWidget(_make_lbl(
                f"📦 <i>Output results compressed into ZIP archive: {self.created_zip}</i>",
                "font-size: 12px; color: #4f46e5; font-weight: 600; padding: 2px 0;",
            ))
        c_layout.addWidget(_make_lbl(f"• <b>Skipped Records:</b> {self.skipped}", _lbl_style))
        c_layout.addWidget(_make_lbl(f"• <b>Failed Records:</b> {self.failed}", _lbl_style))
        c_layout.addWidget(_make_lbl(
            f"• <b>Audit Report:</b> <span style='color: #059669; font-weight: 600;'>generation_report.txt</span> (Saved in destination)",
            _lbl_style
        ))
        c_layout.addWidget(_make_lbl(
            f"• <b>Destination Folder:</b><br><span style='color: #4b5563;'>{self.output_dir}</span>",
            _lbl_style
        ))
        layout.addWidget(card)

        layout.addStretch()

        # Action Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        open_btn = QPushButton("📁 Open Folder")
        open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_btn.setStyleSheet("""
            QPushButton {
                background: #4f7ef8; color: white; border: none;
                border-radius: 5px; padding: 8px 14px; font-weight: 600; font-size: 12px;
            }
            QPushButton:hover { background: #3b6ef0; }
        """)
        open_btn.clicked.connect(self._on_open_folder)
        btn_row.addWidget(open_btn)

        report_btn = QPushButton("📄 View Report")
        report_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        report_btn.setStyleSheet("""
            QPushButton {
                background: #f3f4f6; color: #374151; border: 1px solid #d1d5db;
                border-radius: 5px; padding: 8px 14px; font-weight: 600; font-size: 12px;
            }
            QPushButton:hover { background: #e5e7eb; color: #111827; }
        """)
        report_btn.clicked.connect(self._on_view_report)
        btn_row.addWidget(report_btn)

        if self.failed > 0:
            view_failed_btn = QPushButton("🔍 View Failed Records")
            view_failed_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            view_failed_btn.setStyleSheet("""
                QPushButton {
                    background: #fee2e2; color: #b91c1c; border: 1px solid #fca5a5;
                    border-radius: 5px; padding: 8px 14px; font-weight: 600; font-size: 12px;
                }
                QPushButton:hover { background: #fecaca; }
            """)
            view_failed_btn.clicked.connect(self._on_view_failed)
            btn_row.addWidget(view_failed_btn)

        continue_btn = QPushButton("Continue")
        continue_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        continue_btn.setStyleSheet("""
            QPushButton {
                background: #ffffff; color: #374151; border: 1px solid #d1d5db;
                border-radius: 5px; padding: 8px 18px; font-weight: 600; font-size: 12px;
            }
            QPushButton:hover { background: #f3f4f6; color: #111827; }
        """)
        continue_btn.clicked.connect(self.accept)
        btn_row.addWidget(continue_btn)

        layout.addLayout(btn_row)

    def _on_open_folder(self) -> None:
        if os.path.exists(self.output_dir):
            os.startfile(self.output_dir)

    def _on_view_report(self) -> None:
        rep_p = self.report_path or os.path.join(self.output_dir, "generation_report.txt")
        if os.path.exists(rep_p):
            os.startfile(rep_p)
        else:
            QMessageBox.information(self, "Audit Report", f"Report file not found at:\n{rep_p}")

    def _on_view_failed(self) -> None:
        dlg = FailedRecordsDialog(self.failed_records, self.template_state, self.output_dir, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            # Update counts if items were successfully retried
            self.generated += dlg.resolved_count
            self.failed -= dlg.resolved_count
            if self.failed == 0:
                self.setWindowTitle("Generation Completed Successfully")


# ═════════════════════════════════════════════════════════════════════════════
# 4. FAILED RECORDS DIALOG
# ═════════════════════════════════════════════════════════════════════════════

class FailedRecordsDialog(QDialog):
    """View and individually retry failed student records."""

    def __init__(
        self,
        failed_records: list[dict[str, Any]],
        template_state: dict[str, Any],
        output_dir: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.failed_records = list(failed_records)
        self.template_state = template_state
        self.output_dir = output_dir
        self.resolved_count = 0

        self.setWindowTitle("Failed Records Management")
        self.resize(680, 420)
        self.setMinimumSize(560, 360)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        title = QLabel("Failed Records")
        title.setStyleSheet("font-size: 15px; font-weight: 700; color: #b91c1c;")
        layout.addWidget(title)

        self._table = QTableWidget(len(self.failed_records), 4)
        self._table.setHorizontalHeaderLabels(["Student Name", "Unique ID", "Error Reason", "Action"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(3, 90)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setStyleSheet("color: #000000; background: white;")

        self._populate_table()
        layout.addWidget(self._table)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: #ffffff; color: #374151; border: 1px solid #d1d5db;
                border-radius: 4px; padding: 6px 14px; font-weight: 500;
            }
            QPushButton:hover { background: #f3f4f6; color: #111827; }
        """)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _populate_table(self) -> None:
        for row_idx, rec in enumerate(self.failed_records):
            s_name = QTableWidgetItem(rec.get("student_name", ""))
            u_val = QTableWidgetItem(rec.get("unique_val", ""))
            err = QTableWidgetItem(rec.get("error", ""))

            s_name.setFlags(s_name.flags() & ~Qt.ItemFlag.ItemIsEditable)
            u_val.setFlags(u_val.flags() & ~Qt.ItemFlag.ItemIsEditable)
            err.setFlags(err.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self._table.setItem(row_idx, 0, s_name)
            self._table.setItem(row_idx, 1, u_val)
            self._table.setItem(row_idx, 2, err)

            retry_btn = QPushButton("🔄 Retry")
            retry_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            retry_btn.setStyleSheet("""
                QPushButton {
                    background: #10b981; color: white; border: none;
                    border-radius: 3px; padding: 4px 8px; font-weight: 600; font-size: 11px;
                }
                QPushButton:hover { background: #059669; }
            """)
            retry_btn.clicked.connect(lambda _c, idx=row_idx: self._retry_record(idx))
            self._table.setCellWidget(row_idx, 3, retry_btn)

    def _retry_record(self, idx: int) -> None:
        rec = self.failed_records[idx]
        row_data = rec.get("row_data", {})
        u_val = rec.get("unique_val", "Student")
        name_val = rec.get("student_name", "")

        out_file = get_unique_result_filename(self.output_dir, u_val, name_val, ".PDF")
        try:
            generate_single_pdf(self.template_state, row_data, out_file)
            self.resolved_count += 1
            self._table.removeRow(idx)
            self.failed_records.pop(idx)
            QMessageBox.information(self, "Success", f"Successfully generated:\n{os.path.basename(out_file)}")
            if not self.failed_records:
                QMessageBox.information(self, "All Errors Resolved", "All failed records have been successfully resolved!")
                self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Retry Failed", f"Record generation failed again:\n{exc}")
