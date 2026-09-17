"""
tests/test_field_item.py
Full-scale tests for ui/widgets/field_item.py
"""
import sys
import unittest
from PyQt6.QtWidgets import QApplication
_app = QApplication.instance() or QApplication(sys.argv)


class TestFieldItemDefaults(unittest.TestCase):
    def _make(self, **kw):
        from ui.widgets.field_item import FieldItem
        return FieldItem(**kw)

    def test_default_label(self):
        item = self._make()
        self.assertEqual(item.label, "New Field")

    def test_default_font_family(self):
        item = self._make()
        self.assertEqual(item.font_family, "Segoe UI")

    def test_default_font_size(self):
        item = self._make()
        self.assertEqual(item.font_size, 12)

    def test_default_color(self):
        item = self._make()
        self.assertEqual(item.color, "#000000")

    def test_default_bold_false(self):
        item = self._make()
        self.assertFalse(item.bold)

    def test_default_italic_false(self):
        item = self._make()
        self.assertFalse(item.italic)

    def test_default_underline_false(self):
        item = self._make()
        self.assertFalse(item.underline)

    def test_default_multiline_false(self):
        item = self._make()
        self.assertFalse(item.multiline)

    def test_default_alignment(self):
        item = self._make()
        self.assertEqual(item.alignment, "Left")

    def test_default_is_unique_false(self):
        item = self._make()
        self.assertFalse(item.is_unique)

    def test_default_mapped_column_empty(self):
        item = self._make()
        self.assertEqual(item.mapped_column, "")

    def test_minimum_width_enforced(self):
        item = self._make(width=10)
        self.assertEqual(item.width, 60.0)

    def test_minimum_height_enforced(self):
        item = self._make(height=5)
        self.assertEqual(item.height, 20.0)


class TestFieldItemSetters(unittest.TestCase):
    def _make(self, **kw):
        from ui.widgets.field_item import FieldItem
        return FieldItem(**kw)

    def test_set_label(self):
        item = self._make()
        item.set_label("Score")
        self.assertEqual(item.label, "Score")

    def test_set_mapped_column(self):
        item = self._make()
        item.set_mapped_column("Physics_Marks")
        self.assertEqual(item.mapped_column, "Physics_Marks")

    def test_set_is_unique_true(self):
        item = self._make()
        item.set_is_unique(True)
        self.assertTrue(item.is_unique)

    def test_set_is_unique_false(self):
        item = self._make()
        item.set_is_unique(True)
        item.set_is_unique(False)
        self.assertFalse(item.is_unique)

    def test_set_bold(self):
        item = self._make()
        item.set_bold(True)
        self.assertTrue(item.bold)

    def test_set_italic(self):
        item = self._make()
        item.set_italic(True)
        self.assertTrue(item.italic)

    def test_set_underline(self):
        item = self._make()
        item.set_underline(True)
        self.assertTrue(item.underline)

    def test_set_multiline(self):
        item = self._make()
        item.set_multiline(True)
        self.assertTrue(item.multiline)

    def test_set_color(self):
        item = self._make()
        item.set_color("#FF5733")
        self.assertEqual(item.color, "#FF5733")

    def test_set_font_family(self):
        item = self._make()
        item.set_font_family("Arial")
        self.assertEqual(item.font_family, "Arial")

    def test_set_font_size_valid(self):
        item = self._make()
        item.set_font_size(18)
        self.assertEqual(item.font_size, 18)

    def test_set_font_size_minimum(self):
        item = self._make()
        item.set_font_size(1)
        self.assertEqual(item.font_size, 6)

    def test_set_alignment_left(self):
        item = self._make()
        item.set_alignment("Left")
        self.assertEqual(item.alignment, "Left")

    def test_set_alignment_center(self):
        item = self._make()
        item.set_alignment("Center")
        self.assertEqual(item.alignment, "Center")

    def test_set_alignment_right(self):
        item = self._make()
        item.set_alignment("Right")
        self.assertEqual(item.alignment, "Right")

    def test_set_alignment_invalid_no_change(self):
        item = self._make()
        item.set_alignment("Justify")
        self.assertEqual(item.alignment, "Left")  # default unchanged

    def test_set_v_alignment_top(self):
        item = self._make()
        item.set_v_alignment("Top")
        self.assertEqual(item.v_alignment, "Top")

    def test_set_v_alignment_middle(self):
        item = self._make()
        item.set_v_alignment("Middle")
        self.assertEqual(item.v_alignment, "Middle")

    def test_set_v_alignment_bottom(self):
        item = self._make()
        item.set_v_alignment("Bottom")
        self.assertEqual(item.v_alignment, "Bottom")

    def test_set_v_alignment_invalid_no_change(self):
        item = self._make()
        item.set_v_alignment("Invalid")
        self.assertEqual(item.v_alignment, "Top")

    def test_set_field_size(self):
        item = self._make()
        item.set_field_size(300.0, 50.0)
        self.assertEqual(item.width, 300.0)
        self.assertEqual(item.height, 50.0)

    def test_set_field_size_minimum_width(self):
        item = self._make()
        item.set_field_size(10.0, 50.0)
        self.assertEqual(item.width, 60.0)

    def test_set_field_size_minimum_height(self):
        item = self._make()
        item.set_field_size(200.0, 5.0)
        self.assertEqual(item.height, 20.0)


