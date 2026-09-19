"""
Tests for PhotoItem, student photo path resolution, and photo rendering in PDF generator.
"""
from __future__ import annotations

import os
import tempfile
import pytest
from PIL import Image
import pymupdf

from ui.widgets.photo_item import PhotoItem
from generation.pdf_generator import find_student_photo_path, generate_single_pdf


class TestPhotoItem:
    def test_photo_item_initialization(self):
        item = PhotoItem(label="Student Photo 1", x=120, y=140, width=100, height=120)
        assert item.label == "Student Photo 1"
        assert item.width == 100.0
        assert item.height == 120.0
        assert item.photo_id_column == ""
        assert item.border_color == "#6b7280"
        assert item.border_width == 1.0
        assert item.corner_radius == 4.0

    def test_photo_item_to_dict_and_from_dict(self):
        item = PhotoItem(
            label="Passport Photo",
            x=50.0,
            y=60.0,
            width=90.0,
            height=110.0,
            photo_id_column="Enrollment number",
            border_color="#2563eb",
            border_width=2.0,
            corner_radius=8.0,
        )

        d = item.to_dict()
        assert d["item_type"] == "photo"
        assert d["label"] == "Passport Photo"
        assert d["photo_id_column"] == "Enrollment number"
        assert d["border_color"] == "#2563eb"
        assert d["border_width"] == 2.0
        assert d["corner_radius"] == 8.0
        assert d["x"] == 50.0
        assert d["y"] == 60.0
        assert d["width"] == 90.0
        assert d["height"] == 110.0

        item2 = PhotoItem.from_dict(d)
        assert item2.label == "Passport Photo"
        assert item2.photo_id_column == "Enrollment number"
        assert item2.border_color == "#2563eb"
        assert item2.border_width == 2.0
        assert item2.corner_radius == 8.0
        assert item2.width == 90.0
        assert item2.height == 110.0


class TestStudentPhotoResolution:
    def test_find_student_photo_exact_and_extensions(self, tmp_path):
        photo_dir = str(tmp_path)

        # Create sample photos
        p1 = tmp_path / "STU101.jpg"
        p1.write_bytes(b"fake-jpg")
        p2 = tmp_path / "stu102.PNG"
        p2.write_bytes(b"fake-png")
        p3 = tmp_path / "STU103.jpeg"
        p3.write_bytes(b"fake-jpeg")

        assert find_student_photo_path(photo_dir, "STU101") is not None
        assert os.path.samefile(find_student_photo_path(photo_dir, "STU101"), str(p1))
        assert os.path.samefile(find_student_photo_path(photo_dir, "stu101"), str(p1))  # Case-insensitive
        assert os.path.samefile(find_student_photo_path(photo_dir, "STU102"), str(p2))
        assert os.path.samefile(find_student_photo_path(photo_dir, "STU103"), str(p3))
        assert find_student_photo_path(photo_dir, "NONEXISTENT") is None
        assert find_student_photo_path(photo_dir, "") is None
        assert find_student_photo_path("", "STU101") is None

    def test_pdf_generation_with_student_photo(self, tmp_path):
        photo_dir = str(tmp_path / "photos")
        os.makedirs(photo_dir, exist_ok=True)

        # Generate a real valid PIL image photo
        photo_path = os.path.join(photo_dir, "ENR2026.png")
        img = Image.new("RGB", (100, 120), color=(50, 120, 200))
        img.save(photo_path)

        template_state = {
            "version": "1.0",
            "template_id": "test-photo-id",
            "template_name": "TestPhotoTemplate",
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
                    "font_size": 12,
                    "color": "#000000",
                }
            ],
            "charts": [],
            "badges": [],
            "photos": [
                {
                    "label": "Student Photo",
                    "photo_id_column": "Enrollment number",
                    "x": 600,
                    "y": 50,
                    "width": 100,
                    "height": 120,
                    "border_color": "#1e40af",
                    "border_width": 2.0,
                    "corner_radius": 4.0,
                }
            ],
        }

        row_with_photo = {
            "Enrollment number": "ENR2026",
            "Name": "John Doe",
        }

        out_pdf = str(tmp_path / "result_john.pdf")
        generate_single_pdf(template_state, row_with_photo, out_pdf, photo_dir=photo_dir)

        assert os.path.exists(out_pdf)
        doc = pymupdf.open(out_pdf)
        assert len(doc) == 1
        page = doc[0]
        # Should contain text and image
        images = page.get_images()
        assert len(images) >= 1
        doc.close()

    def test_pdf_generation_missing_photo_graceful(self, tmp_path):
        photo_dir = str(tmp_path / "photos_empty")
        os.makedirs(photo_dir, exist_ok=True)

        template_state = {
            "version": "1.0",
            "template_id": "test-missing-photo-id",
            "template_name": "TestMissingPhoto",
            "canvas_width": 794.0,
            "canvas_height": 1123.0,
            "background": {"type": "", "path": ""},
            "fields": [
                {
                    "label": "Name",
                    "mapped_column": "Name",
                    "x": 50,
                    "y": 50,
                    "width": 200,
                    "height": 30,
                    "font_size": 12,
                    "color": "#000000",
                }
            ],
            "charts": [],
            "badges": [],
            "photos": [
                {
                    "label": "Student Photo",
                    "photo_id_column": "Enrollment number",
                    "x": 600,
                    "y": 50,
                    "width": 100,
                    "height": 120,
                    "border_color": "#6b7280",
                    "border_width": 1.0,
                }
            ],
        }

        row_missing_photo = {
            "Enrollment number": "ENR9999",  # Does not exist on disk
            "Name": "Jane Smith",
        }

        out_pdf = str(tmp_path / "result_jane.pdf")
        # Should generate without crashing
        generate_single_pdf(template_state, row_missing_photo, out_pdf, photo_dir=photo_dir)

        assert os.path.exists(out_pdf)
        doc = pymupdf.open(out_pdf)
        assert len(doc) == 1
        doc.close()
