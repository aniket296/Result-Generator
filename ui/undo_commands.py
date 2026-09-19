"""
ui/undo_commands.py
QUndoCommand subclasses for Template Editor Undo/Redo operations.

Includes:
- MoveItemCommand: Single item drag/move.
- MoveMultipleItemsCommand: Multi-item alignment/distribution moves.
- AddItemCommand: Adding field, chart, or badge items.
- DeleteItemCommand: Removing field, chart, or badge items.
- ResizeItemCommand: Resizing items via handle drag or geometry spinboxes.
- ChangePropertyCommand: Changing item properties (fonts, alignments, mappings, rules).
"""
from __future__ import annotations

from typing import Any
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QUndoCommand


class MoveItemCommand(QUndoCommand):
    """Undo/Redo moving a single canvas item."""

    def __init__(
        self,
        editor: Any,
        item: Any,
        old_pos: QPointF,
        new_pos: QPointF,
        text: str = "Move Item",
    ) -> None:
        super().__init__(text)
        self.editor = editor
        self.item = item
        self.old_pos = QPointF(old_pos)
        self.new_pos = QPointF(new_pos)

    def undo(self) -> None:
        self.item.setPos(self.old_pos)
        if hasattr(self.editor, "_selected_item") and self.editor._selected_item is self.item:
            self.editor._panel.update_position(self.old_pos.x(), self.old_pos.y())
        if hasattr(self.editor, "_mark_dirty"):
            self.editor._mark_dirty()

    def redo(self) -> None:
        self.item.setPos(self.new_pos)
        if hasattr(self.editor, "_selected_item") and self.editor._selected_item is self.item:
            self.editor._panel.update_position(self.new_pos.x(), self.new_pos.y())
        if hasattr(self.editor, "_mark_dirty"):
            self.editor._mark_dirty()


class MoveMultipleItemsCommand(QUndoCommand):
    """Undo/Redo moving multiple canvas items simultaneously (e.g. alignment tools)."""

    def __init__(
        self,
        editor: Any,
        moves: list[tuple[Any, QPointF, QPointF]],
        text: str = "Align Items",
    ) -> None:
        super().__init__(text)
        self.editor = editor
        self.moves = [(item, QPointF(old_pos), QPointF(new_pos)) for item, old_pos, new_pos in moves]

    def undo(self) -> None:
        for item, old_pos, _ in self.moves:
            item.setPos(old_pos)
            if hasattr(self.editor, "_selected_item") and self.editor._selected_item is item:
                self.editor._panel.update_position(old_pos.x(), old_pos.y())
        if hasattr(self.editor, "_mark_dirty"):
            self.editor._mark_dirty()

    def redo(self) -> None:
        for item, _, new_pos in self.moves:
            item.setPos(new_pos)
            if hasattr(self.editor, "_selected_item") and self.editor._selected_item is item:
                self.editor._panel.update_position(new_pos.x(), new_pos.y())
        if hasattr(self.editor, "_mark_dirty"):
            self.editor._mark_dirty()