class TestFieldItemSerialization(unittest.TestCase):
    def _make_full(self):
        from ui.widgets.field_item import FieldItem
        item = FieldItem(label="EnrollNo", x=50, y=80, width=180, height=35)
        item.set_mapped_column("Enrollment_Number")
        item.set_is_unique(True)
        item.set_bold(True)
        item.set_italic(True)
        item.set_underline(True)
        item.set_multiline(True)
        item.set_color("#2563eb")
        item.set_alignment("Center")
        item.set_v_alignment("Middle")
        item.set_font_family("Arial")
        item.set_font_size(14)
        return item

    def test_to_dict_all_keys_present(self):
        item = self._make_full()
        d = item.to_dict()
        keys = ["label", "mapped_column", "is_unique", "x", "y", "width", "height",
                "font_family", "font_size", "color", "bold", "italic", "underline",
                "multiline", "alignment", "v_alignment"]
        for key in keys:
            self.assertIn(key, d)

    def test_to_dict_values(self):
        item = self._make_full()
        d = item.to_dict()
        self.assertEqual(d["label"], "EnrollNo")
        self.assertEqual(d["mapped_column"], "Enrollment_Number")
        self.assertTrue(d["is_unique"])
        self.assertTrue(d["bold"])
        self.assertTrue(d["italic"])
        self.assertTrue(d["underline"])
        self.assertTrue(d["multiline"])
        self.assertEqual(d["color"], "#2563eb")
        self.assertEqual(d["alignment"], "Center")
        self.assertEqual(d["v_alignment"], "Middle")
        self.assertEqual(d["font_family"], "Arial")
        self.assertEqual(d["font_size"], 14)

    def test_from_dict_roundtrip(self):
        from ui.widgets.field_item import FieldItem
        item = self._make_full()
        d = item.to_dict()
        restored = FieldItem.from_dict(d)
        self.assertEqual(restored.label, item.label)
        self.assertEqual(restored.mapped_column, item.mapped_column)
        self.assertEqual(restored.is_unique, item.is_unique)
        self.assertEqual(restored.bold, item.bold)
        self.assertEqual(restored.italic, item.italic)
        self.assertEqual(restored.underline, item.underline)
        self.assertEqual(restored.multiline, item.multiline)
        self.assertEqual(restored.color, item.color)
        self.assertEqual(restored.alignment, item.alignment)
        self.assertEqual(restored.v_alignment, item.v_alignment)
        self.assertEqual(restored.font_family, item.font_family)
        self.assertEqual(restored.font_size, item.font_size)

    def test_from_dict_defaults_used_for_missing_keys(self):
        from ui.widgets.field_item import FieldItem
        restored = FieldItem.from_dict({"label": "Test"})
        self.assertEqual(restored.label, "Test")
        self.assertFalse(restored.is_unique)
        self.assertFalse(restored.bold)
        self.assertFalse(restored.underline)
        self.assertEqual(restored.color, "#000000")
        self.assertEqual(restored.alignment, "Left")
        self.assertEqual(restored.v_alignment, "Top")

    def test_to_dict_coordinates_rounded(self):
        from ui.widgets.field_item import FieldItem
        item = FieldItem(label="X", x=12.3456789, y=99.9999)
        d = item.to_dict()
        self.assertEqual(d["x"], round(12.3456789, 2))
        self.assertEqual(d["y"], round(99.9999, 2))

    def test_from_dict_then_to_dict_stable(self):
        from ui.widgets.field_item import FieldItem
        d1 = self._make_full().to_dict()
        restored = FieldItem.from_dict(d1)
        d2 = restored.to_dict()
        # All comparable non-position fields should match
        for k in ["label", "mapped_column", "is_unique", "bold", "italic",
                   "underline", "multiline", "color", "alignment", "v_alignment", "font_family", "font_size"]:
            self.assertEqual(d1[k], d2[k], f"Key '{k}' differs: {d1[k]} vs {d2[k]}")


