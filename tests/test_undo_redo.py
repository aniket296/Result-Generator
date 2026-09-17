"""
tests/test_undo_redo.py
Comprehensive unit tests for the Template Editor Undo/Redo architecture.
"""
from __future__ import annotations

import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QUndoStack

from ui.widgets.field_item import FieldItem
from ui.widgets.chart_item import ChartItem
from ui.widgets.badge_item import BadgeItem
from ui.views.template_editor_view import TemplateEditorView
from ui.undo_commands import (
    MoveItemCommand,
    MoveMultipleItemsCommand,
    AddItemCommand,
    DeleteItemCommand,
    ResizeItemCommand,
    ChangePropertyCommand,
)


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def editor(qapp):
    view = TemplateEditorView()
    return view


class TestUndoCommands:
    def test_add_and_delete_field_item_command(self, editor):
        stack = QUndoStack()
        item = FieldItem("TestField", x=100, y=100, width=150, height=30)

        # 1. Add item
        add_cmd = AddItemCommand(editor, item, item_type="field")
        stack.push(add_cmd)

        assert item in editor._field_items
        assert item.scene() is editor._scene

        # Undo add
        stack.undo()
        assert item not in editor._field_items
        assert item.scene() is None

        # Redo add
        stack.redo()
        assert item in editor._field_items
        assert item.scene() is editor._scene

        # 2. Delete item
        del_cmd = DeleteItemCommand(editor, item, item_type="field")
        stack.push(del_cmd)

        assert item not in editor._field_items
        assert item.scene() is None

        # Undo delete
        stack.undo()
        assert item in editor._field_items
        assert item.scene() is editor._scene

        # Redo delete
        stack.redo()
        assert item not in editor._field_items
        assert item.scene() is None

    def test_add_and_delete_chart_and_badge_commands(self, editor):
        stack = QUndoStack()
        chart = ChartItem("Performance Chart", x=50, y=50, width=200, height=150)
        badge = BadgeItem("Badge 1", x=80, y=80, width=80, height=80)

        # Add Chart
        stack.push(AddItemCommand(editor, chart, item_type="chart"))
        assert chart in editor._chart_items
        assert chart.scene() is editor._scene

        # Add Badge
        stack.push(AddItemCommand(editor, badge, item_type="badge"))
        assert badge in editor._badge_items
        assert badge.scene() is editor._scene

        # Undo Badge
        stack.undo()
        assert badge not in editor._badge_items
        assert badge.scene() is None
        assert chart in editor._chart_items

        # Undo Chart
        stack.undo()
        assert chart not in editor._chart_items
        assert chart.scene() is None

        # Redo Chart and Badge
        stack.redo()
        assert chart in editor._chart_items
        stack.redo()
        assert badge in editor._badge_items

    def test_move_item_command(self, editor):
        stack = QUndoStack()
        item = FieldItem("Movable", x=10, y=20, width=100, height=30)
        editor._scene.addItem(item)
        editor._field_items.append(item)

        old_pos = QPointF(10, 20)
        new_pos = QPointF(100, 200)

        cmd = MoveItemCommand(editor, item, old_pos, new_pos)
        stack.push(cmd)
        assert item.pos() == new_pos

        stack.undo()
        assert item.pos() == old_pos

        stack.redo()
        assert item.pos() == new_pos

    def test_move_multiple_items_command(self, editor):
        stack = QUndoStack()
        f1 = FieldItem("F1", x=10, y=10)
        f2 = FieldItem("F2", x=30, y=50)
        editor._scene.addItem(f1)
        editor._scene.addItem(f2)
        editor._field_items.extend([f1, f2])

        moves = [
            (f1, QPointF(10, 10), QPointF(50, 10)),
            (f2, QPointF(30, 50), QPointF(50, 50)),
        ]
        cmd = MoveMultipleItemsCommand(editor, moves, text="Align Left")
        stack.push(cmd)

        assert f1.pos() == QPointF(50, 10)
        assert f2.pos() == QPointF(50, 50)

        stack.undo()
        assert f1.pos() == QPointF(10, 10)
        assert f2.pos() == QPointF(30, 50)

        stack.redo()
        assert f1.pos() == QPointF(50, 10)
        assert f2.pos() == QPointF(50, 50)

    def test_resize_item_command(self, editor):
        stack = QUndoStack()
        item = FieldItem("Resizable", x=0, y=0, width=100, height=30)
        editor._scene.addItem(item)
        editor._field_items.append(item)

        cmd = ResizeItemCommand(editor, item, (100, 30), (250, 60))
        stack.push(cmd)
        assert item.width == 250
        assert item.height == 60

        stack.undo()
        assert item.width == 100
        assert item.height == 30

        stack.redo()
        assert item.width == 250
        assert item.height == 60

    def test_change_property_command_field_properties(self, editor):
        stack = QUndoStack()
        item = FieldItem("PropsField", x=0, y=0)
        editor._scene.addItem(item)
        editor._field_items.append(item)

        # Label
        stack.push(ChangePropertyCommand(editor, item, "label", "PropsField", "UpdatedLabel"))
        assert item.label == "UpdatedLabel"
        stack.undo()
        assert item.label == "PropsField"
        stack.redo()
        assert item.label == "UpdatedLabel"

        # Font size
        stack.push(ChangePropertyCommand(editor, item, "font_size", 11, 16))
        assert item.font_size == 16
        stack.undo()
        assert item.font_size == 11

        # Alignment
        stack.push(ChangePropertyCommand(editor, item, "alignment", "Left", "Center"))
        assert item.alignment == "Center"
        stack.undo()
        assert item.alignment == "Left"

        # Vertical Alignment
        stack.push(ChangePropertyCommand(editor, item, "v_alignment", "Top", "Middle"))
        assert item.v_alignment == "Middle"
        stack.undo()
        assert item.v_alignment == "Top"

        # Bold
        stack.push(ChangePropertyCommand(editor, item, "bold", False, True))
        assert item.bold is True
        stack.undo()
        assert item.bold is False

        # Color
        stack.push(ChangePropertyCommand(editor, item, "color", "#000000", "#ff0000"))
        assert item.color == "#ff0000"
        stack.undo()
        assert item.color == "#000000"

    def test_change_property_command_chart_and_badge_properties(self, editor):
        stack = QUndoStack()
        chart = ChartItem("Chart", x=0, y=0)
        badge = BadgeItem("Badge", x=0, y=0)
        editor._scene.addItem(chart)
        editor._scene.addItem(badge)

        # Chart style
        stack.push(ChangePropertyCommand(editor, chart, "chart_style", "vertical", "horizontal"))
        assert chart.chart_style == "horizontal"
        stack.undo()
        assert chart.chart_style == "vertical"

        # Chart columns
        stack.push(ChangePropertyCommand(editor, chart, "chart_columns", [], ["Math", "Sci"]))
        assert chart.chart_columns == ["Math", "Sci"]
        stack.undo()
        assert chart.chart_columns == []

        # Badge rule
        old_rule = (badge.rule_column, badge.rule_operator, badge.rule_value)
        new_rule = ("Total", ">=", 90.0)
        stack.push(ChangePropertyCommand(editor, badge, "rule", old_rule, new_rule))
        assert badge.rule_column == "Total"
        assert badge.rule_operator == ">="
        assert badge.rule_value == 90.0
        stack.undo()
        assert badge.rule_column == old_rule[0]
        assert badge.rule_operator == old_rule[1]
        assert badge.rule_value == old_rule[2]


