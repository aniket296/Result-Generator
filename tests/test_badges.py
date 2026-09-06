"""
Tests for BadgeItem and conditional rules engine in PDF generation.
"""
from __future__ import annotations

import os
import tempfile
import pytest
from PIL import Image

from ui.widgets.badge_item import BadgeItem
from generation.pdf_generator import _evaluate_badge_rule, generate_single_pdf


class TestBadgeItem:
    def test_badge_item_initialization(self):
        item = BadgeItem(label="Distinction Badge", x=100, y=120, width=150, height=150)
        assert item.label == "Distinction Badge"
        assert item.width == 150.0
        assert item.height == 150.0
        assert item.rule_column == ""
        assert item.rule_operator == ">="
        assert item.rule_value == "0"
        assert item.badge_image_path == ""

    def test_badge_item_to_dict_and_from_dict(self):
        item = BadgeItem(label="Top Rank", x=80, y=90, width=110, height=110)
        item.rule_column = "Rank"
        item.rule_operator = "=="
        item.rule_value = "1"
        item.badge_image_path = "assets/rank1.png"

        d = item.to_dict()
        assert d["item_type"] == "badge"
        assert d["label"] == "Top Rank"
        assert d["rule_column"] == "Rank"
        assert d["rule_operator"] == "=="
        assert d["rule_value"] == "1"
        assert d["badge_image_path"] == "assets/rank1.png"
        assert d["width"] == 110.0
        assert d["height"] == 110.0

        item2 = BadgeItem.from_dict(d)
        assert item2.label == "Top Rank"
        assert item2.rule_column == "Rank"
        assert item2.rule_operator == "=="
        assert item2.rule_value == "1"
        assert item2.badge_image_path == "assets/rank1.png"
        assert item2.width == 110.0
        assert item2.height == 110.0


class TestBadgeRulesEngine:
    def test_numeric_comparisons(self):
        row = {"Marks": "85", "Total": "450"}
        assert _evaluate_badge_rule("Marks", ">=", "80", row) is True
        assert _evaluate_badge_rule("Marks", ">", "85", row) is False
        assert _evaluate_badge_rule("Marks", "<=", "85", row) is True
        assert _evaluate_badge_rule("Marks", "<", "90", row) is True
        assert _evaluate_badge_rule("Total", "==", "450", row) is True
        assert _evaluate_badge_rule("Total", "!=", "450", row) is False

    def test_percentage_strings(self):
        row = {"Percentage": "94.5%"}
        assert _evaluate_badge_rule("Percentage", ">=", "90", row) is True
        assert _evaluate_badge_rule("Percentage", ">=", "90%", row) is True
        assert _evaluate_badge_rule("Percentage", "<", "90", row) is False

    def test_string_equality(self):
        row = {"Grade": "A+", "Result": "PASSED"}
        assert _evaluate_badge_rule("Grade", "==", "A+", row) is True
        assert _evaluate_badge_rule("Grade", "==", "a+", row) is True  # Case-insensitive
        assert _evaluate_badge_rule("Grade", "!=", "B", row) is True
        assert _evaluate_badge_rule("Result", "==", "PASSED", row) is True

    def test_empty_and_nan_handling(self):
        row = {"Score": "", "Grade": "nan"}
        assert _evaluate_badge_rule("Score", ">=", "50", row) is False
        assert _evaluate_badge_rule("Grade", ">=", "50", row) is False
        assert _evaluate_badge_rule("MissingCol", ">=", "50", row) is False

    def test_pdf_generation_conditional_badge(self):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f_img:
            img_path = f_img.name
        img = Image.new("RGBA", (80, 80), color=(255, 215, 0, 255))
        img.save(img_path)

        template_state = {
            "version": "1.0",
            "template_id": "test-badge-id",
            "template_name": "TestBadge",
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
            "badges": [
                {
                    "item_type": "badge",
                    "label": "Gold Medal",
                    "badge_image_path": img_path,
                    "rule_column": "Total",
                    "rule_operator": ">=",
                    "rule_value": "400",
                    "x": 550,
                    "y": 50,
                    "width": 80,
                    "height": 80,
                }
            ],
        }

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f_a:
            pdf_a = f_a.name
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f_b:
            pdf_b = f_b.name

        try:
            # Student A has 450 -> Badge stamped
            generate_single_pdf(template_state, {"Name": "Alice", "Total": "450"}, pdf_a)
            # Student B has 350 -> Badge skipped
            generate_single_pdf(template_state, {"Name": "Bob", "Total": "350"}, pdf_b)

            assert os.path.exists(pdf_a)
            assert os.path.exists(pdf_b)
            assert os.path.getsize(pdf_a) > os.path.getsize(pdf_b)
        finally:
            for p in (img_path, pdf_a, pdf_b):
                if os.path.exists(p):
                    os.unlink(p)

