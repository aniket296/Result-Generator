"""
tests/test_multipage_template.py
Comprehensive test suite for Phase 3.2: Multi-Page Template Architecture
(Duplex / Two-Page Support), view toggling, property panel integration,
and duplex PDF export.
"""
from __future__ import annotations

import os
import pymupdf
import pytest
from PyQt6.QtWidgets import QApplication

from ui.widgets.field_item import FieldItem
from ui.widgets.chart_item import ChartItem
from ui.widgets.badge_item import BadgeItem
from ui.widgets.photo_item import PhotoItem
from ui.widgets.qr_item import QRItem
from ui.widgets.table_item import TableItem
from ui.widgets.properties_panel import PropertiesPanel
from ui.views.template_editor_view import TemplateEditorView
from generation.pdf_generator import generate_single_pdf


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


# ── 1. Item Serialization & Deserialization ──────────────────────────────────

def test_all_canvas_items_page_property_serialization():
    """Verify that all 6 canvas widget items serialize and deserialize their page index."""
    items = [
        FieldItem(label="Student Name", x=50, y=50, width=150, height=30),
        ChartItem(label="Performance Chart", x=50, y=100, width=200, height=150),
        BadgeItem(label="Honors Badge", x=50, y=260, width=80, height=80),
        PhotoItem(label="Student Photo", x=50, y=350, width=90, height=110),
        QRItem(label="Verification QR", x=50, y=470, width=80, height=80),
        TableItem(label="Marks Table", x=50, y=560, width=400, height=150),
    ]

    for item in items:
        # Defaults to Page 1
        assert getattr(item, "page", 1) == 1
        d_p1 = item.to_dict()
        assert d_p1.get("page") == 1

        # Switch to Page 2
        item.page = 2
        d_p2 = item.to_dict()
        assert d_p2.get("page") == 2

        # Roundtrip deserialization
        restored = type(item).from_dict(d_p2)
        assert getattr(restored, "page", 1) == 2

        # Backward compatibility: dictionaries without 'page' key default to 1
        d_no_page = dict(d_p2)
        d_no_page.pop("page", None)
        restored_default = type(item).from_dict(d_no_page)
        assert getattr(restored_default, "page", 1) == 1


# ── 2. Properties Panel Page Selection ───────────────────────────────────────

def test_properties_panel_page_selection(qapp):
    panel = PropertiesPanel()
    assert hasattr(panel, "_page_combo")

    emitted_pages = []
    panel.page_changed.connect(emitted_pages.append)

    item = FieldItem(label="Test Field")
    item.page = 1
    panel.load_item(item)
    assert panel._page_combo.currentIndex() == 0  # Page 1

    item.page = 2
    panel.load_item(item)
    assert panel._page_combo.currentIndex() == 1  # Page 2

    # Changing selection triggers page_changed signal
    panel._page_combo.setCurrentIndex(0)
    assert emitted_pages[-1] == 1

    panel._page_combo.setCurrentIndex(1)
    assert emitted_pages[-1] == 2


# ── 3. Template Editor Page Switching & Visibility ───────────────────────────

def test_template_editor_page_switching(qapp):
    editor = TemplateEditorView()
    assert editor._current_page == 1
    assert editor._num_pages == 1

    # Add field on Page 1
    editor.switch_page(1)
    editor._on_add_field()
    assert len(editor._field_items) == 1
    field_p1 = editor._field_items[0]
    assert field_p1.page == 1
    assert field_p1.isVisible() is True

    # Switch to Page 2
    editor.switch_page(2)
    assert editor._current_page == 2
    assert editor._num_pages == 2
    assert field_p1.isVisible() is False

    # Add field on Page 2
    editor._on_add_field()
    assert len(editor._field_items) == 2
    field_p2 = editor._field_items[1]
    assert field_p2.page == 2
    assert field_p2.isVisible() is True

    # Switch back to Page 1
    editor.switch_page(1)
    assert editor._current_page == 1
    assert field_p1.isVisible() is True
    assert field_p2.isVisible() is False

    # Move field_p1 from Page 1 to Page 2 via _on_item_page_changed
    editor._selected_item = field_p1
    editor._on_item_page_changed(2)
    assert field_p1.page == 2
    assert field_p1.isVisible() is False  # currently on Page 1

    # Switch to Page 2: both fields should now be visible
    editor.switch_page(2)
    assert field_p1.isVisible() is True
    assert field_p2.isVisible() is True


