"""
tests/test_presets.py
Test suite for Phase 4.3: Built-In Production Template Library & Preset Selector.
Validates generation of offline vector background PDFs, pre-mapped JSON configurations,
preset loading integrity, TemplatePresetDialog modal, and TemplateEditorView integration.
"""
from __future__ import annotations

import os
import pymupdf
import pytest
from PyQt6.QtWidgets import QApplication

from utils.preset_manager import (
    ensure_presets_built,
    load_preset_template_state,
    PRESETS_DIR,
)
from ui.dialogs.preset_dialog import TemplatePresetDialog
from ui.views.template_editor_view import TemplateEditorView


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


# ── 1. Presets Generation & Metadata ─────────────────────────────────────────

def test_ensure_presets_built():
    presets = ensure_presets_built()
    assert len(presets) == 3

    preset_ids = [p["id"] for p in presets]
    assert "school_marksheet" in preset_ids
    assert "certificate_merit" in preset_ids
    assert "student_id_card" in preset_ids

    for p in presets:
        assert os.path.exists(p["bg_path"]), f"Background PDF missing for {p['id']}"
        assert os.path.exists(p["json_path"]), f"JSON config missing for {p['id']}"
        assert len(p["name"]) > 0
        assert len(p["description"]) > 0
        assert len(p["category"]) > 0
        assert len(p["recommended_cols"]) > 0
        assert len(p["dimensions"]) == 2


# ── 2. Vector PDF Visual & Geometric Integrity ───────────────────────────────

def test_marksheet_background_pdf():
    presets = {p["id"]: p for p in ensure_presets_built()}
    p = presets["school_marksheet"]
    doc = pymupdf.open(p["bg_path"])
    assert len(doc) == 1
    page = doc[0]
    assert pytest.approx(page.rect.width, 1.0) == 595.0
    assert pytest.approx(page.rect.height, 1.0) == 842.0

    text = page.get_text()
    assert "DELHI PUBLIC ACADEMY" in text
    assert "REPORT CARD" in text
    assert "STUDENT PROFILE" in text
    doc.close()


def test_certificate_background_pdf():
    presets = {p["id"]: p for p in ensure_presets_built()}
    p = presets["certificate_merit"]
    doc = pymupdf.open(p["bg_path"])
    assert len(doc) == 1
    page = doc[0]
    # Landscape A4: 842 x 595
    assert pytest.approx(page.rect.width, 1.0) == 842.0
    assert pytest.approx(page.rect.height, 1.0) == 595.0

    text = page.get_text()
    assert "CERTIFICATE OF MERIT" in text
    assert "PRESENTED TO" in text
    doc.close()


def test_id_card_background_pdf():
    presets = {p["id"]: p for p in ensure_presets_built()}
    p = presets["student_id_card"]
    doc = pymupdf.open(p["bg_path"])
    assert len(doc) == 1
    page = doc[0]
    # CR80 standard: 242 x 153
    assert pytest.approx(page.rect.width, 1.0) == 242.0
    assert pytest.approx(page.rect.height, 1.0) == 153.0

    text = page.get_text()
    assert "STUDENT IDENTITY CARD" in text
    doc.close()


# ── 3. Preset JSON Layout Configurations ─────────────────────────────────────

def test_marksheet_json_state():
    state = load_preset_template_state("school_marksheet")
    assert state is not None
    assert state["template_name"] == "Standard School Marksheet"
    assert pytest.approx(state["canvas_width"], 1.0) == 595.0
    assert pytest.approx(state["canvas_height"], 1.0) == 842.0

    # Verify background path is valid and absolute
    bg_path = state["background"]["path"]
    assert os.path.isabs(bg_path)
    assert os.path.exists(bg_path)

    # Check pre-mapped items
    field_labels = [f["label"] for f in state.get("fields", [])]
    assert "Student Name" in field_labels
    assert "Roll No" in field_labels
    assert "Class" in field_labels
    assert "Calculated Grade" in field_labels
    assert "Result Status" in field_labels

    # Verify table item
    assert len(state.get("tables", [])) >= 1
    table = state["tables"][0]
    assert table["item_type"] == "table"
    assert "Subject" in table["columns"]
    assert "Marks Obtained" in table["columns"]

    # Verify photo item
    assert len(state.get("photos", [])) >= 1
    assert state["photos"][0]["item_type"] == "photo"

    # Verify QR item
    assert len(state.get("qrs", [])) >= 1
    assert state["qrs"][0]["item_type"] == "qr"


