"""
ui/widgets/qr_item.py
QRItem - Draggable, resizable QR code placeholder on the template canvas.

Features:
- Visual QR pattern placeholder box with "🔲 QR Code" label and a tiny pixel grid preview.
- Configurable token-based payload string (e.g. "ID:[Enrollment number] Name:[Name]").
- Configurable QR border (margin cells inside QR standard border).
- Configurable QR box size for rendering resolution.
- Undo/Redo integration via geometry change signals.
- Full JSON serialization (to_dict / from_dict).
"""
from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsObject


# Default QR payload template tokens
DEFAULT_QR_PAYLOAD = "ID:[Enrollment number] | Name:[Name]"


class QRItem(QGraphicsObject):
    """Draggable, resizable QR code placeholder on the QGraphicsScene."""

    position_changed = pyqtSignal(float, float)
    geometry_changed = pyqtSignal(float, float)
    move_committed   = pyqtSignal(object, QPointF, QPointF)
    resize_committed = pyqtSignal(object, float, float, float, float)

    HANDLE_SIZE: int = 10   # px – resize handle square side length
    ITEM_TYPE:   str = "qr"

    def __init__(
        self,
        label: str = "QR Code",
        x: float = 100.0,
        y: float = 100.0,
        width: float = 80.0,
        height: float = 80.0,
        qr_payload: str = DEFAULT_QR_PAYLOAD,
        border_cells: int = 1,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.label: str = label
        self.qr_payload: str = qr_payload
        self.border_cells: int = max(0, int(border_cells))

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
        h = self.HANDLE_SIZE
        return QRectF(-h * 0.5, -h * 0.5, self._width + h, self._height + h)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        w, h = self._width, self._height
        rect = QRectF(0, 0, w, h)

        is_selected = self.isSelected()

        # Background
        bg_color = QColor("#ecfdf5") if not is_selected else QColor("#d1fae5")
        painter.setBrush(QBrush(bg_color))
        border_pen = QPen(
            QColor("#10b981") if is_selected else QColor("#6ee7b7"),
            1.5 if not is_selected else 2.0,
            Qt.PenStyle.SolidLine,
        )
        painter.setPen(border_pen)
        painter.drawRoundedRect(rect, 4, 4)

        # Draw a tiny QR grid preview (3×3 finder pattern hints)
        grid_margin = max(4.0, w * 0.08)
        inner_x = grid_margin
        inner_y = grid_margin + 14  # leave space for label
        inner_w = w - grid_margin * 2
        inner_h = h - grid_margin * 2 - 14

        if inner_w > 10 and inner_h > 8:
            cell = min(inner_w, inner_h) / 7.0
            painter.setPen(Qt.PenStyle.NoPen)

            # Draw a simplified 3-corner finder pattern representation
            for corner_x, corner_y in [(inner_x, inner_y + 14),
                                        (inner_x + inner_w - cell * 3, inner_y + 14),
                                        (inner_x, inner_y + inner_h - cell * 3 + 14)]:
                # Outer square
                painter.setBrush(QBrush(QColor("#065f46")))
                painter.drawRect(QRectF(corner_x, corner_y, cell * 3, cell * 3))
                # White inner
                painter.setBrush(QBrush(QColor("#ecfdf5")))
                painter.drawRect(QRectF(corner_x + cell * 0.5, corner_y + cell * 0.5,
                                        cell * 2, cell * 2))
                # Inner dot
                painter.setBrush(QBrush(QColor("#065f46")))
                painter.drawRect(QRectF(corner_x + cell, corner_y + cell, cell, cell))

            # Draw a few scattered data cells (impression)
            data_cells = [(3, 1), (4, 2), (3, 3), (5, 1), (4, 4), (5, 3), (6, 5), (3, 5)]
            for col, row in data_cells:
                cx_ = inner_x + col * cell
                cy_ = inner_y + row * cell + 14
                if cx_ + cell < inner_x + inner_w and cy_ + cell < inner_y + inner_h + 14:
                    painter.setBrush(QBrush(QColor("#065f46")))
                    painter.drawRect(QRectF(cx_, cy_, cell * 0.8, cell * 0.8))

        # Label
        painter.setPen(QPen(QColor("#065f46")))
        font = QFont("Segoe UI", max(6, int(w / 12)))
        font.setBold(True)
        painter.setFont(font)
        label_rect = QRectF(2, 2, w - 4, 13)
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         f"🔲 {self.label}")

        # Resize handle (bottom-right)
        hr = self._handle_rect()
        painter.setBrush(QBrush(QColor("#10b981")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(hr)

    # ── Geometry ───────────────────────────────────────────────────────────────

    def set_field_size(self, w: float, h: float) -> None:
        self.prepareGeometryChange()
        self._width = max(30.0, w)
        self._height = max(30.0, h)
        self.update()
        self.geometry_changed.emit(self._width, self._height)

    def set_snap_to_grid(self, enabled: bool, grid_size: float = 10.0) -> None:
        self.snap_to_grid = enabled
        self.grid_size = grid_size

    def _snap(self, v: float) -> float:
        if self.snap_to_grid and self.grid_size > 0:
            return round(v / self.grid_size) * self.grid_size
        return v

    # ── Property setters ──────────────────────────────────────────────────────

    @property
    def qr_payload_template(self) -> str:
        return self.qr_payload

    @qr_payload_template.setter
    def qr_payload_template(self, payload: str) -> None:
        self.set_qr_payload(payload)

    def set_qr_payload(self, payload: str) -> None:
        self.qr_payload = payload
        self.update()

    def set_qr_payload_template(self, payload: str) -> None:
        self.set_qr_payload(payload)

    def set_border_cells(self, cells: int) -> None:
        self.border_cells = max(0, int(cells))
        self.update()

    def set_label(self, label: str) -> None:
        self.label = label
        self.update()

    # ── Mouse events ──────────────────────────────────────────────────────────

    def _handle_rect(self) -> QRectF:
        h = self.HANDLE_SIZE
        return QRectF(self._width - h, self._height - h, h, h)

    def hoverMoveEvent(self, event) -> None:
        if self._handle_rect().contains(event.pos()):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        else:
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._handle_rect().contains(event.pos()):
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
            new_w = self._snap(max(30.0, self._resize_start_w + delta.x()))
            new_h = self._snap(max(30.0, self._resize_start_h + delta.y()))
            self.prepareGeometryChange()
            self._width = new_w
            self._height = new_h
            self.update()
            self.geometry_changed.emit(new_w, new_h)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._resizing and event.button() == Qt.MouseButton.LeftButton:
            self._resizing = False
            self.resize_committed.emit(
                self,
                self._resize_start_w, self._resize_start_h,
                self._width, self._height,
            )
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged and not self._resizing:
            p = self.pos()
            self.position_changed.emit(p.x(), p.y())
        return super().itemChange(change, value)

    def mouseDoubleClickEvent(self, event) -> None:
        # Store old position before move for undo commit
        self._pre_move_pos = self.pos()
        super().mouseDoubleClickEvent(event)

    def _commit_move(self, old_pos: QPointF) -> None:
        self.move_committed.emit(self, old_pos, self.pos())

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "item_type"           : "qr",
            "label"               : self.label,
            "qr_payload"          : self.qr_payload,
            "qr_payload_template" : self.qr_payload,
            "border_cells"        : self.border_cells,
            "x"                   : round(self.pos().x(), 2),
            "y"                   : round(self.pos().y(), 2),
            "width"               : round(self._width, 2),
            "height"              : round(self._height, 2),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "QRItem":
        return cls(
            label         = d.get("label", "QR Code"),
            x             = float(d.get("x", 100.0)),
            y             = float(d.get("y", 100.0)),
            width         = float(d.get("width", 80.0)),
            height        = float(d.get("height", 80.0)),
            qr_payload    = d.get("qr_payload_template", d.get("qr_payload", DEFAULT_QR_PAYLOAD)),
            border_cells  = int(d.get("border_cells", 1)),
        )

