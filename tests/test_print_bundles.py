"""
Tests for Class-Wise Smart Print Bundling and PDF merging.
"""
from __future__ import annotations

import os
import tempfile
import pymupdf
import pytest

from generation.pdf_generator import (
    create_class_print_bundles,
    generate_single_pdf,
    GeneratorWorker,
)


class TestClassWisePrintBundling:
    def test_create_class_print_bundles_merging(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            # 1. Create 3 individual student PDFs (2 in Class 10-A, 1 in Class 10-B)
            template_state = {
                "version": "1.0",
                "template_id": "test-bundle-id",
                "template_name": "TestBundle",
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
            }

            pdf1 = os.path.join(temp_dir, "STU001_ALICE.PDF")
            pdf2 = os.path.join(temp_dir, "STU002_BOB.PDF")
            pdf3 = os.path.join(temp_dir, "STU003_CHARLIE.PDF")

            generate_single_pdf(template_state, {"Name": "Alice", "Class": "10-A"}, pdf1)
            generate_single_pdf(template_state, {"Name": "Bob", "Class": "10-A"}, pdf2)
            generate_single_pdf(template_state, {"Name": "Charlie", "Class": "10-B"}, pdf3)

            mappings = [
                ({"Name": "Alice", "Class": "10-A"}, pdf1),
                ({"Name": "Bob", "Class": "10-A"}, pdf2),
                ({"Name": "Charlie", "Class": "10-B"}, pdf3),
            ]

            # 2. Execute print bundling
            bundles = create_class_print_bundles(temp_dir, mappings, "Class")

            # 3. Assertions
            assert len(bundles) == 2

            bundle_dir = os.path.join(temp_dir, "Print_Bundles")
            assert os.path.exists(bundle_dir)

            bundle_10a = os.path.join(bundle_dir, "Class_10-A_Master_Print.pdf")
            bundle_10b = os.path.join(bundle_dir, "Class_10-B_Master_Print.pdf")

            assert os.path.exists(bundle_10a)
            assert os.path.exists(bundle_10b)

            # Check page counts
            doc_10a = pymupdf.open(bundle_10a)
            assert doc_10a.page_count == 2
            doc_10a.close()

            doc_10b = pymupdf.open(bundle_10b)
            assert doc_10b.page_count == 1
            doc_10b.close()

    def test_empty_mappings_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            bundles = create_class_print_bundles(temp_dir, [], "Class")
            assert bundles == []

    def test_missing_column_groups_into_unassigned(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            template_state = {
                "version": "1.0",
                "canvas_width": 794.0,
                "canvas_height": 1123.0,
                "fields": [],
            }
            pdf = os.path.join(temp_dir, "STU001.PDF")
            generate_single_pdf(template_state, {"Name": "David"}, pdf)

            mappings = [({"Name": "David"}, pdf)]
            bundles = create_class_print_bundles(temp_dir, mappings, "Class")
            assert len(bundles) == 1
            assert "Class_Unassigned_Master_Print.pdf" in bundles[0]