class TestSnapToGridAndBounding(unittest.TestCase):
    def test_snap_to_grid_clamps_to_multiples_of_step(self):
        from PyQt6.QtCore import QPointF
        from PyQt6.QtWidgets import QGraphicsItem, QGraphicsScene
        from ui.widgets.field_item import FieldItem

        scene = QGraphicsScene(0, 0, 800, 1000)
        item = FieldItem(x=0, y=0, width=100, height=50)
        scene.addItem(item)

        item.set_snap_to_grid(True, step=10.0)

        # Proposed pos (104.3, 107.8) -> snapped to (100.0, 110.0)
        res_pos = item.itemChange(QGraphicsItem.GraphicsItemChange.ItemPositionChange, QPointF(104.3, 107.8))
        self.assertEqual(res_pos.x(), 100.0)
        self.assertEqual(res_pos.y(), 110.0)

    def test_snap_to_grid_disabled_keeps_subpixel(self):
        from PyQt6.QtCore import QPointF
        from PyQt6.QtWidgets import QGraphicsItem, QGraphicsScene
        from ui.widgets.field_item import FieldItem

        scene = QGraphicsScene(0, 0, 800, 1000)
        item = FieldItem(x=0, y=0, width=100, height=50)
        scene.addItem(item)

        item.set_snap_to_grid(False)
        res_pos = item.itemChange(QGraphicsItem.GraphicsItemChange.ItemPositionChange, QPointF(104.3, 107.8))
        self.assertAlmostEqual(res_pos.x(), 104.3)
        self.assertAlmostEqual(res_pos.y(), 107.8)

    def test_bounds_clamping_to_scene_rect(self):
        from PyQt6.QtCore import QPointF
        from PyQt6.QtWidgets import QGraphicsItem, QGraphicsScene
        from ui.widgets.field_item import FieldItem

        scene = QGraphicsScene(0, 0, 500, 600)
        item = FieldItem(x=0, y=0, width=100, height=50)
        scene.addItem(item)
        item.set_snap_to_grid(False)

        # Attempt to place outside top/left (< 0)
        res_neg = item.itemChange(QGraphicsItem.GraphicsItemChange.ItemPositionChange, QPointF(-20.0, -50.0))
        self.assertEqual(res_neg.x(), 0.0)
        self.assertEqual(res_neg.y(), 0.0)

        # Attempt to place beyond right/bottom (> max_x = 400, max_y = 550)
        res_over = item.itemChange(QGraphicsItem.GraphicsItemChange.ItemPositionChange, QPointF(900.0, 800.0))
        self.assertEqual(res_over.x(), 400.0)
        self.assertEqual(res_over.y(), 550.0)


