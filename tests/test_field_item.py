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


class TestFieldItemBoundingRect(unittest.TestCase):
    def test_bounding_rect_includes_padding(self):
        from ui.widgets.field_item import FieldItem
        item = FieldItem(width=200, height=40)
        rect = item.boundingRect()
        self.assertAlmostEqual(rect.width(), 202.0)
        self.assertAlmostEqual(rect.height(), 42.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
