"""
ui/widgets/table_item.py
TableItem - Draggable, resizable Dynamic Subject Table placeholder on the template canvas.

Features:
- Configurable subject columns list (columns checked for subject marks).
- Display options: show Max Marks column, show Grade column.
- Configurable max marks threshold (e.g. 100).
- Configurable styling: Header background, Header text color, Alt row background, Border color.
- Configurable base row height and font size.
- Canvas preview drawing a mock table with header and sample subject rows.
- Full undo/redo integration via move/resize committed signals.
- Full JSON serialization (to_dict / from_dict).
"""
from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsObject


class TableItem(QGraphicsObject):
    """Draggable, resizable Dynamic Subject Table placeholder on the QGraphicsScene."""

    position_changed = pyqtSignal(float, float)
    geometry_changed = pyqtSignal(float, float)
    move_committed   = pyqtSignal(object, QPointF, QPointF)
    resize_committed = pyqtSignal(object, float, float, float, float)

    HANDLE_SIZE: int = 10   # px – resize handle square side length
    ITEM_TYPE:   str = "table"

    def __init__(
        self,
        label: str = "Subject Marks Table",
        x: float = 50.0,
        y: float = 200.0,
        width: float = 400.0,
        height: float = 140.0,
        subject_columns: list[str] | None = None,
        show_max_marks: bool = True,
        show_grade: bool = True,
        max_marks: float = 100.0,
        row_height: float = 22.0,
        font_size: int = 9,
        header_bg: str = "#1e3a8a",
        header_color: str = "#ffffff",
        alt_row_bg: str = "#f8fafc",
        border_color: str = "#cbd5e1",
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.label: str = label
        self.subject_columns: list[str] = list(subject_columns or [])
        self.show_max_marks: bool = show_max_marks
        self.show_grade: bool = show_grade
        self.max_marks: float = max_marks
        self.row_height: float = max(12.0, float(row_height))
        self.font_size: int = max(6, int(font_size))
        self.header_bg: str = header_bg
        self.header_color: str = header_color
        self.alt_row_bg: str = alt_row_bg
        self.border_color: str = border_color

        # Geometry
        self._width: float = max(150.0, width)
        self._height: float = max(60.0, height)

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
        self.setZValue(1)

    # ── QGraphicsItem interface ────────────────────────────────────────────────

    def boundingRect(self) -> QRectF:
        h = self.HANDLE_SIZE
        return QRectF(-h * 0.5, -h * 0.5, self._width + h, self._height + h)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        w, h = self._width, self._height
        is_selected = self.isSelected()

        # Outer border / selection indicator
        frame_rect = QRectF(0, 0, w, h)
        if is_selected:
            sel_pen = QPen(QColor("#6366f1"), 2.0, Qt.PenStyle.SolidLine)
            painter.setPen(sel_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(frame_rect)

        # Columns to draw in preview
        col_headers = ["Subject", "Marks"]
        col_shares = [0.55, 0.45]
        if self.show_max_marks and self.show_grade:
            col_headers = ["Subject", "Marks", "Max", "Grade"]
            col_shares = [0.42, 0.20, 0.18, 0.20]
        elif self.show_max_marks:
            col_headers = ["Subject", "Marks", "Max"]
            col_shares = [0.50, 0.25, 0.25]
        elif self.show_grade:
            col_headers = ["Subject", "Marks", "Grade"]
            col_shares = [0.50, 0.25, 0.25]

        header_h = min(h * 0.35, max(18.0, self.row_height * 1.1))

        # 1. Draw Header
        curr_x = 0.0
        for i, (title, share) in enumerate(zip(col_headers, col_shares)):
            col_w = w * share if i < len(col_headers) - 1 else (w - curr_x)
            cell_rect = QRectF(curr_x, 0.0, col_w, header_h)

            painter.setBrush(QBrush(QColor(self.header_bg)))
            painter.setPen(QPen(QColor(self.border_color), 1.0))
            painter.drawRect(cell_rect)

            painter.setPen(QPen(QColor(self.header_color)))
            font = QFont("Segoe UI", max(6, int(self.font_size)))
            font.setBold(True)
            painter.setFont(font)
            align = Qt.AlignmentFlag.AlignLeft if i == 0 else Qt.AlignmentFlag.AlignCenter
            text_rect = cell_rect.adjusted(6, 0, -4, 0) if i == 0 else cell_rect
            painter.drawText(text_rect, align | Qt.AlignmentFlag.AlignVCenter, title)

            curr_x += col_w

        # 2. Draw Sample Preview Rows
        sample_rows = [
            ("Mathematics", "95", "100", "A1"),
            ("Science", "88", "100", "A2"),
            ("English", "92", "100", "A1"),
            ("Social Studies", "84", "100", "B1"),
        ]

        curr_y = header_h
        row_h = self.row_height
        for r_idx, row_vals in enumerate(sample_rows):
            if curr_y + row_h > h:
                break

            bg_col = QColor(self.alt_row_bg) if r_idx % 2 == 1 else QColor("#ffffff")
            curr_x = 0.0

            # Match values to columns
            vals = [row_vals[0], row_vals[1]]
            if self.show_max_marks and self.show_grade:
                vals = [row_vals[0], row_vals[1], row_vals[2], row_vals[3]]
            elif self.show_max_marks:
                vals = [row_vals[0], row_vals[1], row_vals[2]]
            elif self.show_grade:
                vals = [row_vals[0], row_vals[1], row_vals[3]]

            for c_idx, (val, share) in enumerate(zip(vals, col_shares)):
                col_w = w * share if c_idx < len(col_shares) - 1 else (w - curr_x)
                cell_rect = QRectF(curr_x, curr_y, col_w, row_h)

                painter.setBrush(QBrush(bg_col))
                painter.setPen(QPen(QColor(self.border_color), 0.75))
                painter.drawRect(cell_rect)

                painter.setPen(QPen(QColor("#334155")))
                font = QFont("Segoe UI", max(6, int(self.font_size - 0.5)))
                font.setBold(False)
                painter.setFont(font)
                align = Qt.AlignmentFlag.AlignLeft if c_idx == 0 else Qt.AlignmentFlag.AlignCenter
                text_rect = cell_rect.adjusted(6, 0, -4, 0) if c_idx == 0 else cell_rect
                painter.drawText(text_rect, align | Qt.AlignmentFlag.AlignVCenter, val)

                curr_x += col_w

            curr_y += row_h

        # Label watermark at bottom left
        painter.setPen(QPen(QColor("#64748b")))
        font_lbl = QFont("Segoe UI", 7)
        font_lbl.setItalic(True)
        painter.setFont(font_lbl)
        painter.drawText(QRectF(4, h - 14, w - 18, 12), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         f"📋 {self.label} (Dynamic variable rows)")

        # Resize handle (bottom-right)
        hr = self._handle_rect()
        painter.setBrush(QBrush(QColor("#6366f1")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(hr)

    # ── Geometry ───────────────────────────────────────────────────────────────

    def set_field_size(self, w: float, h: float) -> None:
        self.prepareGeometryChange()
        self._width = max(150.0, w)
        self._height = max(60.0, h)
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

    def set_label(self, label: str) -> None:
        self.label = label
        self.update()

    def set_subject_columns(self, columns: list[str]) -> None:
        self.subject_columns = list(columns)
        self.update()

    def set_show_max_marks(self, show: bool) -> None:
        self.show_max_marks = bool(show)
        self.update()

    def set_show_grade(self, show: bool) -> None:
        self.show_grade = bool(show)
        self.update()

    def set_max_marks(self, val: float) -> None:
        self.max_marks = max(1.0, float(val))
        self.update()

    def set_row_height(self, h: float) -> None:
        self.row_height = max(12.0, float(h))
        self.update()

    def set_font_size(self, sz: int) -> None:
        self.font_size = max(6, int(sz))
        self.update()

    def set_header_bg(self, color_hex: str) -> None:
        self.header_bg = color_hex
        self.update()

    def set_header_color(self, color_hex: str) -> None:
        self.header_color = color_hex
        self.update()

    def set_alt_row_bg(self, color_hex: str) -> None:
        self.alt_row_bg = color_hex
        self.update()

    def set_border_color(self, color_hex: str) -> None:
        self.border_color = color_hex
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
            new_w = self._snap(max(150.0, self._resize_start_w + delta.x()))
            new_h = self._snap(max(60.0, self._resize_start_h + delta.y()))
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

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "item_type"       : "table",
            "label"           : self.label,
            "subject_columns" : list(self.subject_columns),
            "show_max_marks"  : self.show_max_marks,
            "show_grade"      : self.show_grade,
            "max_marks"       : self.max_marks,
            "row_height"      : self.row_height,
            "font_size"       : self.font_size,
            "header_bg"       : self.header_bg,
            "header_color"    : self.header_color,
            "alt_row_bg"      : self.alt_row_bg,
            "border_color"    : self.border_color,
            "x"               : round(self.pos().x(), 2),
            "y"               : round(self.pos().y(), 2),
            "width"           : round(self._width, 2),
            "height"          : round(self._height, 2),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TableItem":
        return cls(
            label           = d.get("label", "Subject Marks Table"),
            x               = float(d.get("x", 50.0)),
            y               = float(d.get("y", 200.0)),
            width           = float(d.get("width", 400.0)),
            height          = float(d.get("height", 140.0)),
            subject_columns = d.get("subject_columns", []),
            show_max_marks  = bool(d.get("show_max_marks", True)),
            show_grade      = bool(d.get("show_grade", True)),
            max_marks       = float(d.get("max_marks", 100.0)),
            row_height      = float(d.get("row_height", 22.0)),
            font_size       = int(d.get("font_size", 9)),
            header_bg       = d.get("header_bg", "#1e3a8a"),
            header_color    = d.get("header_color", "#ffffff"),
            alt_row_bg      = d.get("alt_row_bg", "#f8fafc"),
            border_color    = d.get("border_color", "#cbd5e1"),
        )

