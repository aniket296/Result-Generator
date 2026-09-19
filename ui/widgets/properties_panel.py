"""
PropertiesPanel - right-side sidebar for configuring the selected FieldItem, ChartItem, or BadgeItem.

Allows live editing of:
  FieldItem mode:
    - Field Label (Excel variable identifier)
    - Unique Field designation
    - Excel column mapping dropdown
    - Typography (Font Family, Size, Color Picker, Bold, Italic, Underline, Alignment, Multiline)
  ChartItem mode:
    - Chart type (Vertical / Horizontal Bars)
    - Subject column checkboxes (multi-select from Excel headers)
  BadgeItem mode:
    - Badge image file selector
    - Visibility rule: [Column] [Operator] [Threshold Value]
  Shared (all modes):
    - Precise geometry spinboxes (X, Y, Width, Height)
    - Delete button
"""
from __future__ import annotations

import os

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QFileDialog,
    QFontComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from data_engine.header_normalizer import find_matching_header
from ui.widgets.badge_item import BadgeItem
from ui.widgets.chart_item import ChartItem
from ui.widgets.field_item import FieldItem
from ui.widgets.photo_item import PhotoItem
from ui.widgets.qr_item import QRItem
from ui.widgets.table_item import TableItem


class PropertiesPanel(QWidget):
    """Sidebar widget displayed on the right of the Template Editor."""

    # ── Signals (FieldItem) ───────────────────────────────────────────────────
    label_changed       = pyqtSignal(str)
    column_changed      = pyqtSignal(str)
    unique_changed      = pyqtSignal(bool)
    font_family_changed = pyqtSignal(str)
    font_size_changed   = pyqtSignal(int)
    color_changed       = pyqtSignal(str)
    bold_changed        = pyqtSignal(bool)
    italic_changed      = pyqtSignal(bool)
    underline_changed   = pyqtSignal(bool)
    multiline_changed   = pyqtSignal(bool)
    alignment_changed   = pyqtSignal(str)
    v_alignment_changed = pyqtSignal(str)

    # ── Signals (shared geometry) ─────────────────────────────────────────────
    x_changed        = pyqtSignal(float)
    y_changed        = pyqtSignal(float)
    width_changed    = pyqtSignal(float)
    height_changed   = pyqtSignal(float)
    delete_requested = pyqtSignal()

    # ── Signals (ChartItem) ───────────────────────────────────────────────────
    chart_columns_changed = pyqtSignal(list)
    chart_style_changed   = pyqtSignal(str)

    # ── Signals (BadgeItem) ───────────────────────────────────────────────────
    badge_image_changed = pyqtSignal(str)          # absolute image path
    badge_rule_changed  = pyqtSignal(str, str, str) # column, operator, value

    # ── Signals (PhotoItem) ───────────────────────────────────────────────────
    photo_id_column_changed    = pyqtSignal(str)
    photo_border_color_changed = pyqtSignal(str)
    photo_border_width_changed = pyqtSignal(float)
    photo_corner_radius_changed = pyqtSignal(float)

    # ── Signals (QRItem) ─────────────────────────────────────────────────────
    qr_payload_changed     = pyqtSignal(str)
    qr_border_cells_changed = pyqtSignal(int)

    # ── Signals (TableItem) ──────────────────────────────────────────────────
    table_columns_changed     = pyqtSignal(list)
    table_show_max_changed    = pyqtSignal(bool)
    table_show_grade_changed  = pyqtSignal(bool)
    table_max_marks_changed   = pyqtSignal(float)
    table_row_height_changed  = pyqtSignal(float)
    table_font_size_changed   = pyqtSignal(int)
    table_header_bg_changed   = pyqtSignal(str)
    table_header_color_changed = pyqtSignal(str)
    table_alt_row_bg_changed  = pyqtSignal(str)

    _NO_COL = "-- None (use Label) --"
    _AUTO_ID_COL = "-- Auto (Enrollment/Unique) --"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._item: FieldItem | ChartItem | BadgeItem | PhotoItem | QRItem | TableItem | None = None
        self._updating: bool = False
        self._color_hex: str = "#000000"
        self._table_header_bg_hex: str = "#1e3a8a"
        self._table_header_color_hex: str = "#ffffff"
        self._table_alt_row_bg_hex: str = "#f8fafc"
        self._excel_columns: list[str] = []
        self._chart_column_checkboxes: dict[str, QCheckBox] = {}
        self._table_column_checkboxes: dict[str, QCheckBox] = {}

        self.setMinimumWidth(240)
        self.setMaximumWidth(360)
        self.setStyleSheet("background: white;")
        self._build_ui()

    # ── Public API ────────────────────────────────────────────────────────────

    def set_excel_columns(self, columns: list[str]) -> None:
        """Update available Excel columns for field mapping, chart checkboxes, and badge rule combo."""
        self._excel_columns = list(columns)

        # Field: update column combo
        current = self._column_combo.currentText()
        self._column_combo.blockSignals(True)
        self._column_combo.clear()
        self._column_combo.addItem(self._NO_COL)
        for col in self._excel_columns:
            self._column_combo.addItem(col)
        idx = self._column_combo.findText(current)
        self._column_combo.setCurrentIndex(max(0, idx))
        self._column_combo.blockSignals(False)

        # Chart: rebuild checkboxes
        self._rebuild_chart_checkboxes(columns)

        # Badge: update rule column combo
        current_badge = self._badge_col_combo.currentText()
        self._badge_col_combo.blockSignals(True)
        self._badge_col_combo.clear()
        for col in self._excel_columns:
            self._badge_col_combo.addItem(col)
        idx2 = self._badge_col_combo.findText(current_badge)
        self._badge_col_combo.setCurrentIndex(max(0, idx2))
        self._badge_col_combo.blockSignals(False)

        # Photo: update photo ID mapping column combo
        current_photo = self._photo_id_combo.currentText()
        self._photo_id_combo.blockSignals(True)
        self._photo_id_combo.clear()
        self._photo_id_combo.addItem(self._AUTO_ID_COL)
        for col in self._excel_columns:
            self._photo_id_combo.addItem(col)
        idx3 = self._photo_id_combo.findText(current_photo)
        self._photo_id_combo.setCurrentIndex(max(0, idx3))
        self._photo_id_combo.blockSignals(False)

        # Table: rebuild checkboxes
        self._rebuild_table_checkboxes(columns)

    def load_item(self, item: FieldItem | ChartItem | BadgeItem | PhotoItem | QRItem | TableItem | None) -> None:
        """Bind to the currently selected item, or show empty state."""
        self._item = item
        if item is None:
            self._scroll.hide()
            self._empty.show()
            return

        self._empty.hide()
        self._scroll.show()

        self._updating = True
        try:
            # Shared: geometry
            p = item.pos()
            self._x_spin.setValue(int(p.x()))
            self._y_spin.setValue(int(p.y()))
            self._w_spin.setValue(int(item.width))
            self._h_spin.setValue(int(item.height))

            if isinstance(item, ChartItem):
                # ── Chart mode ──
                self._field_container.hide()
                self._badge_container.hide()
                self._photo_container.hide()
                self._qr_container.hide()
                self._table_container.hide()
                self._chart_container.show()
                self._panel_title.setText("Chart Properties")

                # Style combo
                style_map = {"vertical": "Vertical Bars", "horizontal": "Horizontal Bars"}
                self._chart_style_combo.setCurrentText(style_map.get(item.chart_style, "Vertical Bars"))

                # Checkboxes: update checked state
                for col, cb in self._chart_column_checkboxes.items():
                    cb.blockSignals(True)
                    cb.setChecked(col in item.chart_columns)
                    cb.blockSignals(False)

            elif isinstance(item, BadgeItem):
                # ── Badge mode ──
                self._field_container.hide()
                self._chart_container.hide()
                self._photo_container.hide()
                self._qr_container.hide()
                self._table_container.hide()
                self._badge_container.show()
                self._panel_title.setText("Badge Properties")

                # Image label
                if item.badge_image_path:
                    self._badge_path_lbl.setText(os.path.basename(item.badge_image_path))
                    self._badge_path_lbl.setStyleSheet(
                        "font-size: 11px; color: #374151; padding: 2px 0;"
                    )
                else:
                    self._badge_path_lbl.setText("No image selected")
                    self._badge_path_lbl.setStyleSheet(
                        "font-size: 11px; color: #9ca3af; font-style: italic; padding: 2px 0;"
                    )

                # Rule column
                idx = self._badge_col_combo.findText(item.rule_column)
                if idx >= 0:
                    self._badge_col_combo.setCurrentIndex(idx)

                # Rule operator
                op_idx = self._badge_op_combo.findText(item.rule_operator)
                self._badge_op_combo.setCurrentIndex(max(0, op_idx))

                # Rule value
                self._badge_value_edit.setText(item.rule_value)

            elif isinstance(item, PhotoItem):
                # ── Photo mode ──
                self._field_container.hide()
                self._chart_container.hide()
                self._badge_container.hide()
                self._qr_container.hide()
                self._table_container.hide()
                self._photo_container.show()
                self._panel_title.setText("Photo Properties")

                # ID Column
                if item.photo_id_column and item.photo_id_column in self._excel_columns:
                    self._photo_id_combo.setCurrentText(item.photo_id_column)
                else:
                    self._photo_id_combo.setCurrentIndex(0)

                # Border styling
                self._photo_color_hex = item.border_color
                self._sync_photo_color_btn()
                self._photo_border_width_spin.setValue(int(item.border_width))
                self._photo_radius_spin.setValue(int(item.corner_radius))

            elif isinstance(item, QRItem):
                # ── QR Code mode ──
                self._field_container.hide()
                self._chart_container.hide()
                self._badge_container.hide()
                self._photo_container.hide()
                self._table_container.hide()
                self._qr_container.show()
                self._panel_title.setText("QR Code Properties")

                # Payload
                self._qr_payload_edit.blockSignals(True)
                self._qr_payload_edit.setPlainText(item.qr_payload)
                self._qr_payload_edit.blockSignals(False)

                # Border cells
                self._qr_border_spin.blockSignals(True)
                self._qr_border_spin.setValue(item.border_cells)
                self._qr_border_spin.blockSignals(False)

            elif isinstance(item, TableItem):
                # ── Dynamic Table mode ──
                self._field_container.hide()
                self._chart_container.hide()
                self._badge_container.hide()
                self._photo_container.hide()
                self._qr_container.hide()
                self._table_container.show()
                self._panel_title.setText("Subject Table Properties")

                # Checkboxes: update checked subject columns
                for col, cb in self._table_column_checkboxes.items():
                    cb.blockSignals(True)
                    cb.setChecked(col in item.subject_columns)
                    cb.blockSignals(False)

                # Display options
                self._table_show_max_cb.blockSignals(True)
                self._table_show_max_cb.setChecked(item.show_max_marks)
                self._table_show_max_cb.blockSignals(False)

                self._table_show_grade_cb.blockSignals(True)
                self._table_show_grade_cb.setChecked(item.show_grade)
                self._table_show_grade_cb.blockSignals(False)

                self._table_max_marks_spin.blockSignals(True)
                self._table_max_marks_spin.setValue(int(item.max_marks))
                self._table_max_marks_spin.blockSignals(False)

                self._table_row_height_spin.blockSignals(True)
                self._table_row_height_spin.setValue(int(item.row_height))
                self._table_row_height_spin.blockSignals(False)

                self._table_font_size_spin.blockSignals(True)
                self._table_font_size_spin.setValue(int(item.font_size))
                self._table_font_size_spin.blockSignals(False)

                self._table_header_bg_hex = item.header_bg
                self._sync_table_header_bg_btn()

                self._table_header_color_hex = item.header_color
                self._sync_table_header_color_btn()

                self._table_alt_row_bg_hex = item.alt_row_bg
                self._sync_table_alt_row_bg_btn()

            else:
                # ── Field mode ──
                self._chart_container.hide()
                self._badge_container.hide()
                self._photo_container.hide()
                self._qr_container.hide()
                self._table_container.hide()
                self._field_container.show()
                self._panel_title.setText("Field Properties")

                self._label_edit.setText(item.label)

                # Auto-resolve mapped column with header aliasing if unmapped or not in current columns
                mapped_val = item.mapped_column
                if not mapped_val or mapped_val not in self._excel_columns:
                    matched = find_matching_header(item.label, self._excel_columns)
                    if matched:
                        mapped_val = matched
                        item.set_mapped_column(matched)

                if mapped_val and mapped_val in self._excel_columns:
                    self._column_combo.setCurrentText(mapped_val)
                else:
                    self._column_combo.setCurrentIndex(0)

                self._unique_cb.setChecked(item.is_unique)

                # Typography
                self._font_combo.setCurrentFont(QFont(item.font_family))
                self._size_spin.setValue(item.font_size)
                self._color_hex = item.color
                self._sync_color_btn()
                self._bold_cb.setChecked(item.bold)
                self._italic_cb.setChecked(item.italic)
                self._underline_cb.setChecked(item.underline)
                self._multiline_cb.setChecked(item.multiline)
                self._set_align_active(item.alignment)
                self._set_v_align_active(getattr(item, "v_alignment", "Top"))
        finally:
            self._updating = False

    def update_position(self, x: float, y: float) -> None:
        """Called externally when the item is dragged on canvas."""
        self._updating = True
        try:
            self._x_spin.setValue(int(x))
            self._y_spin.setValue(int(y))
        finally:
            self._updating = False

    def update_geometry(self, w: float, h: float) -> None:
        """Called externally when the item is resized via handle."""
        self._updating = True
        try:
            self._w_spin.setValue(int(w))
            self._h_spin.setValue(int(h))
        finally:
            self._updating = False

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ──────────────────────────────────────────────────────
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background: #f9fafb;
                border-bottom: 1px solid #e5e7eb;
                padding: 10px 14px;
            }
        """)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(14, 10, 14, 10)
        self._panel_title = QLabel("Field Properties")
        self._panel_title.setStyleSheet("font-weight: 700; font-size: 13px; color: #1a1a2e;")
        h_layout.addWidget(self._panel_title)
        root.addWidget(header)

        # ── Scrollable form ──────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("border-left: 1px solid #e5e7eb;")
        self._scroll = scroll

        content = QWidget()
        self._form = QVBoxLayout(content)
        self._form.setContentsMargins(14, 12, 14, 14)
        self._form.setSpacing(8)

        # ── Field-specific container ─────────────────────────────────────
        self._field_container = QWidget()
        fc_layout = QVBoxLayout(self._field_container)
        fc_layout.setContentsMargins(0, 0, 0, 0)
        fc_layout.setSpacing(8)
        self._build_field_section(fc_layout)
        self._build_typography_section(fc_layout)
        self._form.addWidget(self._field_container)

        # ── Chart-specific container ─────────────────────────────────────
        self._chart_container = QWidget()
        cc_layout = QVBoxLayout(self._chart_container)
        cc_layout.setContentsMargins(0, 0, 0, 0)
        cc_layout.setSpacing(8)
        self._build_chart_section(cc_layout)
        self._form.addWidget(self._chart_container)
        self._chart_container.hide()

        # ── Badge-specific container ─────────────────────────────────────
        self._badge_container = QWidget()
        bc_layout = QVBoxLayout(self._badge_container)
        bc_layout.setContentsMargins(0, 0, 0, 0)
        bc_layout.setSpacing(8)
        self._build_badge_section(bc_layout)
        self._form.addWidget(self._badge_container)
        self._badge_container.hide()

        # ── Photo-specific container ─────────────────────────────────────
        self._photo_container = QWidget()
        pc_layout = QVBoxLayout(self._photo_container)
        pc_layout.setContentsMargins(0, 0, 0, 0)
        pc_layout.setSpacing(8)
        self._build_photo_section(pc_layout)
        self._form.addWidget(self._photo_container)
        self._photo_container.hide()

        # ── QR-specific container ────────────────────────────────────────
        self._qr_container = QWidget()
        qc_layout = QVBoxLayout(self._qr_container)
        qc_layout.setContentsMargins(0, 0, 0, 0)
        qc_layout.setSpacing(8)
        self._build_qr_section(qc_layout)
        self._form.addWidget(self._qr_container)
        self._qr_container.hide()

        # ── Table-specific container ──────────────────────────────────────
        self._table_container = QWidget()
        tc_layout = QVBoxLayout(self._table_container)
        tc_layout.setContentsMargins(0, 0, 0, 0)
        tc_layout.setSpacing(8)
        self._build_table_section(tc_layout)
        self._form.addWidget(self._table_container)
        self._table_container.hide()

        # ── Shared sections ──────────────────────────────────────────────
        self._build_geometry_section(self._form)
        self._build_actions_section(self._form)
        self._form.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll, stretch=1)

        # ── Empty-state placeholder ──────────────────────────────────────
        self._empty = QLabel("Select a field, chart, or badge\non the canvas to edit.")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setStyleSheet("""
            color: #9ca3af; font-size: 12px;
            border-left: 1px solid #e5e7eb;
            padding: 24px;
        """)
        root.addWidget(self._empty, stretch=1)

        scroll.hide()

    # ── Section builders ──────────────────────────────────────────────────────

    def _build_field_section(self, layout: QVBoxLayout) -> None:
        layout.addWidget(self._section_lbl("Field Identity"))

        # Label
        layout.addWidget(self._caption("Field Name (Label)"))
        self._label_edit = QLineEdit()
        self._label_edit.setPlaceholderText("e.g. Student_Name")
        self._label_edit.setStyleSheet(self._INPUT)
        self._label_edit.textChanged.connect(
            lambda t: self._live(lambda: self.label_changed.emit(t))
        )
        layout.addWidget(self._label_edit)

        # Column mapping
        layout.addWidget(self._caption("Map to Excel Column"))
        self._column_combo = QComboBox()
        self._column_combo.setStyleSheet(self._INPUT)
        self._column_combo.addItem(self._NO_COL)
        self._column_combo.currentTextChanged.connect(
            lambda t: self._live(
                lambda: self.column_changed.emit("" if t == self._NO_COL else t)
            )
        )
        layout.addWidget(self._column_combo)

        # Unique designation
        self._unique_cb = QCheckBox("★ Unique Field (Record Identifier)")
        self._unique_cb.setStyleSheet(
            "font-size: 12px; font-weight: 600; color: #1d4ed8; margin-top: 4px;"
        )
        self._unique_cb.toggled.connect(
            lambda v: self._live(lambda: self.unique_changed.emit(v))
        )
        layout.addWidget(self._unique_cb)

    def _build_typography_section(self, layout: QVBoxLayout) -> None:
        layout.addSpacing(10)
        layout.addWidget(self._section_lbl("Typography & Text"))

        # Font family
        layout.addWidget(self._caption("Font Family"))
        self._font_combo = QFontComboBox()
        self._font_combo.setStyleSheet(self._INPUT)
        self._font_combo.currentFontChanged.connect(
            lambda f: self._live(lambda: self.font_family_changed.emit(f.family()))
        )
        layout.addWidget(self._font_combo)

        # Size + Color
        row1 = QHBoxLayout()
        row1.setSpacing(6)

        self._size_spin = QSpinBox()
        self._size_spin.setRange(6, 144)
        self._size_spin.setValue(12)
        self._size_spin.setStyleSheet(self._INPUT)
        self._size_spin.valueChanged.connect(
            lambda v: self._live(lambda: self.font_size_changed.emit(v))
        )

        self._color_btn = QPushButton()
        self._color_btn.setFixedSize(36, 26)
        self._color_btn.setToolTip("Click to change text colour")
        self._color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._color_btn.clicked.connect(self._on_color_clicked)
        self._sync_color_btn()

        row1.addWidget(self._caption("Size:"))
        row1.addWidget(self._size_spin, stretch=1)
        row1.addSpacing(4)
        row1.addWidget(self._caption("Color:"))
        row1.addWidget(self._color_btn)
        layout.addLayout(row1)

        # Bold / Italic / Underline
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        self._bold_cb      = QCheckBox("Bold")
        self._italic_cb    = QCheckBox("Italic")
        self._underline_cb = QCheckBox("Underline")
        self._bold_cb.toggled.connect(
            lambda v: self._live(lambda: self.bold_changed.emit(v))
        )
        self._italic_cb.toggled.connect(
            lambda v: self._live(lambda: self.italic_changed.emit(v))
        )
        self._underline_cb.toggled.connect(
            lambda v: self._live(lambda: self.underline_changed.emit(v))
        )
        row2.addWidget(self._bold_cb)
        row2.addWidget(self._italic_cb)
        row2.addWidget(self._underline_cb)
        row2.addStretch()
        layout.addLayout(row2)

        # Multiline
        self._multiline_cb = QCheckBox("Multiline Text (Auto Wrap)")
        self._multiline_cb.setStyleSheet("font-size: 12px; color: #374151;")
        self._multiline_cb.toggled.connect(
            lambda v: self._live(lambda: self.multiline_changed.emit(v))
        )
        layout.addWidget(self._multiline_cb)

        # Alignment buttons (Horizontal & Vertical)
        row3 = QHBoxLayout()
        row3.setSpacing(4)
        row3.addWidget(self._caption("H:"))
        self._align_btns: dict[str, QPushButton] = {}
        for key, sym in [("Left", "L"), ("Center", "C"), ("Right", "R")]:
            btn = QPushButton(sym)
            btn.setCheckable(True)
            btn.setFixedSize(28, 26)
            btn.setToolTip(f"Horizontal Align: {key}")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(self._TOGGLE_OFF)
            btn.clicked.connect(lambda _c, k=key: self._on_align(k))
            self._align_btns[key] = btn
            row3.addWidget(btn)

        row3.addSpacing(6)
        row3.addWidget(self._caption("V:"))
        self._v_align_btns: dict[str, QPushButton] = {}
        for key, sym in [("Top", "T"), ("Middle", "M"), ("Bottom", "B")]:
            btn = QPushButton(sym)
            btn.setCheckable(True)
            btn.setFixedSize(28, 26)
            btn.setToolTip(f"Vertical Align: {key}")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(self._TOGGLE_OFF)
            btn.clicked.connect(lambda _c, k=key: self._on_v_align(k))
            self._v_align_btns[key] = btn
            row3.addWidget(btn)

        row3.addStretch()
        layout.addLayout(row3)

    def _build_chart_section(self, layout: QVBoxLayout) -> None:
        layout.addWidget(self._section_lbl("Chart Configuration"))

        # Chart type
        layout.addWidget(self._caption("Chart Type"))
        self._chart_style_combo = QComboBox()
        self._chart_style_combo.setStyleSheet(self._INPUT)
        self._chart_style_combo.addItems(["Vertical Bars", "Horizontal Bars"])
        self._chart_style_combo.currentTextChanged.connect(self._on_chart_style_changed)
        layout.addWidget(self._chart_style_combo)

        # Column checkboxes
        layout.addSpacing(6)
        layout.addWidget(self._section_lbl("Data Columns"))
        layout.addWidget(self._caption("Select subject columns to chart:"))

        self._chart_cols_container = QWidget()
        self._chart_cols_layout = QVBoxLayout(self._chart_cols_container)
        self._chart_cols_layout.setContentsMargins(0, 4, 0, 4)
        self._chart_cols_layout.setSpacing(4)

        self._chart_cols_placeholder = QLabel(
            "Load an Excel dataset to\nsee available columns."
        )
        self._chart_cols_placeholder.setStyleSheet("font-size: 11px; color: #9ca3af; padding: 4px 0;")
        layout.addWidget(self._chart_cols_container)

    def _build_badge_section(self, layout: QVBoxLayout) -> None:
        layout.addWidget(self._section_lbl("Badge Image"))

        # File selector row
        img_row = QHBoxLayout()
        img_row.setSpacing(6)
        browse_btn = QPushButton("📁 Browse Image")
        browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_btn.setStyleSheet("""
            QPushButton {
                background: #ffffff; color: #374151; border: 1px solid #d1d5db;
                border-radius: 4px; padding: 4px 8px; font-size: 11px; font-weight: 600;
            }
            QPushButton:hover { background: #f3f4f6; color: #111827; }
        """)
        browse_btn.clicked.connect(self._on_browse_badge_image)
        img_row.addWidget(browse_btn)

        self._badge_path_lbl = QLabel("No image selected")
        self._badge_path_lbl.setStyleSheet("font-size: 11px; color: #9ca3af; font-style: italic;")
        img_row.addWidget(self._badge_path_lbl, stretch=1)
        layout.addLayout(img_row)

        layout.addSpacing(6)
        layout.addWidget(self._section_lbl("Badge Rule Condition"))
        layout.addWidget(self._caption("Stamp badge if condition is met:"))

        # Column selection
        layout.addWidget(self._caption("Data Column"))
        self._badge_col_combo = QComboBox()
        self._badge_col_combo.setStyleSheet(self._INPUT)
        self._badge_col_combo.currentTextChanged.connect(self._on_badge_rule_edited)
        layout.addWidget(self._badge_col_combo)

        # Operator & Threshold Value row
        rule_row = QHBoxLayout()
        rule_row.setSpacing(6)

        self._badge_op_combo = QComboBox()
        self._badge_op_combo.setStyleSheet(self._INPUT)
        self._badge_op_combo.addItems([">=", ">", "<=", "<", "==", "!="])
        self._badge_op_combo.currentTextChanged.connect(self._on_badge_rule_edited)

        self._badge_value_edit = QLineEdit()
        self._badge_value_edit.setPlaceholderText("e.g. 90 or Distinction")
        self._badge_value_edit.setStyleSheet(self._INPUT)
        self._badge_value_edit.textChanged.connect(self._on_badge_rule_edited)

        op_col = QVBoxLayout()
        op_col.addWidget(self._caption("Operator"))
        op_col.addWidget(self._badge_op_combo)

        val_col = QVBoxLayout()
        val_col.addWidget(self._caption("Value / Threshold"))
        val_col.addWidget(self._badge_value_edit)

        rule_row.addLayout(op_col, stretch=1)
        rule_row.addLayout(val_col, stretch=2)
        layout.addLayout(rule_row)

    def _build_photo_section(self, layout: QVBoxLayout) -> None:
        layout.addWidget(self._section_lbl("Photo Identification"))
        layout.addWidget(self._caption("Student ID Column for Photo lookup:"))

        # Column selection
        self._photo_id_combo = QComboBox()
        self._photo_id_combo.setStyleSheet(self._INPUT)
        self._photo_id_combo.addItem(self._AUTO_ID_COL)
        self._photo_id_combo.currentTextChanged.connect(self._on_photo_id_changed)
        layout.addWidget(self._photo_id_combo)

        desc = QLabel("Searches Photo Folder for {ID}.jpg / .png")
        desc.setStyleSheet("font-size: 11px; color: #64748b; font-style: italic;")
        layout.addWidget(desc)

        layout.addSpacing(6)
        layout.addWidget(self._section_lbl("Frame & Styling"))

        # Border Color & Width
        b_row = QHBoxLayout()
        b_row.setSpacing(6)

        self._photo_color_btn = QPushButton()
        self._photo_color_btn.setFixedSize(36, 26)
        self._photo_color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._photo_color_btn.clicked.connect(self._on_photo_color_clicked)
        self._photo_color_hex = "#6b7280"
        self._sync_photo_color_btn()

        self._photo_border_width_spin = QSpinBox()
        self._photo_border_width_spin.setRange(0, 20)
        self._photo_border_width_spin.setValue(1)
        self._photo_border_width_spin.setStyleSheet(self._INPUT)
        self._photo_border_width_spin.valueChanged.connect(self._on_photo_border_width_changed)

        self._photo_radius_spin = QSpinBox()
        self._photo_radius_spin.setRange(0, 50)
        self._photo_radius_spin.setValue(4)
        self._photo_radius_spin.setStyleSheet(self._INPUT)
        self._photo_radius_spin.valueChanged.connect(self._on_photo_radius_changed)

        b_row.addWidget(self._caption("Color:"))
        b_row.addWidget(self._photo_color_btn)
        b_row.addSpacing(4)
        b_row.addWidget(self._caption("Border:"))
        b_row.addWidget(self._photo_border_width_spin, stretch=1)
        b_row.addSpacing(4)
        b_row.addWidget(self._caption("Radius:"))
        b_row.addWidget(self._photo_radius_spin, stretch=1)
        layout.addLayout(b_row)

    def _build_qr_section(self, layout: QVBoxLayout) -> None:
        """Build QR code configuration controls."""
        layout.addWidget(self._section_lbl("QR Code Payload"))

        desc = QLabel(
            "Use [Column Name] tokens to embed student data.\n"
            "Example: ID:[Enrollment number] | Name:[Name]"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 11px; color: #64748b; font-style: italic;")
        layout.addWidget(desc)

        self._qr_payload_edit = QPlainTextEdit()
        self._qr_payload_edit.setFixedHeight(90)
        self._qr_payload_edit.setStyleSheet(
            "border: 1px solid #d1d5db; border-radius: 4px; "
            "padding: 4px; font-size: 11px; color: #111827; background: white;"
        )
        self._qr_payload_edit.textChanged.connect(self._on_qr_payload_changed)
        layout.addWidget(self._qr_payload_edit)

        layout.addSpacing(6)
        layout.addWidget(self._section_lbl("Border / Margin"))

        bc_row = QHBoxLayout()
        bc_row.setSpacing(6)
        bc_row.addWidget(self._caption("QR margin cells:"))
        self._qr_border_spin = QSpinBox()
        self._qr_border_spin.setRange(0, 10)
        self._qr_border_spin.setValue(1)
        self._qr_border_spin.setStyleSheet(self._INPUT)
        self._qr_border_spin.valueChanged.connect(self._on_qr_border_cells_changed)
        bc_row.addWidget(self._qr_border_spin, stretch=1)
        layout.addLayout(bc_row)

    def _build_table_section(self, layout: QVBoxLayout) -> None:
        """Build Dynamic Subject Table configuration controls."""
        layout.addWidget(self._section_lbl("Table Configuration"))

        # Display checkboxes
        self._table_show_max_cb = QCheckBox("Show Max Marks column")
        self._table_show_max_cb.setChecked(True)
        self._table_show_max_cb.setStyleSheet("font-size: 12px; color: #374151;")
        self._table_show_max_cb.toggled.connect(
            lambda v: self._table_live(lambda: self.table_show_max_changed.emit(v))
        )
        layout.addWidget(self._table_show_max_cb)

        self._table_show_grade_cb = QCheckBox("Show Grade column")
        self._table_show_grade_cb.setChecked(True)
        self._table_show_grade_cb.setStyleSheet("font-size: 12px; color: #374151;")
        self._table_show_grade_cb.toggled.connect(
            lambda v: self._table_live(lambda: self.table_show_grade_changed.emit(v))
        )
        layout.addWidget(self._table_show_grade_cb)

        # Max marks spinbox
        mm_row = QHBoxLayout()
        mm_row.setSpacing(6)
        mm_row.addWidget(self._caption("Max Marks:"))
        self._table_max_marks_spin = QSpinBox()
        self._table_max_marks_spin.setRange(1, 1000)
        self._table_max_marks_spin.setValue(100)
        self._table_max_marks_spin.setStyleSheet(self._INPUT)
        self._table_max_marks_spin.valueChanged.connect(
            lambda v: self._table_live(lambda: self.table_max_marks_changed.emit(float(v)))
        )
        mm_row.addWidget(self._table_max_marks_spin, stretch=1)
        layout.addLayout(mm_row)

        # Row height & Font size
        geom_row = QHBoxLayout()
        geom_row.setSpacing(6)
        geom_row.addWidget(self._caption("Row Height:"))
        self._table_row_height_spin = QSpinBox()
        self._table_row_height_spin.setRange(12, 60)
        self._table_row_height_spin.setValue(22)
        self._table_row_height_spin.setStyleSheet(self._INPUT)
        self._table_row_height_spin.valueChanged.connect(
            lambda v: self._table_live(lambda: self.table_row_height_changed.emit(float(v)))
        )
        geom_row.addWidget(self._table_row_height_spin, stretch=1)

        geom_row.addWidget(self._caption("Font Size:"))
        self._table_font_size_spin = QSpinBox()
        self._table_font_size_spin.setRange(6, 24)
        self._table_font_size_spin.setValue(9)
        self._table_font_size_spin.setStyleSheet(self._INPUT)
        self._table_font_size_spin.valueChanged.connect(
            lambda v: self._table_live(lambda: self.table_font_size_changed.emit(v))
        )
        geom_row.addWidget(self._table_font_size_spin, stretch=1)
        layout.addLayout(geom_row)

        # Color controls: Header BG, Header Text, Alt Row BG
        layout.addSpacing(4)
        layout.addWidget(self._section_lbl("Table Colors"))
        c_row = QHBoxLayout()
        c_row.setSpacing(6)

        self._table_header_bg_btn = QPushButton()
        self._table_header_bg_btn.setFixedSize(28, 24)
        self._table_header_bg_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._table_header_bg_btn.setToolTip("Header Background Color")
        self._table_header_bg_btn.clicked.connect(self._on_table_header_bg_clicked)

        self._table_header_color_btn = QPushButton()
        self._table_header_color_btn.setFixedSize(28, 24)
        self._table_header_color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._table_header_color_btn.setToolTip("Header Text Color")
        self._table_header_color_btn.clicked.connect(self._on_table_header_color_clicked)

        self._table_alt_row_bg_btn = QPushButton()
        self._table_alt_row_bg_btn.setFixedSize(28, 24)
        self._table_alt_row_bg_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._table_alt_row_bg_btn.setToolTip("Alternate Row Fill Color")
        self._table_alt_row_bg_btn.clicked.connect(self._on_table_alt_row_bg_clicked)

        self._sync_table_header_bg_btn()
        self._sync_table_header_color_btn()
        self._sync_table_alt_row_bg_btn()

        c_row.addWidget(self._caption("Header:"))
        c_row.addWidget(self._table_header_bg_btn)
        c_row.addWidget(self._caption("Text:"))
        c_row.addWidget(self._table_header_color_btn)
        c_row.addWidget(self._caption("Alt Row:"))
        c_row.addWidget(self._table_alt_row_bg_btn)
        c_row.addStretch()
        layout.addLayout(c_row)

        # Subject columns checklist
        layout.addSpacing(6)
        layout.addWidget(self._section_lbl("Subject Columns"))
        layout.addWidget(self._caption("Select columns to include in table:"))

        self._table_cols_container = QWidget()
        self._table_cols_layout = QVBoxLayout(self._table_cols_container)
        self._table_cols_layout.setContentsMargins(0, 4, 0, 4)
        self._table_cols_layout.setSpacing(4)

        self._table_cols_placeholder = QLabel(
            "Load an Excel dataset to\nsee available subject columns."
        )
        self._table_cols_placeholder.setStyleSheet("font-size: 11px; color: #9ca3af; padding: 4px 0;")
        self._table_cols_layout.addWidget(self._table_cols_placeholder)
        layout.addWidget(self._table_cols_container)

    def _build_geometry_section(self, layout: QVBoxLayout) -> None:
        layout.addSpacing(10)
        layout.addWidget(self._section_lbl("Position & Dimensions"))

        xy = QHBoxLayout()
        xy.setSpacing(6)
        self._x_spin = self._coord_spin()
        self._y_spin = self._coord_spin()
        self._x_spin.valueChanged.connect(
            lambda v: self._live(lambda: self.x_changed.emit(v))
        )
        self._y_spin.valueChanged.connect(
            lambda v: self._live(lambda: self.y_changed.emit(v))
        )
        xy.addWidget(self._caption("X:"))
        xy.addWidget(self._x_spin)
        xy.addWidget(self._caption("Y:"))
        xy.addWidget(self._y_spin)
        layout.addLayout(xy)

        wh = QHBoxLayout()
        wh.setSpacing(6)
        self._w_spin = self._coord_spin(60, 4000)
        self._h_spin = self._coord_spin(20, 4000)
        self._w_spin.valueChanged.connect(
            lambda v: self._live(lambda: self.width_changed.emit(v))
        )
        self._h_spin.valueChanged.connect(
            lambda v: self._live(lambda: self.height_changed.emit(v))
        )
        wh.addWidget(self._caption("W:"))
        wh.addWidget(self._w_spin)
        wh.addWidget(self._caption("H:"))
        wh.addWidget(self._h_spin)
        layout.addLayout(wh)

    def _build_actions_section(self, layout: QVBoxLayout) -> None:
        layout.addSpacing(12)
        btn = QPushButton("🗑  Delete Selected Item")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background: #fee2e2; color: #b91c1c;
                border: 1px solid #fca5a5; border-radius: 5px;
                padding: 6px 12px; font-size: 12px; font-weight: 600;
            }
            QPushButton:hover { background: #fecaca; color: #991b1b; }
        """)
        btn.clicked.connect(self.delete_requested.emit)
        layout.addWidget(btn)

    # ── Chart helper methods ──────────────────────────────────────────────────

    def _rebuild_chart_checkboxes(self, columns: list[str]) -> None:
        """Recreate chart column checkboxes from the given column list."""
        # Remove & schedule deletion of existing checkboxes
        for cb in self._chart_column_checkboxes.values():
            self._chart_cols_layout.removeWidget(cb)
            cb.deleteLater()
        self._chart_column_checkboxes.clear()

        if not columns:
            self._chart_cols_placeholder.show()
            return

        self._chart_cols_placeholder.hide()

        # Determine which columns are currently selected in the chart item
        selected: set[str] = set()
        if isinstance(self._item, ChartItem):
            selected = set(self._item.chart_columns)

        for col in columns:
            cb = QCheckBox(col)
            cb.setChecked(col in selected)
            cb.setStyleSheet("font-size: 12px; color: #374151; padding: 1px 0;")
            cb.toggled.connect(self._on_chart_column_toggled)
            self._chart_column_checkboxes[col] = cb
            self._chart_cols_layout.addWidget(cb)

    def _on_chart_column_toggled(self, _checked: bool) -> None:
        selected = [col for col, cb in self._chart_column_checkboxes.items() if cb.isChecked()]
        self._chart_live(lambda: self.chart_columns_changed.emit(selected))

    def _on_chart_style_changed(self, text: str) -> None:
        style_map = {"Vertical Bars": "vertical", "Horizontal Bars": "horizontal"}
        style = style_map.get(text, "vertical")
        self._chart_live(lambda: self.chart_style_changed.emit(style))

    # ── Badge helper methods ──────────────────────────────────────────────────

    def _on_browse_badge_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Badge Image",
            "",
            "Images (*.png *.jpg *.jpeg *.svg *.webp);;All Files (*)",
        )
        if path:
            self._badge_path_lbl.setText(os.path.basename(path))
            self._badge_path_lbl.setStyleSheet("font-size: 11px; color: #374151; padding: 2px 0;")
            self._badge_live(lambda: self.badge_image_changed.emit(path))

    def _on_badge_rule_edited(self) -> None:
        col = self._badge_col_combo.currentText().strip()
        op = self._badge_op_combo.currentText().strip()
        val = self._badge_value_edit.text().strip()
        self._badge_live(lambda: self.badge_rule_changed.emit(col, op, val))

    # ── Private event helpers ─────────────────────────────────────────────────

    def _live(self, emit_fn) -> None:
        """Emit signal only when not programmatically updating and an item is selected."""
        if not self._updating and self._item is not None:
            emit_fn()

    def _chart_live(self, emit_fn) -> None:
        """Emit signal only when not updating and a ChartItem is selected."""
        if not self._updating and isinstance(self._item, ChartItem):
            emit_fn()

    def _badge_live(self, emit_fn) -> None:
        """Emit signal only when not updating and a BadgeItem is selected."""
        if not self._updating and isinstance(self._item, BadgeItem):
            emit_fn()

    def _photo_live(self, emit_fn) -> None:
        """Emit signal only when not updating and a PhotoItem is selected."""
        if not self._updating and isinstance(self._item, PhotoItem):
            emit_fn()

    def _on_photo_id_changed(self, text: str) -> None:
        col = "" if text == self._AUTO_ID_COL else text.strip()
        self._photo_live(lambda: self.photo_id_column_changed.emit(col))

    def _on_photo_color_clicked(self) -> None:
        col = QColorDialog.getColor(QColor(self._photo_color_hex), self, "Select Photo Border Color")
        if col.isValid():
            self._photo_color_hex = col.name()
            self._sync_photo_color_btn()
            self._photo_live(lambda: self.photo_border_color_changed.emit(self._photo_color_hex))

    def _sync_photo_color_btn(self) -> None:
        if hasattr(self, "_photo_color_btn"):
            self._photo_color_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self._photo_color_hex};
                    border: 1px solid #9ca3af;
                    border-radius: 3px;
                }}
            """)

    def _on_photo_border_width_changed(self, val: int) -> None:
        self._photo_live(lambda: self.photo_border_width_changed.emit(float(val)))

    def _on_photo_radius_changed(self, val: int) -> None:
        self._photo_live(lambda: self.photo_corner_radius_changed.emit(float(val)))

    def _qr_live(self, emit_fn) -> None:
        """Emit signal only when not updating and a QRItem is selected."""
        if not self._updating and isinstance(self._item, QRItem):
            emit_fn()

    def _on_qr_payload_changed(self) -> None:
        if hasattr(self, "_qr_payload_edit"):
            text = self._qr_payload_edit.toPlainText()
            self._qr_live(lambda: self.qr_payload_changed.emit(text))

    def _on_qr_border_cells_changed(self, val: int) -> None:
        self._qr_live(lambda: self.qr_border_cells_changed.emit(val))

    # ── Table helper methods ──────────────────────────────────────────────────

    def _rebuild_table_checkboxes(self, columns: list[str]) -> None:
        """Recreate table subject column checkboxes from the given column list."""
        if not hasattr(self, "_table_cols_layout"):
            return

        for cb in self._table_column_checkboxes.values():
            self._table_cols_layout.removeWidget(cb)
            cb.deleteLater()
        self._table_column_checkboxes.clear()

        if not columns:
            self._table_cols_placeholder.show()
            return

        self._table_cols_placeholder.hide()

        selected: set[str] = set()
        if isinstance(self._item, TableItem):
            selected = set(self._item.subject_columns)

        for col in columns:
            cb = QCheckBox(col)
            cb.setChecked(col in selected)
            cb.setStyleSheet("font-size: 12px; color: #374151; padding: 1px 0;")
            cb.toggled.connect(self._on_table_column_toggled)
            self._table_column_checkboxes[col] = cb
            self._table_cols_layout.addWidget(cb)

    def _on_table_column_toggled(self, _checked: bool) -> None:
        selected = [col for col, cb in self._table_column_checkboxes.items() if cb.isChecked()]
        self._table_live(lambda: self.table_columns_changed.emit(selected))

    def _table_live(self, emit_fn) -> None:
        if not self._updating and isinstance(self._item, TableItem):
            emit_fn()

    def _on_table_header_bg_clicked(self) -> None:
        col = QColorDialog.getColor(QColor(self._table_header_bg_hex), self, "Select Header Background Color")
        if col.isValid():
            self._table_header_bg_hex = col.name()
            self._sync_table_header_bg_btn()
            self._table_live(lambda: self.table_header_bg_changed.emit(self._table_header_bg_hex))

    def _on_table_header_color_clicked(self) -> None:
        col = QColorDialog.getColor(QColor(self._table_header_color_hex), self, "Select Header Text Color")
        if col.isValid():
            self._table_header_color_hex = col.name()
            self._sync_table_header_color_btn()
            self._table_live(lambda: self.table_header_color_changed.emit(self._table_header_color_hex))

    def _on_table_alt_row_bg_clicked(self) -> None:
        col = QColorDialog.getColor(QColor(self._table_alt_row_bg_hex), self, "Select Alternate Row Color")
        if col.isValid():
            self._table_alt_row_bg_hex = col.name()
            self._sync_table_alt_row_bg_btn()
            self._table_live(lambda: self.table_alt_row_bg_changed.emit(self._table_alt_row_bg_hex))

    def _sync_table_header_bg_btn(self) -> None:
        if hasattr(self, "_table_header_bg_btn"):
            self._table_header_bg_btn.setStyleSheet(
                f"background-color: {self._table_header_bg_hex}; border: 1px solid #9ca3af; border-radius: 3px;"
            )

    def _sync_table_header_color_btn(self) -> None:
        if hasattr(self, "_table_header_color_btn"):
            self._table_header_color_btn.setStyleSheet(
                f"background-color: {self._table_header_color_hex}; border: 1px solid #9ca3af; border-radius: 3px;"
            )

    def _sync_table_alt_row_bg_btn(self) -> None:
        if hasattr(self, "_table_alt_row_bg_btn"):
            self._table_alt_row_bg_btn.setStyleSheet(
                f"background-color: {self._table_alt_row_bg_hex}; border: 1px solid #9ca3af; border-radius: 3px;"
            )

    def _on_color_clicked(self) -> None:
        col = QColorDialog.getColor(QColor(self._color_hex), self, "Select Text Color")
        if col.isValid():
            self._color_hex = col.name()
            self._sync_color_btn()
            self._live(lambda: self.color_changed.emit(self._color_hex))

    def _sync_color_btn(self) -> None:
        self._color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._color_hex};
                border: 1px solid #9ca3af;
                border-radius: 3px;
            }}
        """)

    def _on_align(self, key: str) -> None:
        self._set_align_active(key)
        self._live(lambda: self.alignment_changed.emit(key))

    def _set_align_active(self, active_key: str) -> None:
        for k, btn in self._align_btns.items():
            btn.blockSignals(True)
            btn.setChecked(k == active_key)
            btn.blockSignals(False)
            btn.setStyleSheet(self._TOGGLE_ON if btn.isChecked() else self._TOGGLE_OFF)

    def _on_v_align(self, key: str) -> None:
        self._set_v_align_active(key)
        self._live(lambda: self.v_alignment_changed.emit(key))

    def _set_v_align_active(self, active_key: str) -> None:
        if not hasattr(self, "_v_align_btns"):
            return
        for k, btn in self._v_align_btns.items():
            btn.blockSignals(True)
            btn.setChecked(k == active_key)
            btn.blockSignals(False)
            btn.setStyleSheet(self._TOGGLE_ON if btn.isChecked() else self._TOGGLE_OFF)

    @staticmethod
    def _section_lbl(text: str) -> QLabel:
        lbl = QLabel(text.upper())
        lbl.setStyleSheet("""
            font-size: 10px; font-weight: 700;
            color: #9ca3af; letter-spacing: 0.5px;
            margin-top: 2px;
        """)
        return lbl

    @staticmethod
    def _caption(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("font-size: 11px; color: #6b7280; margin-top: 3px;")
        return lbl

    @staticmethod
    def _coord_spin(mn: int = 0, mx: int = 9999) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(mn, mx)
        spin.setStyleSheet("""
            QSpinBox {
                border: 1px solid #d1d5db; border-radius: 4px;
                padding: 2px 4px; font-size: 12px; background: white;
                color: #000000;
            }
            QSpinBox:focus { border-color: #4f7ef8; }
        """)
        return spin

    # ── Style constants ───────────────────────────────────────────────────────

    _INPUT = """
        QWidget {
            border: 1px solid #d1d5db; border-radius: 4px;
            padding: 3px 6px; font-size: 12px; background: white;
            color: #000000;
        }
        QWidget:focus { border-color: #4f7ef8; }
        QComboBox QAbstractItemView {
            background-color: white;
            color: #000000;
            selection-background-color: #eff6ff;
            selection-color: #1d4ed8;
        }
    """

    _TOGGLE_OFF = """
        QPushButton {
            background: #ffffff;
            color: #111827;
            border: 1px solid #d1d5db;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 700;
            padding: 0px;
            margin: 0px;
            min-width: 0px;
            min-height: 0px;
        }
        QPushButton:hover {
            background: #f3f4f6;
            color: #111827;
        }
    """

    _TOGGLE_ON = """
        QPushButton {
            background: #2563eb;
            color: #ffffff;
            border: 1px solid #1d4ed8;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 700;
            padding: 0px;
            margin: 0px;
            min-width: 0px;
            min-height: 0px;
        }
        QPushButton:hover {
            background: #1d4ed8;
            color: #ffffff;
        }
    """
