"""
generation/imposition.py
Print Imposition Engine (N-Up Multi-Card & Document Layouts).

Supports:
- 2-Up Mode: Combines two A5 documents side-by-side onto a single landscape A4 sheet.
- 8-Up Mode: Tiles 8 ID cards (2x4) onto a single portrait A4 sheet.
- 10-Up Mode: Tiles 10 standard CR80 ID cards (2x5) onto a portrait A4 sheet.
- Optional dashed cutting guides between cards and sheets.
- Automatic authentication and page extraction for password-encrypted student PDFs.
- Consolidation into a single master Print_Ready_Imposed.pdf.
"""
from __future__ import annotations

import os
from typing import Any
import pymupdf

fitz = pymupdf

MODE_2UP = "2-up"
MODE_8UP = "8-up"
MODE_10UP = "10-up"

# Standard Dimensions in PDF points (72 points = 1 inch, 25.4 mm = 72 pt)
A4_WIDTH = 595.0
A4_HEIGHT = 842.0


def normalize_imposition_mode(mode: str) -> str:
    """Normalize user-facing or programmatic mode string to canonical mode identifier."""
    cleaned = (mode or "").strip().lower()
    if "2" in cleaned:
        return MODE_2UP
    if "8" in cleaned:
        return MODE_8UP
    if "10" in cleaned:
        return MODE_10UP
    return MODE_2UP


def _authenticate_doc_if_needed(
    doc: pymupdf.Document,
    pdf_path: str,
    row_data: dict[str, str] | None = None,
    password_col: str = "",
    passwords: list[str] | dict[str, str] | None = None,
) -> bool:
    """
    Authenticate an encrypted document using row data, password column,
    or explicit passwords dictionary/list.
    Returns True if document is accessible (unencrypted or successfully authenticated), False otherwise.
    """
    if not doc.needs_pass:
        return True

    # 1. Check explicit passwords dict or list
    if isinstance(passwords, dict):
        pw = passwords.get(pdf_path) or passwords.get(os.path.basename(pdf_path))
        if pw and doc.authenticate(str(pw).strip()) > 0:
            return True
    elif isinstance(passwords, list):
        for pw in passwords:
            if pw and doc.authenticate(str(pw).strip()) > 0:
                return True

    # 2. Check row_data password column
    if row_data:
        if password_col:
            pw = str(row_data.get(password_col, "") or "").strip()
            if pw and doc.authenticate(pw) > 0:
                return True

        # 3. Check common credential candidates
        for cand in [
            row_data.get("Date of Birth", ""),
            row_data.get("DOB", ""),
            row_data.get("Birth Date", ""),
            row_data.get("Enrollment number", ""),
            row_data.get("Enrollment", ""),
            row_data.get("Roll No", ""),
            row_data.get("ID", ""),
            row_data.get("Student ID", ""),
        ]:
            if cand and doc.authenticate(str(cand).strip()) > 0:
                return True

    return not doc.needs_pass


def _draw_cutting_guides(
    page: pymupdf.Page,
    mode: str,
    sheet_w: float,
    sheet_h: float,
    margin_x: float,
    margin_y: float,
    cell_w: float,
    cell_h: float,
    cols: int,
    rows: int,
) -> None:
    """Draw subtle dashed cutting guides on the sheet for trimming cards/pages."""
    guide_color = (0.6, 0.6, 0.6)
    dash_spec = "[3 3] 0"
    ext = 8.0  # guide line tick extension beyond card borders

    if mode == MODE_2UP:
        # Vertical center dividing cut line
        center_x = sheet_w / 2.0
        page.draw_line(
            pymupdf.Point(center_x, 0.0),
            pymupdf.Point(center_x, sheet_h),
            color=guide_color,
            width=0.75,
            dashes=dash_spec,
        )
        return

    # For 8-Up and 10-Up: grid boundary lines
    # Vertical lines
    for c in range(cols + 1):
        x = margin_x + c * cell_w
        page.draw_line(
            pymupdf.Point(x, max(0.0, margin_y - ext)),
            pymupdf.Point(x, min(sheet_h, margin_y + rows * cell_h + ext)),
            color=guide_color,
            width=0.6,
            dashes=dash_spec,
        )

    # Horizontal lines
    for r in range(rows + 1):
        y = margin_y + r * cell_h
        page.draw_line(
            pymupdf.Point(max(0.0, margin_x - ext), y),
            pymupdf.Point(min(sheet_w, margin_x + cols * cell_w + ext), y),
            color=guide_color,
            width=0.6,
            dashes=dash_spec,
        )


