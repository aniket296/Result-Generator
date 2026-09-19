"""
ui/dialogs/preset_dialog.py
Template Presets Modal Dialog for Phase 4.3.
Allows teachers and administrators to browse, preview, and load
production-ready templates (Standard School Marksheet, Certificate of Merit, Student ID Card).
"""
from __future__ import annotations

import os
from typing import Any
import pymupdf
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QImage, QFont
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QWidget,
    QFrame,
    QScrollArea,
    QMessageBox,
)

from utils.preset_manager import (
    ensure_presets_built,
    load_preset_template_state,
)


class TemplatePresetDialog(QDialog):
    """Interactive gallery modal for browsing and loading production template presets."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("🎨 Built-in Production Template Presets")
        self.resize(880, 600)
        self.setMinimumSize(780, 520)
        self.setModal(True)

        self._presets = ensure_presets_built()
        self._selected_state: dict[str, Any] | None = None
        self._preview_cache: dict[str, QPixmap] = {}

        self._build_ui()
        if self._preset_list.count() > 0:
            self._preset_list.setCurrentRow(0)

    @property
    def selected_preset_state(self) -> dict[str, Any] | None:
        return self._selected_state

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # ── Header ──────────────────────────────────────────────────────────
        header_row = QHBoxLayout()
        header_row.setSpacing(10)

        header_icon = QLabel("🎨")
        header_icon.setStyleSheet("font-size: 26px;")
        header_row.addWidget(header_icon)

        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(2)
        title_lbl = QLabel("Built-In Production Template Library")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: 700; color: #1e1b4b;")
        sub_lbl = QLabel("Choose a pre-configured template with vector background, fields, and tables to jump-start your design.")
        sub_lbl.setStyleSheet("font-size: 12px; color: #64748b;")
        title_vbox.addWidget(title_lbl)
        title_vbox.addWidget(sub_lbl)
        header_row.addLayout(title_vbox, stretch=1)
        layout.addLayout(header_row)

        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet("color: #e2e8f0; margin: 2px 0;")
        layout.addWidget(div)

        # ── Main Content: Split List & Preview ──────────────────────────────
        content_split = QHBoxLayout()
        content_split.setSpacing(16)

        # Left Column: Presets List
        left_box = QVBoxLayout()
        left_box.setSpacing(8)

        list_header = QLabel("AVAILABLE DESIGNS:")
        list_header.setStyleSheet("font-size: 11px; font-weight: 700; color: #475569; letter-spacing: 0.5px;")
        left_box.addWidget(list_header)

        self._preset_list = QListWidget()
        self._preset_list.setStyleSheet("""
            QListWidget {
                background: #f8fafc;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                outline: none;
                padding: 4px;
            }
            QListWidget::item {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                margin: 4px;
                padding: 10px;
            }
            QListWidget::item:hover {
                background: #f1f5f9;
                border-color: #94a3b8;
            }
            QListWidget::item:selected {
                background: #eff6ff;
                border: 1.5px solid #3b82f6;
            }
        """)
        self._preset_list.currentRowChanged.connect(self._on_preset_selected)

        for p in self._presets:
            item = QListWidgetItem(self._preset_list)
            item.setSizeHint(QSize(300, 84))
            item.setData(Qt.ItemDataRole.UserRole, p)

            # Custom item widget
            card = self._build_preset_card_widget(p)
            self._preset_list.setItemWidget(item, card)

        left_box.addWidget(self._preset_list, stretch=1)
        content_split.addLayout(left_box, stretch=4)

        # Right Column: Live Visual Preview & Specs
        right_box = QVBoxLayout()
        right_box.setSpacing(8)

        prev_header = QLabel("TEMPLATE PREVIEW & SPECS:")
        prev_header.setStyleSheet("font-size: 11px; font-weight: 700; color: #475569; letter-spacing: 0.5px;")
        right_box.addWidget(prev_header)

        prev_container = QFrame()
        prev_container.setStyleSheet("""
            QFrame {
                background: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 12px;
            }
        """)
        prev_layout = QVBoxLayout(prev_container)
        prev_layout.setSpacing(10)

        # Scrollable image preview
        self._preview_lbl = QLabel("Loading preview...")
        self._preview_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_lbl.setStyleSheet("background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 4px;")
        self._preview_lbl.setMinimumHeight(240)
        prev_layout.addWidget(self._preview_lbl, stretch=1)

        # Template Details
        self._details_lbl = QLabel()
        self._details_lbl.setWordWrap(True)
        self._details_lbl.setStyleSheet("font-size: 12px; color: #334155; line-height: 1.4;")
        prev_layout.addWidget(self._details_lbl)

        right_box.addWidget(prev_container, stretch=1)
        content_split.addLayout(right_box, stretch=5)

        layout.addLayout(content_split, stretch=1)

        # ── Action Buttons ──────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1;
                border-radius: 5px; padding: 7px 18px; font-size: 12px; font-weight: 600;
            }
            QPushButton:hover { background: #e2e8f0; color: #0f172a; }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        self._load_btn = QPushButton("🚀  Load Preset Template")
        self._load_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._load_btn.setStyleSheet("""
            QPushButton {
                background: #3b82f6; color: #ffffff; border: none;
                border-radius: 5px; padding: 7px 22px; font-size: 13px; font-weight: 700;
            }
            QPushButton:hover { background: #2563eb; }
        """)
        self._load_btn.clicked.connect(self._on_load_clicked)
        btn_row.addWidget(self._load_btn)

        layout.addLayout(btn_row)

    def _build_preset_card_widget(self, p: dict[str, Any]) -> QWidget:
        """Create rich card for item in list widget."""
        w = QWidget()
        vbox = QVBoxLayout(w)
        vbox.setContentsMargins(6, 4, 6, 4)
        vbox.setSpacing(3)

        title_row = QHBoxLayout()
        title_row.setSpacing(6)

        icon_map = {
            "school_marksheet": "🏫",
            "certificate_merit": "📜",
            "student_id_card": "🪪",
        }
        icon_lbl = QLabel(icon_map.get(p["id"], "📄"))
        icon_lbl.setStyleSheet("font-size: 16px;")
        title_row.addWidget(icon_lbl)

        name_lbl = QLabel(p["name"])
        name_lbl.setStyleSheet("font-size: 12px; font-weight: 700; color: #0f172a;")
        title_row.addWidget(name_lbl, stretch=1)
        vbox.addLayout(title_row)

        badge_row = QHBoxLayout()
        badge_row.setSpacing(6)
        cat_badge = QLabel(f" {p['category']} ")
        cat_badge.setStyleSheet("font-size: 10px; background: #e0f2fe; color: #0369a1; border-radius: 3px; font-weight: 600;")
        size_badge = QLabel(f" {p['paper_size']} ")
        size_badge.setStyleSheet("font-size: 10px; background: #f1f5f9; color: #475569; border-radius: 3px;")
        badge_row.addWidget(cat_badge)
        badge_row.addWidget(size_badge)
        badge_row.addStretch()
        vbox.addLayout(badge_row)

        return w

    def _on_preset_selected(self, row: int) -> None:
        if row < 0 or row >= len(self._presets):
            return

        preset = self._presets[row]
        pid = preset["id"]

        # Render preview pixmap
        if pid not in self._preview_cache:
            bg_path = preset["bg_path"]
            if os.path.exists(bg_path):
                try:
                    doc = pymupdf.open(bg_path)
                    page = doc[0]
                    pix = page.get_pixmap(dpi=110)
                    qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
                    qpix = QPixmap.fromImage(qimg)
                    self._preview_cache[pid] = qpix
                    doc.close()
                except Exception:
                    self._preview_cache[pid] = QPixmap()
            else:
                self._preview_cache[pid] = QPixmap()

        qpix = self._preview_cache.get(pid, QPixmap())
        if not qpix.isNull():
            scaled = qpix.scaled(
                360, 240,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._preview_lbl.setPixmap(scaled)
        else:
            self._preview_lbl.setText("No Preview Available")

        # Load state for metadata counts
        state = load_preset_template_state(preset["json_path"])
        f_count = len(state.get("fields", [])) if state else 0
        t_count = len(state.get("tables", [])) if state else 0
        p_count = len(state.get("photos", [])) if state else 0
        q_count = len(state.get("qrs", [])) if state else 0
        b_count = len(state.get("badges", [])) if state else 0

        cols_str = ", ".join(preset["recommended_cols"][:7])
        if len(preset["recommended_cols"]) > 7:
            cols_str += "..."

        details_html = f"""
        <b>Description:</b> {preset['description']}<br><br>
        <b>Dimensions:</b> {preset['dimensions'][0]} × {preset['dimensions'][1]} pt ({preset['paper_size']})<br>
        <b>Pre-Mapped Elements:</b> {f_count} fields, {t_count} table, {p_count} photo, {q_count} QR stamp, {b_count} badge<br>
        <b>Recommended Columns:</b> <span style="color: #0369a1;">{cols_str}</span>
        """
        self._details_lbl.setText(details_html)

    def _on_load_clicked(self) -> None:
        row = self._preset_list.currentRow()
        if row < 0 or row >= len(self._presets):
            QMessageBox.warning(self, "No Selection", "Please select a template preset first.")
            return

        preset = self._presets[row]
        state = load_preset_template_state(preset["json_path"])
        if not state:
            QMessageBox.critical(self, "Load Error", f"Failed to load preset configuration:\n{preset['json_path']}")
            return

        self._selected_state = state
        self.accept()