class AddItemCommand(QUndoCommand):
    """Undo/Redo adding an item (Field, Chart, or Badge) to the canvas."""

    def __init__(
        self,
        editor: Any,
        item: Any,
        item_type: str = "field",
        text: str = "Add Item",
    ) -> None:
        super().__init__(text)
        self.editor = editor
        self.item = item
        self.item_type = item_type  # "field" | "chart" | "badge"

    def undo(self) -> None:
        if self.item.scene():
            self.editor._scene.removeItem(self.item)

        if self.item_type == "field" and self.item in self.editor._field_items:
            self.editor._field_items.remove(self.item)
        elif self.item_type == "chart" and self.item in self.editor._chart_items:
            self.editor._chart_items.remove(self.item)
        elif self.item_type == "badge" and self.item in self.editor._badge_items:
            self.editor._badge_items.remove(self.item)
        elif self.item_type == "photo" and self.item in self.editor._photo_items:
            self.editor._photo_items.remove(self.item)
        elif self.item_type == "qr" and self.item in self.editor._qr_items:
            self.editor._qr_items.remove(self.item)
        elif self.item_type == "table" and self.item in self.editor._table_items:
            self.editor._table_items.remove(self.item)

        self.editor._scene.clearSelection()
        if hasattr(self.editor, "_mark_dirty"):
            self.editor._mark_dirty()

    def redo(self) -> None:
        if not self.item.scene():
            self.editor._scene.addItem(self.item)
        self.item.setVisible(getattr(self.item, "page", 1) == getattr(self.editor, "_current_page", 1))

        if self.item_type == "field" and self.item not in self.editor._field_items:
            self.editor._field_items.append(self.item)
        elif self.item_type == "chart" and self.item not in self.editor._chart_items:
            self.editor._chart_items.append(self.item)
        elif self.item_type == "badge" and self.item not in self.editor._badge_items:
            self.editor._badge_items.append(self.item)
        elif self.item_type == "photo" and self.item not in self.editor._photo_items:
            self.editor._photo_items.append(self.item)
        elif self.item_type == "qr" and self.item not in self.editor._qr_items:
            self.editor._qr_items.append(self.item)
        elif self.item_type == "table" and self.item not in self.editor._table_items:
            self.editor._table_items.append(self.item)

        self.editor._scene.clearSelection()
        self.item.setSelected(True)
        if hasattr(self.editor, "_mark_dirty"):
            self.editor._mark_dirty()


class DeleteItemCommand(QUndoCommand):
    """Undo/Redo deleting an item from the canvas."""

    def __init__(
        self,
        editor: Any,
        item: Any,
        item_type: str = "field",
        text: str = "Delete Item",
    ) -> None:
        super().__init__(text)
        self.editor = editor
        self.item = item
        self.item_type = item_type

    def undo(self) -> None:
        if not self.item.scene():
            self.editor._scene.addItem(self.item)
        self.item.setVisible(getattr(self.item, "page", 1) == getattr(self.editor, "_current_page", 1))

        if self.item_type == "field" and self.item not in self.editor._field_items:
            self.editor._field_items.append(self.item)
        elif self.item_type == "chart" and self.item not in self.editor._chart_items:
            self.editor._chart_items.append(self.item)
        elif self.item_type == "badge" and self.item not in self.editor._badge_items:
            self.editor._badge_items.append(self.item)
        elif self.item_type == "photo" and self.item not in self.editor._photo_items:
            self.editor._photo_items.append(self.item)
        elif self.item_type == "qr" and self.item not in self.editor._qr_items:
            self.editor._qr_items.append(self.item)
        elif self.item_type == "table" and self.item not in self.editor._table_items:
            self.editor._table_items.append(self.item)

        self.editor._scene.clearSelection()
        self.item.setSelected(True)
        if hasattr(self.editor, "_mark_dirty"):
            self.editor._mark_dirty()

    def redo(self) -> None:
        if self.item.scene():
            self.editor._scene.removeItem(self.item)

        if self.item_type == "field" and self.item in self.editor._field_items:
            self.editor._field_items.remove(self.item)
        elif self.item_type == "chart" and self.item in self.editor._chart_items:
            self.editor._chart_items.remove(self.item)
        elif self.item_type == "badge" and self.item in self.editor._badge_items:
            self.editor._badge_items.remove(self.item)
        elif self.item_type == "photo" and self.item in self.editor._photo_items:
            self.editor._photo_items.remove(self.item)
        elif self.item_type == "qr" and self.item in self.editor._qr_items:
            self.editor._qr_items.remove(self.item)
        elif self.item_type == "table" and self.item in self.editor._table_items:
            self.editor._table_items.remove(self.item)

        self.editor._scene.clearSelection()
        if hasattr(self.editor, "_mark_dirty"):
            self.editor._mark_dirty()


