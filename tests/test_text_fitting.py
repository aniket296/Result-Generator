"""
Unit and integration tests for Phase 3.1: Auto-Flowing & Auto-Shrink Text Engine.
Tests text measurement, single-line font size stepping, multiline word-wrapping,
and boundary guards during PDF rendering.
"""

import os
import tempfile
import pytest
import pymupdf

from generation.pdf_generator import (
    measure_text_width,
    fit_single_line_font_size,
    fit_multiline_font_size,
    generate_single_pdf,
)


class TestTextMeasurementAndFittingHelpers:
    """Tests for standalone text measurement and fitting helper functions."""

    def test_measure_text_width_empty(self):
        assert measure_text_width("", "helv", 12.0) == 0.0
        assert measure_text_width(None, "helv", 12.0) == 0.0

    def test_measure_text_width_positive(self):
        w12 = measure_text_width("Alexander Hamilton", "helv", 12.0)
        w24 = measure_text_width("Alexander Hamilton", "helv", 24.0)
        assert w12 > 0.0
        assert w24 > w12
        # Approximately 2x for double font size
        assert abs(w24 - (w12 * 2.0)) < 1.0

    def test_fit_single_line_font_size_already_fits(self):
        # Short string in wide box should retain initial font size
        initial = 12.0
        fitted = fit_single_line_font_size("John", "helv", initial, max_width=200.0)
        assert fitted == initial

    def test_fit_single_line_font_size_shrinks_to_fit(self):
        long_name = "Dr. Christopher Bartholomew Montgomery-Fitzgerald III"
        initial = 20.0
        max_w = 120.0  # Narrow box

        fitted = fit_single_line_font_size(
            long_name, "helv", initial, max_width=max_w, min_size=4.0, step=0.5
        )

        assert fitted < initial
        assert fitted >= 4.0
        # Check that measured width at fitted size fits comfortably within max_w
        fitted_w = measure_text_width(long_name, "helv", fitted)
        assert fitted_w <= max_w

    def test_fit_single_line_font_size_respects_min_size(self):
        super_long = "A" * 500
        fitted = fit_single_line_font_size(
            super_long, "helv", 14.0, max_width=30.0, min_size=4.0, step=0.5
        )
        assert fitted == 4.0

    def test_fit_single_line_edge_cases(self):
        assert fit_single_line_font_size("", "helv", 12.0, 100.0) == 12.0
        assert fit_single_line_font_size("Test", "helv", 12.0, -10.0) == 12.0
        assert fit_single_line_font_size("Test", "helv", 12.0, 0.0) == 12.0

    def test_fit_multiline_font_size_already_fits(self):
        rect = pymupdf.Rect(0, 0, 300, 100)
        fitted = fit_multiline_font_size(rect, "Short remark.", "helv", 12.0)
        assert fitted == 12.0

    def test_fit_multiline_font_size_shrinks_to_fit(self):
        rect = pymupdf.Rect(0, 0, 120, 40)
        text = (
            "The student demonstrated consistent academic excellence and proactive "
            "engagement across all curriculum subjects during the academic year."
        )
        initial = 14.0
        fitted = fit_multiline_font_size(
            rect, text, "helv", initial, min_size=4.0, step=0.5
        )

        assert fitted < initial
        assert fitted >= 4.0

    def test_fit_multiline_font_size_min_size_limit(self):
        rect = pymupdf.Rect(0, 0, 30, 20)
        long_text = "Word " * 200
        fitted = fit_multiline_font_size(
            rect, long_text, "helv", 12.0, min_size=4.0, step=0.5
        )
        assert fitted == 4.0

    def test_fit_multiline_edge_cases(self):
        assert fit_multiline_font_size(pymupdf.Rect(0, 0, 0, 0), "Text", "helv", 12.0) == 12.0
        assert fit_multiline_font_size(pymupdf.Rect(0, 0, 100, 100), "", "helv", 12.0) == 12.0


