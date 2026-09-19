"""
tests/test_pdf_encryption.py
Test suite for Phase 4.1: Individual PDF Password Encryption
Validates AES-256 password protection, Dashboard settings integration,
GenerationSetupDialog configuration, and batch generation with student-specific credentials.
"""
from __future__ import annotations

import os
import pymupdf
import pytest
from PyQt6.QtWidgets import QApplication

from generation.pdf_generator import (
    GeneratorWorker,
    create_class_print_bundles,
    generate_single_pdf,
)
from ui.dialogs.generation_dialog import GenerationSetupDialog
from ui.views.dashboard_view import DashboardView


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


# ── 1. PyMuPDF Native AES-256 PDF Encryption ─────────────────────────────────

def test_generate_single_pdf_direct_password(tmp_path):
    """Verify that passing password parameter encrypts the PDF with AES-256."""
    out_pdf = str(tmp_path / "student_encrypted.pdf")
    template_state = {
        "canvas_width": 595.0,
        "canvas_height": 842.0,
        "fields": [
            {"label": "Student Name", "x": 50, "y": 50, "width": 200, "height": 30}
        ],
    }
    row_data = {"Student Name": "Harry Potter"}
    pw = "Gryffindor#2026"

    generate_single_pdf(template_state, row_data, out_pdf, password=pw)

    assert os.path.exists(out_pdf)

    # Open document and verify encryption flags
    doc = pymupdf.open(out_pdf)
    assert doc.is_encrypted is True
    assert doc.needs_pass == 1

    # Attempt wrong password
    auth_fail = doc.authenticate("WrongPassword")
    assert auth_fail == 0

    # Attempt correct password
    auth_success = doc.authenticate(pw)
    assert auth_success > 0

    # Text extraction succeeds after authentication
    text = doc[0].get_text()
    assert "Harry Potter" in text
    doc.close()


def test_generate_single_pdf_unencrypted_by_default(tmp_path):
    """Ensure standard output PDFs without password remain unencrypted."""
    out_pdf = str(tmp_path / "student_unencrypted.pdf")
    template_state = {
        "canvas_width": 595.0,
        "canvas_height": 842.0,
        "fields": [
            {"label": "Student Name", "x": 50, "y": 50, "width": 200, "height": 30}
        ],
    }
    row_data = {"Student Name": "Ron Weasley"}

    generate_single_pdf(template_state, row_data, out_pdf)

    assert os.path.exists(out_pdf)
    doc = pymupdf.open(out_pdf)
    assert doc.is_encrypted is False
    assert doc.needs_pass == 0
    text = doc[0].get_text()
    assert "Ron Weasley" in text
    doc.close()


def test_generate_single_pdf_template_state_encryption(tmp_path):
    """Verify that template_state with encrypt_pdf & password_column encrypts automatically."""
    out_pdf = str(tmp_path / "template_state_encrypted.pdf")
    template_state = {
        "canvas_width": 595.0,
        "canvas_height": 842.0,
        "encrypt_pdf": True,
        "password_column": "Date of Birth",
        "fields": [
            {"label": "Student Name", "x": 50, "y": 50, "width": 200, "height": 30}
        ],
    }
    row_data = {
        "Student Name": "Hermione Granger",
        "Date of Birth": "19-09-1979",
    }

    generate_single_pdf(template_state, row_data, out_pdf)

    assert os.path.exists(out_pdf)
    doc = pymupdf.open(out_pdf)
    assert doc.is_encrypted is True
    assert doc.authenticate("19-09-1979") > 0
    assert "Hermione Granger" in doc[0].get_text()
    doc.close()


# ── 2. Dashboard View Encryption Settings ─────────────────────────────────────

