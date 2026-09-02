"""
PropertiesPanel - right-side sidebar for configuring the selected FieldItem.

Allows live editing of:
- Field Label (Excel variable identifier)
- Unique Field designation (Student / Record Identifier)
- Excel column mapping dropdown
- Typography (Font Family, Size, Color Picker, Bold, Italic, Underline, Alignment, Multiline)
- Precise geometry spinboxes (X, Y, Width, Height)
- Delete button with confirmation
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QFontComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ui.widgets.field_item import FieldItem


class PropertiesPanel(QWidget):
    """Sidebar widget displayed on the right of the Template Editor."""

    # ── Signals emitted on user edits ─────────────────────────────────────────
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
    x_changed           = pyqtSignal(float)
    y_changed           = pyqtSignal(float)
    width_changed       = pyqtSignal(float)
    height_changed      = pyqtSignal(float)
    delete_requested    = pyqtSignal()

    _NO_COL = "-- None (use Label) --"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._item: FieldItem | None = None
        self._updating: bool = False
        self._color_hex: str = "#000000"
        self._excel_columns: list[str] = []

        self.setFixedWidth(290)
        self.setStyleSheet("background: white;")
        self._build_ui()

    # ── Public API ────────────────────────────────────────────────────────────

    def set_excel_columns(self, columns: list[str]) -> None:
        """Update available Excel columns for mapping."""
        self._excel_columns = list(columns)
        current = self._column_combo.currentText()
        self._column_combo.blockSignals(True)
        self._column_combo.clear()
        self._column_combo.addItem(self._NO_COL)
        for col in self._excel_columns:
            self._column_combo.addItem(col)
        idx = self._column_combo.findText(current)
        self._column_combo.setCurrentIndex(max(0, idx))
        self._column_combo.blockSignals(False)

    def load_item(self, item: FieldItem | None) -> None:
        """Bind to the currently selected FieldItem, or show empty state."""
        self._item = item
        if item is None:
            self._scroll.hide()
            self._empty.show()
            return

        self._empty.hide()
        self._scroll.show()

        self._updating = True
        try:
            self._label_edit.setText(item.label)

            # Column combo
            if item.mapped_column and item.mapped_column in self._excel_columns:
                self._column_combo.setCurrentText(item.mapped_column)
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

            # Geometry
            p = item.pos()
            self._x_spin.setValue(int(p.x()))
            self._y_spin.setValue(int(p.y()))
            self._w_spin.setValue(int(item.width))
            self._h_spin.setValue(int(item.height))
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

        # Header
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
        title = QLabel("Field Properties")
        title.setStyleSheet("font-weight: 700; font-size: 13px; color: #1a1a2e;")
        h_layout.addWidget(title)
        root.addWidget(header)

        # Scrollable form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("border-left: 1px solid #e5e7eb;")
        self._scroll = scroll

        content = QWidget()
        self._form = QVBoxLayout(content)
        self._form.setContentsMargins(14, 12, 14, 14)
        self._form.setSpacing(8)

        self._build_field_section()
        self._build_typography_section()
        self._build_geometry_section()
        self._build_actions_section()

        scroll.setWidget(content)
        root.addWidget(scroll, stretch=1)

        # Empty-state placeholder
        self._empty = QLabel("Select a field on the canvas\nto edit its properties.")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setStyleSheet("""
            color: #9ca3af; font-size: 12px;
            border-left: 1px solid #e5e7eb;
            padding: 24px;
        """)
        root.addWidget(self._empty, stretch=1)

        scroll.hide()

    def _build_field_section(self) -> None:
        self._form.addWidget(self._section_lbl("Field Identity"))

        # Label
        self._form.addWidget(self._caption("Field Name (Label)"))
        self._label_edit = QLineEdit()
        self._label_edit.setPlaceholderText("e.g. Student_Name")
        self._label_edit.setStyleSheet(self._INPUT)
        self._label_edit.textChanged.connect(
            lambda t: self._live(lambda: self.label_changed.emit(t))
        )
        self._form.addWidget(self._label_edit)

        # Column mapping
        self._form.addWidget(self._caption("Map to Excel Column"))
        self._column_combo = QComboBox()
        self._column_combo.setStyleSheet(self._INPUT)
        self._column_combo.addItem(self._NO_COL)
        self._column_combo.currentTextChanged.connect(
            lambda t: self._live(
                lambda: self.column_changed.emit("" if t == self._NO_COL else t)
            )
        )
        self._form.addWidget(self._column_combo)

        # Unique designation checkbox
        self._unique_cb = QCheckBox("★ Unique Field (Record Identifier)")
        self._unique_cb.setStyleSheet("font-size: 12px; font-weight: 600; color: #1d4ed8; margin-top: 4px;")
        self._unique_cb.toggled.connect(
            lambda v: self._live(lambda: self.unique_changed.emit(v))
        )
        self._form.addWidget(self._unique_cb)

    def _build_typography_section(self) -> None:
        self._form.addSpacing(10)
        self._form.addWidget(self._section_lbl("Typography & Text"))

        # Font family
        self._form.addWidget(self._caption("Font Family"))
        self._font_combo = QFontComboBox()
        self._font_combo.setStyleSheet(self._INPUT)
        self._font_combo.currentFontChanged.connect(
            lambda f: self._live(lambda: self.font_family_changed.emit(f.family()))
        )
        self._form.addWidget(self._font_combo)

        # Size + Color on same row
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

        row1.addWidget(QLabel("Size:"))
        row1.addWidget(self._size_spin, stretch=1)
        row1.addSpacing(4)
        row1.addWidget(QLabel("Color:"))
        row1.addWidget(self._color_btn)
        self._form.addLayout(row1)

        # Bold + Italic + Underline
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
        self._form.addLayout(row2)

        # Multiline text wrap
        self._multiline_cb = QCheckBox("Multiline Text (Auto Wrap)")
        self._multiline_cb.setStyleSheet("font-size: 12px; color: #374151;")
        self._multiline_cb.toggled.connect(
            lambda v: self._live(lambda: self.multiline_changed.emit(v))
        )
        self._form.addWidget(self._multiline_cb)

        # Alignment buttons
        row3 = QHBoxLayout()
        row3.setSpacing(4)
        row3.addWidget(QLabel("Align:"))
        self._align_btns: dict[str, QPushButton] = {}
        for key, sym in [("Left", "L"), ("Center", "C"), ("Right", "R")]:
            btn = QPushButton(sym)
            btn.setCheckable(True)
            btn.setFixedSize(30, 26)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(self._TOGGLE_OFF)
            btn.clicked.connect(lambda _c, k=key: self._on_align(k))
            self._align_btns[key] = btn
            row3.addWidget(btn)
        row3.addStretch()
        self._form.addLayout(row3)

    def _build_geometry_section(self) -> None:
        self._form.addSpacing(10)
        self._form.addWidget(self._section_lbl("Position & Dimensions"))

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
        xy.addWidget(QLabel("X:"))
        xy.addWidget(self._x_spin)
        xy.addWidget(QLabel("Y:"))
        xy.addWidget(self._y_spin)
        self._form.addLayout(xy)

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
        wh.addWidget(QLabel("W:"))
        wh.addWidget(self._w_spin)
        wh.addWidget(QLabel("H:"))
        wh.addWidget(self._h_spin)
        self._form.addLayout(wh)

    def _build_actions_section(self) -> None:
        self._form.addSpacing(12)
        btn = QPushButton("🗑  Delete Field")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background: #fee2e2; color: #b91c1c;
                border: 1px solid #fca5a5; border-radius: 5px;
                padding: 6px 12px; font-size: 12px; font-weight: 600;
            }
            QPushButton:hover { background: #fecaca; }
        """)
        btn.clicked.connect(self.delete_requested.emit)
        self._form.addWidget(btn)

    # ── Private event helpers ─────────────────────────────────────────────────

    def _live(self, emit_fn) -> None:
        if not self._updating and self._item is not None:
            emit_fn()

    def _on_color_clicked(self) -> None:
        col = QColorDialog.getColor(
            QColor(self._color_hex), self, "Select Text Color"
        )
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
            background: white; color: #374151;
            border: 1px solid #d1d5db; border-radius: 4px;
            font-size: 12px; font-weight: 600;
        }
        QPushButton:hover { background: #f3f4f6; }
    """

    _TOGGLE_ON = """
        QPushButton {
            background: #4f7ef8; color: white;
            border: 1px solid #4f7ef8; border-radius: 4px;
            font-size: 12px; font-weight: 700;
        }
    """
