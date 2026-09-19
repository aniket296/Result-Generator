"""
tests/test_table_item.py
Unit tests for TableItem widget, subject extraction, dynamic height computation,
downward expansion, and PyMuPDF vector table rendering.
"""
from __future__ import annotations

import os
import pymupdf
import pytest

from ui.widgets.table_item import TableItem
from generation.pdf_generator import (
    _extract_student_subjects,
    _calculate_table_metrics,
    generate_single_pdf,
)


def test_table_item_defaults():
    item = TableItem(label="Marks Table", x=60.0, y=180.0, width=420.0, height=150.0)
    assert item.label == "Marks Table"
    assert item.pos().x() == 60.0
    assert item.pos().y() == 180.0
    assert item.show_max_marks is True
    assert item.show_grade is True
    assert item.max_marks == 100.0
    assert item.row_height == 22.0
    assert item.font_size == 9
    assert item.header_bg == "#1e3a8a"


def test_table_item_setters():
    item = TableItem()
    item.set_label("Custom Table")
    assert item.label == "Custom Table"

    item.set_subject_columns(["Maths", "Science", "English"])
    assert item.subject_columns == ["Maths", "Science", "English"]

    item.set_show_max_marks(False)
    assert item.show_max_marks is False

    item.set_show_grade(False)
    assert item.show_grade is False

    item.set_max_marks(80.0)
    assert item.max_marks == 80.0

    item.set_row_height(26.0)
    assert item.row_height == 26.0

    item.set_font_size(11)
    assert item.font_size == 11


def test_table_item_serialization_roundtrip():
    item = TableItem(
        label="Midterm Table",
        x=80.0,
        y=220.0,
        width=450.0,
        height=160.0,
        subject_columns=["Physics", "Chemistry", "Biology"],
        show_max_marks=True,
        show_grade=True,
        max_marks=70.0,
        row_height=24.0,
        font_size=10,
        header_bg="#065f46",
        header_color="#ffffff",
        alt_row_bg="#f0fdf4",
        border_color="#a7f3d0",
    )
    d = item.to_dict()
    assert d["item_type"] == "table"
    assert d["label"] == "Midterm Table"
    assert d["x"] == 80.0
    assert d["y"] == 220.0
    assert d["width"] == 450.0
    assert d["height"] == 160.0
    assert d["subject_columns"] == ["Physics", "Chemistry", "Biology"]
    assert d["max_marks"] == 70.0
    assert d["header_bg"] == "#065f46"

    restored = TableItem.from_dict(d)
    assert restored.label == "Midterm Table"
    assert restored.pos().x() == 80.0
    assert restored.pos().y() == 220.0
    assert restored.subject_columns == ["Physics", "Chemistry", "Biology"]
    assert restored.max_marks == 70.0
    assert restored.header_bg == "#065f46"


def test_extract_student_subjects_explicit():
    table_spec = {
        "subject_columns": ["Mathematics", "Physics", "Chemistry", "Computer Science"],
        "max_marks": 100.0,
        "show_grade": True,
        "show_max_marks": True,
    }
    # Student A: 3 subjects (Computer Science empty/None)
    row_a = {
        "Mathematics": "92",
        "Physics": "85",
        "Chemistry": "78",
        "Computer Science": "",
    }
    subjects_a = _extract_student_subjects(table_spec, row_a)
    assert len(subjects_a) == 3
    assert subjects_a[0]["subject"] == "Mathematics"
    assert subjects_a[0]["marks"] == "92"
    assert subjects_a[0]["grade"] == "A1"
    assert subjects_a[1]["subject"] == "Physics"
    assert subjects_a[1]["grade"] == "A2"
    assert subjects_a[2]["subject"] == "Chemistry"
    assert subjects_a[2]["grade"] == "B1"

    # Student B: all 4 subjects
    row_b = {
        "Mathematics": "65",
        "Physics": "55",
        "Chemistry": "48",
        "Computer Science": "95",
    }
    subjects_b = _extract_student_subjects(table_spec, row_b)
    assert len(subjects_b) == 4
    assert subjects_b[3]["subject"] == "Computer Science"
    assert subjects_b[3]["marks"] == "95"
    assert subjects_b[3]["grade"] == "A1"


