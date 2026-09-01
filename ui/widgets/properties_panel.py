"""
PropertiesPanel - right-side panel for inspecting and editing a selected FieldItem.

Signal flow (all changes are emitted as signals; TemplateEditorView applies
them to the active FieldItem, keeping this widget fully decoupled from
the graphics layer):

  User edits control → PropertiesPanel emits signal
                     → TemplateEditorView slot applies change to FieldItem

  FieldItem dragged  → position_changed signal
                     → TemplateEditorView calls update_position()
                     → PropertiesPanel silently updates X/Y spinboxes

  FieldItem resized  → geometry_changed signal
                     → TemplateEditorView calls update_geometry()
                     → PropertiesPanel silently updates W/H spinboxes
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


class PropertiesPanel(QWidget):
    """Sidebar panel for editing the properties of a selected FieldItem."""

    # Emitted when the user changes a property
    label_changed       = pyqtSignal(str)
    column_changed      = pyqtSignal(str)
    font_family_changed = pyqtSignal(str)
    font_size_changed   = pyqtSignal(int)
    color_changed       = pyqtSignal(str)
    bold_changed        = pyqtSignal(bool)
    italic_changed      = pyqtSignal(bool)
    alignment_changed   = pyqtSignal(str)   # "Left" | "Center" | "Right"
    x_changed           = pyqtSignal(int)
    y_changed           = pyqtSignal(int)
    width_changed       = pyqtSignal(int)
    height_changed      = pyqtSignal(int)
    delete_requested    = pyqtSignal()

    _NO_COL = "(No column mapped)"

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._updating = False          # suppresses recursive signal emissions
        self._current_color = "#000000"
        self.setFixedWidth(272)
        self.setStyleSheet("background: white;")
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Panel header ─────────────────────────────────────────────────
        header = QLabel("   Field Properties")
        header.setFixedHeight(46)
        header.setStyleSheet("""
            background: #f9fafb;
            border-left: 1px solid #e5e7eb;
            border-bottom: 1px solid #e5e7eb;
            font-size: 13px; font-weight: 700; color: #1a1a2e;
        """)
        root.addWidget(header)

        # ── Scroll area (holds all property controls) ────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("border-left: 1px solid #e5e7eb;")

        inner = QWidget()
        self._form = QVBoxLayout(inner)
        self._form.setContentsMargins(14, 12, 14, 16)
        self._form.setSpacing(5)

        self._build_field_section()
        self._build_typography_section()
        self._build_geometry_section()
        self._build_delete_button()
        self._form.addStretch()

        scroll.setWidget(inner)
        root.addWidget(scroll, stretch=1)
        self._scroll = scroll

        # ── Empty state ──────────────────────────────────────────────────
        self._empty = QLabel("Select a field\nto edit its properties.")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setStyleSheet("""
            font-size: 12px; color: #9ca3af; padding: 24px;
            border-left: 1px solid #e5e7eb;
        """)
        root.addWidget(self._empty, stretch=1)

        # Start with empty state
        scroll.hide()

    # ── Section builders ──────────────────────────────────────────────────

    def _build_field_section(self) -> None:
        self._form.addWidget(self._section_lbl("Field"))

        # Label
        self._form.addWidget(self._caption("Label"))
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

    def _build_typography_section(self) -> None:
        self._form.addSpacing(10)
        self._form.addWidget(self._section_lbl("Typography"))

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

        # Bold + Italic
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        self._bold_cb   = QCheckBox("Bold")
        self._italic_cb = QCheckBox("Italic")
        self._bold_cb.toggled.connect(
            lambda v: self._live(lambda: self.bold_changed.emit(v))
        )
        self._italic_cb.toggled.connect(
            lambda v: self._live(lambda: self.italic_changed.emit(v))
        )
        row2.addWidget(self._bold_cb)
        row2.addWidget(self._italic_cb)
        row2.addStretch()
        self._form.addLayout(row2)

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
        self._form.addWidget(self._section_lbl("Position & Size"))

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
        self._w_spin = self._coord_spin(mn=60)
        self._h_spin = self._coord_spin(mn=20)
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

    def _build_delete_button(self) -> None:
        self._form.addSpacing(16)
        btn = QPushButton("🗑   Delete This Field")
        btn.setFixedHeight(34)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background: #fee2e2; color: #dc2626;
                border: 1px solid #fca5a5; border-radius: 6px;
                font-size: 13px; font-weight: 600;
            }
            QPushButton:hover { background: #fecaca; }
        """)
        btn.clicked.connect(self.delete_requested.emit)
        self._form.addWidget(btn)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_excel_headers(self, headers: list[str]) -> None:
        """Repopulate the column-mapping dropdown with new Excel headers."""
        self._updating = True
        saved = self._column_combo.currentText()
        self._column_combo.clear()
        self._column_combo.addItem(self._NO_COL)
        for h in headers:
            self._column_combo.addItem(h)
        idx = self._column_combo.findText(saved)
        self._column_combo.setCurrentIndex(max(0, idx))
        self._updating = False

    def load_item(self, item) -> None:
        """
        Populate all controls from *item* (a FieldItem) and show the form.
        Pass None to revert to the empty-state placeholder.
        """
        if item is None:
            self._scroll.hide()
            self._empty.show()
            return

        self._updating = True

        self._label_edit.setText(item.label)

        idx = self._column_combo.findText(item.mapped_column)
        self._column_combo.setCurrentIndex(max(0, idx))

        self._font_combo.setCurrentFont(QFont(item.font_family))
        self._size_spin.setValue(item.font_size)

        self._current_color = item.color
        self._sync_color_btn()

        self._bold_cb.setChecked(item.bold)
        self._italic_cb.setChecked(item.italic)

        for key, btn in self._align_btns.items():
            btn.setChecked(key == item.alignment)
        self._sync_align_styles()

        p = item.pos()
        self._x_spin.setValue(round(p.x()))
        self._y_spin.setValue(round(p.y()))
        self._w_spin.setValue(round(item.width))
        self._h_spin.setValue(round(item.height))

        self._updating = False

        self._empty.hide()
        self._scroll.show()

    def update_position(self, x: float, y: float) -> None:
        """Called by TemplateEditorView when the item is dragged."""
        self._updating = True
        self._x_spin.setValue(round(x))
        self._y_spin.setValue(round(y))
        self._updating = False

    def update_geometry(self, w: float, h: float) -> None:
        """Called by TemplateEditorView when the item is resized via handle."""
        self._updating = True
        self._w_spin.setValue(round(w))
        self._h_spin.setValue(round(h))
        self._updating = False

    # ------------------------------------------------------------------
    # Private slots
    # ------------------------------------------------------------------

    def _on_color_clicked(self) -> None:
        col = QColorDialog.getColor(QColor(self._current_color), self, "Select Text Colour")
        if col.isValid():
            self._current_color = col.name()
            self._sync_color_btn()
            if not self._updating:
                self.color_changed.emit(self._current_color)

    def _on_align(self, key: str) -> None:
        for k, btn in self._align_btns.items():
            btn.setChecked(k == key)
        self._sync_align_styles()
        if not self._updating:
            self.alignment_changed.emit(key)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _live(self, fn) -> None:
        """Call fn() only when not in a programmatic update."""
        if not self._updating:
            fn()

    def _sync_color_btn(self) -> None:
        self._color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._current_color};
                border: 2px solid #d1d5db; border-radius: 4px;
            }}
            QPushButton:hover {{ border-color: #6b7280; }}
        """)

    def _sync_align_styles(self) -> None:
        for key, btn in self._align_btns.items():
            btn.setStyleSheet(self._TOGGLE_ON if btn.isChecked() else self._TOGGLE_OFF)

    @staticmethod
    def _section_lbl(text: str) -> QLabel:
        lbl = QLabel(text.upper())
        lbl.setStyleSheet("""
            font-size: 10px; font-weight: 700; color: #9ca3af;
            letter-spacing: 0.8px; padding-top: 2px;
            border-bottom: 1px solid #f0f0f0; padding-bottom: 3px;
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
            }
            QSpinBox:focus { border-color: #4f7ef8; }
        """)
        return spin

    # ── Style constants ───────────────────────────────────────────────────────

    _INPUT = """
        QWidget {
            border: 1px solid #d1d5db; border-radius: 4px;
            padding: 3px 6px; font-size: 12px; background: white;
        }
        QWidget:focus { border-color: #4f7ef8; }
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