def test_certificate_json_state():
    state = load_preset_template_state("certificate_merit")
    assert state is not None
    assert state["template_name"] == "Certificate of Merit"
    assert pytest.approx(state["canvas_width"], 1.0) == 842.0
    assert pytest.approx(state["canvas_height"], 1.0) == 595.0

    field_labels = [f["label"] for f in state.get("fields", [])]
    assert "Student Name" in field_labels
    assert "Achievement Details" in field_labels

    # Verify QR & Badges
    assert len(state.get("qrs", [])) >= 1
    assert len(state.get("badges", [])) >= 1


def test_id_card_json_state():
    state = load_preset_template_state("student_id_card")
    assert state is not None
    assert state["template_name"] == "Student Identity Card"
    assert pytest.approx(state["canvas_width"], 1.0) == 242.0
    assert pytest.approx(state["canvas_height"], 1.0) == 153.0

    field_labels = [f["label"] for f in state.get("fields", [])]
    assert "Student Name" in field_labels
    assert "Roll No" in field_labels
    assert "Date of Birth" in field_labels

    # Verify photo & QR
    assert len(state.get("photos", [])) >= 1
    assert len(state.get("qrs", [])) >= 1


def test_load_preset_invalid():
    assert load_preset_template_state("non_existent_preset_xyz") is None


# ── 4. TemplatePresetDialog Modal UI ─────────────────────────────────────────

def test_preset_dialog_ui(qapp):
    dlg = TemplatePresetDialog()
    assert dlg._preset_list.count() == 3

    # Switch selections and verify preview and description update
    for row in range(3):
        dlg._preset_list.setCurrentRow(row)
        assert not dlg._preview_lbl.pixmap().isNull()
        assert len(dlg._details_lbl.text()) > 20

    # Test load clicked
    dlg._preset_list.setCurrentRow(0)
    dlg._on_load_clicked()
    assert dlg.selected_preset_state is not None
    assert dlg.selected_preset_state["template_name"] == "Standard School Marksheet"


# ── 5. TemplateEditorView Integration ────────────────────────────────────────

def test_template_editor_view_preset_button_and_loading(qapp):
    editor = TemplateEditorView()
    assert hasattr(editor, "_presets_btn")
    assert editor._presets_btn.isEnabled() is True

    # Test locking disables presets button
    editor.set_locked_state(True, reason="Active Dataset")
    assert editor._presets_btn.isEnabled() is False
    editor.set_locked_state(False)
    assert editor._presets_btn.isEnabled() is True

    # Load School Marksheet preset
    marksheet_state = load_preset_template_state("school_marksheet")
    editor._restore_state(marksheet_state)

    assert editor._template_name == "Standard School Marksheet"
    assert pytest.approx(editor._scene.sceneRect().width(), 1.0) == 595.0
    assert pytest.approx(editor._scene.sceneRect().height(), 1.0) == 842.0
    assert len(editor._field_items) >= 10
    assert len(editor._table_items) == 1
    assert len(editor._photo_items) == 1
    assert len(editor._qr_items) == 1
    assert len(editor._badge_items) == 1

    # Load ID Card preset
    id_card_state = load_preset_template_state("student_id_card")
    editor._restore_state(id_card_state)

    assert editor._template_name == "Student Identity Card"
    assert pytest.approx(editor._scene.sceneRect().width(), 1.0) == 242.0
    assert pytest.approx(editor._scene.sceneRect().height(), 1.0) == 153.0
    assert len(editor._field_items) >= 5
    assert len(editor._table_items) == 0
    assert len(editor._photo_items) == 1
    assert len(editor._qr_items) == 1