class TestMultiItemAlignment(unittest.TestCase):
    def setUp(self):
        from ui.views.template_editor_view import TemplateEditorView
        self.editor = TemplateEditorView()
        self.editor._snap_to_grid = False  # test exact coordinates

    def test_align_left(self):
        from ui.widgets.field_item import FieldItem
        f1 = FieldItem(label="F1", x=150.0, y=100.0, width=100, height=40)
        f2 = FieldItem(label="F2", x=80.0,  y=160.0, width=120, height=40)
        f3 = FieldItem(label="F3", x=220.0, y=220.0, width=100, height=40)
        for f in [f1, f2, f3]:
            self.editor._scene.addItem(f)
            self.editor._field_items.append(f)
            f.setSelected(True)

        self.editor._on_align_left()
        self.assertEqual(f1.pos().x(), 80.0)
        self.assertEqual(f2.pos().x(), 80.0)
        self.assertEqual(f3.pos().x(), 80.0)

    def test_align_center(self):
        from ui.widgets.field_item import FieldItem
        f1 = FieldItem(label="F1", x=100.0, y=100.0, width=200, height=40)  # span [100, 300]
        f2 = FieldItem(label="F2", x=200.0, y=200.0, width=100, height=40)  # span [200, 300]
        for f in [f1, f2]:
            self.editor._scene.addItem(f)
            self.editor._field_items.append(f)
            f.setSelected(True)

        # Midpoint of combined [100, 300] is 200.0
        # F1 target x: 200 - 100 = 100
        # F2 target x: 200 - 50 = 150
        self.editor._on_align_center()
        self.assertEqual(f1.pos().x(), 100.0)
        self.assertEqual(f2.pos().x(), 150.0)

    def test_align_right(self):
        from ui.widgets.field_item import FieldItem
        f1 = FieldItem(label="F1", x=50.0,  y=100.0, width=100, height=40)  # right edge = 150
        f2 = FieldItem(label="F2", x=150.0, y=160.0, width=150, height=40)  # right edge = 300
        for f in [f1, f2]:
            self.editor._scene.addItem(f)
            self.editor._field_items.append(f)
            f.setSelected(True)

        self.editor._on_align_right()
        # Max right is 300.0
        # F1 target x: 300 - 100 = 200.0
        # F2 target x: 300 - 150 = 150.0
        self.assertEqual(f1.pos().x(), 200.0)
        self.assertEqual(f2.pos().x(), 150.0)

    def test_distribute_vertically(self):
        from ui.widgets.field_item import FieldItem
        f1 = FieldItem(label="F1", x=100.0, y=100.0, width=100, height=50)
        f2 = FieldItem(label="F2", x=100.0, y=180.0, width=100, height=50)
        f3 = FieldItem(label="F3", x=100.0, y=400.0, width=100, height=50)
        for f in [f1, f2, f3]:
            self.editor._scene.addItem(f)
            self.editor._field_items.append(f)
            f.setSelected(True)

        # Top = 100, Bottom = 450 (span 350, total heights 150, total gap 200 -> gap = 100 each)
        # f1: 100
        # f2: 100 + 50 + 100 = 250
        # f3: 250 + 50 + 100 = 400
        self.editor._on_distribute_vertically()
        self.assertEqual(f1.pos().y(), 100.0)
        self.assertEqual(f2.pos().y(), 250.0)
        self.assertEqual(f3.pos().y(), 400.0)

    def test_alignment_toolbar_button_states(self):
        from ui.widgets.field_item import FieldItem
        f1 = FieldItem(label="F1")
        f2 = FieldItem(label="F2")
        f3 = FieldItem(label="F3")
        for f in [f1, f2, f3]:
            self.editor._scene.addItem(f)
            self.editor._field_items.append(f)

        # 0 items selected
        self.editor._scene.clearSelection()
        self.assertFalse(self.editor._align_left_btn.isEnabled())
        self.assertFalse(self.editor._distribute_v_btn.isEnabled())

        # 1 item selected
        f1.setSelected(True)
        self.assertFalse(self.editor._align_left_btn.isEnabled())
        self.assertFalse(self.editor._distribute_v_btn.isEnabled())

        # 2 items selected
        f2.setSelected(True)
        self.assertTrue(self.editor._align_left_btn.isEnabled())
        self.assertTrue(self.editor._align_center_btn.isEnabled())
        self.assertTrue(self.editor._align_right_btn.isEnabled())
        self.assertFalse(self.editor._distribute_v_btn.isEnabled())

        # 3 items selected
        f3.setSelected(True)
        self.assertTrue(self.editor._align_left_btn.isEnabled())
        self.assertTrue(self.editor._distribute_v_btn.isEnabled())


if __name__ == "__main__":
    unittest.main(verbosity=2)