class TestPDFGenerationWithAutoShrink:
    """Integration tests verifying PDF generation with single-line & multiline auto-shrink fields."""

    @pytest.fixture
    def blank_template_pdf(self, tmp_path):
        pdf_path = str(tmp_path / "blank_template.pdf")
        doc = pymupdf.open()
        doc.new_page(width=595.276, height=841.890)  # A4
        doc.save(pdf_path)
        doc.close()
        return pdf_path

    def test_single_line_long_name_auto_shrink(self, blank_template_pdf, tmp_path):
        out_pdf = str(tmp_path / "student_long_name.pdf")
        long_student_name = "Wolfeschlegelsteinhausenbergerdorff Velasquez von Hapsburg Senior"

        template_state = {
            "fields": [
                {
                    "mapped_column": "Student Name",
                    "label": "Student Name",
                    "x": 50,
                    "y": 100,
                    "width": 100,  # Tight bounding box (width 100)
                    "height": 25,
                    "font_family": "Helvetica",
                    "font_size": 18,
                    "color": "#000000",
                    "multiline": False,
                    "alignment": "Left",
                    "v_alignment": "Middle",
                }
            ],
            "badges": [],
            "charts": [],
            "photos": [],
            "qr_codes": [],
            "tables": [],
        }
        template_state["background"] = {"path": blank_template_pdf, "type": "pdf"}
        row_data = {"Student Name": long_student_name}

        generate_single_pdf(
            template_state=template_state,
            row_data=row_data,
            output_path=out_pdf,
        )

        assert os.path.exists(out_pdf)
        doc = pymupdf.open(out_pdf)
        page_text = doc[0].get_text()
        doc.close()

        assert "Wolfeschlegelsteinhausenbergerdorff" in page_text

    def test_multiline_remarks_auto_shrink(self, blank_template_pdf, tmp_path):
        out_pdf = str(tmp_path / "student_multiline_remarks.pdf")
        remarks = (
            "Outstanding performance throughout the academic session. Shows exceptional "
            "aptitude in mathematical reasoning, computer programming, and physics laboratory experiments. "
            "Consistently leads peer discussion groups with distinction."
        )

        template_state = {
            "fields": [
                {
                    "mapped_column": "Principal Remarks",
                    "label": "Principal Remarks",
                    "x": 50,
                    "y": 200,
                    "width": 150,  # 150pt box
                    "height": 50,  # 50pt height
                    "font_family": "Helvetica",
                    "font_size": 14,
                    "color": "#112233",
                    "multiline": True,
                    "alignment": "Left",
                    "v_alignment": "Top",
                }
            ],
            "badges": [],
            "charts": [],
            "photos": [],
            "qr_codes": [],
            "tables": [],
        }

        template_state["background"] = {"path": blank_template_pdf, "type": "pdf"}
        row_data = {"Principal Remarks": remarks}

        generate_single_pdf(
            template_state=template_state,
            row_data=row_data,
            output_path=out_pdf,
        )

        assert os.path.exists(out_pdf)
        doc = pymupdf.open(out_pdf)
        page_text = doc[0].get_text()
        doc.close()

        assert "Outstanding performance" in page_text
        assert "distinction" in page_text

    def test_alignment_variants_with_auto_shrink(self, blank_template_pdf, tmp_path):
        out_pdf = str(tmp_path / "alignments.pdf")

        template_state = {
            "fields": [
                {
                    "mapped_column": "Center_Middle",
                    "label": "Center_Middle",
                    "x": 50,
                    "y": 100,
                    "width": 80,
                    "height": 20,
                    "font_family": "Times",
                    "font_size": 16,
                    "multiline": False,
                    "alignment": "Center",
                    "v_alignment": "Middle",
                },
                {
                    "mapped_column": "Right_Bottom",
                    "label": "Right_Bottom",
                    "x": 50,
                    "y": 150,
                    "width": 80,
                    "height": 20,
                    "font_family": "Courier",
                    "font_size": 16,
                    "multiline": False,
                    "alignment": "Right",
                    "v_alignment": "Bottom",
                },
            ],
            "badges": [],
            "charts": [],
            "photos": [],
            "qr_codes": [],
            "tables": [],
        }
        template_state["background"] = {"path": blank_template_pdf, "type": "pdf"}

        row_data = {
            "Center_Middle": "Centrally Positioned Text Long",
            "Right_Bottom": "Right Aligned Text Long",
        }

        generate_single_pdf(
            template_state=template_state,
            row_data=row_data,
            output_path=out_pdf,
        )

        assert os.path.exists(out_pdf)
        doc = pymupdf.open(out_pdf)
        text = doc[0].get_text()
        doc.close()
        assert "Centrally" in text
        assert "Right Aligned" in text
