"""
ui/main_window.py
Top-level application window, navigation routing, operation coordination, and lifecycle management.
"""
from __future__ import annotations

import os

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from data_engine.preflight_sanitizer import audit_dataset, auto_sanitize_dataset
from generation.pdf_generator import GeneratorWorker
from generation.printer import print_all_student_records
from ui.dialogs.audit_dialog import AuditPreCheckDialog
from ui.dialogs.generation_dialog import (
    GenerationCompletedDialog,
    GenerationProgressDialog,
    GenerationSetupDialog,
)
from ui.dialogs.print_one_dialog import PrintOneDialog
from ui.views.dashboard_view import DashboardView
from ui.views.settings_view import SettingsView
from ui.views.template_editor_view import TemplateEditorView
from utils.constants import APP_NAME

# ── Colors ─────────────────────────────────────────────────────────────────
SIDEBAR_BG       = "#1a1a2e"
SIDEBAR_HOVER    = "#16213e"
SIDEBAR_ACTIVE   = "#4f7ef8"
SIDEBAR_TEXT     = "#c8cde4"
SIDEBAR_TEXT_ACT = "#ffffff"
CONTENT_BG       = "#f3f4f8"


class MainWindow(QMainWindow):
    """Top-level application window coordinating all views and background jobs."""

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(1080, 720)
        self.resize(1240, 780)

        self._nav_buttons: list[QPushButton] = []
        self._build_ui()
        self._navigate(0)  # Start on Dashboard

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_sidebar())
        root.addWidget(self._build_content_area())

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(230)
        sidebar.setStyleSheet(f"QWidget#Sidebar {{ background-color: {SIDEBAR_BG}; }}")

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Logo / Title
        logo_area = QWidget()
        logo_area.setFixedHeight(84)
        logo_area.setStyleSheet(f"background-color: {SIDEBAR_BG};")
        logo_layout = QVBoxLayout(logo_area)
        logo_layout.setContentsMargins(20, 0, 20, 0)
        logo_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        app_label = QLabel("📋  Teacher Results")
        app_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        app_label.setStyleSheet("""
            color: #ffffff;
            font-size: 15px;
            font-weight: 700;
            letter-spacing: 0.5px;
        """)
        sub_label = QLabel("Offline Result Engine")
        sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub_label.setStyleSheet("color: #94a3b8; font-size: 11px;")

        logo_layout.addWidget(app_label)
        logo_layout.addWidget(sub_label)
        layout.addWidget(logo_area)

        # Divider
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #2a2d4a;")
        layout.addWidget(sep)

        layout.addSpacing(16)

        # Nav Buttons
        nav_items = [
            ("📊", "Dashboard"),
            ("🎨", "Template Editor"),
            ("⚙️", "Settings"),
        ]

        for i, (icon, text) in enumerate(nav_items):
            btn = self._make_nav_button(icon, text, i)
            self._nav_buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch()

        # Footer
        footer = QWidget()
        footer.setFixedHeight(50)
        foot_layout = QVBoxLayout(footer)
        foot_layout.setContentsMargins(20, 0, 20, 10)
        ver = QLabel("v1.0.0 • Offline Release")
        ver.setStyleSheet("color: #8b92b8; font-size: 11px;")
        foot_layout.addWidget(ver)
        layout.addWidget(footer)

        return sidebar

    def _make_nav_button(self, icon: str, text: str, index: int) -> QPushButton:
        btn = QPushButton(f"  {icon}   {text}")
        btn.setFixedHeight(46)
        btn.setCheckable(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {SIDEBAR_TEXT};
                border: none;
                border-left: 4px solid transparent;
                padding-left: 20px;
                text-align: left;
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {SIDEBAR_HOVER};
                color: #ffffff;
            }}
            QPushButton:checked {{
                background-color: {SIDEBAR_HOVER};
                color: {SIDEBAR_TEXT_ACT};
                border-left: 4px solid {SIDEBAR_ACTIVE};
                font-weight: 600;
            }}
        """)
        btn.clicked.connect(lambda: self._navigate(index))
        return btn

    def _build_content_area(self) -> QWidget:
        self._stack = QStackedWidget()
        self._stack.setStyleSheet(f"background-color: {CONTENT_BG};")

        self._dashboard_view = DashboardView(self)
        self._template_editor_view = TemplateEditorView(self)
        self._settings_view = SettingsView(self)

        self._stack.addWidget(self._dashboard_view)
        self._stack.addWidget(self._template_editor_view)
        self._stack.addWidget(self._settings_view)

        # Wire cross-view events
        self._dashboard_view.excel_loaded.connect(self._on_excel_loaded)
        self._dashboard_view.dataset_cleared.connect(self._on_dataset_cleared)
        self._dashboard_view.print_one_requested.connect(self._on_print_one)
        self._dashboard_view.print_all_requested.connect(self._on_print_all)
        self._dashboard_view.generate_requested.connect(self._on_generate_all)

        return self._stack

    # ── Cross-View Coordination ───────────────────────────────────────────────

    def _on_excel_loaded(self, headers: list[str]) -> None:
        self._template_editor_view.set_excel_columns(headers)
        self._template_editor_view.set_locked_state(True, "Template locked while active dataset is loaded")

    def _on_dataset_cleared(self) -> None:
        self._template_editor_view.set_locked_state(False)

    def _on_print_one(self) -> None:
        template_state = self._template_editor_view.get_state()
        if not template_state.get("fields"):
            QMessageBox.warning(self, "No Template Fields", "Please place at least one field in the Template Editor before printing.")
            return

        headers, rows = self._dashboard_view.get_dataset()
        if not rows:
            QMessageBox.warning(self, "No Data", "Please load a student dataset first.")
            return

        dlg = PrintOneDialog(template_state, headers, rows, self)
        dlg.exec()

    def _on_print_all(self) -> None:
        template_state = self._template_editor_view.get_state()
        if not template_state.get("fields"):
            QMessageBox.warning(self, "No Template Fields", "Please place at least one field in the Template Editor before printing.")
            return

        headers, rows = self._dashboard_view.get_dataset()
        if not rows:
            QMessageBox.warning(self, "No Data", "Please load a student dataset first.")
            return

        reply = QMessageBox.question(
            self,
            "Confirm Batch Print",
            f"Are you sure you want to send all {len(rows)} student result papers to the printer?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            printed, failed = print_all_student_records(template_state, rows, self)
            QMessageBox.information(
                self,
                "Printing Finished",
                f"Batch Print Results:\n• Successfully Spooled: {printed}\n• Failed: {failed}",
            )

    def _on_generate_all(self) -> None:
        template_state = self._template_editor_view.get_state()
        if not template_state.get("fields"):
            res = QMessageBox.question(
                self,
                "No Fields Configured",
                "Your template currently has no text fields placed.\n\n"
                "Would you like to switch to the Template Editor to configure fields first?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if res == QMessageBox.StandardButton.Yes:
                self._navigate(1)
            return

        bg_path = template_state.get("background", {}).get("path", "")
        if not bg_path or not os.path.exists(bg_path):
            QMessageBox.warning(
                self,
                "Missing Background",
                "The template has no background image/PDF or the file path is invalid.\n\n"
                "Please configure a valid background in the Template Editor.",
            )
            self._navigate(1)
            return

        headers, rows = self._dashboard_view.get_dataset()
        if not rows:
            QMessageBox.warning(self, "No Data", "Please load an Excel dataset first.")
            return

        dash_bundle_enabled, dash_bundle_col = self._dashboard_view.get_bundle_options()

        # 1. Setup Dialog
        setup_dlg = GenerationSetupDialog(
            template_state.get("template_name", "Result"),
            headers,
            rows,
            self,
            init_bundle_enabled=dash_bundle_enabled,
            init_bundle_col=dash_bundle_col,
        )
        if setup_dlg.exec() != GenerationSetupDialog.DialogCode.Accepted:
            return

        out_dir = setup_dlg.selected_dir
        u_col = setup_dlg.unique_column
        n_col = setup_dlg.name_column
        bundle_enabled = setup_dlg.bundle_enabled
        bundle_col = setup_dlg.bundle_column

        # 2. Pre-Flight Data Sanitizer & Audit Check
        mapped_columns: list[str] = []
        for f in template_state.get("fields", []):
            col = f.get("mapped_column") or f.get("label", "")
            if col and col not in mapped_columns:
                mapped_columns.append(col)
        for c in template_state.get("charts", []):
            for col in c.get("chart_columns", []):
                if col and col not in mapped_columns:
                    mapped_columns.append(col)
        for b in template_state.get("badges", []):
            col = b.get("condition_column", "")
            if col and col not in mapped_columns:
                mapped_columns.append(col)
        if n_col and n_col not in mapped_columns:
            mapped_columns.append(n_col)

        cleaned_rows, audit_report = audit_dataset(rows, mapped_columns, unique_col=u_col)
        rows_to_generate = cleaned_rows

        if audit_report.has_flaws:
            audit_dlg = AuditPreCheckDialog(audit_report, self)
            if audit_dlg.exec() != AuditPreCheckDialog.DialogCode.Accepted:
                return  # Cancel generation

            # Auto-sanitize dataset
            rows_to_generate = auto_sanitize_dataset(
                rows,
                mapped_columns,
                unique_col=u_col,
            )

        # 3. Worker Thread & Live Dashboard
        worker = GeneratorWorker(
            template_state=template_state,
            rows=rows_to_generate,
            output_dir=out_dir,
            unique_col=u_col,
            name_col=n_col,
            parent=self,
            bundle_enabled=bundle_enabled,
            bundle_col=bundle_col,
        )

        prog_dlg = GenerationProgressDialog(worker, len(rows_to_generate), self)
        worker.start()

        if prog_dlg.exec() == GenerationProgressDialog.DialogCode.Accepted:
            # 3. Completion Summary Dialog
            comp_dlg = GenerationCompletedDialog(
                generated=prog_dlg.generated_count,
                skipped=prog_dlg.skipped_count,
                failed=prog_dlg.failed_count,
                output_dir=prog_dlg.output_directory,
                failed_records=prog_dlg.failed_records,
                template_state=template_state,
                parent=self,
                created_bundles=prog_dlg.created_bundles,
            )
            comp_dlg.exec()

    # ── Navigation & Close Event ───────────────────────────────────────────────

    def _navigate(self, index: int) -> None:
        self._stack.setCurrentIndex(index)
        for i, btn in enumerate(self._nav_buttons):
            btn.setChecked(i == index)

    def closeEvent(self, event) -> None:
        if not hasattr(self, "_template_editor_view") or not self._template_editor_view.has_unsaved_changes():
            event.accept()
            return

        msg = QMessageBox(self)
        msg.setWindowTitle("Unsaved Changes")
        msg.setText("You have unsaved changes in your template.")
        msg.setInformativeText("Do you want to save before closing?")
        msg.setIcon(QMessageBox.Icon.Warning)

        save_btn    = msg.addButton("Save",       QMessageBox.ButtonRole.AcceptRole)
        no_save_btn = msg.addButton("Don't Save", QMessageBox.ButtonRole.DestructiveRole)
        cancel_btn  = msg.addButton("Cancel",     QMessageBox.ButtonRole.RejectRole)

        msg.setDefaultButton(save_btn)
        msg.exec()

        clicked = msg.clickedButton()
        if clicked == save_btn:
            saved = self._template_editor_view._on_save_template()
            if saved:
                event.accept()
            else:
                event.ignore()
        elif clicked == no_save_btn:
            event.accept()
        else:
            event.ignore()
