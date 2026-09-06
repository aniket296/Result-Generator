"""
Tests for ChartItem and matplotlib chart rendering in PDF generation.
"""
from __future__ import annotations

import os
import tempfile
import pytest

from ui.widgets.chart_item import ChartItem
from generation.pdf_generator import _render_chart_to_image, generate_single_pdf


class TestChartItem:
    def test_chart_item_initialization(self):
        item = ChartItem(label="Math Performance", x=50, y=100, width=320, height=220)
        assert item.label == "Math Performance"
        assert item.width == 320.0
        assert item.height == 220.0
        assert item.chart_columns == []
        assert item.chart_style == "vertical"

    def test_chart_item_to_dict_and_from_dict(self):
        item = ChartItem(label="Performance Chart", x=120, y=150, width=400, height=250)
        item.chart_columns = ["Math", "Physics", "Chemistry"]
        item.chart_style = "horizontal"

        d = item.to_dict()
        assert d["item_type"] == "chart"
        assert d["label"] == "Performance Chart"
        assert d["chart_columns"] == ["Math", "Physics", "Chemistry"]
        assert d["chart_style"] == "horizontal"
        assert d["width"] == 400.0
        assert d["height"] == 250.0

        item2 = ChartItem.from_dict(d)
        assert item2.label == "Performance Chart"
        assert item2.chart_columns == ["Math", "Physics", "Chemistry"]
        assert item2.chart_style == "horizontal"
        assert item2.width == 400.0
        assert item2.height == 250.0


class TestChartRendering:
    def test_render_chart_to_image_vertical(self):
        chart_spec = {
            "label": "Performance Chart",
            "chart_columns": ["Subject 1", "Subject 2", "Subject 3"],
            "chart_style": "vertical",
            "x": 0,
            "y": 0,
            "width": 300,
            "height": 200,
        }
        row_data = {"Subject 1": "85", "Subject 2": "92", "Subject 3": "78"}
        png_bytes = _render_chart_to_image(chart_spec, row_data, 300, 200)

        assert len(png_bytes) > 500
        assert png_bytes[:4] == b"\x89PNG"

    def test_render_chart_to_image_horizontal(self):
        chart_spec = {
            "label": "Performance Chart",
            "chart_columns": ["Math", "English"],
            "chart_style": "horizontal",
            "x": 0,
            "y": 0,
            "width": 350,
            "height": 180,
        }
        row_data = {"Math": "90", "English": "80"}
        png_bytes = _render_chart_to_image(chart_spec, row_data, 350, 180)

        assert len(png_bytes) > 500
        assert png_bytes[:4] == b"\x89PNG"

    def test_render_chart_missing_or_nan_data(self):
        chart_spec = {
            "label": "Performance Chart",
            "chart_columns": ["Subject 1", "Subject 2"],
            "chart_style": "vertical",
        }
        row_data = {"Subject 1": "nan", "Subject 2": ""}
        png_bytes = _render_chart_to_image(chart_spec, row_data, 300, 200)
        assert len(png_bytes) > 500

    def test_pdf_generation_with_chart(self):
        template_state = {
            "version": "1.0",
            "template_id": "test-chart-id",
            "template_name": "TestChart",
            "canvas_width": 794.0,
            "canvas_height": 1123.0,
            "background": {"type": "", "path": ""},
            "fields": [
                {
                    "label": "Name",
                    "mapped_column": "Name",
                    "is_unique": False,
                    "x": 50,
                    "y": 50,
                    "width": 200,
                    "height": 30,
                    "font_family": "Segoe UI",
                    "font_size": 12,
                    "color": "#000000",
                    "bold": False,
                    "italic": False,
                    "underline": False,
                    "multiline": False,
                    "alignment": "Left",
                }
            ],
            "charts": [
                {
                    "item_type": "chart",
                    "label": "Performance Chart",
                    "chart_columns": ["Math", "Science"],
                    "chart_style": "vertical",
                    "x": 50,
                    "y": 150,
                    "width": 350,
                    "height": 200,
                }
            ],
        }
        row_data = {"Name": "Charlie", "Math": "95", "Science": "88"}
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            pdf_path = f.name

        try:
            generate_single_pdf(template_state, row_data, pdf_path)
            assert os.path.exists(pdf_path)
            assert os.path.getsize(pdf_path) > 3000
        finally:
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)

