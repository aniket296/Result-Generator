"""
FieldItem - draggable, resizable text placeholder on the template canvas.

Each instance represents one text field that will be filled with a value
from a mapped Excel column during result generation.  At design time it
displays  {{ColumnName}}  over the background image so the teacher can
position it precisely.

Resize: blue square handle at bottom-right corner (drag to resize).
Move  : drag anywhere else on the item body.
"""
from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPen
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsObject


class FieldItem(QGraphicsObject):
    """Draggable, resizable text placeholder on the QGraphicsScene."""

    # Emitted whenever the item moves (drag or setX/setY).
    position_changed = pyqtSignal(float, float)
    # Emitted during resize-handle drag so the panel can update W/H spinboxes.
    geometry_changed = pyqtSignal(float, float)

    HANDLE_SIZE: int = 10   # px – resize handle square side length

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

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

        # Typography
        self.font_family: str = "Segoe UI"
        self.font_size: int = 12
        self.color: str = "#000000"
        self.bold: bool = False
        self.italic: bool = False
        self.alignment: str = "Left"   # "Left" | "Center" | "Right"

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
        # +1 px margin so the dashed selection border is not clipped
        return QRectF(-1.0, -1.0, self._width + 2.0, self._height + 2.0)

    def paint(self, painter, option, widget=None) -> None:  # noqa: ARG002
        painter.save()

        rect = QRectF(0.0, 0.0, self._width, self._height)
        selected = self.isSelected()

        # ── Text ────────────────────────────────────────────────────────
        font = QFont(self.font_family, self.font_size)
        font.setBold(self.bold)
        font.setItalic(self.italic)
        painter.setFont(font)
        painter.setPen(QColor(self.color))

        align_h = {
            "Left"  : Qt.AlignmentFlag.AlignLeft,
            "Center": Qt.AlignmentFlag.AlignHCenter,
            "Right" : Qt.AlignmentFlag.AlignRight,
        }.get(self.alignment, Qt.AlignmentFlag.AlignLeft)

        display = "{{" + (self.mapped_column or self.label) + "}}"
        painter.drawText(rect, align_h | Qt.AlignmentFlag.AlignVCenter, display)

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

    def set_label(self, v: str) -> None:
        self.label = v
        self.update()

    def set_mapped_column(self, v: str) -> None:
        self.mapped_column = v
        self.update()

    def set_font_family(self, v: str) -> None:
        self.font_family = v
        self.update()

    def set_font_size(self, v: int) -> None:
        self.font_size = v
        self.update()

    def set_color(self, v: str) -> None:
        self.color = v
        self.update()

    def set_bold(self, v: bool) -> None:
        self.bold = v
        self.update()

    def set_italic(self, v: bool) -> None:
        self.italic = v
        self.update()

    def set_alignment(self, v: str) -> None:
        self.alignment = v
        self.update()

    def set_width(self, w: float) -> None:
        self.prepareGeometryChange()
        self._width = max(60.0, float(w))
        self.update()

    def set_height(self, h: float) -> None:
        self.prepareGeometryChange()
        self._height = max(20.0, float(h))
        self.update()

    # ------------------------------------------------------------------
    # Read-only geometry accessors
    # ------------------------------------------------------------------

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
            "x"            : round(p.x(), 2),
            "y"            : round(p.y(), 2),
            "width"        : round(self._width, 2),
            "height"       : round(self._height, 2),
            "font_family"  : self.font_family,
            "font_size"    : self.font_size,
            "color"        : self.color,
            "bold"         : self.bold,
            "italic"       : self.italic,
            "alignment"    : self.alignment,
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
        item.font_family   = d.get("font_family",   "Segoe UI")
        item.font_size     = d.get("font_size",      12)
        item.color         = d.get("color",          "#000000")
        item.bold          = d.get("bold",           False)
        item.italic        = d.get("italic",         False)
        item.alignment     = d.get("alignment",      "Left")
        return item

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _on_handle(self, pos: QPointF) -> bool:
        """True if pos is inside the resize-handle square."""
        hs = float(self.HANDLE_SIZE)
        return QRectF(self._width - hs, self._height - hs, hs, hs).contains(pos)