def create_imposed_print_sheet(
    input_pdf_paths: list[str] | None = None,
    output_pdf_path: str = "",
    mode: str = MODE_2UP,
    draw_cut_guides: bool = True,
    student_mappings: list[tuple[dict[str, str], str]] | None = None,
    password_col: str = "",
    passwords: list[str] | dict[str, str] | None = None,
    **kwargs: Any,
) -> str | None:
    """
    Imposes individual student PDF pages onto standardized master sheets
    and saves the result to output_pdf_path.

    Supported modes:
    - MODE_2UP ('2-up'): 2 portrait A5 documents side-by-side on landscape A4.
    - MODE_8UP ('8-up'): 8 ID cards (2 cols x 4 rows) on portrait A4.
    - MODE_10UP ('10-up'): 10 standard CR80 ID cards (2 cols x 5 rows) on portrait A4.

    Returns the absolute path to the generated imposed PDF file, or None if no inputs.
    """
    effective_paths = input_pdf_paths or kwargs.get("pdf_paths") or []
    effective_output = output_pdf_path or kwargs.get("output_path") or ""
    effective_guides = kwargs.get("draw_cutting_guides", draw_cut_guides)
    effective_passwords = passwords or kwargs.get("passwords_by_file")

    if not effective_paths or not effective_output:
        return None

    canon_mode = normalize_imposition_mode(mode)

    # Map file path to row data if student_mappings is provided
    path_to_row: dict[str, dict[str, str]] = {}
    if student_mappings:
        for row, path in student_mappings:
            path_to_row[os.path.abspath(path)] = row
            path_to_row[path] = row

    # Configure grid layout parameters
    if canon_mode == MODE_2UP:
        sheet_w = A4_HEIGHT  # 842.0 (Landscape A4)
        sheet_h = A4_WIDTH   # 595.0
        cols = 2
        rows = 1
        cell_w = sheet_w / 2.0  # 421.0
        cell_h = sheet_h        # 595.0
        margin_x = 0.0
        margin_y = 0.0
        inner_pad = 4.0
    elif canon_mode == MODE_8UP:
        sheet_w = A4_WIDTH   # 595.0 (Portrait A4)
        sheet_h = A4_HEIGHT  # 842.0
        cols = 2
        rows = 4
        cell_w = 260.0
        cell_h = 180.0
        margin_x = (sheet_w - cols * cell_w) / 2.0  # 37.5
        margin_y = (sheet_h - rows * cell_h) / 2.0  # 61.0
        inner_pad = 2.0
    else:  # MODE_10UP
        sheet_w = A4_WIDTH   # 595.0 (Portrait A4)
        sheet_h = A4_HEIGHT  # 842.0
        cols = 2
        rows = 5
        cell_w = 242.0       # Standard CR80 Card width in pt
        cell_h = 153.0       # Standard CR80 Card height in pt
        margin_x = (sheet_w - cols * cell_w) / 2.0  # 55.5
        margin_y = (sheet_h - rows * cell_h) / 2.0  # 38.5
        inner_pad = 2.0

    capacity_per_sheet = cols * rows

    # Collect source items: list of (pdf_path, page_idx, row_dict)
    source_items: list[tuple[str, int, dict[str, str] | None]] = []
    for p in effective_paths:
        if not os.path.exists(p):
            continue
        try:
            doc_chk = pymupdf.open(p)
            r_data = path_to_row.get(p) or path_to_row.get(os.path.abspath(p))
            _authenticate_doc_if_needed(doc_chk, p, r_data, password_col, effective_passwords)
            p_count = doc_chk.page_count
            doc_chk.close()
            for p_idx in range(p_count):
                source_items.append((p, p_idx, r_data))
        except Exception as e:
            print(f"[DEBUG IMPOSITION] Skipping invalid file {p}: {e}")

    if not source_items:
        return None

    dest_doc = pymupdf.open()
    current_sheet: pymupdf.Page | None = None
    open_docs_cache: dict[str, pymupdf.Document] = {}

    try:
        for idx, (p_path, p_idx, r_data) in enumerate(source_items):
            slot_in_sheet = idx % capacity_per_sheet
            if slot_in_sheet == 0:
                # Start new master sheet
                current_sheet = dest_doc.new_page(width=sheet_w, height=sheet_h)
                if effective_guides:
                    _draw_cutting_guides(
                        current_sheet,
                        canon_mode,
                        sheet_w,
                        sheet_h,
                        margin_x,
                        margin_y,
                        cell_w,
                        cell_h,
                        cols,
                        rows,
                    )

            # Determine row and col within sheet
            col_idx = slot_in_sheet % cols
            row_idx = slot_in_sheet // cols

            slot_x0 = margin_x + col_idx * cell_w + inner_pad
            slot_y0 = margin_y + row_idx * cell_h + inner_pad
            slot_x1 = margin_x + (col_idx + 1) * cell_w - inner_pad
            slot_y1 = margin_y + (row_idx + 1) * cell_h - inner_pad
            target_rect = pymupdf.Rect(slot_x0, slot_y0, slot_x1, slot_y1)

            # Open or reuse cached source document
            if p_path not in open_docs_cache:
                src_doc = pymupdf.open(p_path)
                _authenticate_doc_if_needed(src_doc, p_path, r_data, password_col, effective_passwords)
                open_docs_cache[p_path] = src_doc
            else:
                src_doc = open_docs_cache[p_path]

            if current_sheet is not None:
                current_sheet.show_pdf_page(target_rect, src_doc, p_idx, keep_proportion=True)

        # Save imposed PDF
        os.makedirs(os.path.dirname(effective_output) or ".", exist_ok=True)
        dest_doc.set_metadata({
            "title": f"Print Ready Imposed ({canon_mode.upper()})",
            "producer": "TeacherResultSoftware Imposition Engine",
        })
        dest_doc.save(effective_output, garbage=4, deflate=True)
    finally:
        for d in open_docs_cache.values():
            try:
                d.close()
            except Exception:
                pass
        dest_doc.close()

    return os.path.abspath(effective_output)