def test_dashboard_view_encryption_controls(qapp):
    dashboard = DashboardView()
    assert hasattr(dashboard, "_encrypt_cb")
    assert hasattr(dashboard, "_encrypt_col_combo")
    assert hasattr(dashboard, "_encrypt_col_lbl")

    # Initial toggle test
    dashboard._encrypt_cb.setChecked(False)
    assert dashboard._encrypt_col_lbl.isHidden() is True
    assert dashboard._encrypt_col_combo.isHidden() is True
    assert dashboard.get_encryption_options()[0] is False

    dashboard._encrypt_cb.setChecked(True)
    assert dashboard._encrypt_col_lbl.isHidden() is False
    assert dashboard._encrypt_col_combo.isHidden() is False
    assert dashboard.get_encryption_options()[0] is True

    # Ingest mock headers and verify candidate auto-selection
    mock_headers = ["Enrollment number", "Name", "Date of Birth", "Class"]
    dashboard._apply_dataset("test.xlsx", mock_headers, [{"Enrollment number": "E1", "Name": "Alice"}])

    assert dashboard._encrypt_col_combo.count() >= len(mock_headers)
    idx = dashboard._encrypt_col_combo.findText("Date of Birth")
    assert idx >= 0
    dashboard._encrypt_col_combo.setCurrentIndex(idx)
    assert dashboard._encrypt_col_combo.currentText() == "Date of Birth"
    assert dashboard.get_encryption_options() == (True, "Date of Birth")


# ── 3. Generation Setup Dialog Integration ───────────────────────────────────

def test_generation_setup_dialog_encryption_controls(qapp):
    headers = ["Roll No", "Student Name", "DOB", "Section"]
    rows = [{"Roll No": "101", "Student Name": "Bob", "DOB": "2008-05-12", "Section": "A"}]

    dialog = GenerationSetupDialog(
        template_name="Term Report",
        headers=headers,
        rows=rows,
        init_encryption_enabled=True,
        init_password_col="DOB",
    )

    assert dialog.encryption_enabled is True
    assert dialog.password_column == "DOB"

    # Toggle off
    dialog._encrypt_cb.setChecked(False)
    assert dialog.encryption_enabled is False
    assert dialog._encrypt_col_lbl.isHidden() is True
    assert dialog._encrypt_combo.isHidden() is True

    # Toggle on
    dialog._encrypt_cb.setChecked(True)
    assert dialog.encryption_enabled is True
    assert dialog._encrypt_col_lbl.isHidden() is False
    assert dialog._encrypt_combo.isHidden() is False


# ── 4. Batch GeneratorWorker with AES-256 Encryption ──────────────────────────

def test_generator_worker_encryption_batch(tmp_path, qapp):
    out_dir = str(tmp_path / "batch_out")
    os.makedirs(out_dir, exist_ok=True)

    template_state = {
        "template_name": "ReportCard",
        "canvas_width": 595.0,
        "canvas_height": 842.0,
        "fields": [
            {"label": "Name", "x": 50, "y": 50, "width": 200, "height": 30},
            {"label": "Total Marks", "x": 50, "y": 90, "width": 150, "height": 30},
        ],
    }
    rows = [
        {"Enrollment": "ENR001", "Name": "Student One", "Total Marks": "450", "DOB": "2007-01-10", "Class": "X-A"},
        {"Enrollment": "ENR002", "Name": "Student Two", "Total Marks": "480", "DOB": "2007-03-25", "Class": "X-A"},
    ]

    worker = GeneratorWorker(
        template_state=template_state,
        rows=rows,
        output_dir=out_dir,
        unique_col="Enrollment",
        name_col="Name",
        bundle_enabled=True,
        bundle_col="Class",
        encryption_enabled=True,
        password_column="DOB",
    )

    # Run batch synchronously for testing
    worker.run()

    # Verify both output files were generated and are encrypted with their respective DOBs
    assert len(worker.generated_files) == 2
    for i, row in enumerate(rows):
        pdf_file = worker.generated_files[i]
        assert os.path.exists(pdf_file)

        doc = pymupdf.open(pdf_file)
        assert doc.is_encrypted is True
        assert doc.authenticate(row["DOB"]) > 0
        text = doc[0].get_text()
        assert row["Name"] in text
        assert row["Total Marks"] in text
        doc.close()

    # Verify class master print bundle was merged successfully
    bundle_file = os.path.join(out_dir, "Print_Bundles", "Class_X-A_Master_Print.pdf")
    assert os.path.exists(bundle_file)
    bundle_doc = pymupdf.open(bundle_file)
    assert bundle_doc.page_count == 2
    bundle_doc.close()
