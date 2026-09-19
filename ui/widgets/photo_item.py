"""
ui/widgets/photo_item.py
PhotoItem - Draggable, resizable student photo placeholder on the template canvas.

Features:
- Visual passport photo placeholder frame with avatar silhouette & mapped ID column indicator.
- Draggable & resizable with bottom-right corner handles.
- Configurable photo ID column mapping (e.g., 'Enrollment number', 'Roll No', or 'ID').
- Border and corner radius styling.
- Undo/Redo integration via geometry change signals.
- Full JSON serialization (to_dict / from_dict).
"""
from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsObject


class PhotoItem(QGraphicsObject):
    """Draggable, resizable student photo placeholder on the QGraphicsScene."""

    position_changed = pyqtSignal(float, float)
    geometry_changed = pyqtSignal(float, float)
    move_committed   = pyqtSignal(object, QPointF, QPointF)
    resize_committed = pyqtSignal(object, float, float, float, float)

    HANDLE_SIZE: int = 10   # px – resize handle square side length
    ITEM_TYPE:   str = "photo"

    def __init__(
        self,
        label: str = "Student Photo",
        x: float = 100.0,
        y: float = 100.0,
        width: float = 90.0,
        height: float = 110.0,
        photo_id_column: str = "",
        border_color: str = "#6b7280",
        border_width: float = 1.0,
        corner_radius: float = 4.0,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.label: str = label
        self.photo_id_column: str = photo_id_column

        # Visual styling
        self.border_color: str = border_color
        self.border_width: float = max(0.0, float(border_width))
        self.corner_radius: float = max(0.0, float(corner_radius))
        self.show_border: bool = True

        # Geometry
        self._width: float = max(30.0, width)
        self._height: float = max(30.0, height)

        # Resize-drag state
        self._resizing: bool = False
        self._resize_origin: QPointF = QPointF()
        self._resize_start_w: float = self._width
        self._resize_start_h: float = self._height

        # Snap to grid
        self.snap_to_grid: bool = True
        self.grid_size: float = 10.0

        self.setPos(x, y)
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.setZValue(2)

    # ── QGraphicsItem interface ────────────────────────────────────────────────

    def boundingRect(self) -> QRectF:
        return QRectF(-2.0, -2.0, self._width + 4.0, self._height + 4.0)

    def paint(self, painter: QPainter, option, widget=None) -> None:  # noqa: ARG002
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(0.0, 0.0, self._width, self._height)
        selected = self.isSelected()

        # Background fill (clean neutral photo card)
        bg_color = QColor("#f3f4f6") if not selected else QColor("#eff6ff")
        painter.setBrush(QBrush(bg_color))
        pen_color = QColor("#3b82f6") if selected else QColor(self.border_color)
        pen_width = 2.0 if selected else self.border_width
        painter.setPen(QPen(pen_color, pen_width))
        painter.drawRoundedRect(rect, self.corner_radius, self.corner_radius)

        # Inner subtle dash border when unselected
        if not selected:
            inner_rect = rect.adjusted(3, 3, -3, -3)
            dash_pen = QPen(QColor("#d1d5db"), 1.0, Qt.PenStyle.DashLine)
            painter.setPen(dash_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(inner_rect, max(0.0, self.corner_radius - 2), max(0.0, self.corner_radius - 2))

        # Avatar silhouette & icon
        cx = self._width / 2.0
        cy = self._height * 0.38
        head_radius = min(self._width, self._height) * 0.16

        # Silhouette head
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#9ca3af") if not selected else QColor("#60a5fa")))
        painter.drawEllipse(QPointF(cx, cy), head_radius, head_radius)

        # Silhouette shoulders
        shoulders_rect = QRectF(cx - head_radius * 1.6, cy + head_radius * 0.9, head_radius * 3.2, head_radius * 1.8)
        painter.drawChord(shoulders_rect, 0, 180 * 16)

        # Labels
        # Header / Type
        painter.setPen(QColor("#1e293b") if not selected else QColor("#1e40af"))
        font_main = QFont("Segoe UI", 9, QFont.Weight.Bold)
        painter.setFont(font_main)
        painter.drawText(
            QRectF(4, self._height * 0.65, self._width - 8, 16),
            Qt.AlignmentFlag.AlignCenter,
            "📷 Photo",
        )

        # ID Mapping info
        mapped_text = f"ID: [{self.photo_id_column}]" if self.photo_id_column else "ID: [Auto]"
        font_sub = QFont("Segoe UI", 8)
        painter.setFont(font_sub)
        painter.setPen(QColor("#64748b"))
        painter.drawText(
            QRectF(2, self._height * 0.80, self._width - 4, 16),
            Qt.AlignmentFlag.AlignCenter,
            mapped_text,
        )

        # Resize handle
        if selected:
            hs = float(self.HANDLE_SIZE)
            handle_rect = QRectF(self._width - hs, self._height - hs, hs, hs)
            painter.setBrush(QBrush(QColor("#2563eb")))
            painter.setPen(QPen(QColor("#ffffff"), 1.5))
            painter.drawRect(handle_rect)

        painter.restore()

    # ── Mouse Interaction ─────────────────────────────────────────────────────

    def hoverMoveEvent(self, event) -> None:
        if self._on_handle(event.pos()) and self.isSelected():
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        else:
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._move_origin = self.pos()
            if self.isSelected() and self._on_handle(event.pos()):
                self._resizing = True
                self._resize_origin = event.scenePos()
                self._resize_start_w = self._width
                self._resize_start_h = self._height
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._resizing:
            delta = event.scenePos() - self._resize_origin
            new_w = max(30.0, self._resize_start_w + delta.x())
            new_h = max(30.0, self._resize_start_h + delta.y())

            if self.snap_to_grid and self.grid_size > 0:
                new_w = round(new_w / self.grid_size) * self.grid_size
                new_h = round(new_h / self.grid_size) * self.grid_size

            self.prepareGeometryChange()
            self._width = max(30.0, new_w)
            self._height = max(30.0, new_h)
            self.update()
            self.geometry_changed.emit(self._width, self._height)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._resizing:
            self._resizing = False
            self.resize_committed.emit(
                self, self._resize_start_w, self._resize_start_h, self._width, self._height
            )
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            if hasattr(self, "_move_origin") and self.pos() != self._move_origin:
                self.move_committed.emit(self, self._move_origin, self.pos())
        super().mouseReleaseEvent(event)

    def set_snap_to_grid(self, enabled: bool, step: float = 10.0) -> None:
        self.snap_to_grid = enabled
        self.grid_size = max(1.0, float(step))

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            new_pos = value
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

    def set_photo_id_column(self, col: str) -> None:
        self.photo_id_column = str(col or "").strip()
        self.update()

    def set_border_color(self, hex_color: str) -> None:
        self.border_color = str(hex_color or "#6b7280")
        self.update()

    def set_border_width(self, width: float) -> None:
        self.border_width = max(0.0, float(width))
        self.update()

    def set_corner_radius(self, radius: float) -> None:
        self.corner_radius = max(0.0, float(radius))
        self.update()

    def set_field_size(self, w: float, h: float) -> None:
        self.prepareGeometryChange()
        self._width = max(30.0, float(w))
        self._height = max(30.0, float(h))
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
            "item_type": self.ITEM_TYPE,
            "label": self.label,
            "photo_id_column": self.photo_id_column,
            "border_color": self.border_color,
            "border_width": self.border_width,
            "corner_radius": self.corner_radius,
            "x": round(p.x(), 2),
            "y": round(p.y(), 2),
            "width": round(self._width, 2),
            "height": round(self._height, 2),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PhotoItem":
        item = cls(
            label=d.get("label", "Student Photo"),
            x=d.get("x", 100.0),
            y=d.get("y", 100.0),
            width=d.get("width", 90.0),
            height=d.get("height", 110.0),
            photo_id_column=d.get("photo_id_column", ""),
            border_color=d.get("border_color", "#6b7280"),
            border_width=d.get("border_width", 1.0),
            corner_radius=d.get("corner_radius", 4.0),
        )
        return item

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _on_handle(self, pos: QPointF) -> bool:
        hs = float(self.HANDLE_SIZE)
        return QRectF(self._width - hs, self._height - hs, hs, hs).contains(pos)