class ResizeItemCommand(QUndoCommand):
    """Undo/Redo resizing a canvas item."""

    def __init__(
        self,
        editor: Any,
        item: Any,
        old_size: tuple[float, float],
        new_size: tuple[float, float],
        text: str = "Resize Item",
    ) -> None:
        super().__init__(text)
        self.editor = editor
        self.item = item
        self.old_w, self.old_h = old_size
        self.new_w, self.new_h = new_size

    def undo(self) -> None:
        self.item.set_field_size(self.old_w, self.old_h)
        if hasattr(self.editor, "_selected_item") and self.editor._selected_item is self.item:
            self.editor._panel.update_geometry(self.old_w, self.old_h)
        if hasattr(self.editor, "_mark_dirty"):
            self.editor._mark_dirty()

    def redo(self) -> None:
        self.item.set_field_size(self.new_w, self.new_h)
        if hasattr(self.editor, "_selected_item") and self.editor._selected_item is self.item:
            self.editor._panel.update_geometry(self.new_w, self.new_h)
        if hasattr(self.editor, "_mark_dirty"):
            self.editor._mark_dirty()


class ChangePropertyCommand(QUndoCommand):
    """Undo/Redo changing any property on a Field, Chart, or Badge item."""

    def __init__(
        self,
        editor: Any,
        item: Any,
        property_name: str,
        old_value: Any,
        new_value: Any,
        text: str = "Change Property",
    ) -> None:
        super().__init__(text)
        self.editor = editor
        self.item = item
        self.property_name = property_name
        self.old_value = old_value
        self.new_value = new_value

    def _apply(self, val: Any) -> None:
        prop = self.property_name
        if prop == "label":
            self.item.set_label(val)
        elif prop == "mapped_column":
            self.item.set_mapped_column(val)
        elif prop == "is_unique":
            self.item.set_is_unique(val)
        elif prop == "font_family":
            self.item.set_font_family(val)
        elif prop == "font_size":
            self.item.set_font_size(val)
        elif prop == "color":
            self.item.set_color(val)
        elif prop == "bold":
            self.item.set_bold(val)
        elif prop == "italic":
            self.item.set_italic(val)
        elif prop == "underline":
            self.item.set_underline(val)
        elif prop == "multiline":
            self.item.set_multiline(val)
        elif prop == "alignment":
            self.item.set_alignment(val)
        elif prop == "v_alignment":
            self.item.set_v_alignment(val)
        elif prop == "chart_columns":
            self.item.set_chart_columns(val)
        elif prop == "chart_style":
            self.item.set_chart_style(val)
        elif prop == "badge_image":
            self.item.set_badge_image(val)
        elif prop == "rule":
            col, op, v = val
            self.item.set_rule(col, op, v)
        elif prop == "photo_id_column":
            self.item.set_photo_id_column(val)
        elif prop == "border_color":
            self.item.set_border_color(val)
        elif prop == "border_width":
            self.item.set_border_width(val)
        elif prop == "corner_radius":
            self.item.set_corner_radius(val)
        elif prop in ("qr_payload", "qr_payload_template"):
            self.item.set_qr_payload(val)
        elif prop == "border_cells":
            self.item.set_border_cells(val)
        elif prop == "subject_columns":
            self.item.set_subject_columns(val)
        elif prop == "show_max_marks":
            self.item.set_show_max_marks(val)
        elif prop == "show_grade":
            self.item.set_show_grade(val)
        elif prop == "max_marks":
            self.item.set_max_marks(val)
        elif prop == "row_height":
            self.item.set_row_height(val)
        elif prop == "header_bg":
            self.item.set_header_bg(val)
        elif prop == "header_color":
            self.item.set_header_color(val)
        elif prop == "alt_row_bg":
            self.item.set_alt_row_bg(val)

        if hasattr(self.editor, "_selected_item") and self.editor._selected_item is self.item:
            self.editor._panel.load_item(self.item)
        if hasattr(self.editor, "_mark_dirty"):
            self.editor._mark_dirty()

    def undo(self) -> None:
        self._apply(self.old_value)

    def redo(self) -> None:
        self._apply(self.new_value)