def test_template_editor_state_roundtrip(qapp):
    editor = TemplateEditorView()
    editor.switch_page(1)
    editor._on_add_field()
    field1 = editor._field_items[0]
    field1.set_label("Front Label")
    field1.page = 1

    editor.switch_page(2)
    editor._on_add_field()
    field2 = editor._field_items[1]
    field2.set_label("Back Remarks")
    field2.page = 2

    state = editor._get_state()
    assert state.get("num_pages") == 2
    fields_state = state.get("fields", [])
    assert len(fields_state) == 2
    assert fields_state[0].get("page") == 1
    assert fields_state[1].get("page") == 2

    # Restore in fresh editor
    editor2 = TemplateEditorView()
    editor2._restore_state(state)
    assert editor2._num_pages == 2
    assert len(editor2._field_items) == 2
    assert editor2._field_items[0].page == 1
    assert editor2._field_items[1].page == 2

    # Verify initial view after restore is Page 1
    assert editor2._current_page == 1
    assert editor2._field_items[0].isVisible() is True
    assert editor2._field_items[1].isVisible() is False

    # Switch to Page 2
    editor2.switch_page(2)
    assert editor2._field_items[0].isVisible() is False
    assert editor2._field_items[1].isVisible() is True


# ── 4. PDF Generation Duplex / Multi-Page Output ─────────────────────────────

def test_pdf_generator_backward_compatibility_single_page(tmp_path):
    """A standard 1-page template should output a 1-page PDF."""
    out_pdf = str(tmp_path / "single_page_test.pdf")
    template_state = {
        "num_pages": 1,
        "canvas_width": 595.0,
        "canvas_height": 842.0,
        "fields": [
            {"label": "Name", "x": 50, "y": 50, "width": 200, "height": 30, "page": 1}
        ],
    }
    row_data = {"Name": "John Doe"}
    generate_single_pdf(template_state, row_data, out_pdf)

    assert os.path.exists(out_pdf)
    doc = pymupdf.open(out_pdf)
    assert doc.page_count == 1
    text = doc[0].get_text()
    assert "John Doe" in text
    doc.close()


def test_pdf_generator_duplex_two_page_output(tmp_path):
    """A 2-page duplex template should output a 2-page PDF with items routed correctly."""
    out_pdf = str(tmp_path / "duplex_output_test.pdf")
    template_state = {
        "num_pages": 2,
        "canvas_width": 595.0,
        "canvas_height": 842.0,
        "fields": [
            {"label": "Front Student", "x": 50, "y": 50, "width": 200, "height": 30, "page": 1},
            {"label": "Back Remarks", "x": 50, "y": 100, "width": 300, "height": 30, "page": 2},
        ],
    }
    row_data = {
        "Front Student": "Alice Wonderland",
        "Back Remarks": "Attendance Conduct Satisfactory",
    }
    generate_single_pdf(template_state, row_data, out_pdf)

    assert os.path.exists(out_pdf)
    doc = pymupdf.open(out_pdf)
    assert doc.page_count == 2

    # Page 1 contains Front Student, but NOT Back Remarks
    p1_text = doc[0].get_text()
    assert "Alice Wonderland" in p1_text
    assert "Attendance Conduct Satisfactory" not in p1_text

    # Page 2 contains Back Remarks, but NOT Front Student
    p2_text = doc[1].get_text()
    assert "Attendance Conduct Satisfactory" in p2_text
    assert "Alice Wonderland" not in p2_text

    doc.close()