class TestEditorUndoRedoIntegration:
    def test_editor_add_undo_redo_field(self, editor):
        assert len(editor._field_items) == 0
        assert editor._undo_stack.canUndo() is False
        assert editor._undo_stack.canRedo() is False

        editor._on_add_field()
        assert len(editor._field_items) == 1
        assert editor._undo_stack.canUndo() is True
        assert editor._undo_stack.canRedo() is False
        field = editor._field_items[0]

        # Undo addition
        editor._undo_stack.undo()
        assert len(editor._field_items) == 0
        assert editor._undo_stack.canUndo() is False
        assert editor._undo_stack.canRedo() is True

        # Redo addition
        editor._undo_stack.redo()
        assert len(editor._field_items) == 1
        assert editor._field_items[0] is field
        assert editor._undo_stack.canUndo() is True

    def test_editor_alignment_undo_redo(self, editor):
        f1 = FieldItem("F1", x=20, y=10, width=100, height=30)
        f2 = FieldItem("F2", x=80, y=50, width=100, height=30)
        editor._scene.addItem(f1)
        editor._scene.addItem(f2)
        editor._field_items.extend([f1, f2])

        f1.setSelected(True)
        f2.setSelected(True)
        editor._snap_to_grid = False

        editor._on_align_left()
        assert f1.pos().x() == 20
        assert f2.pos().x() == 20

        editor._undo_stack.undo()
        assert f1.pos().x() == 20
        assert f2.pos().x() == 80

        editor._undo_stack.redo()
        assert f1.pos().x() == 20
        assert f2.pos().x() == 20

    def test_editor_distribute_vertically_undo_redo(self, editor):
        f1 = FieldItem("F1", x=10, y=0, width=100, height=20)
        f2 = FieldItem("F2", x=10, y=40, width=100, height=20)
        f3 = FieldItem("F3", x=10, y=100, width=100, height=20)
        editor._scene.addItem(f1)
        editor._scene.addItem(f2)
        editor._scene.addItem(f3)
        editor._field_items.extend([f1, f2, f3])

        f1.setSelected(True)
        f2.setSelected(True)
        f3.setSelected(True)
        editor._snap_to_grid = False

        editor._on_distribute_vertically()
        # total_span = (100+20)-0 = 120, total items height = 60, total gap = 60 => gap = 30
        # f1: 0, f2: 0 + 20 + 30 = 50, f3: 50 + 20 + 30 = 100
        assert f1.pos().y() == 0
        assert f2.pos().y() == 50
        assert f3.pos().y() == 100

        editor._undo_stack.undo()
        assert f1.pos().y() == 0
        assert f2.pos().y() == 40
        assert f3.pos().y() == 100

        editor._undo_stack.redo()
        assert f1.pos().y() == 0
        assert f2.pos().y() == 50
        assert f3.pos().y() == 100

    def test_editor_delete_undo_redo(self, editor):
        editor._on_add_field()
        field = editor._field_items[0]
        field.setSelected(True)
        editor._selected_item = field

        editor._on_delete_selected()
        assert len(editor._field_items) == 0

        editor._undo_stack.undo()
        assert len(editor._field_items) == 1
        assert editor._field_items[0] is field

        editor._undo_stack.redo()
        assert len(editor._field_items) == 0

    def test_editor_panel_coordinates_undo_redo(self, editor):
        editor._on_add_field()
        field = editor._field_items[0]
        field.setSelected(True)
        editor._selected_item = field

        init_x = field.pos().x()
        editor._on_panel_x(init_x + 50)
        assert field.pos().x() == init_x + 50

        editor._undo_stack.undo()
        assert field.pos().x() == init_x

        editor._undo_stack.redo()
        assert field.pos().x() == init_x + 50
