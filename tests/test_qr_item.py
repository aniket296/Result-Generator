"""
tests/test_qr_item.py
Unit tests for QRItem widget, payload interpolation, PNG generation, and PDF stamping.
"""
from __future__ import annotations

import os
import tempfile
import pytest
import pymupdf

from ui.widgets.qr_item import QRItem, DEFAULT_QR_PAYLOAD
from generation.pdf_generator import (
    _interpolate_qr_payload,
    _generate_qr_png_bytes,
    generate_single_pdf,
    _QRCODE_AVAILABLE,
)


def test_qr_item_defaults():
    item = QRItem(label="VerifyQR", x=50.0, y=60.0, width=90.0, height=90.0)
    assert item.label == "VerifyQR"
    assert item.pos().x() == 50.0
    assert item.pos().y() == 60.0
    assert item.qr_payload == DEFAULT_QR_PAYLOAD
    assert item.qr_payload_template == DEFAULT_QR_PAYLOAD
    assert item.border_cells == 1


def test_qr_item_setters():
    item = QRItem()
    item.set_qr_payload("ID:[Roll] Name:[Name]")
    assert item.qr_payload == "ID:[Roll] Name:[Name]"
    assert item.qr_payload_template == "ID:[Roll] Name:[Name]"

    item.set_qr_payload_template("New:[Template]")
    assert item.qr_payload == "New:[Template]"

    item.set_border_cells(3)
    assert item.border_cells == 3


def test_qr_item_serialization_roundtrip():
    item = QRItem(
        label="StudentQR",
        x=120.0,
        y=150.0,
        width=100.0,
        height=100.0,
        qr_payload="ID:[Enrollment number] | Total:[Total Marks]",
        border_cells=2,
    )
    d = item.to_dict()
    assert d["item_type"] == "qr"
    assert d["label"] == "StudentQR"
    assert d["x"] == 120.0
    assert d["y"] == 150.0
    assert d["width"] == 100.0
    assert d["height"] == 100.0
    assert d["qr_payload"] == "ID:[Enrollment number] | Total:[Total Marks]"
    assert d["qr_payload_template"] == "ID:[Enrollment number] | Total:[Total Marks]"
    assert d["border_cells"] == 2

    restored = QRItem.from_dict(d)
    assert restored.label == "StudentQR"
    assert restored.pos().x() == 120.0
    assert restored.pos().y() == 150.0
    assert restored.qr_payload == "ID:[Enrollment number] | Total:[Total Marks]"
    assert restored.border_cells == 2


def test_interpolate_qr_payload():
    row = {
        "Enrollment number": "EN12345",
        "Student Name": "Alice Smith",
        "Total": "480",
        "Result_Status": "PASS",
    }
    template = "ID: [Enrollment number] | Name: [Student Name] | Marks: [Total] | Status: [Result_Status]"
    res = _interpolate_qr_payload(template, row)
    assert res == "ID: EN12345 | Name: Alice Smith | Marks: 480 | Status: PASS"


def test_interpolate_qr_payload_fuzzy_header():
    row = {
        "Enrollment_Number": "EN999",
        "Name": "Bob",
    }
    template = "ID:[enrollment number] Name:[name]"
    res = _interpolate_qr_payload(template, row)
    assert res == "ID:EN999 Name:Bob"


def test_interpolate_qr_payload_missing_token():
    row = {"Name": "Charlie"}
    template = "Name:[Name] Dept:[Department]"
    res = _interpolate_qr_payload(template, row)
    assert res == "Name:Charlie Dept:[Department]"


def test_generate_qr_png_bytes():
    if not _QRCODE_AVAILABLE:
        pytest.skip("qrcode library not installed")

    payload = "ID: EN12345 | Name: Alice | Status: PASS"
    png_bytes = _generate_qr_png_bytes(payload, box_size=8, border=2)
    assert isinstance(png_bytes, bytes)
    assert len(png_bytes) > 0
    # PNG signature check: \x89PNG\r\n\x1a\n
    assert png_bytes.startswith(b"\x89PNG\r\n\x1a\n")


def test_generate_single_pdf_with_qr(tmp_path):
    if not _QRCODE_AVAILABLE:
        pytest.skip("qrcode library not installed")

    out_file = str(tmp_path / "student_with_qr.pdf")
    template_state = {
        "version": "1.0",
        "template_id": "test-qr-template",
        "template_name": "QR Certificate",
        "canvas_width": 595.0,
        "canvas_height": 842.0,
        "background": {"type": "image", "path": ""},
        "fields": [
            {
                "label": "Name",
                "mapped_column": "Name",
                "x": 50.0,
                "y": 50.0,
                "width": 200.0,
                "height": 30.0,
                "font_size": 14,
            }
        ],
        "charts": [],
        "badges": [],
        "photos": [],
        "qr_codes": [
            {
                "label": "Verification QR",
                "qr_payload": "ID: [Roll No] | Name: [Name] | Status: [Status]",
                "border_cells": 1,
                "x": 400.0,
                "y": 50.0,
                "width": 80.0,
                "height": 80.0,
            }
        ],
    }

    row_data = {
        "Roll No": "101",
        "Name": "Diana Prince",
        "Status": "PROMOTED",
    }

    generate_single_pdf(template_state, row_data, out_file)
    assert os.path.exists(out_file)
    assert os.path.getsize(out_file) > 0

    doc = pymupdf.open(out_file)
    assert len(doc) == 1
    page = doc[0]
    # Check that an image was inserted on the page
    images = page.get_images()
    assert len(images) >= 1
    doc.close()