def test_pdf_generator_duplex_table_push_down_page_isolation(tmp_path):
    """
    Dynamic subject table height expansion on Page 1 MUST NOT affect
    or shift elements positioned on Page 2.
    """
    out_pdf = str(tmp_path / "table_isolation_test.pdf")
    template_state = {
        "num_pages": 2,
        "canvas_width": 595.0,
        "canvas_height": 842.0,
        "tables": [
            {
                "label": "Marks Table",
                "x": 50.0,
                "y": 100.0,
                "width": 400.0,
                "height": 50.0,  # Small initial height
                "subject_columns": ["Maths", "Science", "History", "Geography", "English"],
                "row_height": 25.0,
                "page": 1,
            }
        ],
        "fields": [
            # Page 1 field below the table
            {"label": "P1 Below Table", "x": 50, "y": 160, "width": 200, "height": 25, "page": 1},
            # Page 2 field at identical y-coordinate
            {"label": "P2 Neutral Field", "x": 50, "y": 160, "width": 200, "height": 25, "page": 2},
        ],
    }
    row_data = {
        "Maths": 95,
        "Science": 88,
        "History": 76,
        "Geography": 82,
        "English": 90,
        "P1 Below Table": "Page 1 Footer",
        "P2 Neutral Field": "Page 2 Content",
    }
    generate_single_pdf(template_state, row_data, out_pdf)

    assert os.path.exists(out_pdf)
    doc = pymupdf.open(out_pdf)
    assert doc.page_count == 2

    # Extract positions of text elements
    p1_blocks = doc[0].get_text("blocks")
    p2_blocks = doc[1].get_text("blocks")

    # Find the y-coordinate for "Page 1 Footer"
    p1_footer_y = None
    for b in p1_blocks:
        if "Page 1 Footer" in b[4]:
            p1_footer_y = b[1]
            break

    # Find the y-coordinate for "Page 2 Content"
    p2_content_y = None
    for b in p2_blocks:
        if "Page 2 Content" in b[4]:
            p2_content_y = b[1]
            break

    assert p1_footer_y is not None
    assert p2_content_y is not None

    # On Page 1, the table with 5 subjects grew significantly, pushing "Page 1 Footer" down.
    # Initial y was 160, table expanded by (25 header + 5*25 rows = 150) - 50 = +100 delta.
    # So p1_footer_y should be around 260.
    # On Page 2, there is no table, so p2_content_y should stay near 160 (or top of page).
    assert p1_footer_y > p2_content_y + 50.0

    doc.close()


def test_pdf_generator_duplex_with_2page_pdf_background(tmp_path):
    """
    If a 2-page PDF is loaded as the template background, Page 1 of the background
    should be stamped on PDF Page 1, and Page 2 on PDF Page 2.
    """
    bg_pdf_path = str(tmp_path / "two_page_bg.pdf")
    bg_doc = pymupdf.open()
    # Create page 1
    p1 = bg_doc.new_page(width=595, height=842)
    p1.draw_rect(pymupdf.Rect(10, 10, 100, 100), color=(1, 0, 0), fill=(1, 0, 0))  # Red
    p1.insert_text(pymupdf.Point(20, 50), "BG_PAGE_ONE", fontsize=14)
    # Create page 2
    p2 = bg_doc.new_page(width=595, height=842)
    p2.draw_rect(pymupdf.Rect(10, 10, 100, 100), color=(0, 0, 1), fill=(0, 0, 1))  # Blue
    p2.insert_text(pymupdf.Point(20, 50), "BG_PAGE_TWO", fontsize=14)
    bg_doc.save(bg_pdf_path)
    bg_doc.close()

    out_pdf = str(tmp_path / "duplex_with_bg.pdf")
    template_state = {
        "num_pages": 2,
        "canvas_width": 595.0,
        "canvas_height": 842.0,
        "background": {"path": bg_pdf_path, "type": "pdf"},
        "fields": [
            {"label": "Front Title", "x": 150, "y": 50, "width": 200, "height": 30, "page": 1},
            {"label": "Back Title", "x": 150, "y": 50, "width": 200, "height": 30, "page": 2},
        ],
    }
    row_data = {
        "Front Title": "Front Page Title",
        "Back Title": "Back Page Title",
    }
    generate_single_pdf(template_state, row_data, out_pdf)

    assert os.path.exists(out_pdf)
    res_doc = pymupdf.open(out_pdf)
    assert res_doc.page_count == 2

    p1_text = res_doc[0].get_text()
    assert "BG_PAGE_ONE" in p1_text
    assert "Front Page Title" in p1_text
    assert "BG_PAGE_TWO" not in p1_text

    p2_text = res_doc[1].get_text()
    assert "BG_PAGE_TWO" in p2_text
    assert "Back Page Title" in p2_text
    assert "BG_PAGE_ONE" not in p2_text

    res_doc.close()

