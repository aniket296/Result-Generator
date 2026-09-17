"""
ChartItem - draggable, resizable performance chart placeholder on the template canvas.

Represents a region where a performance bar chart will be rendered during PDF generation.
Stores the list of Excel columns to include as data series and the chart orientation style.

Supports:
- Label
- Selected chart columns (list of Excel column names)
- Chart style: "vertical" | "horizontal"
- Dynamic Geometry & Drag-Resize Handling (identical to FieldItem)
- Complete JSON Serialization (to_dict / from_dict)
- Mini preview of chart bars in the placeholder area
"""
from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QPen
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsObject


class ChartItem(QGraphicsObject):
    """Draggable, resizable performance chart placeholder on the QGraphicsScene."""

    position_changed = pyqtSignal(float, float)
    geometry_changed = pyqtSignal(float, float)

    HANDLE_SIZE: int = 10   # px – resize handle square side length
    ITEM_TYPE:   str = "chart"

    def __init__(
        self,
        label: str  = "Performance Chart",
        x: float    = 100.0,
        y: float    = 100.0,
        width: float  = 300.0,
        height: float = 200.0,
        parent=None,
    ) -> None:
        super().__init__(parent)

        # Identity & data config
        self.label: str = label
        self.chart_columns: list[str] = []
        self.chart_style: str = "vertical"   # "vertical" | "horizontal"

        # Geometry
        self._width:  float = max(80.0, width)
        self._height: float = max(60.0, height)

        # Resize-drag state
        self._resizing: bool = False
        self._resize_origin: QPointF = QPointF()
        self._resize_start_w: float = self._width
        self._resize_start_h: float = self._height

        # Snap to grid settings
        self.snap_to_grid: bool = True
        self.grid_size: float = 10.0

        self.setPos(x, y)
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.setZValue(1)

    # ── QGraphicsItem interface ────────────────────────────────────────────────

    def boundingRect(self) -> QRectF:
        return QRectF(-1.0, -1.0, self._width + 2.0, self._height + 2.0)

    def paint(self, painter, option, widget=None) -> None:  # noqa: ARG002
        painter.save()

        rect     = QRectF(0.0, 0.0, self._width, self._height)
        selected = self.isSelected()

        # ── Background fill ──────────────────────────────────────────────
        painter.fillRect(rect, QBrush(QColor("#eff6ff")))

        # ── Border ──────────────────────────────────────────────────────
        border_color = QColor("#4f7ef8") if selected else QColor("#93c5fd")
        pen_style    = Qt.PenStyle.SolidLine if selected else Qt.PenStyle.DashLine
        painter.setPen(QPen(border_color, 1.5, pen_style))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(rect.adjusted(0.5, 0.5, -0.5, -0.5))

        # ── Mini bar chart preview ───────────────────────────────────────
        self._draw_preview_bars(painter, rect)

        # ── Label text ──────────────────────────────────────────────────
        font = QFont("Segoe UI", 9)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor("#1d4ed8"))
        col_count = len(self.chart_columns)
        col_text  = f"{col_count} column{'s' if col_count != 1 else ''}" if col_count else "no columns selected"
        label_txt = f"📊 {self.label}\n[{col_text}]"
        painter.drawText(
            rect.adjusted(6, 4, -6, -4),
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
            label_txt,
        )

        # ── Resize handle ────────────────────────────────────────────────
        if selected:
            hs = float(self.HANDLE_SIZE)
            painter.fillRect(
                QRectF(self._width - hs, self._height - hs, hs, hs),
                QColor("#4f7ef8"),
            )

        painter.restore()

    def _draw_preview_bars(self, painter, rect: QRectF) -> None:
        """Draw a tiny representative bar chart inside the placeholder."""
        n = min(max(len(self.chart_columns), 3), 8) if self.chart_columns else 5

        margin_l = 14
        margin_r = 8
        margin_t = 36   # leave room for label above
        margin_b = 12

        inner_w = rect.width()  - margin_l - margin_r
        inner_h = rect.height() - margin_t - margin_b
        if inner_w < 20 or inner_h < 10:
            return

        # Static sample normalised heights (0–1)
        _SAMPLE = [0.85, 0.60, 0.75, 0.50, 0.90, 0.40, 0.70, 0.55]
        gap = 3

        if self.chart_style == "horizontal":
            bar_h = max(2.0, (inner_h - gap * (n - 1)) / n)
            for i in range(n):
                bw  = inner_w * _SAMPLE[i % len(_SAMPLE)]
                bx  = rect.left() + margin_l
                by  = rect.top()  + margin_t + i * (bar_h + gap)
                col = QColor(79, 126, 248, 170 if i % 2 == 0 else 120)
                painter.fillRect(QRectF(bx, by, bw, bar_h), QBrush(col))
        else:
            bar_w = max(2.0, (inner_w - gap * (n - 1)) / n)
            for i in range(n):
                bh  = inner_h * _SAMPLE[i % len(_SAMPLE)]
                bx  = rect.left() + margin_l + i * (bar_w + gap)
                by  = rect.top()  + margin_t + inner_h - bh
                col = QColor(79, 126, 248, 170 if i % 2 == 0 else 120)
                painter.fillRect(QRectF(bx, by, bar_w, bh), QBrush(col))

    # ── Mouse events ──────────────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        if self.isSelected() and self._on_handle(event.pos()):
            self._resizing = True
            self._resize_origin  = event.pos()
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
            self._width  = max(80.0, self._resize_start_w + delta.x())
            self._height = max(60.0, self._resize_start_h + delta.y())
            self.update()
            self.geometry_changed.emit(self._width, self._height)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._resizing = False
        super().mouseReleaseEvent(event)

    # ── Hover ─────────────────────────────────────────────────────────────────

    def hoverMoveEvent(self, event) -> None:
        if self.isSelected() and self._on_handle(event.pos()):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        else:
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        self.unsetCursor()
        super().hoverLeaveEvent(event)

    # ── Item change ───────────────────────────────────────────────────────────

    def set_snap_to_grid(self, enabled: bool, step: float = 10.0) -> None:
        """Configure magnetic snap-to-grid alignment and step size."""
        self.snap_to_grid = enabled
        self.grid_size = max(1.0, float(step))

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            new_pos = value  # QPointF
            x = new_pos.x()
            y = new_pos.y()

            if getattr(self, "snap_to_grid", False):
                step = getattr(self, "grid_size", 10.0)
                if step > 0:
                    x = round(x / step) * step
                    y = round(y / step) * step

            if self.scene():
                scene_rect = self.scene().sceneRect()
                max_x = max(0.0, scene_rect.width() - self._width)
                max_y = max(0.0, scene_rect.height() - self._height)
                x = min(max(scene_rect.x(), x), scene_rect.x() + max_x)
                y = min(max(scene_rect.y(), y), scene_rect.y() + max_y)

            return QPointF(x, y)
        elif change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            p = self.pos()
            self.position_changed.emit(p.x(), p.y())
        return super().itemChange(change, value)

    # ── Property setters ──────────────────────────────────────────────────────

    def set_chart_columns(self, columns: list[str]) -> None:
        self.chart_columns = list(columns)
        self.update()

    def set_chart_style(self, style: str) -> None:
        if style in ("vertical", "horizontal"):
            self.chart_style = style
            self.update()

    def set_field_size(self, w: float, h: float) -> None:
        """Shared geometry setter — same API as FieldItem."""
        self.prepareGeometryChange()
        self._width  = max(80.0,  float(w))
        self._height = max(60.0, float(h))
        self.update()

    @property
    def width(self) -> float:
        return self._width

    @property
    def height(self) -> float:
        return self._height

    # ── JSON serialization ────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        p = self.pos()
        return {
            "item_type"    : self.ITEM_TYPE,
            "label"        : self.label,
            "chart_columns": list(self.chart_columns),
            "chart_style"  : self.chart_style,
            "x"            : round(p.x(), 2),
            "y"            : round(p.y(), 2),
            "width"        : round(self._width, 2),
            "height"       : round(self._height, 2),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ChartItem":
        item = cls(
            label  = d.get("label",  "Performance Chart"),
            x      = d.get("x",      100.0),
            y      = d.get("y",      100.0),
            width  = d.get("width",  300.0),
            height = d.get("height", 200.0),
        )
        item.chart_columns = list(d.get("chart_columns", []))
        item.chart_style   = d.get("chart_style", "vertical")
        return item

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _on_handle(self, pos: QPointF) -> bool:
        hs = float(self.HANDLE_SIZE)
        return QRectF(self._width - hs, self._height - hs, hs, hs).contains(pos)

