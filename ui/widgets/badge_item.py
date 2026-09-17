"""
BadgeItem - draggable, resizable conditional image badge placeholder on the template canvas.

Represents a region where a badge image (e.g., Gold Medal, Distinction) is stamped
during PDF generation only when the student's data satisfies a defined rule:
    <rule_column> <rule_operator> <rule_value>

Visual preview:
  - Shows the actual badge image scaled to the bounding box when a valid path is set.
  - Falls back to an amber placeholder with a rule-description overlay when no image is loaded.
"""
from __future__ import annotations

import os

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QPen, QPixmap
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsObject


class BadgeItem(QGraphicsObject):
    """Draggable, resizable conditional image badge on the QGraphicsScene."""

    position_changed = pyqtSignal(float, float)
    geometry_changed = pyqtSignal(float, float)

    HANDLE_SIZE: int = 10   # px – resize handle square side length
    ITEM_TYPE:   str = "badge"

    def __init__(
        self,
        label: str    = "Badge",
        x: float      = 100.0,
        y: float      = 100.0,
        width: float  = 100.0,
        height: float = 100.0,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.label: str = label

        # Badge image
        self.badge_image_path: str         = ""
        self._cached_pixmap:   QPixmap | None = None

        # Visibility rule
        self.rule_column:   str = ""
        self.rule_operator: str = ">="
        self.rule_value:    str = "0"

        # Geometry
        self._width:  float = max(20.0, width)
        self._height: float = max(20.0, height)

        # Resize-drag state
        self._resizing:       bool    = False
        self._resize_origin:  QPointF = QPointF()
        self._resize_start_w: float   = self._width
        self._resize_start_h: float   = self._height

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
        self.setZValue(2)   # Above chart items (z=1)

    # ── QGraphicsItem interface ────────────────────────────────────────────────

    def boundingRect(self) -> QRectF:
        return QRectF(-1.0, -1.0, self._width + 2.0, self._height + 2.0)

    def paint(self, painter, option, widget=None) -> None:  # noqa: ARG002
        painter.save()

        rect     = QRectF(0.0, 0.0, self._width, self._height)
        selected = self.isSelected()

        # ── Main content ─────────────────────────────────────────────────
        if self._cached_pixmap and not self._cached_pixmap.isNull():
            # Draw the actual badge image, aspect-ratio preserved and centred
            scaled = self._cached_pixmap.scaled(
                int(self._width),
                int(self._height),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            offset_x = (self._width  - scaled.width())  / 2.0
            offset_y = (self._height - scaled.height()) / 2.0
            painter.drawPixmap(int(offset_x), int(offset_y), scaled)
        else:
            # Amber placeholder background
            painter.fillRect(rect, QBrush(QColor("#fef3c7")))
            font = QFont("Segoe UI", max(7, int(min(self._width, self._height) * 0.14)))
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QColor("#92400e"))
            painter.drawText(
                rect.adjusted(4, 4, -4, -20 if self.rule_column else -4),
                Qt.AlignmentFlag.AlignCenter,
                "[ BADGE ]",
            )

        # ── Rule description overlay (dark strip at bottom) ──────────────
        if self.rule_column and self._height > 28:
            strip_h = 16.0
            strip = QRectF(0.0, self._height - strip_h, self._width, strip_h)
            painter.fillRect(strip, QBrush(QColor(31, 41, 55, 190)))
            rule_font = QFont("Segoe UI", 6)
            painter.setFont(rule_font)
            painter.setPen(QColor("#ffffff"))
            rule_text = f"IF {self.rule_column} {self.rule_operator} {self.rule_value}"
            painter.drawText(
                strip.adjusted(3.0, 0.0, -3.0, 0.0),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                rule_text,
            )

        # ── Border ───────────────────────────────────────────────────────
        border_color = QColor("#4f7ef8") if selected else QColor("#f59e0b")
        pen_style    = Qt.PenStyle.SolidLine if selected else Qt.PenStyle.DashLine
        painter.setPen(QPen(border_color, 1.5, pen_style))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(rect.adjusted(0.5, 0.5, -0.5, -0.5))

        # ── Resize handle ─────────────────────────────────────────────────
        if selected:
            hs = float(self.HANDLE_SIZE)
            painter.fillRect(
                QRectF(self._width - hs, self._height - hs, hs, hs),
                QColor("#4f7ef8"),
            )

        painter.restore()

    # ── Mouse events ──────────────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        if self.isSelected() and self._on_handle(event.pos()):
            self._resizing       = True
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
            self._width  = max(20.0, self._resize_start_w + delta.x())
            self._height = max(20.0, self._resize_start_h + delta.y())
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

    def set_badge_image(self, path: str) -> None:
        """Set the badge image path and cache a QPixmap for canvas preview."""
        self.badge_image_path = path
        if path and os.path.exists(path):
            pix = QPixmap(path)
            self._cached_pixmap = pix if not pix.isNull() else None
        else:
            self._cached_pixmap = None
        self.update()

    def set_rule(self, column: str, operator: str, value: str) -> None:
        self.rule_column   = column
        self.rule_operator = operator
        self.rule_value    = value
        self.update()

    def set_field_size(self, w: float, h: float) -> None:
        """Shared geometry setter — same API as FieldItem and ChartItem."""
        self.prepareGeometryChange()
        self._width  = max(20.0, float(w))
        self._height = max(20.0, float(h))
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
            "item_type"       : self.ITEM_TYPE,
            "label"           : self.label,
            "badge_image_path": self.badge_image_path,
            "rule_column"     : self.rule_column,
            "rule_operator"   : self.rule_operator,
            "rule_value"      : self.rule_value,
            "x"               : round(p.x(), 2),
            "y"               : round(p.y(), 2),
            "width"           : round(self._width,  2),
            "height"          : round(self._height, 2),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BadgeItem":
        item = cls(
            label  = d.get("label",  "Badge"),
            x      = d.get("x",      100.0),
            y      = d.get("y",      100.0),
            width  = d.get("width",  100.0),
            height = d.get("height", 100.0),
        )
        item.set_badge_image(d.get("badge_image_path", ""))  # loads pixmap
        item.rule_column   = d.get("rule_column",   "")
        item.rule_operator = d.get("rule_operator", ">=")
        item.rule_value    = d.get("rule_value",    "0")
        return item

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _on_handle(self, pos: QPointF) -> bool:
        hs = float(self.HANDLE_SIZE)
        return QRectF(self._width - hs, self._height - hs, hs, hs).contains(pos)
