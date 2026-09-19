"""
tests/test_imposition.py
Test suite for Phase 4.2: Print Imposition Engine (N-Up Multi-Card Layouts)
Validates 2-Up, 8-Up, and 10-Up sheet tiling, dashed cutting guides,
encrypted source PDF handling, Dashboard and Setup Dialog UI controls,
and GeneratorWorker integration.
"""
from __future__ import annotations

import os
import pymupdf
import pytest
from PyQt6.QtWidgets import QApplication

from generation.imposition import (
    create_imposed_print_sheet,
    normalize_imposition_mode,
    MODE_2UP,
    MODE_8UP,
    MODE_10UP,
)
from generation.pdf_generator import (
    GeneratorWorker,
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


def _create_sample_pdf(filepath: str, width: float, height: float, text: str, password: str | None = None) -> str:
    """Helper to generate a lightweight test PDF with specific dimensions and optional password."""
    doc = pymupdf.open()
    page = doc.new_page(width=width, height=height)
    page.draw_rect(pymupdf.Rect(10, 10, width - 10, height - 10), color=(0.2, 0.4, 0.8), width=1.5)
    page.insert_text(pymupdf.Point(20, height / 2), text, fontsize=14, color=(0, 0, 0))

    if password:
        perm = int(
            pymupdf.PDF_PERM_PRINT
            | pymupdf.PDF_PERM_COPY
            | pymupdf.PDF_PERM_ACCESSIBILITY
        )
        doc.save(
            filepath,
            encryption=pymupdf.PDF_ENCRYPT_AES_256,
            user_pw=password,
            owner_pw=f"{password}_owner",
            permissions=perm,
        )
    else:
        doc.save(filepath)
    doc.close()
    return filepath


# ── 1. Mode Normalization ───────────────────────────────────────────────────

def test_normalize_imposition_mode():
    assert normalize_imposition_mode("2-up") == MODE_2UP
    assert normalize_imposition_mode("2UP") == MODE_2UP
    assert normalize_imposition_mode("2") == MODE_2UP
    assert normalize_imposition_mode("8-up") == MODE_8UP
    assert normalize_imposition_mode("8UP") == MODE_8UP
    assert normalize_imposition_mode("8") == MODE_8UP
    assert normalize_imposition_mode("10-up") == MODE_10UP
    assert normalize_imposition_mode("10UP") == MODE_10UP
    assert normalize_imposition_mode("10") == MODE_10UP
    # Fallback to 2-up
    assert normalize_imposition_mode("unknown") == MODE_2UP
    assert normalize_imposition_mode("") == MODE_2UP
    assert normalize_imposition_mode(None) == MODE_2UP


# ── 2. 2-Up Imposition (Side-by-Side Landscape A4) ──────────────────────────

def test_create_imposed_print_sheet_2up(tmp_path):
    """Test 3 A5 documents imposed onto 2-up landscape A4 sheets."""
    pdf_paths = []
    for i in range(1, 4):
        p = str(tmp_path / f"a5_doc_{i}.pdf")
        _create_sample_pdf(p, width=420.0, height=595.0, text=f"A5 Document {i}")
        pdf_paths.append(p)

    out_sheet = str(tmp_path / "Imposed_2Up.pdf")
    res = create_imposed_print_sheet(
        pdf_paths=pdf_paths,
        output_path=out_sheet,
        mode=MODE_2UP,
        draw_cutting_guides=True,
    )

    assert res == out_sheet
    assert os.path.exists(out_sheet)

    doc = pymupdf.open(out_sheet)
    # 3 items placed at 2 per page -> 2 landscape A4 pages
    assert len(doc) == 2

    # Check landscape A4 dimensions (842 x 595 pt)
    page1 = doc[0]
    assert pytest.approx(page1.rect.width, 1.0) == 842.0
    assert pytest.approx(page1.rect.height, 1.0) == 595.0

    page2 = doc[1]
    assert pytest.approx(page2.rect.width, 1.0) == 842.0
    assert pytest.approx(page2.rect.height, 1.0) == 595.0
    doc.close()


# ── 3. 8-Up Imposition (2x4 Grid Portrait A4) ───────────────────────────────

def test_create_imposed_print_sheet_8up(tmp_path):
    """Test 10 ID cards imposed onto 8-up portrait A4 sheets."""
    pdf_paths = []
    for i in range(1, 11):
        p = str(tmp_path / f"card_8up_{i}.pdf")
        _create_sample_pdf(p, width=260.0, height=180.0, text=f"ID Card {i}")
        pdf_paths.append(p)

    out_sheet = str(tmp_path / "Imposed_8Up.pdf")
    res = create_imposed_print_sheet(
        pdf_paths=pdf_paths,
        output_path=out_sheet,
        mode=MODE_8UP,
        draw_cutting_guides=True,
    )

    assert res == out_sheet
    assert os.path.exists(out_sheet)

    doc = pymupdf.open(out_sheet)
    # 10 cards at 8 per page -> 2 portrait A4 pages (8 on page 1, 2 on page 2)
    assert len(doc) == 2

    page1 = doc[0]
    assert pytest.approx(page1.rect.width, 1.0) == 595.0
    assert pytest.approx(page1.rect.height, 1.0) == 842.0
    doc.close()


# ── 4. 10-Up Imposition (2x5 Grid Portrait A4) ──────────────────────────────

def test_create_imposed_print_sheet_10up_cutting_guides(tmp_path):
    """Test 12 standard CR80 ID cards imposed onto 10-up portrait A4 sheets with cutting guides."""
    pdf_paths = []
    for i in range(1, 13):
        p = str(tmp_path / f"card_10up_{i}.pdf")
        _create_sample_pdf(p, width=242.0, height=153.0, text=f"Student ID #{i}")
        pdf_paths.append(p)

    out_sheet = str(tmp_path / "Imposed_10Up.pdf")
    res = create_imposed_print_sheet(
        pdf_paths=pdf_paths,
        output_path=out_sheet,
        mode=MODE_10UP,
        draw_cutting_guides=True,
    )

    assert res == out_sheet
    assert os.path.exists(out_sheet)

    doc = pymupdf.open(out_sheet)
    # 12 cards at 10 per page -> 2 portrait A4 pages (10 on page 1, 2 on page 2)
    assert len(doc) == 2

    for page in doc:
        assert pytest.approx(page.rect.width, 1.0) == 595.0
        assert pytest.approx(page.rect.height, 1.0) == 842.0

    doc.close()


# ── 5. Encrypted Source PDFs Imposition ──────────────────────────────────────

def test_create_imposed_print_sheet_encrypted_sources(tmp_path):
    """Verify that password-protected student PDFs are authenticated and imposed properly."""
    pdf_paths = []
    passwords = {}
    for i in range(1, 3):
        p = str(tmp_path / f"enc_student_{i}.pdf")
        pw = f"Pass_{i}#2026"
        _create_sample_pdf(p, width=420.0, height=595.0, text=f"Student {i}", password=pw)
        pdf_paths.append(p)
        passwords[p] = pw

    out_sheet = str(tmp_path / "Imposed_Encrypted_Source.pdf")
    res = create_imposed_print_sheet(
        pdf_paths=pdf_paths,
        output_path=out_sheet,
        mode=MODE_2UP,
        draw_cutting_guides=True,
        passwords_by_file=passwords,
    )

    assert res == out_sheet
    assert os.path.exists(out_sheet)

    doc = pymupdf.open(out_sheet)
    # Resulting print-ready sheet is unencrypted for the print shop operator
    assert doc.is_encrypted is False
    assert len(doc) == 1
    doc.close()


# ── 6. Edge Cases: Empty & Missing Files ─────────────────────────────────────

def test_create_imposed_print_sheet_empty(tmp_path):
    out_sheet = str(tmp_path / "Empty.pdf")
    res = create_imposed_print_sheet([], out_sheet, mode=MODE_2UP)
    assert res is None
    assert not os.path.exists(out_sheet)


def test_create_imposed_print_sheet_missing_files(tmp_path):
    p1 = str(tmp_path / "valid.pdf")
    _create_sample_pdf(p1, 420.0, 595.0, "Valid Doc")
    missing = str(tmp_path / "does_not_exist.pdf")

    out_sheet = str(tmp_path / "Imposed_Partial.pdf")
    res = create_imposed_print_sheet([p1, missing], out_sheet, mode=MODE_2UP)
    assert res == out_sheet
    assert os.path.exists(out_sheet)

    doc = pymupdf.open(out_sheet)
    assert len(doc) == 1
    doc.close()


# ── 7. UI Controls: DashboardView Integration ───────────────────────────────

def test_dashboard_view_imposition_options(qapp):
    dash = DashboardView()
    enabled, mode, guides = dash.get_imposition_options()
    assert isinstance(enabled, bool)
    assert mode in ("2-up", "8-up", "10-up")
    assert isinstance(guides, bool)

    # Test toggling
    dash._impose_cb.setChecked(True)
    dash._impose_mode_combo.setCurrentIndex(dash._impose_mode_combo.findData("10-up"))
    dash._impose_guides_cb.setChecked(False)

    e, m, g = dash.get_imposition_options()
    assert e is True
    assert m == "10-up"
    assert g is False

    # Check controls visibility (using isHidden since parent window is not shown)
    assert not dash._impose_mode_lbl.isHidden()
    assert not dash._impose_mode_combo.isHidden()
    assert not dash._impose_guides_cb.isHidden()

    dash._impose_cb.setChecked(False)
    assert dash._impose_mode_lbl.isHidden()
    assert dash._impose_mode_combo.isHidden()
    assert dash._impose_guides_cb.isHidden()


# ── 8. UI Controls: GenerationSetupDialog Integration ────────────────────────

def test_generation_setup_dialog_imposition_properties(qapp):
    headers = ["Roll No", "Student Name", "Class"]
    rows = [{"Roll No": "101", "Student Name": "Alice", "Class": "10-A"}]

    dlg = GenerationSetupDialog(
        template_name="ID Card",
        headers=headers,
        rows=rows,
        init_impose_enabled=True,
        init_impose_mode="8-up",
        init_impose_guides=False,
    )

    assert dlg.impose_enabled is True
    assert dlg.impose_mode == "8-up"
    assert dlg.impose_guides is False

    dlg._impose_cb.setChecked(False)
    assert dlg.impose_enabled is False


# ── 9. GeneratorWorker End-to-End Imposition ────────────────────────────────

def test_generator_worker_imposition_batch(tmp_path, qapp):
    """Verify GeneratorWorker creates Print_Ready_Imposed.pdf when impose_enabled is True."""
    out_dir = str(tmp_path / "output_imposed")
    os.makedirs(out_dir, exist_ok=True)

    template_state = {
        "canvas_width": 420.0,
        "canvas_height": 595.0,
        "fields": [
            {"label": "Student Name", "x": 30, "y": 30, "width": 150, "height": 25}
        ],
    }
    rows = [
        {"Roll No": "101", "Student Name": "Harry Potter"},
        {"Roll No": "102", "Student Name": "Hermione Granger"},
        {"Roll No": "103", "Student Name": "Ron Weasley"},
    ]

    worker = GeneratorWorker(
        template_state=template_state,
        rows=rows,
        output_dir=out_dir,
        unique_col="Roll No",
        name_col="Student Name",
        impose_enabled=True,
        impose_mode="2-up",
        impose_guides=True,
    )

    worker.run()

    expected_sheet = os.path.join(out_dir, "Print_Ready_Imposed.pdf")
    assert worker.created_imposition_path == expected_sheet
    assert os.path.exists(expected_sheet)

    doc = pymupdf.open(expected_sheet)
    # 3 records at 2 per page -> 2 landscape sheets
    assert len(doc) == 2
    assert pytest.approx(doc[0].rect.width, 1.0) == 842.0
    assert pytest.approx(doc[0].rect.height, 1.0) == 595.0
    doc.close()
