"""
FieldItem - draggable, resizable text placeholder on the template canvas.

Supports:
- Label & Mapped Excel Column
- Unique Field designation (is_unique)
- Typography: Font Family, Size, Color, Bold, Italic, Underline, Alignment
- Multiline wrapping
- Dynamic Geometry & Drag-Resize Handling
- Complete JSON Serialization
"""
from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPen, QTextOption
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsObject


class FieldItem(QGraphicsObject):
    """Draggable, resizable text placeholder on the QGraphicsScene."""

    # Emitted whenever the item moves (drag or setX/setY).
    position_changed = pyqtSignal(float, float)
    # Emitted during resize-handle drag so the panel can update W/H spinboxes.
    geometry_changed = pyqtSignal(float, float)

    HANDLE_SIZE: int = 10   # px – resize handle square side length

    def __init__(
        self,
        label: str = "New Field",
        x: float = 100.0,
        y: float = 100.0,
        width: float = 200.0,
        height: float = 36.0,
        parent=None,
    ) -> None:
        super().__init__(parent)

        # Identity
        self.label: str = label
        self.mapped_column: str = ""
        self.is_unique: bool = False

        # Typography
        self.font_family: str = "Segoe UI"
        self.font_size: int = 12
        self.color: str = "#000000"
        self.bold: bool = False
        self.italic: bool = False
        self.underline: bool = False
        self.multiline: bool = False
        self.alignment: str = "Left"     # "Left" | "Center" | "Right"
        self.v_alignment: str = "Top"    # "Top" | "Middle" | "Bottom"

        # Geometry (local coordinates)
        self._width: float = max(60.0, width)
        self._height: float = max(20.0, height)

        # Resize-drag state
        self._resizing: bool = False
        self._resize_origin: QPointF = QPointF()
        self._resize_start_w: float = self._width
        self._resize_start_h: float = self._height

        self.setPos(x, y)
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.setZValue(1)

    # ------------------------------------------------------------------
    # QGraphicsItem interface
    # ------------------------------------------------------------------

    def boundingRect(self) -> QRectF:
        return QRectF(-1.0, -1.0, self._width + 2.0, self._height + 2.0)

    def paint(self, painter, option, widget=None) -> None:  # noqa: ARG002
        painter.save()

        rect = QRectF(0.0, 0.0, self._width, self._height)
        selected = self.isSelected()

        # ── Text ────────────────────────────────────────────────────────
        font = QFont(self.font_family, self.font_size)
        font.setBold(self.bold)
        font.setItalic(self.italic)
        font.setUnderline(self.underline)
        painter.setFont(font)
        painter.setPen(QColor(self.color))

        align_h_flags = {
            "Left"  : Qt.AlignmentFlag.AlignLeft,
            "Center": Qt.AlignmentFlag.AlignHCenter,
            "Right" : Qt.AlignmentFlag.AlignRight,
        }.get(self.alignment, Qt.AlignmentFlag.AlignLeft)

        align_v_flags = {
            "Top"   : Qt.AlignmentFlag.AlignTop,
            "Middle": Qt.AlignmentFlag.AlignVCenter,
            "Bottom": Qt.AlignmentFlag.AlignBottom,
        }.get(self.v_alignment, Qt.AlignmentFlag.AlignTop)

        prefix = "[★ Unique] " if self.is_unique else ""
        col_name = self.mapped_column or self.label
        display = f"{prefix}{{{{{col_name}}}}}"

        if self.multiline:
            flags = align_h_flags | align_v_flags | Qt.TextFlag.TextWordWrap
        else:
            flags = align_h_flags | align_v_flags

        painter.drawText(rect, flags, display)

        # ── Selection chrome ─────────────────────────────────────────────
        if selected:
            pen = QPen(QColor("#4f7ef8"), 1.5, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect.adjusted(0.5, 0.5, -0.5, -0.5))

            # Resize handle: solid blue square at bottom-right
            hs = float(self.HANDLE_SIZE)
            painter.fillRect(
                QRectF(self._width - hs, self._height - hs, hs, hs),
                QColor("#4f7ef8"),
            )

        painter.restore()

    # ------------------------------------------------------------------
    # Mouse events (move OR resize)
    # ------------------------------------------------------------------

    def mousePressEvent(self, event) -> None:
        if self.isSelected() and self._on_handle(event.pos()):
            self._resizing = True
            self._resize_origin = event.pos()
            self._resize_start_w = self._width
            self._resize_start_h = self._height
            event.accept()
        else:
            self._resizing = False
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._resizing:
            delta = event.pos() - self._resize_origin
            self.prepareGeometryChange()
            self._width  = max(60.0,  self._resize_start_w + delta.x())
            self._height = max(20.0,  self._resize_start_h + delta.y())
            self.update()
            self.geometry_changed.emit(self._width, self._height)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._resizing = False
        super().mouseReleaseEvent(event)

    # ------------------------------------------------------------------
    # Hover (cursor changes)
    # ------------------------------------------------------------------

    def hoverMoveEvent(self, event) -> None:
        if self.isSelected() and self._on_handle(event.pos()):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        else:
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        self.unsetCursor()
        super().hoverLeaveEvent(event)

    # ------------------------------------------------------------------
    # Item change (signals on position/selection change)
    # ------------------------------------------------------------------

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            p = self.pos()
            self.position_changed.emit(p.x(), p.y())
        return super().itemChange(change, value)

    # ------------------------------------------------------------------
    # Property setters (each triggers a repaint)
    # ------------------------------------------------------------------

    def set_label(self, label: str) -> None:
        self.label = label
        self.update()

    def set_mapped_column(self, col: str) -> None:
        self.mapped_column = col
        self.update()

    def set_is_unique(self, is_unique: bool) -> None:
        self.is_unique = is_unique
        self.update()

    def set_font_family(self, family: str) -> None:
        self.font_family = family
        self.update()

    def set_font_size(self, size: int) -> None:
        self.font_size = max(6, size)
        self.update()

    def set_color(self, hex_color: str) -> None:
        self.color = hex_color
        self.update()

    def set_bold(self, bold: bool) -> None:
        self.bold = bold
        self.update()

    def set_italic(self, italic: bool) -> None:
        self.italic = italic
        self.update()

    def set_underline(self, underline: bool) -> None:
        self.underline = underline
        self.update()

    def set_multiline(self, multiline: bool) -> None:
        self.multiline = multiline
        self.update()

    def set_alignment(self, align: str) -> None:
        if align in ("Left", "Center", "Right"):
            self.alignment = align
            self.update()

    def set_v_alignment(self, v_align: str) -> None:
        if v_align in ("Top", "Middle", "Bottom"):
            self.v_alignment = v_align
            self.update()

    def set_field_size(self, w: float, h: float) -> None:
        self.prepareGeometryChange()
        self._width  = max(60.0, float(w))
        self._height = max(20.0, float(h))
        self.update()

    @property
    def width(self) -> float:
        return self._width

    @property
    def height(self) -> float:
        return self._height

    # ------------------------------------------------------------------
    # JSON serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        p = self.pos()
        return {
            "label"        : self.label,
            "mapped_column": self.mapped_column,
            "is_unique"    : self.is_unique,
            "x"            : round(p.x(), 2),
            "y"            : round(p.y(), 2),
            "width"        : round(self._width, 2),
            "height"       : round(self._height, 2),
            "font_family"  : self.font_family,
            "font_size"    : self.font_size,
            "color"        : self.color,
            "bold"         : self.bold,
            "italic"       : self.italic,
            "underline"    : self.underline,
            "multiline"    : self.multiline,
            "alignment"    : self.alignment,
            "v_alignment"  : self.v_alignment,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "FieldItem":
        item = cls(
            label  = d.get("label",  "Field"),
            x      = d.get("x",      100.0),
            y      = d.get("y",      100.0),
            width  = d.get("width",  200.0),
            height = d.get("height",  36.0),
        )
        item.mapped_column = d.get("mapped_column", "")
        item.is_unique     = d.get("is_unique",     False)
        item.font_family   = d.get("font_family",   "Segoe UI")
        item.font_size     = d.get("font_size",      12)
        item.color         = d.get("color",          "#000000")
        item.bold          = d.get("bold",           False)
        item.italic        = d.get("italic",         False)
        item.underline     = d.get("underline",      False)
        item.multiline     = d.get("multiline",      False)
        item.alignment     = d.get("alignment",      "Left")
        item.v_alignment   = d.get("v_alignment",    "Top")
        return item

    def _on_handle(self, pos: QPointF) -> bool:
        hs = float(self.HANDLE_SIZE)
        return QRectF(self._width - hs, self._height - hs, hs, hs).contains(pos)