def test_extract_student_subjects_auto_detect():
    table_spec = {
        "subject_columns": [],
        "max_marks": 100.0,
        "show_grade": True,
        "show_max_marks": True,
    }
    row = {
        "Name": "Alice",
        "Roll No": "12",
        "Enrollment number": "EN100",
        "Algebra": "88",
        "Geometry": "91",
        "History": "74",
        "Total": "253",
        "Percentage": "84.33",
        "Calculated_Grade": "A2",
    }
    subjects = _extract_student_subjects(table_spec, row)
    sub_names = [s["subject"] for s in subjects]
    assert "Algebra" in sub_names
    assert "Geometry" in sub_names
    assert "History" in sub_names
    # Excluded metadata should not be detected as subjects
    assert "Name" not in sub_names
    assert "Roll No" not in sub_names
    assert "Enrollment number" not in sub_names
    assert "Total" not in sub_names


def test_calculate_table_metrics_variable_height():
    table_spec = {
        "x": 50.0,
        "y": 200.0,
        "width": 400.0,
        "height": 100.0,
        "row_height": 20.0,
    }
    scale_x = 1.0
    scale_y = 1.0

    # 3 subjects: header (22) + 3*20 = 82 <= initial_h (100) -> delta_h = 0
    subjs_3 = [{"subject": f"Sub{i}", "marks": "80"} for i in range(3)]
    _, _, _, tot_h_3, _, _, delta_3 = _calculate_table_metrics(table_spec, subjs_3, scale_x, scale_y)
    assert delta_3 == 0.0

    # 8 subjects: header (22) + 8*20 = 182 > initial_h (100) -> delta_h = 82
    subjs_8 = [{"subject": f"Sub{i}", "marks": "80"} for i in range(8)]
    _, _, _, tot_h_8, _, _, delta_8 = _calculate_table_metrics(table_spec, subjs_8, scale_x, scale_y)
    assert delta_8 > 0.0
    assert tot_h_8 == 22.0 + 8 * 20.0
    assert delta_8 == tot_h_8 - 100.0


def test_generate_single_pdf_with_table_and_footer_shift(tmp_path):
    out_pdf = str(tmp_path / "student_report_table.pdf")

    template_state = {
        "version": "1.0",
        "template_id": "test-table-template",
        "template_name": "Marksheet with Table",
        "canvas_width": 595.0,
        "canvas_height": 842.0,
        "background": {"type": "image", "path": ""},
        "fields": [
            # Header field above table
            {
                "label": "Student Name",
                "mapped_column": "Name",
                "x": 50.0,
                "y": 60.0,
                "width": 250.0,
                "height": 25.0,
                "font_size": 14,
            },
            # Footer field below table (y=350)
            {
                "label": "Teacher Remarks",
                "mapped_column": "Remarks",
                "x": 50.0,
                "y": 350.0,
                "width": 300.0,
                "height": 30.0,
                "font_size": 11,
            },
        ],
        "charts": [],
        "badges": [],
        "photos": [],
        "qr_codes": [],
        "tables": [
            {
                "label": "Subject Marks Table",
                "x": 50.0,
                "y": 120.0,
                "width": 450.0,
                "height": 100.0,  # Designed for small table
                "subject_columns": ["English", "Mathematics", "Science", "Social Studies", "Hindi", "French"],
                "show_max_marks": True,
                "show_grade": True,
                "max_marks": 100.0,
                "row_height": 25.0,
                "font_size": 10,
                "header_bg": "#1e3a8a",
                "header_color": "#ffffff",
                "alt_row_bg": "#f1f5f9",
                "border_color": "#94a3b8",
            }
        ],
    }

    row_data = {
        "Name": "Eleanor Vance",
        "English": "85",
        "Mathematics": "96",
        "Science": "90",
        "Social Studies": "82",
        "Hindi": "79",
        "French": "94",
        "Remarks": "Promoted with Distinction",
    }

    generate_single_pdf(template_state, row_data, out_pdf)
    assert os.path.exists(out_pdf)
    assert os.path.getsize(out_pdf) > 0

    doc = pymupdf.open(out_pdf)
    assert len(doc) == 1
    page = doc[0]

    # Verify text rendered on the page
    text = page.get_text()
    assert "Eleanor Vance" in text
    assert "Mathematics" in text
    assert "Science" in text
    assert "French" in text
    assert "Promoted with Distinction" in text
    assert "Grade" in text
    assert "Marks Obtained" in text

    # Verify drawing operations occurred (table borders, cell rectangles)
    drawings = page.get_drawings()
    assert len(drawings) > 0
    doc.close()

